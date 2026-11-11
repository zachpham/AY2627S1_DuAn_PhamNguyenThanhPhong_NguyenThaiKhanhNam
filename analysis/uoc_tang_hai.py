"""Compare the memory a depth-first and a breadth-first search of PHMN hold at level 2.

AlgoPHMN searches depth-first. For each root item X it builds the utility-lists of the pairs
(X, Y), for every Y after X in the item order, recurses into them, and drops them before moving
to the next X. At level 2 it therefore holds the pair lists of one root item at a time. A
breadth-first search builds every level from the previous one, so at level 2 it holds the pair
lists of all root items at once.

A utility-list holds one element per transaction that contains the itemset, so the size of the
list of a pair is the support of the pair. This script counts, for the items that enter the root
of the search (TWU, maxAvg and maxPer tests, as analysis/dem_muc_goc.py), the total number of
elements of all pair lists, and the largest number held at once by the depth-first order. Both
counts are taken before any pruning, so both are upper bounds of what each search would build.

Usage, from the project root:
    py -I analysis/uoc_tang_hai.py data/accidents_negative.txt 19000000 2000 1000
    py -I analysis/uoc_tang_hai.py data/pumsb_negative.txt 5800000 3000 2000
"""

import sys

# Approximate size in bytes of one element of a utility-list in a 64-bit JVM with compressed
# references: an object of four int fields (12 header + 16, padded to 32) plus the reference
# the ArrayList keeps to it (4).
BYTES_PER_ELEMENT = 36


def readDatabase(path):
    """Read the database once and keep, per item, its TWU, support, largest period and tid set.

    :param path: database in SPMF utility format
    :return: (transaction count, twu, support, largest period, bitmask of transactions) per item
    """
    twu, support, last_seen, largest, mask = {}, {}, {}, {}, {}
    tid = 0
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line[0] in "#%@":
                continue
            tid += 1
            fields = line.split(":")
            positive_total = int(fields[1])
            for item in fields[0].split():
                twu[item] = twu.get(item, 0) + positive_total
                support[item] = support.get(item, 0) + 1
                largest[item] = max(largest.get(item, 0), tid - last_seen.get(item, 0))
                last_seen[item] = tid
                mask[item] = mask.get(item, 0) | (1 << tid)
    # step: the gap from the last occurrence to the end of the database also counts
    for item in last_seen:
        largest[item] = max(largest[item], tid - last_seen[item])
    return tid, twu, support, largest, mask


def main():
    """Print the level-2 element counts of both traversal orders.

    :return: nothing
    """
    # Step 1: read the arguments and the database
    path = sys.argv[1]
    min_util, max_per, max_avg = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    size, twu, support, largest, mask = readDatabase(path)

    # Step 2: the root items, in the order of compareItems: ascending TWU, then item number
    threshold = size / max_avg - 1
    root = [i for i in twu
            if twu[i] >= min_util and support[i] >= threshold and largest[i] <= max_per]
    root.sort(key=lambda i: (twu[i], int(i)))

    # Step 3: support of every pair = size of its utility-list
    total = 0
    largest_at_once = 0
    widest_item = None
    for position, first in enumerate(root):
        held = 0
        for second in root[position + 1:]:
            held += bin(mask[first] & mask[second]).count("1")
        total += held
        if held > largest_at_once:
            largest_at_once, widest_item = held, first

    # Step 4: report element counts and an approximate size in megabytes
    pairs = len(root) * (len(root) - 1) // 2
    print("database                          :", path)
    print("root items                        :", len(root))
    print("pairs at level 2                  :", pairs)
    print("elements, all pairs (breadth-first): %d  ~%.0f MB" % (total, total * BYTES_PER_ELEMENT / 2**20))
    print("elements, one root item at a time  : %d  ~%.0f MB  (largest, item %s)"
          % (largest_at_once, largest_at_once * BYTES_PER_ELEMENT / 2**20, widest_item))
    print("ratio                              : %.1f" % (total / largest_at_once))


if __name__ == "__main__":
    main()
