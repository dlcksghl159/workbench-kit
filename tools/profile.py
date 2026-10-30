#!/usr/bin/env python3
"""Zero-token data profiler.

Prints a compact per-column summary of CSV/TSV/JSON/JSONL files (and XLSX when
openpyxl is installed) so an agent can understand data without reading it into
its context. Standard library only; Python 3.8+.

Usage:
  python3 .kit/tools/profile.py <file-or-dir> [...] [--max-rows N] [--samples N] [--max-cols N]
"""
import argparse
import codecs
import csv
import json
import os
import re
import sys
from collections import Counter

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

NULL_TOKENS = {"", "null", "none", "na", "n/a", "nan", "nil", "-", "--", "?", "#n/a"}
SENTINELS = {"-999", "-9999", "9999", "99999", "999999", "-1"}
DATA_EXT = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".xlsx"}
SKIP_DIRS = {".git", ".kit", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
ENCODINGS = ("utf-8-sig", "cp949", "latin-1")
MAX_DISTINCT = 50000
ID_NAME = re.compile(r"(^|[_\s])(id|key|no|code|uuid)$|번호$|코드$|아이디$", re.IGNORECASE)

INT_RE = re.compile(r"^[+-]?\d+$")
FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
COMMA_NUM_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$")
BOOL_TOKENS = {"true", "false", "yes", "no"}
DATE_PATTERNS = (
    ("YYYY-MM-DD", re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")),
    ("YYYY/MM/DD", re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")),
    ("YYYY.MM.DD", re.compile(r"^(\d{4})\.\s?(\d{1,2})\.\s?(\d{1,2})\.?$")),
    ("datetime", re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$")),
    ("datetime/", re.compile(r"^(\d{4})/(\d{2})/(\d{2})[ T]\d{1,2}:\d{2}(:\d{2})?$")),
    ("MM/DD/YYYY?", re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")),
)
YMD_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")


def short(value, width=28):
    text = str(value).replace("\n", "\\n")
    return text if len(text) <= width else text[: width - 1] + "…"


def fmt_num(x):
    if x is None:
        return "-"
    if float(x).is_integer() and abs(x) < 1e15:
        return str(int(x))
    return "%.4g" % x


def valid_ymd(y, m, d):
    return 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31


def date_key(text):
    for fmt, rx in DATE_PATTERNS:
        m = rx.match(text)
        if not m:
            continue
        if fmt == "MM/DD/YYYY?":
            return fmt, None
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if valid_ymd(y, mo, d):
            return fmt, "%04d-%02d-%02d" % (y, mo, d)
    return None, None


class Column:
    def __init__(self, name):
        self.name = name
        self.count = 0
        self.nulls = Counter()
        self.kinds = Counter()
        self.values = Counter()
        self.overflow = False
        self.num_min = self.num_max = None
        self.num_sum = 0.0
        self.num_n = 0
        self.negatives = 0
        self.date_fmts = Counter()
        self.date_min = self.date_max = None
        self.ymd_like = 0
        self.ymd_min = self.ymd_max = None
        self.padded = 0
        self.sentinels = Counter()
        self.leading_zero = 0

    def _track(self, text):
        if text in self.values:
            self.values[text] += 1
        elif len(self.values) < MAX_DISTINCT:
            self.values[text] = 1
        else:
            self.overflow = True

    def _num(self, x):
        if x != x:  # NaN
            return
        self.num_n += 1
        self.num_sum += x
        if x < 0:
            self.negatives += 1
        self.num_min = x if self.num_min is None else min(self.num_min, x)
        self.num_max = x if self.num_max is None else max(self.num_max, x)

    def add(self, raw, missing=False):
        self.count += 1
        if missing:
            self.nulls["(missing)"] += 1
            return
        if raw is None:
            self.nulls["None"] += 1
            return
        if isinstance(raw, bool):
            self._track("true" if raw else "false")
            self.kinds["bool"] += 1
            return
        if isinstance(raw, (int, float)):
            self._track(repr(raw))
            self.kinds["int" if isinstance(raw, int) else "float"] += 1
            self._num(float(raw))
            return
        if isinstance(raw, (list, dict)):
            self._track(json.dumps(raw, ensure_ascii=False, sort_keys=True)[:200])
            self.kinds["nested"] += 1
            return
        if hasattr(raw, "isoformat"):  # datetime/date from xlsx
            raw = raw.isoformat()
        text = str(raw)
        stripped = text.strip()
        if stripped != text:
            self.padded += 1
        if stripped.lower() in NULL_TOKENS:
            self.nulls[stripped if stripped else "''"] += 1
            return
        self._track(stripped)
        if stripped in SENTINELS:
            self.sentinels[stripped] += 1
        fmt, key = date_key(stripped)
        if fmt:
            self.kinds["date"] += 1
            self.date_fmts[fmt] += 1
            if key:
                if self.date_min is None or key < self.date_min:
                    self.date_min = key
                if self.date_max is None or key > self.date_max:
                    self.date_max = key
            return
        if INT_RE.match(stripped):
            self.kinds["int"] += 1
            self._num(float(stripped))
            digits = stripped.lstrip("+-")
            if len(digits) > 1 and digits.startswith("0"):
                self.leading_zero += 1
            m = YMD_RE.match(stripped)
            if m and valid_ymd(int(m.group(1)), int(m.group(2)), int(m.group(3))):
                self.ymd_like += 1
                if self.ymd_min is None or stripped < self.ymd_min:
                    self.ymd_min = stripped
                if self.ymd_max is None or stripped > self.ymd_max:
                    self.ymd_max = stripped
            return
        if FLOAT_RE.match(stripped):
            self.kinds["float"] += 1
            self._num(float(stripped))
            return
        if COMMA_NUM_RE.match(stripped):
            self.kinds["num,comma"] += 1
            self._num(float(stripped.replace(",", "")))
            return
        self.kinds["bool" if stripped.lower() in BOOL_TOKENS else "str"] += 1

    def summary(self, rows):
        null_total = sum(self.nulls.values())
        non_null = self.count - null_total
        kinds = self.kinds.most_common()
        main = kinds[0][0] if kinds else "empty"
        distinct = "%d+" % len(self.values) if self.overflow else str(len(self.values))
        notes = []
        if null_total:
            notes.append("null=%d (%s)" % (null_total, ", ".join("%s:%d" % kv for kv in self.nulls.most_common(3))))
        if len(kinds) > 1:
            notes.append("MIXED " + "/".join("%s:%d" % kv for kv in kinds[:4]))
        if self.num_n:
            notes.append("min=%s max=%s mean=%s" % (fmt_num(self.num_min), fmt_num(self.num_max), fmt_num(self.num_sum / self.num_n)))
        if self.negatives:
            notes.append("neg=%d" % self.negatives)
        if self.sentinels:
            notes.append("sentinel? " + ", ".join("%s:%d" % kv for kv in self.sentinels.most_common(3)))
        if self.leading_zero:
            notes.append("leading-zero=%d (code, not number?)" % self.leading_zero)
        if self.date_fmts:
            fmts = ", ".join("%s:%d" % kv for kv in self.date_fmts.most_common(3))
            notes.append("dates %s%s" % (fmts, " MIXED-FORMAT" if len(self.date_fmts) > 1 else ""))
            if self.date_min:
                notes.append("%s..%s" % (self.date_min, self.date_max))
        if self.ymd_like and self.ymd_like == self.kinds.get("int", 0):
            notes.append("YYYYMMDD? %s..%s" % (self.ymd_min, self.ymd_max))
        if self.padded:
            notes.append("padded-whitespace=%d" % self.padded)
        if not self.overflow:
            repeated = [(v, c) for v, c in self.values.most_common() if c > 1]
            if non_null and len(self.values) == non_null == rows:
                notes.append("UNIQUE")
            elif ID_NAME.search(self.name.strip()) and repeated:
                notes.append("DUP-ID %d values repeat (e.g. %s×%d)" % (len(repeated), short(repeated[0][0], 16), repeated[0][1]))
            if len(self.values) <= 12:
                notes.append("values: " + ", ".join("%s:%d" % (short(v, 16), c) for v, c in self.values.most_common(6)))
            elif repeated and not ID_NAME.search(self.name.strip()):
                notes.append("top: " + ", ".join("%s:%d" % (short(v, 16), c) for v, c in repeated[:3]))
        return "%-24s %-9s %8s  %s" % (short(self.name, 24), main, distinct, " | ".join(notes))


def detect_encoding(path):
    with open(path, "rb") as fh:
        raw = fh.read(262144)
    for enc in ENCODINGS:
        try:
            codecs.getincrementaldecoder(enc)().decode(raw, final=False)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def report(path, kind, rows, cols, row_hashes, samples, truncated, extras, args):
    dup_rows = sum(c - 1 for c in row_hashes.values() if c > 1)
    size = os.path.getsize(path) if os.path.isfile(path) else 0
    print("== %s  (%s, %.1f KB)  rows=%s%s  cols=%d" % (
        path, kind, size / 1024.0, format(rows, ","), "+ (truncated)" if truncated else "", len(cols)))
    print("   %-24s %-9s %8s  %s" % ("column", "type", "distinct", "notes"))
    for col in cols[: args.max_cols]:
        print("   " + col.summary(rows))
    if len(cols) > args.max_cols:
        print("   ... %d more columns" % (len(cols) - args.max_cols))
    print("   full-row duplicates: %d" % dup_rows)
    for line in extras:
        print("   " + line)
    for row in samples:
        print("   sample: " + short(" | ".join("" if v is None else str(v) for v in row), 160))
    print()


def profile_rows(path, kind, header, row_iter, args, extras=None):
    names = [h if str(h).strip() else "col%d" % (i + 1) for i, h in enumerate(header)]
    cols = [Column(str(n)) for n in names]
    extras = list(extras or [])
    dup_names = [n for n, c in Counter(map(str, names)).items() if c > 1]
    if dup_names:
        extras.append("DUPLICATE COLUMN NAMES: %s" % ", ".join(dup_names))
    ragged = Counter()
    row_hashes = Counter()
    samples = []
    rows = 0
    truncated = False
    for row in row_iter:
        if args.max_rows and rows >= args.max_rows:
            truncated = True
            break
        rows += 1
        if len(row) != len(cols):
            ragged[len(row)] += 1
        for i, col in enumerate(cols):
            if i < len(row):
                col.add(row[i])
            else:
                col.add(None, missing=True)
        row_hashes[hash(tuple("" if v is None else str(v) for v in row))] += 1
        if len(samples) < args.samples:
            samples.append(row)
    if ragged:
        extras.append("RAGGED ROWS (field count != %d): %s" % (len(cols), ", ".join("%d fields:%d" % kv for kv in ragged.most_common(4))))
    report(path, kind, rows, cols, row_hashes, samples, truncated, extras, args)


def profile_csv(path, args):
    ext = os.path.splitext(path)[1].lower()
    enc = detect_encoding(path)
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
        header = next(reader, None)
        if header is None:
            print("== %s: empty file\n" % path)
            return
        profile_rows(path, "CSV enc=%s delim=%r" % (enc, delim), header, reader, args)


def flatten(record, prefix=""):
    out = {}
    for key, value in record.items():
        name = "%s.%s" % (prefix, key) if prefix else str(key)
        if isinstance(value, dict) and value and not prefix:
            out.update(flatten(value, name))
        else:
            out[name] = value
    return out


def profile_records(path, kind, records, args, extras=None):
    extras = list(extras or [])
    non_dict = sum(1 for r in records if not isinstance(r, dict))
    if non_dict:
        extras.append("non-object records skipped: %d" % non_dict)
    flat = [flatten(r) for r in records if isinstance(r, dict)]
    header = []
    seen = set()
    for rec in flat:
        for key in rec:
            if key not in seen:
                seen.add(key)
                header.append(key)
    cols = [Column(h) for h in header]
    row_hashes = Counter()
    rows = 0
    truncated = False
    for rec in flat:
        if args.max_rows and rows >= args.max_rows:
            truncated = True
            break
        rows += 1
        for col in cols:
            if col.name in rec:
                col.add(rec[col.name])
            else:
                col.add(None, missing=True)
        row_hashes[hash(json.dumps(rec, sort_keys=True, ensure_ascii=False, default=str))] += 1
    samples = [[rec.get(h) for h in header] for rec in flat[: args.samples]]
    report(path, kind, rows, cols, row_hashes, samples, truncated, extras, args)


def find_record_list(data, path="$", depth=0):
    if isinstance(data, list) and data and sum(isinstance(x, dict) for x in data) >= len(data) / 2:
        return path, data
    if isinstance(data, dict) and depth < 3:
        best = None
        for key, value in data.items():
            found = find_record_list(value, "%s.%s" % (path, key), depth + 1)
            if found and (best is None or len(found[1]) > len(best[1])):
                best = found
        return best
    return None


def outline(data, path="$", depth=0, budget=None):
    budget = budget if budget is not None else [40]
    if budget[0] <= 0:
        return
    budget[0] -= 1
    if isinstance(data, dict):
        print("   %s: object(%d keys)" % (path, len(data)))
        if depth < 3:
            for key, value in list(data.items())[:15]:
                outline(value, "%s.%s" % (path, key), depth + 1, budget)
    elif isinstance(data, list):
        print("   %s: array(%d)" % (path, len(data)))
        if data and depth < 3:
            outline(data[0], path + "[0]", depth + 1, budget)
    else:
        print("   %s: %s = %s" % (path, type(data).__name__, short(data, 40)))


def read_jsonl(path, enc, args):
    records, bad = [], 0
    with open(path, encoding=enc, errors="replace") as fh:
        for line in fh:
            if args.max_rows and len(records) >= args.max_rows:
                break
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                bad += 1
    return records, bad


def profile_json(path, args):
    ext = os.path.splitext(path)[1].lower()
    enc = detect_encoding(path)
    if ext in (".jsonl", ".ndjson"):
        records, bad = read_jsonl(path, enc, args)
        profile_records(path, "JSONL enc=%s" % enc, records, args, ["unparseable lines: %d" % bad] if bad else [])
        return
    try:
        with open(path, encoding=enc, errors="replace") as fh:
            data = json.load(fh)
    except ValueError as exc:
        records, bad = read_jsonl(path, enc, args)
        if records:
            profile_records(path, "JSON-lines enc=%s" % enc, records, args, ["unparseable lines: %d" % bad] if bad else [])
        else:
            print("== %s: invalid JSON (%s)\n" % (path, exc))
        return
    found = find_record_list(data)
    if found:
        where, records = found
        profile_records(path, "JSON records at %s" % where, records, args)
        if not (isinstance(data, list)):
            print("   (top-level structure)")
            outline(data)
            print()
    else:
        print("== %s (JSON, no record list found)" % path)
        outline(data)
        print()


def profile_xlsx(path, args):
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("== %s: XLSX needs openpyxl, which is not installed. Ask the human before installing anything.\n" % path)
        return
    import openpyxl

    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for sheet in book.worksheets:
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            print("== %s [%s]: empty sheet\n" % (path, sheet.title))
            continue
        profile_rows("%s [%s]" % (path, sheet.title), "XLSX", ["" if h is None else h for h in header], rows, args)


def iter_paths(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
                for name in sorted(files):
                    if os.path.splitext(name)[1].lower() in DATA_EXT:
                        yield os.path.join(root, name)
        else:
            yield p


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--max-rows", type=int, default=1000000, help="rows per file (0 = all)")
    parser.add_argument("--samples", type=int, default=2, help="sample rows to print")
    parser.add_argument("--max-cols", type=int, default=60)
    args = parser.parse_args()
    found = False
    for path in iter_paths(args.paths):
        found = True
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".json", ".jsonl", ".ndjson"):
                profile_json(path, args)
            elif ext == ".xlsx":
                profile_xlsx(path, args)
            else:
                profile_csv(path, args)
        except Exception as exc:  # keep going; report the failure instead of hiding it
            print("== %s: ERROR %s: %s\n" % (path, type(exc).__name__, exc))
    if not found:
        print("no data files found (looked for: %s)" % ", ".join(sorted(DATA_EXT)))


if __name__ == "__main__":
    main()
