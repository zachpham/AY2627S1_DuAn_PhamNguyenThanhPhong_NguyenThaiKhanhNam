"""Generate the "Strategy 4 as written" variant of AlgoPHMN from the published SPMF source.

The variant answers one question: if the implementation followed Definition 8 of F0 exactly
(remaining utility made of positive utilities only) but kept the pruning test of Strategy 4
exactly as F0 states it (U(X) + RU(X) < minUtil), would it be correct? Running it against
exhaustive enumeration separates the defect of the implementation from the defect of the paper.

Every anchor must occur exactly once in the published source, otherwise the script stops and
writes nothing.

Usage, from the project root:
    py -I tools/sinh_strategy4.py
    javac -nowarn -cp tools/spmf/spmf.jar -d build/strategy4 src/strategy4/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus/*.java
"""

import os
import shutil
import sys

PACKAGE_PATH = os.path.join("ca", "pfv", "spmf", "algorithms", "frequentpatterns", "phmn_plus")
SOURCE_DIR = os.path.join("tools", "spmf", "source", PACKAGE_PATH)       # published source
TARGET_DIR = os.path.join("src", "strategy4", PACKAGE_PATH)                # generated variant

# Each pair is (text of the published source, replacement). The pruning test at the gate and in
# LA-prune is deliberately NOT changed: it stays U + RU, as Strategy 4 states it.
REPLACEMENTS = [
    ("\t\t\t\t\t\tremainingUtility += pair.utility;\n"
     "\t\t\t\t\t\tnewTWU += pair.utility; // NEW OPTIMIZATION\n",
     "\t\t\t\t\t\t// STRATEGY4 (Definition 8): only positive utilities enter the remaining utility\n"
     "\t\t\t\t\t\tif(pair.utility > 0){\n"
     "\t\t\t\t\t\t\tremainingUtility += pair.utility;\n"
     "\t\t\t\t\t\t}\n"
     "\t\t\t\t\t\t// STRATEGY4 (Definition 6): the TWU used by EUCP is the positive transaction utility\n"
     "\t\t\t\t\t\tif(pair.utility > 0){\n"
     "\t\t\t\t\t\t\tnewTWU += pair.utility;\n"
     "\t\t\t\t\t\t}\n"),
    ("\t\t\t\t\tremainingUtility = remainingUtility - pair.utility;\n",
     "\t\t\t\t\t// STRATEGY4: mirror the accumulation above\n"
     "\t\t\t\t\tif(pair.utility > 0){\n"
     "\t\t\t\t\t\tremainingUtility = remainingUtility - pair.utility;\n"
     "\t\t\t\t\t}\n"),
    ("\t\t\t\t\tint rUtil = element.rutils - mmap.get(item);\n",
     "\t\t\t\t\t// STRATEGY4: rutils holds positive utilities only, so only a positive part is removed\n"
     "\t\t\t\t\tint rUtil = element.rutils - Math.max(0, mmap.get(item));\n"),
    ("\" v2.38\" ",
     "\" v2.38-STRATEGY4\" "),
]


def main():
    """Apply the checked replacements and write the variant next to the other variants.

    :return: nothing; exits with status 1 if an anchor is missing or repeated
    """
    # Step 1: read the published source of the algorithm class
    with open(os.path.join(SOURCE_DIR, "AlgoPHMN.java"), encoding="utf-8") as handle:
        text = handle.read()

    # Step 2: check every anchor before changing anything
    for old, _ in REPLACEMENTS:
        count = text.count(old)
        if count != 1:
            print("anchor found %d times, expected 1: %r" % (count, old))
            sys.exit(1)

    # Step 3: apply the replacements
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    # Step 4: write AlgoPHMN and copy the two unchanged classes of the package
    os.makedirs(TARGET_DIR, exist_ok=True)
    with open(os.path.join(TARGET_DIR, "AlgoPHMN.java"), "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    for name in ("ElementPHMN.java", "UtilityListPHMN.java"):
        shutil.copy(os.path.join(SOURCE_DIR, name), os.path.join(TARGET_DIR, name))
    print("written to", TARGET_DIR)


if __name__ == "__main__":
    main()
