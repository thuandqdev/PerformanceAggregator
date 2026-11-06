import csv
import os
import sys
from fractions import Fraction

import pytest

import aggregator
from aggregator import main
from formatting import round_half_up

HEADER = "date,campaign_id,impressions,clicks,spend,conversions\n"
README_INPUT = (  # the example table from the challenge README, in its own column order
    "campaign_id,date,impressions,clicks,spend,conversions\n"
    "CMP001,2025-01-01,12000,300,45.50,12\n"
    "CMP002,2025-01-01,8000,120,28.00,4\n"
    "CMP001,2025-01-02,14000,340,48.20,15\n"
    "CMP003,2025-01-01,5000,60,15.00,3\n"
    "CMP002,2025-01-02,8500,150,31.00,5\n"
)
CSV_HEADER = "campaign_id,total_impressions,total_clicks,total_spend,total_conversions,CTR,CPA\n"


def run(tmp_path, text, *flags, name="ad.csv", raw=None):
    source = tmp_path / name
    source.write_bytes(raw if raw is not None else text.encode("utf-8"))
    out = tmp_path / "out"
    code = main(["--input", str(source), "--output", str(out), *flags])
    return code, out


def read(out, name):
    return (out / name).read_text(encoding="utf-8")


def read_csv(out, name):
    with open(out / name, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ids(rows):
    return [row["campaign_id"] for row in rows]


def test_readme_example_exact_output(tmp_path):
    code, out = run(tmp_path, README_INPUT)
    assert code == 0
    assert read(out, "top10_ctr.csv") == (
        CSV_HEADER
        + "CMP001,26000,640,93.70,27,0.0246,3.47\n"
        + "CMP002,16500,270,59.00,9,0.0164,6.56\n"
        + "CMP003,5000,60,15.00,3,0.0120,5.00\n"
    )
    assert read(out, "top10_cpa.csv") == (
        CSV_HEADER
        + "CMP001,26000,640,93.70,27,0.0246,3.47\n"
        + "CMP003,5000,60,15.00,3,0.0120,5.00\n"
        + "CMP002,16500,270,59.00,9,0.0164,6.56\n"
    )


def test_rates_come_from_totals_not_mean_of_row_rates(tmp_path):
    text = HEADER + "d,X,10,5,1.00,1\nd,X,1000,10,1.00,1\n"
    _, out = run(tmp_path, text)
    row = read_csv(out, "top10_ctr.csv")[0]
    assert row["CTR"] == "0.0149"  # 15/1010, not (0.5 + 0.01) / 2


def test_zero_conversions_has_no_cpa(tmp_path):
    text = HEADER + "d,A,100,10,5.00,0\nd,B,100,5,5.00,1\n"
    _, out = run(tmp_path, text)
    by_ctr = read_csv(out, "top10_ctr.csv")
    assert ids(by_ctr) == ["A", "B"]
    assert by_ctr[0]["CPA"] == ""
    assert ids(read_csv(out, "top10_cpa.csv")) == ["B"]


def test_zero_impressions_has_no_ctr(tmp_path):
    text = HEADER + "d,A,0,0,5.00,2\nd,B,100,5,5.00,1\n"
    _, out = run(tmp_path, text)
    assert ids(read_csv(out, "top10_ctr.csv")) == ["B"]
    by_cpa = read_csv(out, "top10_cpa.csv")
    assert ids(by_cpa) == ["A", "B"]
    assert by_cpa[0]["CTR"] == ""


def test_ties_break_on_campaign_id_ascending(tmp_path):
    text = HEADER + "d,B,100,10,10.00,5\nd,A,100,10,10.00,5\nd,C,100,10,10.00,5\n"
    _, out = run(tmp_path, text)
    assert ids(read_csv(out, "top10_ctr.csv")) == ["A", "B", "C"]
    assert ids(read_csv(out, "top10_cpa.csv")) == ["A", "B", "C"]


def test_ranking_uses_unrounded_values(tmp_path):
    text = HEADER + "d,A,100000,12346,1.00,1\nd,B,100000,12349,1.00,1\n"
    _, out = run(tmp_path, text)
    rows = read_csv(out, "top10_ctr.csv")
    assert [row["CTR"] for row in rows] == ["0.1235", "0.1235"]
    assert ids(rows) == ["B", "A"]


def test_fewer_than_ten_campaigns_and_top_ten_cap(tmp_path):
    _, out = run(tmp_path, HEADER + "d,A,100,1,1.00,1\n")
    assert ids(read_csv(out, "top10_ctr.csv")) == ["A"]
    many = HEADER + "".join(f"d,C{i:02d},100,{i + 1},1.00,1\n" for i in range(15))
    _, out = run(tmp_path, many, name="many.csv")
    rows = read_csv(out, "top10_ctr.csv")
    assert len(rows) == 10
    assert ids(rows)[0] == "C14"


def test_header_only_writes_empty_results(tmp_path, capsys):
    code, out = run(tmp_path, HEADER)
    assert code == 0
    assert read(out, "top10_ctr.csv") == CSV_HEADER
    assert read(out, "top10_cpa.csv") == CSV_HEADER
    assert "no data rows" in capsys.readouterr().err


def test_empty_file_is_an_error(tmp_path, capsys):
    code, out = run(tmp_path, "")
    assert code == 1
    assert "empty" in capsys.readouterr().err
    assert not out.exists()


def test_missing_required_column_names_the_column(tmp_path, capsys):
    code, out = run(tmp_path, "date,campaign_id,impressions,clicks,conversions\nd,A,1,1,1\n")
    err = capsys.readouterr().err
    assert code == 1
    assert "spend" in err
    assert not out.exists()


@pytest.mark.parametrize(
    "bad_row",
    [
        "d,A,100,10,5.00",
        "d,A,-1,10,5.00,1",
        "d,A,abc,10,5.00,1",
        "d,A,12.0,10,5.00,1",
        "d,A,100,10,-5.00,1",
        "d,A,100,10,NaN,1",
        "d,A,100,10,Infinity,1",
        "d,,100,10,5.00,1",
    ],
)
def test_invalid_row_stops_by_default(tmp_path, capsys, bad_row):
    code, out = run(tmp_path, HEADER + "d,GOOD,100,10,5.00,1\n" + bad_row + "\n")
    err = capsys.readouterr().err
    assert code == 1
    assert "ad.csv:3:" in err
    assert "--skip-invalid" in err
    assert not out.exists()


def test_skip_invalid_skips_and_reports_count(tmp_path, capsys):
    text = HEADER + "d,GOOD,100,10,5.00,1\nd,A,12.0,10,5.00,1\nd,A,100,10\nd,GOOD,100,10,5.00,1\n"
    code, out = run(tmp_path, text, "--skip-invalid")
    err = capsys.readouterr().err
    assert code == 0
    assert "skipped 2 invalid row(s)" in err
    assert "rows read:    4" in err
    (row,) = read_csv(out, "top10_ctr.csv")
    assert row["total_impressions"] == "200"


def test_decimal_exactness_and_half_up_rounding(tmp_path):
    _, out = run(tmp_path, HEADER + "d,A,100,10,0.10,1\nd,A,100,10,0.20,1\n")
    assert read_csv(out, "top10_ctr.csv")[0]["total_spend"] == "0.30"
    assert round_half_up(Fraction(1, 8), 2) == "0.13"
    assert round_half_up(Fraction(5, 100000), 4) == "0.0001"
    assert round_half_up(Fraction(0), 2) == "0.00"
    assert round_half_up(Fraction(25001, 2), 2) == "12500.50"
    assert round_half_up(Fraction(1234567890123456789012345678_91, 100), 2) == "1234567890123456789012345678.91"


def test_precision_boundary(tmp_path, capsys):
    text = HEADER + "d,A,1,1,1234567890123456789012345678.90,1\nd,A,1,1,0.01,1\n"
    _, out = run(tmp_path, text)
    assert read_csv(out, "top10_ctr.csv")[0]["total_spend"] == "1234567890123456789012345678.91"

    overflow = HEADER + "d,A,1,1," + "1" + "0" * 60 + ",1\nd,A,1,1,1,1\n"
    code, out = run(tmp_path, overflow, name="overflow.csv")
    err = capsys.readouterr().err
    assert code == 1
    assert "overflow.csv:3:" in err
    assert "Traceback" not in err


@pytest.mark.parametrize("flags", [(), ("--skip-invalid",)])
def test_malformed_quoting_always_stops(tmp_path, capsys, flags):
    text = HEADER + 'd,GOOD,100,10,5.00,1\nd,"CMP001"junk,100,10,5.00,1\nd,GOOD,100,10,5.00,1\n'
    code, out = run(tmp_path, text, *flags)
    err = capsys.readouterr().err
    assert code == 1
    assert "ad.csv:3:" in err
    assert "malformed CSV" in err
    assert "Traceback" not in err
    assert not out.exists()


def test_reordered_extra_columns_and_bom(tmp_path):
    text = "spend,note,conversions,campaign_id,clicks,date,impressions\n5.00,x,2,A,10,d,100\n"
    _, out = run(tmp_path, "", raw=b"\xef\xbb\xbf" + text.encode())
    (row,) = read_csv(out, "top10_ctr.csv")
    assert row == {
        "campaign_id": "A",
        "total_impressions": "100",
        "total_clicks": "10",
        "total_spend": "5.00",
        "total_conversions": "2",
        "CTR": "0.1000",
        "CPA": "2.50",
    }


def test_missing_input_exits_2_without_output(tmp_path, capsys):
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as exit_info:
        main(["--input", str(tmp_path / "nope.csv"), "--output", str(out)])
    assert exit_info.value.code == 2
    assert "not found" in capsys.readouterr().err
    assert not out.exists()


def test_no_html_writes_only_csvs_and_stdout_stays_empty(tmp_path, capsys):
    code, out = run(tmp_path, README_INPUT, "--no-html")
    captured = capsys.readouterr()
    assert code == 0
    assert sorted(p.name for p in out.iterdir()) == ["top10_cpa.csv", "top10_ctr.csv"]
    assert captured.out == ""


def test_html_written_by_default(tmp_path):
    _, out = run(tmp_path, README_INPUT)
    assert sorted(p.name for p in out.iterdir()) == ["report.html", "top10_cpa.csv", "top10_ctr.csv"]


def test_progress_only_on_tty_and_not_quiet(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(aggregator, "PROGRESS_EVERY", 2)
    text = HEADER + "".join(f"d,A{i},100,10,1.00,1\n" for i in range(6))

    run(tmp_path, text)
    assert "\r" not in capsys.readouterr().err

    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    run(tmp_path, text, "--quiet")
    quiet = capsys.readouterr()
    assert quiet.err == ""
    assert quiet.out == ""

    run(tmp_path, text)
    shown = capsys.readouterr()
    assert "\r6 rows" in shown.err
    assert shown.out == ""


def test_no_partial_files_after_failures(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    out.mkdir()
    text = HEADER + 'd,A,100,10,5.00,1\nd,"B"junk,100,10,5.00,1\n'
    code, _ = run(tmp_path, text)
    assert code == 1
    assert list(out.iterdir()) == []

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)
    code, _ = run(tmp_path, README_INPUT, name="good.csv")
    assert code == 1
    assert "cannot write results" in capsys.readouterr().err
    assert list(out.iterdir()) == []


def test_keyboard_interrupt_exits_130(tmp_path, monkeypatch, capsys):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(aggregator, "aggregate_file", interrupt)
    code, _ = run(tmp_path, README_INPUT)
    assert code == 130
    assert capsys.readouterr().err.strip() == "interrupted"
