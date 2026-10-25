"""Check the U+RU upper bound of SPMF's PHMN against Definition 8 of the paper, on real N-databases.

Definition 8 of the paper builds the remaining utility from POSITIVE item utilities only, so that
U+RU is a true upper bound on every itemset in the subtree. SPMF's AlgoPHMN instead accumulates the
algebraic sum at line 426 of AlgoPHMN.java, so negative utilities lower the bound below the real
value. The gate at line 590 then cuts branches that do contain answers.

This script recomputes both bounds for every single item, using the same item order SPMF uses
(TWU ascending, ties broken by item id), and reports how many genuine high-utility items the gate
rejects even at the lowest possible threshold minUtil = 1.

Run from the project root:
    python -I analysis/check_upper_bound.py chess_negative mushroom_negative pumsb_negative
    python -I analysis/check_upper_bound.py chess_negative --item 46
"""

import sys
from collections import defaultdict


def read_database(path):
    """Read an N-database file and return its transactions plus the TWU of every item.

    Each line holds three fields separated by colons: the item ids, the sum of the POSITIVE
    utilities of the transaction, and the utility of each item. The middle field is what
    AlgoPHMN.java line 236 reads as the transaction utility, so the TWU is accumulated from it
    rather than recomputed.
    """
    item_to_twu = defaultdict(int)                                # item -> transaction weighted utility
    transactions = []                                             # list of (items, utilities)

    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line[0] in "@#%":               # comment or metadata line
                continue
            item_field, utility_field, per_item_field = line.split(":")
            items = [int(token) for token in item_field.split()]
            utilities = [int(token) for token in per_item_field.split()]
            transaction_utility = int(utility_field)
            for item in items:
                item_to_twu[item] += transaction_utility
            transactions.append((items, utilities))

    return transactions, item_to_twu


def build_item_order(item_to_twu):
    """Return the rank of every item in the order AlgoPHMN uses, which is compareItems at line 559.

    That comparator sorts by TWU ascending and breaks ties by item id, so the rank of an item
    decides which items count as "remaining" after it inside a transaction.
    """
    order = sorted(item_to_twu, key=lambda item: (item_to_twu[item], item))
    return {item: rank for rank, item in enumerate(order)}


def compute_bounds(transactions, item_rank):
    """Compute utility and both remaining-utility variants for every single item.

    Returns three dictionaries: the real utility of the item, the remaining utility as SPMF
    accumulates it (algebraic), and the remaining utility Definition 8 asks for (positive only).
    """
    item_utility = defaultdict(int)                               # real utility of the single item
    remaining_algebraic = defaultdict(int)                        # what SPMF stores in rutils
    remaining_positive = defaultdict(int)                         # what Definition 8 requires

    for items, utilities in transactions:
        ranks = [item_rank[item] for item in items]
        for index, item in enumerate(items):
            own_rank = ranks[index]
            item_utility[item] += utilities[index]
            # step: every item placed after this one in the order contributes to its remaining utility
            for other_index, utility in enumerate(utilities):
                if ranks[other_index] > own_rank:
                    remaining_algebraic[item] += utility
                    if utility > 0:
                        remaining_positive[item] += utility

    return item_utility, remaining_algebraic, remaining_positive


def report_single_item(name, target, item_rank, item_utility, remaining_algebraic, remaining_positive):
    """Print the two bounds side by side for one item, to expose the mechanism of the defect."""
    print(f"{name}, item {target} (rank {item_rank[target]} of {len(item_rank)} by TWU ascending)")
    print(f"  real utility of the item        : {item_utility[target]:>12}")
    print(f"  remaining utility, SPMF         : {remaining_algebraic[target]:>12}")
    print(f"  remaining utility, Definition 8 : {remaining_positive[target]:>12}")
    print(f"  upper bound used at line 590    : {item_utility[target] + remaining_algebraic[target]:>12}")
    print(f"  upper bound that is valid       : {item_utility[target] + remaining_positive[target]:>12}")


def report_dataset(name, item_utility, remaining_algebraic):
    """Print one summary row: how many genuine high-utility items the faulty gate rejects.

    An item counts as rejected when its SPMF bound falls below 1, because minUtil = 1 is the
    lowest threshold the algorithm accepts. Such an item can never be reported at any threshold.
    """
    positive_items = [item for item in item_utility if item_utility[item] > 0]
    rejected = [item for item in positive_items
                if item_utility[item] + remaining_algebraic[item] < 1]

    utility_total = sum(item_utility[item] for item in positive_items)
    utility_lost = sum(item_utility[item] for item in rejected)

    print(f"{name:<22}{len(positive_items):>12}{len(rejected):>10}"
          f"{100 * len(rejected) / len(positive_items):>9.1f}%"
          f"{100 * utility_lost / utility_total:>15.1f}%")


def main(argv):
    """Analyse each dataset named on the command line, or one item of one dataset with --item."""
    target_item = None
    if "--item" in argv:                                          # single-item mode
        position = argv.index("--item")
        target_item = int(argv[position + 1])
        argv = argv[:position] + argv[position + 2:]

    if not argv:
        print(__doc__)
        return 1

    if target_item is None:
        print(f"{'dataset':<22}{'items util>0':>12}{'rejected':>10}{'% items':>10}{'% utility lost':>15}")

    for name in argv:
        transactions, item_to_twu = read_database(f"data/{name}.txt")
        item_rank = build_item_order(item_to_twu)
        item_utility, remaining_algebraic, remaining_positive = compute_bounds(transactions, item_rank)

        if target_item is None:
            report_dataset(name, item_utility, remaining_algebraic)
        else:
            report_single_item(name, target_item, item_rank,
                               item_utility, remaining_algebraic, remaining_positive)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
