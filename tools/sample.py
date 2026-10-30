#!/usr/bin/env python3
"""Pick a small, varied sample of records for hand-checking.

Chooses the rows most likely to break logic (missing values, sentinel numbers,
duplicate keys, duplicate rows, negatives, extremes, padded text), a few rows per
category if asked, and some ordinary rows. Prints CSV with the reason for each pick,
so you can add an expected-value column by hand and compare it with the code's output.
Standard library only; Python 3.8+.

Usage:
  python3 .kit/tools/sample.py <file.csv|.tsv|.json|.jsonl> [--id COL] [--by COL] [--per 2] [--max 20]
  python3 .kit/tools/sample.py data/orders.csv --by status > process/samples.csv
"""
import argparse
import codecs
import csv
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

NULLS = {"", "null", "none", "na", "n/a", "nan", "nil", "-", "--", "?", "#n/a"}
SENTINELS = {"-999", "-9999", "9999", "99999", "999999", "-1"}
NUM = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
ID_NAME = re.compile(r"(^|[_\s])(id|key|no|code|uuid)$|번호$|코드$|아이디$", re.IGNORECASE)


def detect_encoding(path):
    with open(path, "rb") as fh:
        raw = fh.read(262144)
    for enc in ("utf-8-sig", "cp949", "latin-1"):
        try:
            codecs.getincrementaldecoder(enc)().decode(raw, final=False)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def read_table(path, max_rows):
    ext = os.path.splitext(path)[1].lower()
    enc = detect_encoding(path)
    if ext in (".json", ".jsonl", ".ndjson"):
        with open(path, encoding=enc, errors="replace") as fh:
            text = fh.read()
        try:
            data = json.loads(text)
            records = data if isinstance(data, list) else next(
                (v for v in data.values() if isinstance(v, list)), []) if isinstance(data, dict) else []
        except ValueError:
            records = []
            for line in text.splitlines():
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except ValueError:
                        continue
        flat = []
        for rec in records[: max_rows or None]:
            if not isinstance(rec, dict):
                continue
            row = {}
            for k, v in rec.items():
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        row["%s.%s" % (k, k2)] = v2
                else:
                    row[str(k)] = v
            flat.append(row)
        header = []
        for row in flat:
            for k in row:
                if k not in header:
                    header.append(k)
        rows = [["" if r.get(h) is None else (json.dumps(r[h], ensure_ascii=False) if isinstance(r.get(h), (list, dict)) else str(r[h])) for h in header] for r in flat]
        return header, rows
    with open(path, newline="", encoding=enc, errors="replace") as fh:
        sample = fh.read(65536)
        fh.seek(0)
        if ext == ".tsv":
            delim = "\t"
        else:
            try:
                delim = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
            except csv.Error:
                delim = ","
        reader = csv.reader(fh, delimiter=delim)
        header = next(reader, [])
        rows = []
        for row in reader:
            if max_rows and len(rows) >= max_rows:
                break
            rows.append(row + [""] * (len(header) - len(row)))
        return header, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path")
    parser.add_argument("--id", help="key column (default: first ID-like column)")
    parser.add_argument("--by", help="category column: take --per rows for each value")
    parser.add_argument("--per", type=int, default=2)
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--max-rows", type=int, default=500000)
    args = parser.parse_args()

    header, rows = read_table(args.path, args.max_rows)
    if not rows:
        sys.exit("no rows found in %s" % args.path)
    picks, seen = [], set()

    def add(index, reason):
        if index not in seen and len(picks) < args.max:
            seen.add(index)
            picks.append((index, reason))

    ncol = len(header)
    for c in range(ncol):
        for i, row in enumerate(rows):
            if row[c].strip().lower() in NULLS:
                add(i, "결측: %s" % header[c])
                break
        for i, row in enumerate(rows):
            if row[c].strip() in SENTINELS:
                add(i, "특수값 %s: %s" % (row[c].strip(), header[c]))
                break
        for i, row in enumerate(rows):
            if row[c] != row[c].strip() and row[c].strip():
                add(i, "앞뒤 공백: %s" % header[c])
                break

    id_col = header.index(args.id) if args.id in header else next(
        (c for c, h in enumerate(header) if ID_NAME.search(str(h).strip())), None)
    if id_col is not None:
        counts = Counter(row[id_col] for row in rows)
        dup = next((k for k, n in counts.most_common() if n > 1 and k.strip()), None)
        if dup is not None:
            for i, row in enumerate(rows):
                if row[id_col] == dup:
                    add(i, "중복 키 %s=%s" % (header[id_col], dup))

    first_seen = {}
    for i, row in enumerate(rows):
        key = tuple(row)
        if key in first_seen:
            add(first_seen[key], "완전 중복 행 (원본)")
            add(i, "완전 중복 행 (사본)")
            break
        first_seen[key] = i

    numeric_cols = [c for c in range(ncol)
                    if sum(1 for r in rows[:2000] if NUM.match(r[c].strip().replace(",", ""))) >= 0.8 * min(len(rows), 2000)
                    and c != id_col][:5]
    for c in numeric_cols:
        values = [(float(r[c].strip().replace(",", "")), i) for i, r in enumerate(rows) if NUM.match(r[c].strip().replace(",", ""))]
        if not values:
            continue
        negatives = [i for v, i in values if v < 0 and str(rows[i][c]).strip() not in SENTINELS]
        if negatives:
            add(negatives[0], "음수: %s" % header[c])
        add(min(values)[1], "최솟값: %s" % header[c])
        add(max(values)[1], "최댓값: %s" % header[c])

    if args.by in header:
        b = header.index(args.by)
        taken = defaultdict(int)
        for i, row in enumerate(rows):
            if taken[row[b]] < args.per:
                taken[row[b]] += 1
                add(i, "범주 %s=%s" % (args.by, row[b]))

    rng = random.Random(0)
    ordinary = [i for i in range(len(rows)) if i not in seen]
    for i in rng.sample(ordinary, min(len(ordinary), max(3, args.max - len(picks)))):
        add(i, "일반 행")

    writer = csv.writer(sys.stdout)
    writer.writerow(["_row", "_reason"] + header + ["expected (직접 계산)"])
    for i, reason in sorted(picks):
        writer.writerow([i + 1, reason] + rows[i] + [""])
    print("# %d rows picked from %d; fill 'expected' independently, then compare with the code's output." % (len(picks), len(rows)), file=sys.stderr)


if __name__ == "__main__":
    main()
