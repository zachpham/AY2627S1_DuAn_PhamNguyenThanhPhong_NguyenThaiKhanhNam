"""Digitise the PHMN curve of Figure 5 of F0 from the image Fig 5.png, panels (a) and (c),
and panel (d) as a check of the method against two values F0 states in its text.

The value of each point is read from pixel positions, not by eye: the y-axis ticks are located
on the left spine of the panel, a linear map from pixel row to seconds is fitted through them,
and the centre of every blue square marker is converted with that map. The value of one pixel is printed
next to each reading: the centre of a square is located to within about one pixel, so that is the
reading uncertainty. The image itself is a raster copy of the published figure, so a difference
of a few seconds from the value the authors measured is expected.

Usage, from the project root:
    py -I analysis/so_hoa_hinh5.py "Fig 5.png"
"""

import os
import sys

from PIL import Image

# Size in pixels of the copy of Figure 5 that the panel boxes below were measured on.
EXPECTED_SIZE = (1137, 760)

# Panel box (left, top, right, bottom) in pixels, the y tick values from bottom to top, the axis
# multiplier, the x values of the five points and the legend box, for the two panels whose
# datasets were obtained.
PANELS = {
    "a_accidents": ((95, 25, 545, 320), [0.5, 1.0, 1.5, 2.0, 2.5, 3.0], 100.0,
                    [13_000_000, 15_000_000, 17_000_000, 18_000_000, 19_000_000],
                    (425, 30, 545, 90)),
    "c_pumsb": ((95, 385, 545, 680), [0, 1, 2, 3, 4, 5, 6, 7, 8], 100.0,
                [5_000_000, 5_200_000, 5_400_000, 5_600_000, 5_800_000], None),
    # Panel (d) is read only to check the method: F0 states 234 s and 60 s for PHMN on
    # connect_negative in the prose of its Section 5.2, at the first and last levels.
    "d_connect_check": ((640, 385, 1090, 680), [0.5, 1.0, 1.5, 2.0], 100.0,
                        [16_000_000, 16_250_000, 16_500_000, 16_750_000, 17_000_000], None),
}


def is_dark(pixel):
    """Tell whether a pixel belongs to the grey axis drawing (the spines are anti-aliased grey).

    :param pixel: an RGBA tuple
    :return: True for a grey pixel darker than 170 on every channel
    """
    return max(pixel[:3]) < 170 and abs(pixel[0] - pixel[2]) < 30


def is_blue(pixel):
    """Tell whether a pixel belongs to the blue PHMN curve or its markers.

    :param pixel: an RGBA tuple
    :return: True for a strongly blue pixel
    """
    return pixel[2] > 180 and pixel[0] < 80 and pixel[1] < 80


def in_box(point, box):
    """Tell whether a point lies inside a box.

    :param point: (x, y) in pixels
    :param box: (left, top, right, bottom) in pixels, or None for no box
    :return: True when the point is inside the box
    """
    return box is not None and box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def digitise(image, box, tick_values, scale, x_values, legend):
    """Read the five PHMN points of one panel.

    :param image: the loaded figure
    :param box: (left, top, right, bottom) of the panel in pixels
    :param tick_values: the y tick labels from bottom to top, in units of scale
    :param scale: the multiplier printed above the axis (1e2 means 100)
    :param x_values: the minUtil value of each point, from left to right
    :param legend: box of the legend, whose blue sample square must be ignored, or None
    :return: list of (minUtil, seconds, seconds per pixel)
    """
    left, top, right, bottom = box
    # Step 1: the left spine is the first column holding a long unbroken grey run
    def longest_run(x):
        best = current = 0
        for y in range(top, bottom):
            current = current + 1 if is_dark(image.getpixel((x, y))) else 0
            best = max(best, current)
        return best
    spine = next(x for x in range(left, left + 80) if longest_run(x) > 200)
    # Step 2: a tick is a short dark mark just left of the spine; keep the centre row of each run
    rows = [y for y in range(top, bottom) if is_dark(image.getpixel((spine - 3, y)))]
    ticks, run = [], [rows[0]]
    for y in rows[1:]:
        if y == run[-1] + 1:
            run.append(y)
        else:
            ticks.append(sum(run) / len(run))
            run = [y]
    ticks.append(sum(run) / len(run))
    ticks.sort(reverse=True)                                  # bottom tick first
    if len(ticks) != len(tick_values):
        raise SystemExit("found %d ticks, expected %d" % (len(ticks), len(tick_values)))
    # Step 3: least-squares line from pixel row to value
    n = len(ticks)
    mean_r = sum(ticks) / n
    mean_v = sum(tick_values) / n
    slope = (sum((r - mean_r) * (v - mean_v) for r, v in zip(ticks, tick_values))
             / sum((r - mean_r) ** 2 for r in ticks))
    # Step 4: blue marker pixels, outside the legend box, grouped into runs of columns
    blue = [(x, y) for x in range(spine + 2, right) for y in range(top, bottom)
            if is_blue(image.getpixel((x, y))) and not in_box((x, y), legend)]
    columns = {}
    for x, y in blue:
        columns.setdefault(x, []).append(y)
    # a marker column has many more blue pixels than a column crossed only by the line
    thick = sorted(x for x, ys in columns.items() if len(ys) >= 6)
    groups, current = [], [thick[0]]
    for x in thick[1:]:
        if x <= current[-1] + 5:                              # a red star may hide some columns
            current.append(x)
        else:
            groups.append(current)
            current = [x]
    groups.append(current)
    groups = [g for g in groups if len(g) >= 4]
    if len(groups) != len(x_values):
        raise SystemExit("found %d markers, expected %d" % (len(groups), len(x_values)))
    # Step 5: the rows of a square are the rows that are blue in at least three of its columns
    result = []
    per_pixel = abs(slope) * scale
    for x_value, group in zip(x_values, groups):
        counts = {}
        for x in group:
            for y in columns[x]:
                counts[y] = counts.get(y, 0) + 1
        rows_of_square = sorted(y for y, c in counts.items() if c >= 3)
        centre = (rows_of_square[0] + rows_of_square[-1]) / 2
        value = (mean_v + slope * (centre - mean_r)) * scale
        result.append((x_value, value, per_pixel))
    return result


def main():
    """Print the digitised points of panels (a), (c) and (d).

    :return: nothing
    """
    # Step 0: the figure belongs to the publisher and is not in the repository
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        raise SystemExit("figure not found. Save a 1137 x 760 screenshot of Figure 5 of F0 as "
                         "\"Fig 5.png\" in the project root, then run again (README, section 5)")
    image = Image.open(sys.argv[1]).convert("RGBA")
    # Step 1: the panel boxes above are pixel positions in a 1137 x 760 copy of the figure
    if image.size != EXPECTED_SIZE:
        raise SystemExit("image is %d x %d, expected %d x %d: adjust PANELS before reading it"
                         % (image.size + EXPECTED_SIZE))
    for name, (box, ticks, scale, xs, legend) in PANELS.items():
        print("panel", name)
        for x_value, seconds, per_pixel in digitise(image, box, ticks, scale, xs, legend):
            print("  minUtil %11s  %7.1f s  (one pixel = %.1f s)"
                  % ("{:,}".format(x_value), seconds, per_pixel))


if __name__ == "__main__":
    main()
