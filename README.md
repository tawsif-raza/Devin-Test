# Devin-Test
This is a GitHub repo for testing Devin, nothing else.

## csvprof

A small CLI that prints a profile of a CSV file: row/column counts and, per column, the detected type (`number`, `date`, `text`), missing-value count, and `min`/`max`/`mean` for numeric columns. Columns with more than 30% missing values are marked `[FLAG: >30% empty]`.

### Install

```bash
pip install pandas pytest
```

### Usage

```bash
python csvprof.py data.csv
```

Example:

```bash
python csvprof.py tests/sample.csv
```

### Tests

```bash
pytest
```
