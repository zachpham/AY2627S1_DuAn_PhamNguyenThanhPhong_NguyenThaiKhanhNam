# -*- coding: utf-8 -*-
"""Builds the manifest of the pattern files under output/.

The experiments produced 140 pattern files, but only 15 of them have distinct contents: the
repeated runs of E8 write byte-identical output, which is the result E8 set out to measure, and
the runs of the published build write empty files, which is the evidence that it finds nothing.
Committing 140 files would therefore add 168 MB of exact duplicates to the repository.

This script keeps one representative per distinct content and records every one of the 140
original file names in a manifest, together with its size, its MD5 and the representative that
carries its content. Nothing is lost: the manifest proves which file equals which, and the
representative supplies the bytes.

Run from the project root:

    py -I tools/manifest_output.py

It writes output/MANIFEST_output.csv and prints the .gitignore exception lines for the
representatives, so that .gitignore and this script can never drift apart silently.
"""

import csv
import hashlib
import os
import sys

THU_MUC = 'output'                                            # where the pattern files live
MANIFEST = os.path.join(THU_MUC, 'MANIFEST_output.csv')       # the manifest this script writes


def bam_file(duong_dan):
    """Returns the MD5 of a file, read in blocks so a 7 MB file costs no more memory than a small one."""
    h = hashlib.md5()
    with open(duong_dan, 'rb') as f:
        for khoi in iter(lambda: f.read(1 << 20), b''):
            h.update(khoi)
    return h.hexdigest()


def main():
    if not os.path.isdir(THU_MUC):
        print('Khong thay thu muc %s. Chay script tu thu muc goc cua du an.' % THU_MUC)
        return 1

    ten_files = sorted(t for t in os.listdir(THU_MUC)
                       if t.endswith('.txt') and os.path.isfile(os.path.join(THU_MUC, t)))
    if not ten_files:
        print('Khong co file .txt nao trong %s.' % THU_MUC)
        return 1

    # Hash every file once, then group the names by content.
    theo_bam = {}                                             # md5 -> list of names, already sorted
    kich_thuoc = {}                                           # name -> size in bytes
    for ten in ten_files:
        duong_dan = os.path.join(THU_MUC, ten)
        kich_thuoc[ten] = os.path.getsize(duong_dan)
        theo_bam.setdefault(bam_file(duong_dan), []).append(ten)

    # The representative of each group is the first name alphabetically, so the choice is
    # reproducible and does not depend on the order the filesystem happened to list the folder.
    dai_dien = {bam: nhom[0] for bam, nhom in theo_bam.items()}

    with open(MANIFEST, 'w', newline='', encoding='utf-8') as f:
        ghi = csv.writer(f)
        ghi.writerow(['file', 'bytes', 'md5', 'dai_dien', 'trong_repo'])
        for ten in ten_files:
            bam = next(b for b, nhom in theo_bam.items() if ten in nhom)
            ghi.writerow([ten, kich_thuoc[ten], bam, dai_dien[bam],
                          'yes' if dai_dien[bam] == ten else 'no'])

    tong = sum(kich_thuoc.values())
    giu = sum(kich_thuoc[t] for t in dai_dien.values())
    print('%d file, %d noi dung khac nhau.' % (len(ten_files), len(theo_bam)))
    print('Tong %.1f MB, giu lai %.1f MB (%.1f%%).'
          % (tong / 1048576.0, giu / 1048576.0, 100.0 * giu / tong))
    print('Da ghi %s' % MANIFEST)
    print()
    print('Dan nhung dong nay vao .gitignore, ngay sau dong "output/*.txt":')
    for ten in sorted(dai_dien.values()):
        print('!output/%s' % ten)
    return 0


if __name__ == '__main__':
    sys.exit(main())
