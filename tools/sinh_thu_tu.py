# -*- coding: utf-8 -*-
"""Generate the two item-order variants of the corrected build, for the item-order experiment.

The corrected build (src/patched) orders items by ascending TWU alone, as the SPMF code does.
Definition 7 of F0 places every negative item before every positive item, and orders items of
the same sign by ascending TWU. FHN, whose PNU-list F0 adopts, does the opposite: the method
compareItems of AlgoFHN in spmf.jar places positive items first. The experiment compares the
three orders on the same corrected bound PU + RU, so that only the order changes.

  def7         negative items first, then positive; ascending TWU within a sign (Definition 7)
  duong_truoc  positive items first, then negative; ascending TWU within a sign (FHN)

Only three things change, every changed line is marked THU_TU:
  - a set negativeItems, cleared at the start of every run;
  - the first database scan records the sign of every item, because the utility-lists are sorted
    before the second scan, which is the first one that reads the utilities in the published code;
  - the body of compareItems.
The comparator is the only one used to sort both the utility-lists and the transactions from
which RU and EUCS are built, so the new order is applied consistently everywhere.

Every anchor must occur exactly once in src/patched, otherwise the script stops and writes nothing.

Usage, from the project root:
    py -I tools/sinh_thu_tu.py
    javac -nowarn -cp tools/spmf/spmf.jar -d build/def7 src/def7/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus/*.java
    javac -nowarn -cp tools/spmf/spmf.jar -d build/duong_truoc src/duong_truoc/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus/*.java
"""

import io
import os
import shutil
import sys

PACKAGE_PATH = os.path.join('ca', 'pfv', 'spmf', 'algorithms', 'frequentpatterns', 'phmn_plus')
SOURCE_DIR = os.path.join('src', 'patched', PACKAGE_PATH)                   # corrected build

# variant name -> (value returned when item1 is negative and item2 positive, banner suffix, comment)
VARIANTS = {
    'def7': ('-1', 'DEF7', 'negative items first, as Definition 7 of F0'),
    'duong_truoc': ('1', 'DUONG-TRUOC', 'positive items first, as compareItems of AlgoFHN'),
}

OLD_COMPARE = ('\t\tint compare = (int)( mapItemToTWU.get(item1) - mapItemToTWU.get(item2));\n'
               '\t\t// if the same, use the lexical order otherwise use the TWU\n'
               '\t\treturn (compare == 0)? item1 - item2 :  compare;\n')

NEW_COMPARE = ('\t\t// THU_TU: %s\n'
               '\t\tboolean negative1 = negativeItems.contains(item1);\n'
               '\t\tboolean negative2 = negativeItems.contains(item2);\n'
               '\t\tif(negative1 != negative2){\n'
               '\t\t\treturn negative1 ? %s : %s;\n'
               '\t\t}\n'
               '\t\t// THU_TU: same sign, ascending TWU, then item number, as before\n'
               '\t\tint compare = Long.compare(mapItemToTWU.get(item1), mapItemToTWU.get(item2));\n'
               '\t\treturn (compare == 0)? item1 - item2 :  compare;\n')

OLD_DOC = ('\t * Method to compare items by their TWU. The order is ascending TWU, then item number; it does\n'
           '\t * not consider the sign of the utility, unlike Definition 7 of the paper, which places the\n'
           '\t * negative items first. The same order is used for the utility-lists and for the transactions\n'
           '\t * from which the remaining utility is computed.\n')

NEW_DOC = ('\t * Method to compare items. THU_TU: %s; items of the same sign are\n'
           '\t * ordered by ascending TWU, then item number. The same order is used for the utility-lists\n'
           '\t * and for the transactions from which the remaining utility is computed.\n')

FIELD_OLD = '\tMap<Integer, Long> mapItemToTWU;\n'
FIELD_NEW = ('\tMap<Integer, Long> mapItemToTWU;\n\n'
             '\t/** THU_TU: the items whose utility is negative, recorded during the first scan */\n'
             '\tjava.util.Set<Integer> negativeItems = new java.util.HashSet<Integer>();\n')

RESET_OLD = '\t\tmapItemToTWU = new HashMap<Integer, Long>();\n'
RESET_NEW = ('\t\tmapItemToTWU = new HashMap<Integer, Long>();\n'
             '\t\tnegativeItems.clear();                                // THU_TU\n')

SCAN_OLD = '\t\t\t\tsumOfTransactionLength += items.length;\n'
SCAN_NEW = ('\t\t\t\tsumOfTransactionLength += items.length;\n\n'
            '\t\t\t\t// THU_TU: the order needs the sign of every item before the first sort, and the\n'
            '\t\t\t\t// sign of an item is the same in every transaction (its unit profit)\n'
            '\t\t\t\tString signValues[] = split[2].split(" ");\n'
            '\t\t\t\tfor(int s=0; s < items.length; s++){\n'
            '\t\t\t\t\tif(Integer.parseInt(signValues[s]) < 0){\n'
            '\t\t\t\t\t\tnegativeItems.add(Integer.parseInt(items[s]));\n'
            '\t\t\t\t\t}\n'
            '\t\t\t\t}\n')


def replaceOnce(text, old, new, label):
    """Replace one anchor that must occur exactly once.

    :param text: the source text
    :param old: the anchor
    :param new: its replacement
    :param label: name of the anchor, for the error message
    :return: the new text; exits with status 1 when the anchor is missing or repeated
    """
    count = text.count(old)
    if count != 1:
        print('anchor "%s" found %d times, expected 1' % (label, count))
        sys.exit(1)
    return text.replace(old, new)


def generate(name):
    """Write one variant under src/<name>.

    :param name: a key of VARIANTS
    :return: the folder written
    """
    when_negative_first, banner, comment = VARIANTS[name]
    when_positive_first = '1' if when_negative_first == '-1' else '-1'

    # step: read the corrected build and drop trailing blanks, as tools/sinh_e8.py does
    with io.open(os.path.join(SOURCE_DIR, 'AlgoPHMN.java'), encoding='utf-8') as handle:
        text = handle.read()
    text = '\n'.join(line.rstrip() for line in text.split('\n'))

    # step: apply the checked replacements
    text = replaceOnce(text, FIELD_OLD, FIELD_NEW, 'field mapItemToTWU')
    text = replaceOnce(text, RESET_OLD, RESET_NEW, 'reset of mapItemToTWU')
    text = replaceOnce(text, SCAN_OLD, SCAN_NEW, 'first scan')
    text = replaceOnce(text, OLD_DOC, NEW_DOC % comment, 'Javadoc of compareItems')
    text = replaceOnce(text, OLD_COMPARE,
                       NEW_COMPARE % (comment, when_negative_first, when_positive_first),
                       'body of compareItems')
    text = replaceOnce(text, 'v2.38-PATCHED', 'v2.38-PATCHED-' + banner, 'version banner')

    # step: write the variant beside an unchanged copy of the two data classes
    target = os.path.join('src', name, PACKAGE_PATH)
    if os.path.isdir(os.path.join('src', name)):
        shutil.rmtree(os.path.join('src', name))
    os.makedirs(target)
    with io.open(os.path.join(target, 'AlgoPHMN.java'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    for data_class in ('ElementPHMN.java', 'UtilityListPHMN.java'):
        shutil.copy(os.path.join(SOURCE_DIR, data_class), os.path.join(target, data_class))
    return target


if __name__ == '__main__':
    for variant in VARIANTS:
        print('written', generate(variant))
