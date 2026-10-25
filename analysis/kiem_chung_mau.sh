#!/bin/sh
# Recomputes the utility and support of one itemset straight from the data file,
# without going through SPMF, so a pattern SPMF reports can be checked independently.
#
# Usage, from the project root:
#   sh analysis/kiem_chung_mau.sh data/pumsb_negative.txt "4414 3404 4404 4430 7112 7092 4426 4434 180 170"
#
# Known-good answers on pumsb_negative, minUtil 5800000, periodic 1-3000-1-2000:
#   4414 3404 4404 4430 7112 7092 4426 4434 180 170      -> util 5926270, sup 34708
#   4414 17 3404 4404 4430 7112 7092 4426 4434 180 170   -> util 5842926, sup 32140

if [ $# -ne 2 ]; then
    echo "can hai tham so: <file du lieu> \"<cac ma mat hang>\"" >&2
    exit 1
fi

awk -F: -v want="$2" '
BEGIN {
    # step: the wanted itemset becomes an array so every transaction can be tested
    k = split(want, S, " ");
    tong_gd = 0;
}
/^[@#%]/ { next }
{
    tong_gd++;
    n = split($1, it, " ");
    split($3, u, " ");

    # step: map item code to its utility in this transaction
    delete val;
    for (i = 1; i <= n; i++) val[it[i]] = u[i];

    # step: the itemset counts only if every one of its items is present
    du = 1;
    for (j = 1; j <= k; j++) if (!(S[j] in val)) du = 0;
    if (!du) next;

    sup++;
    s = 0;
    for (j = 1; j <= k; j++) s += val[S[j]];
    util += s;

    # step: periods are gaps between consecutive transactions holding the itemset
    if (truoc > 0) {
        gap = tong_gd - truoc;
        if (minper == 0 || gap < minper) minper = gap;
        if (gap > maxper) maxper = gap;
    }
    truoc = tong_gd;
}
END {
    if (sup == 0) { print "tap muc nay khong xuat hien trong giao dich nao"; exit }
    printf "tap muc      : %s\n", want;
    printf "|D|          : %d\n", tong_gd;
    printf "support      : %d\n", sup;
    printf "hui (UTIL)   : %d\n", util;
    printf "minPer       : %d\n", minper;
    printf "maxPer       : %d\n", maxper;
    printf "avgPer       : %.6f   (= |D|/(sup+1))\n", tong_gd / (sup + 1);
}' "$1"
