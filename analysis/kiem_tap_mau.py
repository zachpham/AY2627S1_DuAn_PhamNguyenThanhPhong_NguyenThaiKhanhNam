"""Check a PHMN output file against the database, without going through SPMF.

Two checks, both computed straight from the data file:

  1. Every reported pattern: its utility, support, minPer, maxPer and avgPer are recomputed and
     must equal the five numbers SPMF printed, and the pattern must meet all five thresholds.
  2. Completeness up to two items: every 1-itemset and every co-occurring 2-itemset of the
     database is evaluated, and each one that meets the thresholds must be in the output. A
     2-itemset can only qualify if both of its items pass maxPer and the support bound derived
     from maxAvg, because both measures only get worse on a superset; items failing either are
     left out of the pair count, which keeps it small without changing its answer.

The periodicity follows the code of SPMF (Section 5.11 of the report): positions run from 1 to |D|,
maxPer counts the gap before the first and after the last occurrence, minPer counts only the gaps
between occurrences (and is 2147483647 for a single occurrence), avgPer = |D| / (support + 1).

Usage, from the project root:
    py -I analysis/kiem_tap_mau.py <database> <output file> minUtil minPer maxPer minAvg maxAvg

Prints one summary line and exits with status 1 if any check fails.
"""

import sys
from collections import defaultdict

NO_GAP = 2147483647                                          # minPer of a single occurrence


def readDatabase(path):
    """Read an SPMF utility database.

    :param path: file in the format items:TU:utilities
    :return: list of dicts item -> utility, transaction k at index k-1
    """
    database = []
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if not line.strip() or line[0] in '#%@':
                continue
            items, _, utilities = line.strip().split(':')
            database.append(dict(zip(items.split(), map(int, utilities.split()))))
    return database


def readPatterns(path):
    """Read a PHMN output file.

    :param path: one pattern per line, items then #UTIL #SUP #MINPER #MAXPER #AVGPER
    :return: dict frozenset of items -> tuple (util, sup, minPer, maxPer, avgPer)
    """
    patterns = {}
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if not line.strip():
                continue
            head, rest = line.split(' #UTIL: ')
            fields = rest.split()
            util, sup = int(fields[0]), int(fields[2])
            min_per, max_per, avg_per = int(fields[4]), int(fields[6]), float(fields[8])
            patterns[frozenset(head.split())] = (util, sup, min_per, max_per, avg_per)
    return patterns


def measure(positions, size):
    """Compute support, minPer, maxPer and avgPer from the positions of an itemset.

    :param positions: increasing list of 1-based transaction positions
    :param size: |D|
    :return: tuple (sup, minPer, maxPer, avgPer)
    """
    sup = len(positions)
    inner = [b - a for a, b in zip(positions, positions[1:])]
    min_per = min(inner) if inner else NO_GAP
    max_per = max([positions[0], size - positions[-1]] + inner)
    return sup, min_per, max_per, size / (sup + 1)


def qualifies(util, sup, min_per, max_per, avg_per, thresholds):
    """Apply the five output conditions of AlgoPHMN.

    :param util: utility of the itemset
    :param sup: support (unused, kept for symmetry with the printed fields)
    :param min_per: minimum periodicity
    :param max_per: maximum periodicity
    :param avg_per: average periodicity
    :param thresholds: tuple (minUtil, minPer, maxPer, minAvg, maxAvg)
    :return: True when the itemset is a periodic high-utility itemset
    """
    min_util, min_per_t, max_per_t, min_avg_t, max_avg_t = thresholds
    return (util >= min_util and min_avg_t <= avg_per <= max_avg_t
            and min_per >= min_per_t and max_per <= max_per_t)


def main():
    """Run both checks and print the summary.

    :return: nothing; exits 1 on any failure
    """
    sys.stdout.reconfigure(encoding='utf-8')
    database = readDatabase(sys.argv[1])
    reported = readPatterns(sys.argv[2])
    thresholds = tuple(int(x) for x in sys.argv[3:8])
    size = len(database)

    # Step 1: positions of every item, used by both checks
    positions = defaultdict(list)
    for k, transaction in enumerate(database, 1):
        for item in transaction:
            positions[item].append(k)

    # Step 2: recompute every reported pattern from the transactions holding all its items
    wrong_value = 0
    not_qualifying = 0
    for itemset, printed in reported.items():
        first = min(itemset, key=lambda i: len(positions[i]))
        holding = [k for k in positions[first] if all(i in database[k - 1] for i in itemset)]
        util = sum(sum(database[k - 1][i] for i in itemset) for k in holding)
        sup, min_per, max_per, avg_per = measure(holding, size)
        if (util, sup, min_per, max_per) != printed[:4] or abs(avg_per - printed[4]) > 1e-9:
            wrong_value += 1
            if wrong_value <= 5:
                print('  value differs:', sorted(itemset), printed, (util, sup, min_per, max_per, avg_per))
        if not qualifies(util, sup, min_per, max_per, avg_per, thresholds):
            not_qualifying += 1

    # Step 3: every qualifying 1-itemset
    expected = set()
    support_bound = size / thresholds[4] - 1                 # same bound as supportPruningThreshold
    usable = set()
    for item, where in positions.items():
        sup, min_per, max_per, avg_per = measure(where, size)
        util = sum(database[k - 1][item] for k in where)
        if qualifies(util, sup, min_per, max_per, avg_per, thresholds):
            expected.add(frozenset([item]))
        if max_per <= thresholds[2] and sup >= support_bound:
            usable.add(item)

    # Step 4: every qualifying 2-itemset among the usable items
    pair_util = defaultdict(int)
    pair_positions = defaultdict(list)
    for k, transaction in enumerate(database, 1):
        items = sorted(i for i in transaction if i in usable)
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                key = (items[a], items[b])
                pair_util[key] += transaction[items[a]] + transaction[items[b]]
                pair_positions[key].append(k)
    for key, where in pair_positions.items():
        sup, min_per, max_per, avg_per = measure(where, size)
        if qualifies(pair_util[key], sup, min_per, max_per, avg_per, thresholds):
            expected.add(frozenset(key))

    # Step 5: compare with the output restricted to one and two items
    reported_small = set(p for p in reported if len(p) <= 2)
    missing = expected - reported_small
    spurious = reported_small - expected
    lengths = defaultdict(int)
    for p in reported:
        lengths[len(p)] += 1
    print('%s: %d patterns %s | values: %d wrong, %d not qualifying | length<=2: expected %d, '
          'missing %d, spurious %d (pairs examined %d)'
          % (sys.argv[2], len(reported), dict(sorted(lengths.items())), wrong_value,
             not_qualifying, len(expected), len(missing), len(spurious), len(pair_positions)))
    for p in sorted(missing, key=sorted)[:5]:
        print('  missing:', sorted(p))
    if wrong_value or not_qualifying or missing or spurious:
        sys.exit(1)


if __name__ == '__main__':
    main()
