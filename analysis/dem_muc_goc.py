"""Count the items that enter the root of the search tree of PHMN, the way AlgoPHMN selects them.

An item enters the root list when TWU >= minUtil, support >= |D| / maxAvg - 1 and its largest
period, first and last gap included, is at most maxPer (AlgoPHMN.java, first database scan and
the loop that builds listOfUtilityLists). The TWU-only count is printed as well, because the
two are easy to confuse.

Usage, from the project root:
    py -I analysis/dem_muc_goc.py data/accidents_negative.txt 19000000 2000 1000
    py -I analysis/dem_muc_goc.py data/pumsb_negative.txt 5800000 3000 2000
"""

import sys


def main():
    """Scan the database once and print the three counts.

    :return: nothing
    """
    # Step 1: read the arguments
    path, min_util, max_per, max_avg = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    twu, support, last_seen, largest = {}, {}, {}, {}
    tid = 0
    # Step 2: one pass, transaction identifiers start at 1 as in AlgoPHMN
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line[0] in "#%@":
                continue
            tid += 1
            items, positive_total = line.split(":")[0].split(), int(line.split(":")[1])
            for item in items:
                twu[item] = twu.get(item, 0) + positive_total
                support[item] = support.get(item, 0) + 1
                gap = tid - last_seen.get(item, 0)
                largest[item] = max(largest.get(item, 0), gap)
                last_seen[item] = tid
    # Step 3: the final gap, from the last occurrence to the end of the database
    for item in last_seen:
        largest[item] = max(largest[item], tid - last_seen[item])
    threshold = tid / max_avg - 1
    by_twu = [i for i in twu if twu[i] >= min_util]
    at_root = [i for i in by_twu if support[i] >= threshold and largest[i] <= max_per]
    print("transactions            :", tid)
    print("items                   :", len(twu))
    print("TWU >= minUtil          :", len(by_twu))
    print("support threshold       : %.2f" % threshold)
    print("enter the root list     :", len(at_root))
    print("removed by maxPer       :", sum(1 for i in by_twu if largest[i] > max_per))
    print("removed by maxAvg       :", sum(1 for i in by_twu if support[i] < threshold))


if __name__ == "__main__":
    main()
