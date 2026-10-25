"""Kiem chung cai dat PHMN / PHMN+ cua SPMF bang cach doi chieu voi loi giai vet can.

Cach chay (Windows, tu thu muc goc cua du an):
    python analysis\\spmf_phmn_stress_test.py tools\\spmf\\spmf.jar

Them tham so --patched build/patched de dat mot thu muc class len truoc jar tren
classpath, nho vay ban AlgoPHMN da sua duoc nap thay cho ban trong jar. Loi giai
vet can giu nguyen nen hai ban duoc do bang cung mot thuoc do.

Script sinh ra 60 co so du lieu ngau nhien co ca loi nhuan am va duong, chay
PHMN va PHMN+ tren tung bo, roi so ket qua voi loi giai vet can. Vi duong dan
chua ky tu tieng Viet lam SPMF bao loi "file does not exist", script sao chep
spmf.jar va cac file tam sang thu muc tam cua he thong truoc khi chay.
"""

import os
import random
import shutil
import subprocess
import sys
import tempfile
from itertools import combinations

SEEDS = range(1, 61)


def generate_database(seed):
    """Sinh mot co so du lieu ngau nhien co ca loi nhuan am va duong.

    :param seed: so hat giong de ket qua lap lai duoc
    :return: cap (profit, db); profit anh xa mat hang sang loi nhuan don vi,
             db la danh sach giao dich, moi giao dich la dict {mat hang: so luong}
    """
    rnd = random.Random(seed)
    item_count = rnd.randint(4, 7)
    profit = {i: rnd.choice([x for x in range(-6, 10) if x != 0]) for i in range(1, item_count + 1)}
    db = []
    for _ in range(rnd.randint(6, 12)):
        items = sorted(rnd.sample(list(profit), rnd.randint(1, item_count)))
        db.append({i: rnd.randint(1, 5) for i in items})
    return profit, db


def write_database(path, profit, db):
    """Ghi co so du lieu ra dinh dang SPMF: "cac mat hang:tong loi nhuan duong:loi nhuan tung mat hang"."""
    with open(path, "w") as out:
        for transaction in db:
            utilities = [profit[i] * q for i, q in sorted(transaction.items())]
            positive_sum = sum(u for u in utilities if u > 0)
            out.write("%s:%d:%s\n" % (" ".join(str(i) for i in sorted(transaction)),
                                      positive_sum,
                                      " ".join(str(u) for u in utilities)))


def brute_force(profit, db, min_util, min_per, max_per, min_avg, max_avg):
    """Liet ke moi tap muc thoa dieu kien, theo dung quy uoc chu ky cua code SPMF.

    Code SPMF bo qua khoang dau va khoang cuoi khi tinh minPer, nen ham nay lam
    giong het de phan khac biet con lai chi den tu phan huu ich.

    :return: dict {tap muc: huu ich}
    """
    size = len(db)
    result = {}
    items = sorted(profit)
    for length in range(1, len(items) + 1):
        for itemset in combinations(items, length):
            tids = [j for j, t in enumerate(db) if all(i in t for i in itemset)]
            if not tids:
                continue
            utility = sum(profit[i] * db[j][i] for j in tids for i in itemset)
            gaps = ([tids[0] + 1]
                    + [tids[k + 1] - tids[k] for k in range(len(tids) - 1)]
                    + [size - 1 - tids[-1]])
            inner_gaps = [tids[k + 1] - tids[k] for k in range(len(tids) - 1)]
            smallest = min(inner_gaps) if inner_gaps else 2 ** 31 - 1
            average = size / (len(tids) + 1)
            if (utility >= min_util and max(gaps) <= max_per and smallest >= min_per
                    and min_avg <= average <= max_avg):
                result[itemset] = utility
    return result


def read_output(path):
    """Doc file ket qua cua SPMF thanh dict {tap muc: huu ich}."""
    result = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("@"):
                continue
            left, right = line.split("#UTIL:")
            result[tuple(sorted(int(x) for x in left.split()))] = int(right.split("#")[0])
    return result


def run_spmf(jar, algorithm, db_file, out_file, params, patched_dir=None):
    """Chay mot thuat toan cua SPMF bang dong lenh.

    Khi patched_dir khac None, thu muc do duoc dat truoc jar tren classpath nen
    JVM nap AlgoPHMN da sua thay cho ban goc; phai goi qua lop Main vi tuy chon
    -jar lam JVM bo qua -cp.
    """
    if patched_dir is None:
        command = ["java", "-jar", jar, "run", algorithm, db_file, out_file]
    else:
        classpath = patched_dir + os.pathsep + jar
        command = ["java", "-cp", classpath, "ca.pfv.spmf.gui.Main",
                   "run", algorithm, db_file, out_file]
    subprocess.run(command + [str(p) for p in params], capture_output=True, check=True)


def main():
    """Chay toan bo phep kiem chung va in bang tong ket."""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    source_patched = None
    if "--patched" in sys.argv:                                   # do ban da sua thay vi ban goc
        source_patched = sys.argv[sys.argv.index("--patched") + 1]

    work = tempfile.mkdtemp(prefix="phmn_check_")
    jar = os.path.join(work, "spmf.jar")
    shutil.copy(sys.argv[1], jar)

    # step: thu muc goc du an chua ky tu tieng Viet nen phai sao class sang thu muc tam
    patched_dir = None
    if source_patched is not None:
        patched_dir = os.path.join(work, "patched")
        shutil.copytree(source_patched, patched_dir)

    print("Ban duoc kiem : %s" % ("DA SUA" if patched_dir else "NGUYEN TRANG"))

    seeds_with_loss = 0
    total_true = total_missing = total_extra = disagreements = 0
    for seed in SEEDS:
        profit, db = generate_database(seed)
        db_file = os.path.join(work, "db.txt")
        write_database(db_file, profit, db)

        positive_total = sum(max(0, profit[i] * q) for t in db for i, q in t.items())
        min_util = max(1, int(positive_total * random.Random(seed * 7).choice([0.05, 0.1, 0.2, 0.3])))
        params = (min_util, 1, len(db), 1, len(db))   # minUtil, minPer, maxPer, minAvg, maxAvg

        expected = brute_force(profit, db, *params)
        outputs = {}
        for algorithm, tag in (("PHMN", "phmn"), ("PHMN+", "phmnplus")):
            out_file = os.path.join(work, "out_%s.txt" % tag)
            run_spmf(jar, algorithm, db_file, out_file, params, patched_dir)
            outputs[algorithm] = read_output(out_file)

        if outputs["PHMN"] != outputs["PHMN+"]:
            disagreements += 1
        found = outputs["PHMN"]
        missing = [k for k in expected if k not in found]
        extra = [k for k in found if k not in expected]
        total_true += len(expected)
        total_missing += len(missing)
        total_extra += len(extra)
        if missing:
            seeds_with_loss += 1
            print("seed %2d  minUtil=%-4d bo sot %d / %d tap muc  vi du: %s"
                  % (seed, min_util, len(missing), len(expected), missing[:3]))

    print("\n--- Tong ket ---")
    print("So co so du lieu           : %d" % len(list(SEEDS)))
    print("So bo bi bo sot ket qua    : %d" % seeds_with_loss)
    print("Tong so tap muc dung       : %d" % total_true)
    print("So tap muc bi bo sot       : %d" % total_missing)
    print("So ket qua thua (sai)      : %d" % total_extra)
    print("So lan PHMN khac PHMN+     : %d" % disagreements)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
