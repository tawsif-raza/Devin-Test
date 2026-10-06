import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import csvprof  # noqa: E402

SAMPLE = ROOT / "tests" / "sample.csv"
SCRIPT = ROOT / "csvprof.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
    )


def stats_by_name(summary):
    return {c["name"]: c for c in summary["column_stats"]}


def test_profile_sample_values():
    summary = csvprof.profile(pd.read_csv(SAMPLE))
    assert summary["rows"] == 8
    assert summary["columns"] == 3

    cols = stats_by_name(summary)
    assert cols["name"]["type"] == "text"
    assert cols["age"]["type"] == "number"
    assert cols["signup_date"]["type"] == "date"

    assert cols["name"]["missing"] == 0
    assert cols["age"]["missing"] == 1
    assert cols["signup_date"]["missing"] == 0

    assert cols["age"]["min"] == 22
    assert cols["age"]["max"] == 45
    assert cols["age"]["mean"] == pytest.approx(226 / 7)
    assert "min" not in cols["name"]
    assert not any(c["flagged"] for c in cols.values())


def test_main_sample_output(capsys):
    csvprof.main([str(SAMPLE)])
    out = capsys.readouterr().out
    assert "Rows:    8" in out
    assert "Columns: 3" in out
    lines = {line.split()[0]: line.split() for line in out.splitlines() if line.strip()}
    assert lines["name"] == ["name", "text", "0", "-", "-", "-"]
    assert lines["age"] == ["age", "number", "1", "22", "45", "32.29"]
    assert lines["signup_date"] == ["signup_date", "date", "0", "-", "-", "-"]
    assert "FLAG" not in out


def test_cli_sample_success():
    result = run_cli(SAMPLE)
    assert result.returncode == 0
    assert "Rows:    8" in result.stdout
    assert result.stderr == ""


def test_file_not_found(tmp_path):
    missing = tmp_path / "nope.csv"
    result = run_cli(missing)
    assert result.returncode != 0
    assert "file not found" in result.stderr
    assert result.stdout == ""


def test_empty_file(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    result = run_cli(empty)
    assert result.returncode != 0
    assert "file is empty" in result.stderr


def test_header_only(tmp_path):
    header_only = tmp_path / "header.csv"
    header_only.write_text("name,age,signup_date\n")
    result = run_cli(header_only)
    assert result.returncode != 0
    assert "no data rows" in result.stderr


def test_unreadable_path(tmp_path):
    result = run_cli(tmp_path)
    assert result.returncode != 0
    assert "could not read" in result.stderr


def test_main_exits_with_code_1(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        csvprof.main([str(tmp_path / "nope.csv")])
    assert exc.value.code == 1
    assert "file not found" in capsys.readouterr().err


def test_flags_mostly_empty_columns(tmp_path, capsys):
    data = tmp_path / "sparse.csv"
    # b: 2/3 missing (flagged); c: 1/3 missing (flagged, 33% > 30%); d: 0 missing.
    data.write_text("a,b,c,d\n1,,x,p\n2,,,q\n3,4,y,r\n")
    summary = csvprof.profile(pd.read_csv(data))
    cols = stats_by_name(summary)
    assert cols["b"]["flagged"]
    assert cols["c"]["flagged"]
    assert not cols["a"]["flagged"]
    assert not cols["d"]["flagged"]

    csvprof.main([str(data)])
    out = capsys.readouterr().out
    flagged = [line.split()[0] for line in out.splitlines() if "[FLAG: >30% empty]" in line]
    assert flagged == ["b", "c"]


def test_exactly_30_percent_not_flagged(tmp_path):
    data = tmp_path / "edge.csv"
    rows = ["v"] + ["" if i < 3 else str(i) for i in range(10)]
    data.write_text("\n".join(rows) + "\n")
    df = pd.read_csv(data, skip_blank_lines=False)
    assert df["v"].isna().sum() == 3
    assert not csvprof.profile(df)["column_stats"][0]["flagged"]
