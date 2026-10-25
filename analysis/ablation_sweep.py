"""Chay thi nghiem ablation tren nhieu co so du lieu co loi ich am.

Mot lan chay cua ClientAblationPHMN chi tra loi cho mot co so du lieu. Script nay lap lai
thi nghiem do tren 60 co so du lieu sinh ngau nhien (dung dung bo sinh cua
spmf_phmn_stress_test.py) roi tong hop lai, de tra loi hai cau hoi:

  1. Co cau hinh nao tim ra tap ket qua KHAC E0 khong? Neu co thi chien luoc bi tat
     dang lam mat mau, tuc la no khong chi la ky thuat tang toc.
  2. Moi chien luoc giam duoc bao nhieu phan tram so ung vien?

Cach chay (Windows, tu thu muc goc cua du an):
    python analysis\\ablation_sweep.py
"""

import os
import random
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spmf_phmn_stress_test import generate_database, write_database

SEEDS = range(1, 61)
JAR_PATH = os.path.join("tools", "spmf", "spmf.jar")
BUILD_DIR = "build"
SOURCE_PATH = os.path.join("src", "ClientAblationPHMN.java")
WORK_DIR = os.path.join("output", "ablation_tmp")

TABLE_ROW = re.compile(r"^\|\s*(E\d)\s*\|([^|]*)\|\s*(\d+)\s*\|\s*(\d+)\s*\|")


def compile_client():
    """Bien dich lop client mot lan, de 60 lan chay sau khong phai bien dich lai."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    subprocess.run(["javac", "-cp", JAR_PATH, "-d", BUILD_DIR, SOURCE_PATH], check=True)


def run_client(db_file, params):
    """Chay lop client tren mot co so du lieu, tra ve stdout dang van ban."""
    classpath = JAR_PATH + os.pathsep + BUILD_DIR
    command = (["java", "-cp", classpath, "ClientAblationPHMN", db_file, WORK_DIR]
               + [str(p) for p in params])
    finished = subprocess.run(command, capture_output=True, text=True, check=True)
    return finished.stdout


def parse_output(text):
    """Tach stdout cua client thanh so mau, so ung vien va danh sach cau hinh lech E0.

    :return: cap (rows, differing); rows la dict {ma: (so mau, so ung vien)},
             differing la danh sach ma cau hinh co ket qua khac E0
    """
    rows = {}
    for line in text.splitlines():
        matched = TABLE_ROW.match(line)
        if matched:
            rows[matched.group(1)] = (int(matched.group(3)), int(matched.group(4)))

    differing = re.findall(r"- (E\d) : DIFFERENT", text)
    return rows, differing


def main():
    """Chay toan bo phep quet va in bang tong ket."""
    os.makedirs(WORK_DIR, exist_ok=True)
    compile_client()

    codes = ["E0", "E1", "E2", "E3", "E4", "E5"]
    candidate_total = {code: 0 for code in codes}
    pattern_mismatch = {code: 0 for code in codes}
    seeds_with_difference = []

    for seed in SEEDS:
        profit, db = generate_database(seed)
        db_file = os.path.join(WORK_DIR, "db.txt")
        write_database(db_file, profit, db)

        positive_total = sum(max(0, profit[i] * q) for t in db for i, q in t.items())
        min_util = max(1, int(positive_total * random.Random(seed * 7).choice([0.05, 0.1, 0.2, 0.3])))
        params = (min_util, 1, len(db), 1, len(db))

        rows, differing = parse_output(run_client(db_file, params))

        for code in codes:
            if code in rows:
                candidate_total[code] += rows[code][1]
                if rows[code][0] != rows["E0"][0]:
                    pattern_mismatch[code] += 1

        if differing:
            seeds_with_difference.append((seed, differing))
            print("seed %2d : cau hinh lech E0 -> %s" % (seed, ", ".join(differing)))

    print("\n--- Tong ket tren %d co so du lieu ---" % len(list(SEEDS)))
    print("| Ma  | Tong so ung vien | So voi E0 | So bo lech ket qua E0 |")
    print("|-----|------------------|-----------|-----------------------|")
    baseline = candidate_total["E0"]
    for code in codes:
        ratio = "-" if baseline == 0 else "%+.1f%%" % ((candidate_total[code] - baseline) / baseline * 100)
        print("| %-3s | %16d | %9s | %21d |"
              % (code, candidate_total[code], ratio, pattern_mismatch[code]))

    if not seeds_with_difference:
        print("\nKhong co cau hinh nao cho ket qua khac E0 tren 60 bo nay.")


if __name__ == "__main__":
    main()
