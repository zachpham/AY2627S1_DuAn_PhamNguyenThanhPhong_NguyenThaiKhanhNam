"""Kiem chung cai dat PHMN / PHMN+ cua SPMF bang cach doi chieu voi loi giai vet can.

Cach chay (Windows, tu thu muc goc cua du an):
    python analysis\\spmf_phmn_stress_test.py tools\\spmf\\spmf.jar

Them tham so --patched build/patched de dat mot thu muc class len truoc jar tren
classpath, nho vay ban AlgoPHMN da sua duoc nap thay cho ban trong jar. Loi giai
vet can giu nguyen nen hai ban duoc do bang cung mot thuoc do.

Script sinh ra 60 co so du lieu ngau nhien co ca loi nhuan am va duong, chay
PHMN va PHMN+ tren tung bo, roi so ket qua voi loi giai vet can.

Mac dinh moi bo chay mot lan voi nguong chu ky long nhat (minPer 1, maxPer |D|,
minAvg 1, maxAvg |D|), tuc chi kiem phan tia theo huu ich. Luu y bo nguong nay van loai
khoi dau ra tap muc co support = |D|, vi avgPer = |D|/(|D|+1) < minAvg = 1 (2 tap muc tren
60 bo: {6} cua seed 16 va {3} cua seed 29); ca loi giai vet can lan SPMF deu loai nen phep so
khong bi anh huong. Them --chu-ky de moi
bo chay ba bo nguong chu ky chat, chon ngau nhien nhung co dinh theo seed; khi do
script dem them so lan chay ma nguong chu ky thuc su loai duoc it nhat mot tap muc
dat nguong huu ich, de biet phep kiem co cham toi phan tia chu ky hay khong. Vi duong dan
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

    :return: dict {tap muc: (huu ich, support, minPer, maxPer)}
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
                result[itemset] = (utility, len(tids), smallest, max(gaps))
    return result


def read_output(path):
    """Doc file ket qua cua SPMF.

    :param path: duong dan file ket qua
    :return: dict {tap muc: (huu ich, support, minPer, maxPer)}, cung dang voi brute_force
    """
    result = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("@"):
                continue
            left, right = line.split("#UTIL:", 1)
            fields = {}
            for part in ("UTIL:" + right).split("#"):
                if ":" in part:
                    name, value = part.split(":", 1)
                    fields[name.strip()] = value.strip()
            result[tuple(sorted(int(x) for x in left.split()))] = (
                int(fields["UTIL"]), int(fields["SUP"]), int(fields["MINPER"]), int(fields["MAXPER"]))
    return result


def threshold_settings(seed, db, positive_total, tight):
    """Chon cac bo nguong cho mot co so du lieu.

    :param seed: hat giong cua co so du lieu
    :param db: danh sach giao dich
    :param positive_total: tong huu ich duong cua ca co so du lieu
    :param tight: False thi tra ve mot bo nguong chu ky long nhat nhu truoc,
                  True thi tra ve ba bo nguong chu ky chat
    :return: danh sach bo (minUtil, minPer, maxPer, minAvg, maxAvg)
    """
    size = len(db)
    if not tight:
        # step: giu nguyen cach chon cu de cac con so da cong bo van tai lap duoc
        min_util = max(1, int(positive_total * random.Random(seed * 7).choice([0.05, 0.1, 0.2, 0.3])))
        return [(min_util, 1, size, 1, size)]
    settings = []
    for k in range(3):
        rnd = random.Random(seed * 13 + k)
        # step: nguong huu ich thap hon de con nhieu tap muc cho nguong chu ky loai bot
        min_util = max(1, int(positive_total * rnd.choice([0.02, 0.05, 0.1, 0.2])))
        min_per = rnd.choice([1, 1, 2])
        max_per = rnd.choice([2, 3, 4, size // 2 + 1, size])
        min_avg = rnd.choice([1, 1, 2])
        max_avg = max(min_avg, rnd.choice([2, 3, size]))
        settings.append((min_util, min_per, max_per, min_avg, max_avg))
    return settings


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
    tight = "--chu-ky" in sys.argv                                # nguong chu ky chat
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
    if tight:
        print("Nguong chu ky : CHAT, ba bo moi co so du lieu")

    seeds_with_loss = 0
    total_true = total_missing = total_extra = disagreements = 0
    total_wrong_value = 0                                         # dung tap muc nhung sai gia tri
    seeds_with_negative = 0                                       # bo co it nhat mot muc am
    runs = runs_cut_by_period = cut_by_period = 0                 # do phu cua nguong chu ky
    runs_cut_vs_utility = cut_vs_utility = 0                      # so voi tham chieu chi loc huu ich
    runs_cut_prunable = cut_prunable = 0                          # phan do rieng maxPer, maxAvg
    for seed in SEEDS:
        profit, db = generate_database(seed)
        if any(profit[i] < 0 for t in db for i in t):
            seeds_with_negative += 1
        db_file = os.path.join(work, "db.txt")
        write_database(db_file, profit, db)

        positive_total = sum(max(0, profit[i] * q) for t in db for i, q in t.items())
        seed_lost = False
        for params in threshold_settings(seed, db, positive_total, tight):
            min_util = params[0]                      # minUtil, minPer, maxPer, minAvg, maxAvg
            expected = brute_force(profit, db, *params)
            runs += 1
            if tight:
                # step: bao nhieu tap muc dat nguong huu ich nhung bi nguong chu ky loai
                loose = brute_force(profit, db, min_util, 1, len(db), 1, len(db))
                cut = len(loose) - len(expected)
                cut_by_period += cut
                if cut:
                    runs_cut_by_period += 1
                # step: bo nguong "long" van loai tap muc co support = |D| vi minAvg = 1 > |D|/(|D|+1),
                #       nen dem them so voi tham chieu chi loc huu ich, khong co nguong chu ky nao
                no_limit = 10 ** 9
                utility_only = brute_force(profit, db, min_util, 0, no_limit, 0, no_limit)
                cut = len(utility_only) - len(expected)
                cut_vs_utility += cut
                if cut:
                    runs_cut_vs_utility += 1
                # step: minPer va minAvg chi loc dau ra, khong tia; chi maxPer va maxAvg tia duoc,
                #       nen dem rieng phan hai nguong nay loai
                prunable_only = brute_force(profit, db, min_util, 0, params[2], 0, params[4])
                cut = len(utility_only) - len(prunable_only)
                cut_prunable += cut
                if cut:
                    runs_cut_prunable += 1
            outputs = {}
            for algorithm, tag in (("PHMN", "phmn"), ("PHMN+", "phmnplus")):
                out_file = os.path.join(work, "out_%s.txt" % tag)
                run_spmf(jar, algorithm, db_file, out_file, params, patched_dir)
                outputs[algorithm] = read_output(out_file)

            if outputs["PHMN"] != outputs["PHMN+"]:
                disagreements += 1
                only_plain = sorted(set(outputs["PHMN"]) - set(outputs["PHMN+"]))
                only_plus = sorted(set(outputs["PHMN+"]) - set(outputs["PHMN"]))
                print("seed %2d  nguong=%s PHMN khac PHMN+: chi PHMN %s, chi PHMN+ %s"
                      % (seed, params, only_plain[:3], only_plus[:3]))
            found = outputs["PHMN"]
            missing = [k for k in expected if k not in found]
            extra = [k for k in found if k not in expected]
            # step: voi tap muc tim thay ca hai ben, so ca huu ich, support, minPer va maxPer
            wrong_value = [k for k in found if k in expected and found[k] != expected[k]]
            total_wrong_value += len(wrong_value)
            if wrong_value:
                print("seed %2d  sai gia tri %d tap muc  vi du: %s  SPMF %s  dung %s"
                      % (seed, len(wrong_value), wrong_value[0], found[wrong_value[0]],
                         expected[wrong_value[0]]))
            total_true += len(expected)
            total_missing += len(missing)
            total_extra += len(extra)
            if missing:
                seed_lost = True
                print("seed %2d  nguong=%s bo sot %d / %d tap muc  vi du: %s"
                      % (seed, params, len(missing), len(expected), missing[:3])
                      if tight else
                      "seed %2d  minUtil=%-4d bo sot %d / %d tap muc  vi du: %s"
                      % (seed, min_util, len(missing), len(expected), missing[:3]))
        if seed_lost:
            seeds_with_loss += 1

    print("\n--- Tong ket ---")
    print("So co so du lieu           : %d" % len(list(SEEDS)))
    print("  trong do co muc am       : %d" % seeds_with_negative)
    print("So bo bi bo sot ket qua    : %d" % seeds_with_loss)
    print("Tong so tap muc dung       : %d" % total_true)
    print("So tap muc bi bo sot       : %d" % total_missing)
    print("So ket qua thua (sai)      : %d" % total_extra)
    print("So tap muc sai gia tri     : %d   (huu ich, support, minPer, maxPer)" % total_wrong_value)
    print("So lan PHMN khac PHMN+     : %d" % disagreements)
    if tight:
        print("So lan chay                : %d" % runs)
        print("  nguong chu ky loai >= 1  : %d lan, tong %d tap muc dat nguong huu ich"
              % (runs_cut_by_period, cut_by_period))
        print("  so voi chi loc huu ich   : %d lan, tong %d tap muc"
              % (runs_cut_vs_utility, cut_vs_utility))
        print("  rieng maxPer/maxAvg loai : %d lan, tong %d tap muc (hai nguong duy nhat co tia)"
              % (runs_cut_prunable, cut_prunable))
    shutil.rmtree(work, ignore_errors=True)
    # step: tra ma loi khac 0 khi co bat ky sai khac nao, de dung duoc lam cong kiem tu dong
    if total_missing or total_extra or total_wrong_value or disagreements:
        sys.exit(1)


if __name__ == "__main__":
    main()
