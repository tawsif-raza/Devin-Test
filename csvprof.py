#!/usr/bin/env python3
"""csvprof: print a quick profile of a CSV file."""

import argparse
import sys
import warnings

import pandas as pd

MISSING_FLAG_THRESHOLD = 0.30
FLAG_MARKER = "[FLAG: >30% empty]"


def detect_type(col):
    non_null = col.dropna()
    if non_null.empty:
        return "empty"
    if all(pd.api.types.is_bool(v) for v in non_null):
        return "boolean"
    if pd.api.types.is_numeric_dtype(col):
        return "number"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pd.to_datetime(col, errors="raise")
        return "date"
    except (ValueError, TypeError, OverflowError):
        return "text"


def profile(df):
    """Return a summary dict of row/column counts and per-column stats."""
    rows = len(df)
    columns = []
    for name in df.columns:
        col = df[name]
        missing = int(col.isna().sum())
        info = {
            "name": str(name),
            "type": detect_type(col),
            "missing": missing,
            "flagged": rows > 0 and missing / rows > MISSING_FLAG_THRESHOLD,
        }
        if info["type"] == "number":
            info["min"] = col.min()
            info["max"] = col.max()
            info["mean"] = col.mean()
        columns.append(info)
    return {"rows": rows, "columns": len(df.columns), "column_stats": columns}


def _fmt(value):
    if value is None or pd.isna(value):
        return "-"
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"


def format_profile(summary):
    headers = ["Column", "Type", "Missing", "Min", "Max", "Mean", "Flag"]
    table = [
        [
            c["name"],
            c["type"],
            str(c["missing"]),
            _fmt(c.get("min")),
            _fmt(c.get("max")),
            _fmt(c.get("mean")),
            FLAG_MARKER if c["flagged"] else "",
        ]
        for c in summary["column_stats"]
    ]
    widths = [max(len(r[i]) for r in [headers] + table) for i in range(len(headers))]
    right_aligned = {2, 3, 4, 5}

    def render(row):
        cells = [
            cell.rjust(w) if i in right_aligned else cell.ljust(w)
            for i, (cell, w) in enumerate(zip(row, widths))
        ]
        return "  ".join(cells).rstrip()

    lines = [
        f"Rows:    {summary['rows']}",
        f"Columns: {summary['columns']}",
        "",
        render(headers),
        "  ".join("-" * w for w in widths),
    ]
    lines.extend(render(row) for row in table)
    return "\n".join(lines)


def _fail(message):
    print(f"csvprof: error: {message}", file=sys.stderr)
    sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="csvprof", description="Print a quick profile of a CSV file."
    )
    parser.add_argument("path", help="path to the CSV file")
    args = parser.parse_args(argv)

    try:
        df = pd.read_csv(args.path)
    except FileNotFoundError:
        _fail(f"file not found: {args.path}")
    except pd.errors.EmptyDataError:
        _fail(f"file is empty: {args.path}")
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        _fail(f"could not read {args.path}: {exc}")

    if len(df) == 0:
        _fail(f"file has a header but no data rows: {args.path}")

    print(format_profile(profile(df)))


if __name__ == "__main__":
    main()
