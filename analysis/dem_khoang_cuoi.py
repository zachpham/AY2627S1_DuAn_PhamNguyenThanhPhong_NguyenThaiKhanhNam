"""Count the reported patterns whose last gap would be zero under Definition 1 of F0.

Definition 1 of F0 takes minPer(X) over PS(X), which includes the gap |D| - tid_m from the last
occurrence of X to the end of the database, with transactions numbered from 1. An itemset that
occurs in the last transaction therefore has a last gap of 0, and Definition 1 read literally
would reject it even at minPer = 1. The SPMF implementation ignores that gap. This script counts,
for a few output files of the corrected build, how many patterns are contained in the last
transaction of their database, i.e. how many the literal definition would reject at minPer = 1.
The first gap is tid_1 - 0 >= 1 and can never be zero, so it is not counted.

Usage, from the project root:
    py -I analysis/dem_khoang_cuoi.py > output/runs/dem_khoang_cuoi.log
"""

import csv
import os
import sys

# (dataset, output file of the corrected build) - every run uses minPer = 1
CASES = [
    ('chess', 'chess_f_80000'),
    ('chess', 'chess_f_150000'),
    ('pumsb', 'pumsb_f_5800000'),
    ('pumsb', 'pumsb_f_5600000'),
    ('pumsb', 'pumsb_f_5400000'),
    ('accidents', 'accidents_f_19000000_minavg1'),
    ('mushroom', 'e8_a_mushroom_100000_ma100_r1'),
]


def readLastTransaction(path):
    """Return the item set of the last non-empty transaction of a database file.

    :param path: path of a database in SPMF format, items:transaction utility:utilities
    :return: set of item strings
    """
    last_items = None
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if line.strip() and not line.startswith(('#', '%', '@')):
                last_items = set(line.split(':')[0].split())
    return last_items


def findOutputFile(name):
    """Return the path of an output file, or of its representative when only that one exists.

    The repository keeps one representative of each distinct output content and lists every
    original name in output/MANIFEST_output.csv, so a file such as pumsb_f_5800000.txt exists in
    the project folder but, in a fresh clone, only as its byte-identical representative.

    :param name: file name inside output/, with extension
    :return: path of a file with the same content
    """
    path = os.path.join('output', name)
    if os.path.exists(path):
        return path
    with open(os.path.join('output', 'MANIFEST_output.csv'), encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row['file'] == name:
                return os.path.join('output', row['dai_dien'])
    sys.exit('neither %s nor a representative of it was found' % path)


def countPatterns(path, last_items):
    """Count the patterns of an output file and those contained in the last transaction.

    :param path: output file of SPMF, one pattern per line followed by #UTIL
    :param last_items: item set of the last transaction
    :return: (number of patterns, number contained in the last transaction)
    """
    total = in_last = 0
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if '#UTIL' not in line:
                continue
            itemset = set(line.split('#UTIL')[0].split())
            total += 1
            if itemset <= last_items:
                in_last += 1
    return total, in_last


def main():
    """Print one line per output file."""
    sys.stdout.reconfigure(encoding='utf-8')
    print('%-32s %8s %18s' % ('output file', 'patterns', 'in last transaction'))
    for dataset, name in CASES:
        last_items = readLastTransaction(os.path.join('data', dataset + '_negative.txt'))
        total, in_last = countPatterns(findOutputFile(name + '.txt'), last_items)
        print('%-32s %8d %18d' % (name, total, in_last))


if __name__ == '__main__':
    main()
