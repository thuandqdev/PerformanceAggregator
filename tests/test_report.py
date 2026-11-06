import csv
from fractions import Fraction
from html.parser import HTMLParser

from aggregator import Campaign, RunSummary, main
from formatting import format_currency, format_percent, group_thousands
from report import axis_places, histogram, nice_axis, render_report

HEADER = "date,campaign_id,impressions,clicks,spend,conversions\n"


def make_summary(**overrides):
    values = {
        "input_name": "ad.csv",
        "generated_at": "2026-11-06 10:00 UTC",
        "rows_read": 1234,
        "rows_skipped": 0,
        "campaigns": 3,
        "elapsed_seconds": 1.5,
        "peak_rss_bytes": 50 * 1024 * 1024,
    }
    values.update(overrides)
    return RunSummary(**values)


def make_campaign(campaign_id="A", impressions=100, clicks=10, spend="5", conversions=1):
    spend = Fraction(spend)
    return Campaign(
        campaign_id,
        impressions,
        clicks,
        spend,
        conversions,
        Fraction(clicks, impressions) if impressions else None,
        spend / conversions if conversions else None,
    )


class PageParser(HTMLParser):
    """Collects table titles, role="img" elements and table rank cells."""

    def __init__(self):
        super().__init__()
        self.table_titles = []
        self.charts = []
        self.ranks = []
        self._table_depth = 0
        self._in_rank = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self._table_depth += 1
        if self._table_depth and "title" in attrs:
            self.table_titles.append(attrs["title"])
        if attrs.get("role") == "img":
            self.charts.append(attrs)
        self._in_rank = tag == "td" and attrs.get("class") == "rank"

    def handle_endtag(self, tag):
        if tag == "table":
            self._table_depth -= 1

    def handle_data(self, data):
        if self._in_rank:
            self.ranks.append(data)
            self._in_rank = False


def parse(page):
    parser = PageParser()
    parser.feed(page)
    return parser


def run_to_html(tmp_path, body):
    source = tmp_path / "ad.csv"
    source.write_text(HEADER + body, encoding="utf-8")
    out = tmp_path / "out"
    assert main(["--input", str(source), "--output", str(out)]) == 0
    return out


def test_campaign_id_is_html_escaped():
    campaign = make_campaign("<script>alert(1)</script>")
    page = render_report(make_summary(input_name="<b>x</b>.csv"), [campaign], [campaign], [(0.1, True)], [(5.0, True)])
    assert "<script" not in page
    assert "<b>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_every_csv_cell_is_a_title_in_the_html_tables(tmp_path):
    out = run_to_html(
        tmp_path,
        "d,A,12000,300,45.50,12\nd,B,8000,120,28.00,4\nd,A,14000,340,48.20,15\nd,C,10000,200,36.00,0\n",
    )
    titles = set(parse((out / "report.html").read_text(encoding="utf-8")).table_titles)
    for name in ("top10_ctr.csv", "top10_cpa.csv"):
        with open(out / name, newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))[1:]
        assert rows
        for row in rows:
            for cell in row:
                if cell:
                    assert cell in titles, cell


def test_empty_state_when_no_eligible_campaigns(tmp_path):
    out = run_to_html(tmp_path, "d,A,0,0,5.00,0\n")
    page = (out / "report.html").read_text(encoding="utf-8")
    assert page.count("No eligible campaigns") >= 2
    assert parse(page).charts == []
    assert (out / "top10_ctr.csv").read_text(encoding="utf-8").count("\n") == 1
    assert (out / "top10_cpa.csv").read_text(encoding="utf-8").count("\n") == 1


def test_null_cells_render_dash_with_title():
    campaign = make_campaign(conversions=0)
    page = render_report(make_summary(), [campaign], [], [(0.1, True)], [])
    assert 'title="CPA is undefined: the campaign has 0 conversions">&mdash;</span>' in page


def test_report_is_self_contained():
    campaign = make_campaign()
    page = render_report(make_summary(rows_skipped=3), [campaign], [campaign], [(0.1, True)], [(5.0, True)])
    for forbidden in ("http://", "https://", "<script", "<link"):
        assert forbidden not in page
    assert "<style>" in page
    assert "prefers-color-scheme: dark" in page
    assert "check input" in page


def test_group_thousands():
    assert group_thousands("0") == "0"
    assert group_thousands("999") == "999"
    assert group_thousands("1000") == "1,000"
    assert group_thousands("1234567.89") == "1,234,567.89"
    assert group_thousands("") == ""


def test_percent_and_currency_formatting():
    assert format_percent(Fraction(0), 4) == "0.0000%"
    assert format_percent(Fraction(275, 10000), 2) == "2.75%"
    assert format_percent(Fraction(5, 10000), 1) == "0.1%"  # 0.05 rounds half up
    assert format_percent(Fraction(1, 8), 1) == "12.5%"
    assert format_currency(Fraction(0), 2) == "$0.00"
    assert format_currency(Fraction(1, 8), 2) == "$0.13"
    assert format_currency(Fraction(39478033396, 100), 2) == "$394,780,333.96"
    assert format_currency(Fraction(1000), 4) == "$1,000.0000"


def test_histogram_normal_case_splits_top_and_other():
    points = [(0.0, False), (1.0, True), (1.0, True), (4.0, False), (3.9, False), (2.0, False)]
    bins = histogram(points, bins=4)
    assert len(bins) == 4
    assert bins[0].low == 0.0 and bins[-1].high == 4.0
    assert sum(b.top for b in bins) == 2
    assert sum(b.other for b in bins) == 4
    assert bins[-1].other == 2  # the maximum lands in the last bin


def test_histogram_all_equal_and_single_value():
    equal = histogram([(2.5, True), (2.5, False), (2.5, False)], bins=16)
    assert len(equal) == 1
    assert (equal[0].top, equal[0].other) == (1, 2)
    single = histogram([(7.0, True)])
    assert len(single) == 1 and single[0].top == 1
    assert histogram([]) == []


def test_axis_helpers():
    assert nice_axis(1) == (1, 1)
    assert nice_axis(4) == (1, 4)
    assert nice_axis(7) == (2, 8)
    assert nice_axis(47) == (20, 60)
    assert axis_places(0, 2) == 2
    assert axis_places(0.0076, 2) == 4
    assert axis_places(500, 2) == 2


def test_report_has_two_labelled_charts_and_rank_column(tmp_path):
    body = "".join(f"d,C{i:02d},1000,{10 + i},{100 + i}.00,{5 + i}\n" for i in range(12))
    out = run_to_html(tmp_path, body)
    parsed = parse((out / "report.html").read_text(encoding="utf-8"))
    assert len(parsed.charts) == 2
    assert all(chart["aria-labelledby"] for chart in parsed.charts)
    assert parsed.ranks == [str(n) for n in range(1, 11)] * 2


def test_single_campaign_report_renders(tmp_path):
    out = run_to_html(tmp_path, "d,ONLY,1000,25,10.00,2\n")
    page = (out / "report.html").read_text(encoding="utf-8")
    assert "The only campaign has a CTR of 2.50%." in page
    assert "$5.00" in page
