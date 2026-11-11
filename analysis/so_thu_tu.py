"""Compare the three item orders of the corrected build, from the rows of output/do_luong.csv.

Reads the rows written by tools/chay_thu_tu.ps1 (ghi_chu "thi nghiem thu tu muc"), keeps the
latest row of each (configuration, order), and prints one line per configuration and order:
patterns, candidates, CPU time, peak memory, and whether the pattern set is identical to the one
of the TWU order. SPMF prints the items of a pattern in processing order, so two orders write the
same pattern as different lines; every pattern is therefore normalised (items sorted) before the
sets are compared. The utility, support and periods must match as well.

In a fresh clone of the repository a pattern file may exist only as its byte-identical
representative listed in output/MANIFEST_output.csv; the representative is then read instead.

A run whose elapsed time is more than 1.5 times its CPU time was interrupted by the machine
sleeping, and is flagged; compare CPU times, never elapsed times.

Usage, from the project root:
    py -I analysis/so_thu_tu.py > output/runs/so_thu_tu.log

An order stopped at the deadline of tools/chay_thu_tu.ps1 -han_chot has no row; its log is found
by name and the CPU time it used before the stop is printed as a lower bound.

Exits with status 1 if an order changes the pattern set of a configuration.
"""

import csv
import glob
import hashlib
import os
import sys

NOTE = 'thi nghiem thu tu muc'
TAGS = {'da_sua': 'f', 'def7': 'd7', 'duong_truoc': 'dt'}                   # as chay_do_luong.ps1
ORDERS = [('da_sua', 'TWU only (SPMF)'), ('def7', 'negative first (Def. 7)'),
          ('duong_truoc', 'positive first (FHN)')]


def findOutputFile(path):
    """Return the path of an output file, or of its representative when only that one exists.

    :param path: path as written in the file_mau column, e.g. output/chess_f_150000.txt
    :return: path of a file with the same content
    """
    if os.path.exists(path):
        return path
    name = os.path.basename(path)
    with open(os.path.join('output', 'MANIFEST_output.csv'), encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row['file'] == name:
                return os.path.join('output', row['dai_dien'])
    sys.exit('neither %s nor a representative of it was found' % path)


def normalisedDigest(path):
    """Hash the pattern set of an output file, independent of the order of items and lines.

    :param path: output file of SPMF
    :return: (number of patterns, hex digest)
    """
    lines = []
    with open(findOutputFile(path), encoding='utf-8') as handle:
        for line in handle:
            if '#UTIL' not in line:
                continue
            items, rest = line.split('#UTIL', 1)
            ordered = ' '.join(str(i) for i in sorted(int(x) for x in items.split()))
            lines.append(ordered + ' #UTIL' + rest.rstrip())
    lines.sort()
    return len(lines), hashlib.md5('\n'.join(lines).encode('utf-8')).hexdigest()


def stoppedNote(dataset, min_util, order):
    """Find the deadline note of a run that was stopped before it finished.

    :param dataset: dataset name, e.g. pumsb
    :param min_util: the utility threshold
    :param order: a key of TAGS
    :return: the note written by chay_do_luong.ps1, or None
    """
    pattern = os.path.join('output', 'runs', '%s_%s_%d*.log' % (dataset, TAGS[order], min_util))
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if line.startswith('STOPPED AT DEADLINE'):
                    return line.strip()
    return None


def readRows():
    """Keep the latest row of each (configuration, order) of the experiment.

    :return: dict {(dataset, minUtil, thresholds): {order: row}}
    """
    table = {}
    with open(os.path.join('output', 'do_luong.csv'), encoding='utf-8', errors='replace') as handle:
        for row in csv.DictReader(handle):
            if row['ghi_chu'] != NOTE:
                continue
            key = (row['dataset'], int(row['minUtil']),
                   '-'.join(row[k] for k in ('minPer', 'maxPer', 'minAvg', 'maxAvg')))
            table.setdefault(key, {})[row['ban']] = row               # later rows replace earlier
    return table


def main():
    """Print the comparison table."""
    sys.stdout.reconfigure(encoding='utf-8')
    table = readRows()
    changed = False
    print('%-10s %11s  %-24s %8s %12s %8s %10s %8s  %s'
          % ('dataset', 'minUtil', 'order', 'patterns', 'candidates', 'x TWU', 'CPU s', 'MB',
             'same set as TWU'))
    for key in sorted(table):
        runs = table[key]
        if 'da_sua' not in runs:
            continue
        base_candidates = int(runs['da_sua']['ung_vien'])
        base_digest = normalisedDigest(runs['da_sua']['file_mau'])[1]
        for order, label in ORDERS:
            if order not in runs:
                note = stoppedNote(key[0], key[1], order)
                print('%-10s %11d  %-24s  %s' % (key[0], key[1], label, note or 'not run'))
                continue
            row = runs[order]
            count, digest = normalisedDigest(row['file_mau'])
            same = digest == base_digest
            changed = changed or not same
            cpu = float(row['cpu_giay'] or 0)
            wall = float(row['thoi_gian_ms']) / 1000.0
            flag = '  SLEPT: elapsed %.0f s' % wall if wall > 60 and wall > 1.5 * cpu else ''
            print('%-10s %11d  %-24s %8d %12s %8.2f %10.1f %8.0f  %s%s'
                  % (key[0], key[1], label, count, format(int(row['ung_vien']), ','),
                     int(row['ung_vien']) / base_candidates, cpu, float(row['bo_nho_mb']),
                     'yes' if same else 'NO', flag))
    if changed:
        sys.exit(1)


if __name__ == '__main__':
    main()
