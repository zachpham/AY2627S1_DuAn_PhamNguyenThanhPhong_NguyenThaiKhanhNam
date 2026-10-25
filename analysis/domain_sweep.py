"""Khao sat mien ung dung toi uu cua PHMN (thanh phan C11).

Tra loi hai cau hoi thay dat ra: nen ap dung thuat toan cho du lieu co dac diem gi,
va tham so toi uu nam o vung nao.

Thiet ke co kiem soat: voi moi hat giong, sinh dung MOT bo giao dich va MOT bo do lon
loi nhuan, roi chi doi DAU cua k mat hang. Nho vay giua cac muc ti le am, moi thu khac
giu nguyen y nguyen, bien duy nhat la ti le mat hang co loi nhuan am.

Bang 1: ti le mat hang am  -> ty le bo sot mau (so voi loi giai vet can).
Bang 2: tham so maxAvg     -> suc tia (so ung vien) va ty le bo sot mau.

Cach chay (Windows, tu thu muc goc cua du an):
    python analysis\\domain_sweep.py
"""

import os
import random
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spmf_phmn_stress_test import brute_force, read_output, write_database

JAR_PATH = os.path.join("tools", "spmf", "spmf.jar")
BUILD_DIR = "build"
SOURCE_PATH = os.path.join("src", "ClientDomainPHMN.java")
WORK_DIR = os.path.join("output", "domain_tmp")

SEEDS = range(1, 21)
TRANSACTION_COUNT = 20
ITEM_COUNT = 8
MIN_UTIL_FRACTION = 0.2
NEGATIVE_COUNTS = [0, 1, 2, 3, 4, 6]
MAX_AVG_VALUES = [20, 10, 6, 4, 3, 2]
FIXED_NEGATIVE_COUNT = 2

RESULT_LINE = re.compile(r"patterns=(\d+) candidates=(\d+) time_ms=(\d+) memory_mb=([\d.]+)")


def build_database(seed):
    """Sinh mot co so du lieu voi moi mat hang deu co loi nhuan DUONG.

    :param seed: so hat giong de ket qua lap lai duoc
    :return: cap (profit, db); profit anh xa mat hang sang loi nhuan don vi duong,
             db la danh sach giao dich dang dict {mat hang: so luong}
    """
    rnd = random.Random(seed)
    profit = {i: rnd.randint(1, 9) for i in range(1, ITEM_COUNT + 1)}
    db = []
    for _ in range(TRANSACTION_COUNT):
        items = sorted(rnd.sample(list(profit), rnd.randint(3, 5)))
        db.append({i: rnd.randint(1, 5) for i in items})
    return profit, db


def flip_signs(profit, negative_count, seed):
    """Doi dau loi nhuan cua dung negative_count mat hang, giu nguyen do lon.

    :param profit: bang loi nhuan toan duong
    :param negative_count: so mat hang can chuyen thanh am
    :param seed: hat giong, de cung mot bo mat hang duoc chon cho moi muc ti le
    :return: bang loi nhuan moi
    """
    chosen = random.Random(seed * 13).sample(sorted(profit), negative_count)
    return {i: (-p if i in chosen else p) for i, p in profit.items()}


def compile_client():
    """Bien dich lop client mot lan de cac lan chay sau khong phai bien dich lai."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    subprocess.run(["javac", "-cp", JAR_PATH, "-d", BUILD_DIR, SOURCE_PATH], check=True)


def run_client(db_file, out_file, params):
    """Chay mot lan PHMN, tra ve cap (so ung vien, dict ket qua)."""
    classpath = JAR_PATH + os.pathsep + BUILD_DIR
    command = (["java", "-cp", classpath, "ClientDomainPHMN", db_file, out_file]
               + [str(p) for p in params])
    finished = subprocess.run(command, capture_output=True, text=True, check=True)
    matched = RESULT_LINE.search(finished.stdout)
    if matched is None:
        raise RuntimeError("khong doc duoc ket qua: " + finished.stdout + finished.stderr)
    return int(matched.group(2)), read_output(out_file)


def measure(negative_count, max_avg):
    """Do mot o cua bang: lap qua moi hat giong roi lay trung binh.

    :return: dict cac con so trung binh cua o do
    """
    db_file = os.path.join(WORK_DIR, "db.txt")
    out_file = os.path.join(WORK_DIR, "out.txt")
    total_true = total_found = total_missing = total_extra = total_candidates = 0

    for seed in SEEDS:
        positive_profit, db = build_database(seed)
        profit = flip_signs(positive_profit, negative_count, seed)
        write_database(db_file, profit, db)

        positive_total = sum(max(0, profit[i] * q) for t in db for i, q in t.items())
        min_util = max(1, int(positive_total * MIN_UTIL_FRACTION))
        params = (min_util, 1, TRANSACTION_COUNT, 1, max_avg)

        expected = brute_force(profit, db, *params)
        candidates, found = run_client(db_file, out_file, params)

        total_true += len(expected)
        total_found += len(found)
        total_missing += len([k for k in expected if k not in found])
        total_extra += len([k for k in found if k not in expected])
        total_candidates += candidates

    count = len(list(SEEDS))
    loss = 0.0 if total_true == 0 else total_missing / total_true * 100
    return {"true": total_true / count, "found": total_found / count,
            "missing": total_missing / count, "extra": total_extra,
            "candidates": total_candidates / count, "loss": loss}


def main():
    """Chay hai phep quet va in hai bang Markdown."""
    os.makedirs(WORK_DIR, exist_ok=True)
    compile_client()

    print("Thiet ke: %d giao dich, %d mat hang, minUtil = %d%% tong loi ich duong,"
          " trung binh tren %d hat giong."
          % (TRANSACTION_COUNT, ITEM_COUNT, int(MIN_UTIL_FRACTION * 100), len(list(SEEDS))))

    print("\n## Bang 1: ti le mat hang am -> ty le bo sot mau")
    print("(minPer=1, maxPer=|D|, minAvg=1, maxAvg=|D| nen rang buoc chu ky khong tia gi)\n")
    print("| Mat hang am | Ti le | Mau dung (vet can) | PHMN tim duoc | Bo sot | Ty le bo sot | Ket qua thua |")
    print("|---|---|---|---|---|---|---|")
    for negative_count in NEGATIVE_COUNTS:
        row = measure(negative_count, TRANSACTION_COUNT)
        print("| %d / %d | %.0f%% | %.1f | %.1f | %.1f | **%.1f%%** | %d |"
              % (negative_count, ITEM_COUNT, negative_count / ITEM_COUNT * 100,
                 row["true"], row["found"], row["missing"], row["loss"], row["extra"]))

    print("\n## Bang 2: tham so maxAvg -> suc tia")
    print("(co dinh %d / %d mat hang am; nguong support sinh ra la |D|/maxAvg - 1)\n"
          % (FIXED_NEGATIVE_COUNT, ITEM_COUNT))
    print("| maxAvg | Nguong support | Mau dung | PHMN tim duoc | Ty le bo sot | So ung vien |")
    print("|---|---|---|---|---|---|")
    for max_avg in MAX_AVG_VALUES:
        row = measure(FIXED_NEGATIVE_COUNT, max_avg)
        print("| %d | %.2f | %.1f | %.1f | %.1f%% | %.1f |"
              % (max_avg, TRANSACTION_COUNT / max_avg - 1, row["true"], row["found"],
                 row["loss"], row["candidates"]))


if __name__ == "__main__":
    main()
