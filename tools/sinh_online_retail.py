"""Build the N-database online_retail_negative.txt from the UCI Online Retail dataset.

The source is the file published by the UCI Machine Learning Repository, kept unchanged in
data/uci_online_retail.zip: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning
Repository. https://doi.org/10.24432/C5BW33, licence CC BY 4.0. It holds 541,909 invoice lines of a
UK online retailer between 1 December 2010 and 9 December 2011.

Three modelling decisions turn invoice lines into an N-database. Each one is printed by this script
and argued in Section 6.4 of the report:

  1. A transaction is one customer in one ISO week. An ordinary invoice never holds a negative
     line: every return, discount and fee sits in a separate cancellation invoice that holds only
     negative lines. One invoice per transaction would therefore never put a negative item next to
     a positive one. Grouping by customer and week does, in 8.5 % of the transactions.
     Transactions are ordered by week, then by the time of their first invoice, so the position of
     a transaction follows the calendar and the periods of PHMN are measured in customer-weeks.
  2. The utility of a line is Quantity x UnitPrice in pence, i.e. revenue: the data holds no cost
     price, so profit cannot be computed. A positive line becomes item <StockCode>, a negative line
     becomes the separate item NEG:<StockCode>, so no item ever carries both signs.
  3. Lines without a CustomerID (about a quarter of them) are dropped, since they cannot be
     grouped by customer.

Only the Python standard library is used: an .xlsx file is a ZIP archive of XML files.

Usage, from the project root:
    py -I tools/sinh_online_retail.py > output/runs/sinh_online_retail.log

Writes data/online_retail_negative.txt (SPMF format, items:TU:utilities, where TU is the sum of
the positive utilities as SPMF expects for an N-database) and data/online_retail_items.csv (item
number, original item, description).
"""

import csv
import io
import re
import sys
import zipfile
import xml.etree.ElementTree as ElementTree
from collections import defaultdict
from datetime import datetime, timedelta

SOURCE_ZIP = 'data/uci_online_retail.zip'
DATABASE_PATH = 'data/online_retail_negative.txt'
ITEMS_PATH = 'data/online_retail_items.csv'
SHEET_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
EXCEL_EPOCH = datetime(1899, 12, 30)                         # day 0 of Excel serial dates
COLUMNS = ['InvoiceNo', 'StockCode', 'Description', 'Quantity',
           'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']


def readSharedStrings(xlsx):
    """Read the table of shared strings of a workbook.

    :param xlsx: open ZipFile of the .xlsx workbook
    :return: list of strings, indexed by the number a cell of type "s" holds
    """
    strings = []
    root = ElementTree.fromstring(xlsx.read('xl/sharedStrings.xml'))
    for item in root.iter(SHEET_NS + 'si'):
        # step: a string may be split into several runs, each with its own <t>
        strings.append(''.join(node.text or '' for node in item.iter(SHEET_NS + 't')))
    return strings


def columnIndex(cell_ref):
    """Turn the letters of a cell reference into a zero-based column number.

    :param cell_ref: reference such as "C17"
    :return: column number, 0 for A
    """
    letters = re.match(r'[A-Z]+', cell_ref).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - ord('A') + 1)
    return index - 1


def plainText(raw):
    """Write a numeric cell as an integer when it holds a whole number.

    :param raw: text of the <v> element
    :return: "22423" for "22423" or "22423.0", the raw text otherwise
    """
    try:
        value = float(raw)
    except ValueError:
        return raw
    return str(int(value)) if value.is_integer() else raw


def readRows(zip_path):
    """Read every invoice line of the workbook inside the UCI archive.

    :param zip_path: path of the archive downloaded from UCI
    :return: list of dicts keyed by the eight column names
    """
    with zipfile.ZipFile(zip_path) as outer:
        inner_bytes = outer.read('Online Retail.xlsx')
    rows = []
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as xlsx:
        strings = readSharedStrings(xlsx)
        sheet = ElementTree.fromstring(xlsx.read('xl/worksheets/sheet1.xml'))
        for row in sheet.iter(SHEET_NS + 'row'):
            values = [''] * len(COLUMNS)
            for cell in row.iter(SHEET_NS + 'c'):
                node = cell.find(SHEET_NS + 'v')
                if node is None:
                    continue
                text = strings[int(node.text)] if cell.get('t') == 's' else node.text
                values[columnIndex(cell.get('r'))] = text
            rows.append(values)
    # step: the first row holds the column names; check them rather than trust the order
    if rows[0] != COLUMNS:
        sys.exit('unexpected header: %s' % rows[0])
    return [dict(zip(COLUMNS, values)) for values in rows[1:]]


def excelTime(serial_text):
    """Turn an Excel serial date into a datetime, rounded to the second.

    :param serial_text: serial date as stored in the sheet, e.g. "40513.354166666664"
    :return: datetime
    """
    moment = EXCEL_EPOCH + timedelta(days=float(serial_text))
    return (moment + timedelta(microseconds=500000)).replace(microsecond=0)


def main():
    """Convert the archive, check the result and print the counts quoted in the report.

    :return: nothing
    """
    sys.stdout.reconfigure(encoding='utf-8')

    # Step 1: read the source and count what the report quotes about it
    rows = readRows(SOURCE_ZIP)
    invoices = set(r['InvoiceNo'] for r in rows)
    cancelled = set(i for i in invoices if i.upper().startswith('C'))
    print('source             :', SOURCE_ZIP)
    print('invoice lines      :', len(rows))
    print('invoices           :', len(invoices), '(cancellation invoices: %d)' % len(cancelled))
    print('lines w/o customer :', sum(1 for r in rows if not r['CustomerID']))

    # Step 2: the reason for decision 1 - negative lines sit only in cancellation invoices
    negative_in_ordinary = sum(1 for r in rows
                               if not r['InvoiceNo'].upper().startswith('C')
                               and float(r['Quantity']) * float(r['UnitPrice']) < 0)
    print('negative lines in ordinary invoices:', negative_in_ordinary)

    # Step 3: group the lines of each customer and ISO week into one transaction (decisions 1-3)
    transactions = defaultdict(lambda: defaultdict(int))     # key -> item -> utility in pence
    first_time = {}                                          # key -> time of its first invoice
    descriptions = {}                                        # item -> first description seen
    kept_lines = 0
    for r in rows:
        if not r['CustomerID']:
            continue
        utility = round(float(r['Quantity']) * float(r['UnitPrice']) * 100)
        if utility == 0:
            continue
        moment = excelTime(r['InvoiceDate'])
        key = (moment.isocalendar()[:2], plainText(r['CustomerID']))
        code = plainText(r['StockCode']).strip()
        item = code if utility > 0 else 'NEG:' + code
        transactions[key][item] += utility
        descriptions.setdefault(item, r['Description'])
        first_time[key] = min(first_time.get(key, moment), moment)
        kept_lines += 1
    print('lines kept         :', kept_lines)

    # Step 4: order by week, then first invoice, then customer, and number the items in the order
    #         they first appear, so the output is the same on every run
    order = sorted(transactions, key=lambda k: (k[0], first_time[k], k[1]))
    item_numbers = {}
    lines = []
    for key in order:
        items = [(item, u) for item, u in transactions[key].items() if u != 0]
        if not items:
            continue
        for item, _ in items:
            item_numbers.setdefault(item, len(item_numbers) + 1)
        items.sort(key=lambda pair: item_numbers[pair[0]])
        tu = sum(u for _, u in items if u > 0)
        lines.append((items, tu))

    # Step 5: the two checks applied to every dataset in Section 6.4
    signs = defaultdict(set)
    for items, tu in lines:
        assert tu == sum(u for _, u in items if u > 0)
        for item, u in items:
            signs[item].add(u > 0)
    two_signs = sum(1 for s in signs.values() if len(s) > 1)
    assert two_signs == 0, 'an item carries both signs'
    assert all(tu > 0 or all(u < 0 for _, u in items) for items, tu in lines)

    # Step 6: write the database and the item table
    with open(DATABASE_PATH, 'w', encoding='utf-8', newline='\n') as handle:
        for items, tu in lines:
            handle.write('%s:%d:%s\n' % (' '.join(str(item_numbers[i]) for i, _ in items), tu,
                                         ' '.join(str(u) for _, u in items)))
    with open(ITEMS_PATH, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['id', 'item', 'description'])
        for item, number in sorted(item_numbers.items(), key=lambda pair: pair[1]):
            writer.writerow([number, item, descriptions[item]])

    # Step 7: characteristics for Table 6.2
    mixed = sum(1 for items, _ in lines
                if any(u > 0 for _, u in items) and any(u < 0 for _, u in items))
    only_negative = sum(1 for items, _ in lines if all(u < 0 for _, u in items))
    negative_items = sum(1 for item in item_numbers if item.startswith('NEG:'))
    positive_total = sum(u for items, _ in lines for _, u in items if u > 0)
    negative_total = -sum(u for items, _ in lines for _, u in items if u < 0)
    weeks = sorted(set(k[0] for k in order))
    print('transactions |D|   :', len(lines))
    print('items |I|          :', len(item_numbers), '(negative: %d)' % negative_items)
    print('avg. length        : %.1f' % (sum(len(items) for items, _ in lines) / len(lines)))
    print('mixed transactions : %d (%.1f %%)' % (mixed, 100.0 * mixed / len(lines)))
    print('only negative      :', only_negative)
    print('ISO weeks          : %d (%s to %s)' % (len(weeks), weeks[0], weeks[-1]))
    print('transactions/week  : %.0f' % (len(lines) / len(weeks)))
    print('positive utility   :', positive_total)
    print('negative utility   : %d (%.2f %% of the positive)'
          % (negative_total, 100.0 * negative_total / positive_total))
    print('items with 2 signs :', two_signs)
    print('wrote', DATABASE_PATH, 'and', ITEMS_PATH)


if __name__ == '__main__':
    main()
