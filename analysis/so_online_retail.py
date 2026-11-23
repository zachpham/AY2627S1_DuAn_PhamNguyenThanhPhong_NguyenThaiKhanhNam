"""Summarise and check the real-data case study on online_retail_negative (Section 7.12).

Reads the rows of output/do_luong.csv whose ghi_chu is "online retail" (written by
tools/chay_online_retail.ps1) and, for every configuration:

  * checks every output file with analysis/kiem_tap_mau.py (values recomputed from the data,
    completeness of all 1- and 2-itemsets);
  * compares the pattern sets of the four builds with the patched build;
  * prints candidates and CPU seconds of each build.

Then it lists, with product names, the patterns of the weekly setting at 5,000,000 pence, the
patterns the published build misses, and how many negative items survive the periodicity filters.

Usage, from the project root:
    py -I analysis/so_online_retail.py > output/runs/so_online_retail.log
"""

import csv
import importlib.util
import os
import sys
from collections import defaultdict

DATABASE = 'data/online_retail_negative.txt'
ITEMS = 'data/online_retail_items.csv'
BUILDS = ['cong_bo', 'da_sua', 'def7', 'duong_truoc']


def loadChecker():
    """Load analysis/kiem_tap_mau.py as a module; -I keeps the script folder off sys.path.

    :return: the module object
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kiem_tap_mau.py')
    spec = importlib.util.spec_from_file_location('kiem_tap_mau', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def outputPath(name):
    """Return an output file, or its byte-identical representative listed in the manifest.

    :param name: path as written in the file_mau column
    :return: path of a file with the same content
    """
    name = name.replace('\\', '/')
    if os.path.exists(name):
        return name
    with open('output/MANIFEST_output.csv', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if 'output/' + row['file'] == name:
                return 'output/' + row['dai_dien']
    sys.exit('neither %s nor a representative of it was found' % name)


def checkFile(checker, database, positions, path, thresholds):
    """Run the two checks of kiem_tap_mau on one output file.

    :param checker: the kiem_tap_mau module
    :param database: list of dicts item -> utility
    :param positions: dict item -> list of positions
    :param path: output file
    :param thresholds: tuple (minUtil, minPer, maxPer, minAvg, maxAvg)
    :return: tuple (patterns dict, wrong values, missing up to 2 items, spurious up to 2 items)
    """
    reported = checker.readPatterns(path)
    size = len(database)
    wrong = 0
    for itemset, printed in reported.items():
        first = min(itemset, key=lambda i: len(positions[i]))
        holding = [k for k in positions[first] if all(i in database[k - 1] for i in itemset)]
        util = sum(sum(database[k - 1][i] for i in itemset) for k in holding)
        sup, min_per, max_per, avg_per = checker.measure(holding, size)
        if ((util, sup, min_per, max_per) != printed[:4] or abs(avg_per - printed[4]) > 1e-9
                or not checker.qualifies(util, sup, min_per, max_per, avg_per, thresholds)):
            wrong += 1
    expected = expectedSmall(checker, database, positions, thresholds)
    small = set(p for p in reported if len(p) <= 2)
    return reported, wrong, len(expected - small), len(small - expected)


EXPECTED_CACHE = {}


def expectedSmall(checker, database, positions, thresholds):
    """Every qualifying 1- and 2-itemset, cached per threshold tuple.

    :param checker: the kiem_tap_mau module
    :param database: list of dicts item -> utility
    :param positions: dict item -> list of positions
    :param thresholds: tuple (minUtil, minPer, maxPer, minAvg, maxAvg)
    :return: set of frozensets
    """
    if thresholds in EXPECTED_CACHE:
        return EXPECTED_CACHE[thresholds]
    size = len(database)
    expected = set()
    usable = set()
    for item, where in positions.items():
        sup, min_per, max_per, avg_per = checker.measure(where, size)
        util = sum(database[k - 1][item] for k in where)
        if checker.qualifies(util, sup, min_per, max_per, avg_per, thresholds):
            expected.add(frozenset([item]))
        if max_per <= thresholds[2] and sup >= size / thresholds[4] - 1:
            usable.add(item)
    pair_util = defaultdict(int)
    pair_positions = defaultdict(list)
    for k, transaction in enumerate(database, 1):
        items = sorted(i for i in transaction if i in usable)
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                pair_util[(items[a], items[b])] += transaction[items[a]] + transaction[items[b]]
                pair_positions[(items[a], items[b])].append(k)
    for key, where in pair_positions.items():
        sup, min_per, max_per, avg_per = checker.measure(where, size)
        if checker.qualifies(pair_util[key], sup, min_per, max_per, avg_per, thresholds):
            expected.add(frozenset(key))
    EXPECTED_CACHE[thresholds] = expected
    return expected


def main():
    """Print the case-study tables.

    :return: nothing; exits 1 if any check fails
    """
    sys.stdout.reconfigure(encoding='utf-8')
    checker = loadChecker()
    database = checker.readDatabase(DATABASE)
    positions = defaultdict(list)
    for k, transaction in enumerate(database, 1):
        for item in transaction:
            positions[item].append(k)
    with open(ITEMS, encoding='utf-8') as handle:
        names = {row['id']: (row['item'], row['description']) for row in csv.DictReader(handle)}
    negative = set(i for i, (item, _) in names.items() if item.startswith('NEG:'))

    # Step 1: group the rows of the case study by configuration
    with open('output/do_luong.csv', encoding='utf-8') as handle:
        rows = [r for r in csv.DictReader(handle) if r['ghi_chu'] == 'online retail']
    configs = defaultdict(dict)
    for r in rows:
        key = (int(r['maxPer']), int(r['maxAvg']), int(r['minUtil']))
        configs[key][r['ban']] = r

    # Step 2: one line per configuration
    failures = 0
    missed_by_published = {}
    print('|D| = %d, items = %d (negative %d)' % (len(database), len(names), len(negative)))
    print('maxPer maxAvg  minUtil | patterns o/f/d7/dt | same set as patched | candidates o/f/d7/dt'
          ' | CPU s o/f/d7/dt | check (wrong, missing<=2, spurious<=2)')
    for key in sorted(configs, key=lambda k: (k[0], -k[2])):
        thresholds = (key[2], 1, key[0], 1, key[1])
        found = {}
        checks = []
        for build in BUILDS:
            r = configs[key][build]
            patterns, wrong, missing, spurious = checkFile(checker, database, positions,
                                                           outputPath(r['file_mau']), thresholds)
            found[build] = patterns
            checks.append('%d,%d,%d' % (wrong, missing, spurious))
            # the published build is expected to miss patterns; the others must be complete
            if wrong or spurious or (missing and build != 'cong_bo'):
                failures += 1
        same = ['yes' if found[b] == found['da_sua'] else 'NO' for b in BUILDS]
        if found['cong_bo'] != found['da_sua']:
            missed_by_published[key] = set(found['da_sua']) - set(found['cong_bo'])
        print('%6d %6d %8d | %s | %s | %s | %s | %s'
              % (key[0], key[1], key[2],
                 '/'.join(str(len(found[b])) for b in BUILDS),
                 '/'.join(same),
                 '/'.join(configs[key][b]['ung_vien'] for b in BUILDS),
                 '/'.join(configs[key][b]['cpu_giay'] for b in BUILDS),
                 ' '.join(checks)))

    # Step 3: negative items that survive the periodicity filters, the reason the defect hides
    print()
    for max_per, max_avg in sorted(set((k[0], k[1]) for k in configs)):
        bound = len(database) / max_avg - 1
        kept = [i for i, where in positions.items()
                if checker.measure(where, len(database))[2] <= max_per and len(where) >= bound]
        print('maxPer %5d, maxAvg %5d: %4d items pass both periodicity filters, %4d of them negative'
              % (max_per, max_avg, len(kept), sum(1 for i in kept if i in negative)))

    # Step 4: what the published build misses
    print()
    for key, missed in sorted(missed_by_published.items()):
        lengths = defaultdict(int)
        for p in missed:
            lengths[len(p)] += 1
        print('published build misses %d patterns at maxPer %d, minUtil %d, by length %s'
              % (len(missed), key[0], key[2], dict(sorted(lengths.items()))))
        for p in sorted(missed, key=len)[:2]:
            print('   e.g.', ['%s %s' % names[i] for i in sorted(p, key=int)][:3])

    # Step 5: the weekly patterns at 5,000,000 pence, with product names
    print()
    print('weekly setting, minUtil 5,000,000 pence: the patterns, highest utility first')
    patterns = checker.readPatterns(outputPath(configs[(700, 350, 5000000)]['da_sua']['file_mau']))
    for itemset, (util, sup, min_per, max_per, avg_per) in sorted(patterns.items(),
                                                                  key=lambda x: -x[1][0]):
        print('  %-70s GBP %10.2f  sup %4d  maxPer %3d  avgPer %5.1f'
              % (' + '.join(names[i][1] for i in sorted(itemset, key=int))[:70],
                 util / 100.0, sup, max_per, avg_per))

    print()
    print('checks failed:', failures)
    if failures:
        sys.exit(1)


if __name__ == '__main__':
    main()
