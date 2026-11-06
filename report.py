"""Render the self-contained HTML report (inline CSS and SVG, no JavaScript, no external resources)."""

import math
from fractions import Fraction
from html import escape
from string import Template
from typing import NamedTuple

from formatting import format_currency, format_percent, format_row, group_thousands

MB = 1024 * 1024
BINS = 16
CTR_FILE = "top10_ctr.csv"
CPA_FILE = "top10_cpa.csv"
NULL_TITLES = {
    "CTR": "CTR is undefined: the campaign has 0 impressions",
    "CPA": "CPA is undefined: the campaign has 0 conversions",
}

# Chart geometry, in SVG user units (the viewBox scales to the card width).
VIEW_W, VIEW_H = 420, 250
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 36, 8, 10, 30
MAX_BAR = 24
GAP = 2
RADIUS = 4

PAGE = Template(
    """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Ad Performance Report</title>
<style>
:root {
  --bg: #f9f9f7;
  --surface: #fcfcfb;
  --text: #0b0b0b;
  --text-2: #52514e;
  --muted: #6b6a65;
  --border: #e1e0d9;
  --axis: #c3c2b7;
  --accent: #256abf;
  --accent-hover: #1c5cab;
  --on-accent: #ffffff;
  --top: #1c5cab;
  --other: #86b6ef;
  --tint: rgba(37, 106, 191, 0.07);
  --zebra: rgba(11, 11, 11, 0.025);
  --hover: rgba(37, 106, 191, 0.07);
  --warn-bg: #fff3d1;
  --warn-text: #7a4b00;
  --shadow: 0 1px 2px rgba(11, 11, 11, 0.05);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d0d0d;
    --surface: #1a1a19;
    --text: #f0efec;
    --text-2: #c3c2b7;
    --muted: #898781;
    --border: #2c2c2a;
    --axis: #383835;
    --accent: #6da7ec;
    --accent-hover: #8dbbf1;
    --on-accent: #0d0d0d;
    --top: #6da7ec;
    --other: #184f95;
    --tint: rgba(109, 167, 236, 0.10);
    --zebra: rgba(255, 255, 255, 0.025);
    --hover: rgba(255, 255, 255, 0.06);
    --warn-bg: #3a2d0a;
    --warn-text: #ffd27a;
    --shadow: none;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 1120px; margin: 0 auto; padding: 24px 16px 56px; }
@media (min-width: 720px) { main { padding: 40px 24px 72px; } }
h1 { margin: 0; font-size: 28px; line-height: 1.2; font-weight: 700; letter-spacing: -0.01em; }
h2 { margin: 0 0 16px; font-size: 20px; line-height: 1.3; font-weight: 650; }
h3 { margin: 0; font-size: 15px; font-weight: 650; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
a { color: var(--accent); text-underline-offset: 3px; }
a:focus-visible, .table-wrap:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.page-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 8px 24px; margin-bottom: 32px; }
.meta { margin: 8px 0 0; color: var(--muted); font-size: 13px; }
.downloads { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; width: 100%; }
@media (min-width: 720px) { .downloads { width: auto; } }
.download {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; border-radius: 10px;
  background: var(--accent); color: var(--on-accent);
  text-decoration: none; box-shadow: var(--shadow);
  transition: background-color 120ms ease;
}
.download:hover { background: var(--accent-hover); }
.download svg { flex: none; width: 20px; height: 20px; }
.download .what { display: block; font-size: 14px; font-weight: 650; line-height: 1.3; }
.download .file { display: block; font-size: 12px; line-height: 1.3; opacity: 0.85; white-space: nowrap; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); }
.highlights { display: grid; grid-template-columns: 1fr; gap: 16px; margin-bottom: 16px; }
@media (min-width: 600px) { .highlights { grid-template-columns: 1fr 1fr; } }
.tile { padding: 24px; }
.tile .label { margin: 0; color: var(--muted); font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.tile .winner { margin: 8px 0 0; font-size: 28px; line-height: 1.2; font-weight: 700; overflow-wrap: anywhere; }
.tile .value { margin: 4px 0 0; color: var(--accent); font-size: 20px; font-weight: 650; }
.tile .formula { margin: 8px 0 0; color: var(--muted); font-size: 13px; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px 24px; margin: 0 0 40px; padding: 16px 24px; }
.stat dt { color: var(--muted); font-size: 13px; }
.stat dd { margin: 0; font-size: 15px; font-weight: 650; }
.stat.warn { background: var(--warn-bg); color: var(--warn-text); border-radius: 8px; padding: 4px 12px; }
.stat.warn dt { color: var(--warn-text); }

section { margin-bottom: 40px; }
.charts { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 800px) { .charts { grid-template-columns: 1fr 1fr; } }
.chart { padding: 16px 16px 12px; }
.legend { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 16px; margin: 8px 0; color: var(--text-2); font-size: 13px; }
.legend .keys { display: flex; gap: 16px; }
.key i { display: inline-block; width: 12px; height: 12px; margin-right: 6px; border-radius: 3px; vertical-align: -1px; }
.key .top { background: var(--top); }
.key .other { background: var(--other); }
.chart svg { display: block; width: 100%; height: auto; }
.chart .caption { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
.grid { stroke: var(--border); stroke-width: 1; }
.baseline { stroke: var(--axis); stroke-width: 1; }
.tick { fill: var(--muted); font-size: 11px; font-family: inherit; }
.seg-top { fill: var(--top); }
.seg-other { fill: var(--other); }
.hit { fill: transparent; }
.bin:hover .hit { fill: var(--hover); }

.table-title { margin-bottom: 8px; }
.table-wrap { max-height: 70vh; overflow: auto; }
table { width: 100%; min-width: 820px; border-collapse: separate; border-spacing: 0; }
th, td { padding: 12px 16px; white-space: nowrap; border-top: 1px solid var(--border); }
thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  border-top: 0;
  background: var(--surface);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 600;
  text-align: right;
  vertical-align: bottom;
  box-shadow: inset 0 -1px 0 var(--border);
}
thead th.left, tbody th { text-align: left; }
td { text-align: right; font-variant-numeric: tabular-nums; }
tbody th { font-weight: 600; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 14px; }
td.rank { color: var(--muted); text-align: left; width: 1%; }
tbody tr:nth-child(even) { background: var(--zebra); }
tbody tr:hover { background: var(--hover); }
.ranked { background-color: var(--tint); }
td.ranked { font-weight: 650; }
.sort { display: block; color: var(--muted); font-size: 12px; font-weight: 500; }
.null { color: var(--muted); cursor: help; }
.empty { margin: 0; padding: 24px; color: var(--muted); }

.method { padding: 24px; color: var(--text-2); font-size: 14px; }
.method h2 { color: var(--text); }
.method ul { margin: 0; padding-left: 20px; }
.method li { margin-bottom: 8px; }

@media (max-width: 600px) {
  h1 { font-size: 24px; }
  .tile { padding: 16px; }
  .stats { padding: 16px; }
  .method { padding: 16px; }
}
@media print {
  body { background: #fff; color: #000; }
  .card { box-shadow: none; }
  .downloads { display: none; }
  .table-wrap { max-height: none; overflow: visible; }
  thead { display: table-header-group; }
  tr, .card { break-inside: avoid; }
  main { padding: 0; }
}
</style>
</head>
<body>
<main>
<header class="page-header">
<div>
<h1>Ad Performance Report</h1>
<p class="meta"><code>$input_name</code> &middot; $rows_read rows processed &middot; generated $generated_at</p>
</div>
<nav class="downloads" aria-label="Download results">
<a class="download" href="$ctr_file" download><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 3v10M5.5 8.5 10 13l4.5-4.5M4 16.5h12"/></svg><span><span class="what">Top 10 by CTR</span><span class="file">$ctr_file</span></span></a>
<a class="download" href="$cpa_file" download><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 3v10M5.5 8.5 10 13l4.5-4.5M4 16.5h12"/></svg><span><span class="what">Top 10 by CPA</span><span class="file">$cpa_file</span></span></a>
</nav>
</header>
<h2 class="sr-only">Highlights</h2>
<div class="highlights">
$tiles
</div>
<dl class="card stats">
$stats
</dl>
<section>
<h2>Distribution across campaigns</h2>
<div class="charts">
$charts
</div>
</section>
$ctr_section
$cpa_section
<section class="card method">
<h2>Methodology</h2>
<ul>
<li><strong>CTR</strong> = total clicks &divide; total impressions, computed from each campaign's totals (not an average of row-level rates). Campaigns with 0 impressions have no CTR and are excluded from the CTR ranking.</li>
<li><strong>CPA</strong> = total spend &divide; total conversions. Campaigns with 0 conversions have no CPA and are excluded from the CPA ranking.</li>
<li>Ranking uses exact values before rounding; ties are broken by campaign ID in ascending order.</li>
<li>Rounding is half up. This page shows CTR as a percentage and Spend and CPA in dollars; the ranked metric carries 4 decimals so close rows stay distinguishable, and hovering any number shows the exact CSV value.</li>
<li>The CSV files keep the challenge's format: CTR as a ratio with 4 decimals, Spend and CPA with 2.</li>
</ul>
</section>
</main>
</body>
</html>
"""
)


class Bin(NamedTuple):
    low: float
    high: float
    top: int
    other: int


def histogram(points, bins=BINS):
    """Bin (value, is_top) points into equal-width bins between min and max; all-equal values give one bin."""
    if not points:
        return []
    values = [value for value, _ in points]
    low, high = min(values), max(values)
    if low == high:
        bins = 1
    width = (high - low) / bins
    counts = [[0, 0] for _ in range(bins)]
    for value, is_top in points:
        index = 0 if width == 0 else min(int((value - low) / width), bins - 1)
        counts[index][0 if is_top else 1] += 1
    return [
        Bin(low + i * width, high if i == bins - 1 else low + (i + 1) * width, top, other)
        for i, (top, other) in enumerate(counts)
    ]


def nice_axis(max_count):
    """Return (step, ceiling) for an integer y axis with at most 4 intervals."""
    magnitude = 1
    while True:
        for factor in (1, 2, 5):
            step = factor * magnitude
            if math.ceil(max_count / step) <= 4:
                return step, step * math.ceil(max_count / step)
        magnitude *= 10


def axis_places(span, minimum):
    """Decimals needed so tick labels across `span` stay distinct."""
    if span <= 0:
        return minimum
    return max(minimum, min(8, math.ceil(-math.log10(span)) + 1))


def _stat(label, value, warn=False):
    if warn:
        return (
            f'<div class="stat warn"><dt>{escape(label)}</dt>'
            f'<dd><span aria-hidden="true">&#9888;</span> {escape(value)} &middot; check input</dd></div>'
        )
    return f'<div class="stat"><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>'


def _stats(summary):
    stats = [
        _stat("Campaigns", f"{summary.campaigns:,}"),
        _stat("Rows skipped", f"{summary.rows_skipped:,}", warn=summary.rows_skipped > 0),
        _stat("Processing time", f"{summary.elapsed_seconds:.2f} s"),
    ]
    if summary.peak_rss_bytes is not None:
        stats.append(_stat("Peak memory", f"{summary.peak_rss_bytes / MB:,.0f} MB"))
    return "\n".join(stats)


def _tile(label, winner, value, formula):
    if winner is None:
        return (
            f'<div class="card tile"><p class="label">{escape(label)}</p>'
            f'<p class="winner">&mdash;</p><p class="formula">No eligible campaigns</p></div>'
        )
    return (
        f'<div class="card tile"><p class="label">{escape(label)}</p>'
        f'<p class="winner">{escape(winner)}</p><p class="value">{escape(value)}</p>'
        f'<p class="formula">{escape(formula)}</p></div>'
    )


def _tiles(top_ctr, top_cpa):
    best_ctr = top_ctr[0] if top_ctr else None
    best_cpa = top_cpa[0] if top_cpa else None
    return "\n".join(
        [
            _tile(
                "Highest CTR",
                best_ctr and best_ctr.campaign_id,
                best_ctr and format_percent(best_ctr.ctr, 4),
                "clicks ÷ impressions",
            ),
            _tile(
                "Lowest CPA",
                best_cpa and best_cpa.campaign_id,
                best_cpa and format_currency(best_cpa.cpa, 4),
                "spend ÷ conversions",
            ),
        ]
    )


def _segment_path(x, y, width, height, rounded):
    """A bar segment, square at the bottom; rounded at the top only when it ends the stack."""
    radius = min(RADIUS, width / 2, height) if rounded else 0
    if radius <= 0:
        return f"M{x:.2f},{y:.2f}h{width:.2f}v{height:.2f}h{-width:.2f}z"
    return (
        f"M{x:.2f},{y + height:.2f}V{y + radius:.2f}Q{x:.2f},{y:.2f} {x + radius:.2f},{y:.2f}"
        f"H{x + width - radius:.2f}Q{x + width:.2f},{y:.2f} {x + width:.2f},{y + radius:.2f}"
        f"V{y + height:.2f}z"
    )


def _chart(chart_id, title, format_value, bins, to_display):
    """One card: heading, legend, stacked histogram SVG and a one-sentence caption."""
    heading = f'<h3 id="{chart_id}-title">{escape(title)}</h3>'
    if not bins:
        return f'<div class="card chart">{heading}<p class="empty">No eligible campaigns</p></div>'

    low, high = bins[0].low, bins[-1].high
    places = axis_places(to_display(high) - to_display(low), 2)

    def label(value, extra=0):
        return format_value(Fraction(value), places + extra)

    total = sum(b.top + b.other for b in bins)
    step, ceiling = nice_axis(max(b.top + b.other for b in bins))
    plot_w = VIEW_W - MARGIN_LEFT - MARGIN_RIGHT
    plot_h = VIEW_H - MARGIN_TOP - MARGIN_BOTTOM
    base = MARGIN_TOP + plot_h
    unit = plot_h / ceiling
    slot = plot_w / len(bins)
    bar_w = min(MAX_BAR, slot - GAP)

    parts = []
    for count in range(0, ceiling + 1, step):
        y = base - count * unit
        if count:
            parts.append(f'<line class="grid" x1="{MARGIN_LEFT}" x2="{VIEW_W - MARGIN_RIGHT}" y1="{y:.2f}" y2="{y:.2f}"/>')
        parts.append(f'<text class="tick" x="{MARGIN_LEFT - 6}" y="{y + 4:.2f}" text-anchor="end">{count}</text>')
    for index, b in enumerate(bins):
        slot_x = MARGIN_LEFT + index * slot
        x = slot_x + (slot - bar_w) / 2
        tip = f"{label(b.low, 1)}–{label(b.high, 1)}: {b.top} top-10, {b.other} other"
        other_h = b.other * unit
        top_h = b.top * unit
        segments = []
        if b.other:
            segments.append(
                f'<path class="seg-other" d="{_segment_path(x, base - other_h, bar_w, other_h, b.top == 0)}"/>'
            )
        if b.top:
            gap = GAP if b.other else 0
            height = max(top_h - gap, 1.0)
            segments.append(
                f'<path class="seg-top" d="{_segment_path(x, base - other_h - top_h, bar_w, height, True)}"/>'
            )
        parts.append(
            f'<g class="bin"><title>{escape(tip)}</title>'
            f'<rect class="hit" x="{slot_x:.2f}" y="{MARGIN_TOP}" width="{slot:.2f}" height="{plot_h}"/>'
            f'{"".join(segments)}</g>'
        )
    parts.append(f'<line class="baseline" x1="{MARGIN_LEFT}" x2="{VIEW_W - MARGIN_RIGHT}" y1="{base}" y2="{base}"/>')
    if len(bins) == 1:
        ticks = [(MARGIN_LEFT + plot_w / 2, low, "middle")]
    else:
        ticks = [
            (MARGIN_LEFT + plot_w * k / 3, low + (high - low) * k / 3, anchor)
            for k, anchor in enumerate(("start", "middle", "middle", "end"))
        ]
    for x, value, anchor in ticks:
        parts.append(
            f'<text class="tick" x="{x:.2f}" y="{base + 18}" text-anchor="{anchor}">{escape(label(value))}</text>'
        )

    metric = title.split()[0]
    if low == high:
        who = "The only campaign has" if total == 1 else f"All {total:,} campaigns have"
        caption = f"{who} a {metric} of {label(low)}."
    else:
        caption = f"All {total:,} campaigns with a {metric} fall between {label(low)} and {label(high)}."
    caption_id = f"{chart_id}-caption"
    return (
        f'<div class="card chart">{heading}'
        f'<div class="legend"><span class="keys"><span class="key"><i class="top"></i>Top 10</span>'
        f'<span class="key"><i class="other"></i>Other campaigns</span></span>'
        f"<span>Campaigns per bin</span></div>"
        f'<svg viewBox="0 0 {VIEW_W} {VIEW_H}" role="img" aria-labelledby="{chart_id}-title {caption_id}">'
        f'{"".join(parts)}</svg>'
        f'<p class="caption" id="{caption_id}">{escape(caption)}</p></div>'
    )


def _null_cell(column):
    return f'<td><span class="null" title="{escape(NULL_TITLES[column])}">&mdash;</span></td>'


def _num_cell(text, title, ranked=False):
    css = ' class="ranked"' if ranked else ""
    return f'<td{css} title="{escape(title)}">{escape(text)}</td>'


def _row(rank, campaign, ranked_column):
    cells = format_row(campaign)
    ctr_ranked = ranked_column == "CTR"
    cpa_ranked = ranked_column == "CPA"
    if campaign.ctr is None:
        ctr_cell = _null_cell("CTR")
    else:
        ctr_cell = _num_cell(format_percent(campaign.ctr, 4 if ctr_ranked else 2), cells[5], ctr_ranked)
    if campaign.cpa is None:
        cpa_cell = _null_cell("CPA")
    else:
        cpa_cell = _num_cell(format_currency(campaign.cpa, 4 if cpa_ranked else 2), cells[6], cpa_ranked)
    return (
        f'<tr><td class="rank">{rank}</td>'
        f'<th scope="row" title="{escape(cells[0])}">{escape(cells[0])}</th>'
        f"{_num_cell(group_thousands(cells[1]), cells[1])}"
        f"{_num_cell(group_thousands(cells[2]), cells[2])}"
        f"{_num_cell(format_currency(campaign.spend, 2), cells[3])}"
        f"{_num_cell(group_thousands(cells[4]), cells[4])}"
        f"{ctr_cell}{cpa_cell}</tr>"
    )


def _header_cell(name, ranked_column):
    if name != ranked_column:
        return f'<th scope="col">{name}</th>'
    arrow, text, order = ("▼", "highest first", "descending") if name == "CTR" else ("▲", "lowest first", "ascending")
    return (
        f'<th scope="col" class="ranked" aria-sort="{order}">{name}'
        f'<span class="sort"><span aria-hidden="true">{arrow}</span> {text}</span></th>'
    )


def _table(section_id, title, rows, ranked_column):
    heading = f'<h2 class="table-title" id="{section_id}-title">{escape(title)}</h2>'
    if not rows:
        return f'<section>\n{heading}\n<div class="card"><p class="empty">No eligible campaigns</p></div>\n</section>'
    head = (
        '<th scope="col" class="left">#</th><th scope="col" class="left">Campaign</th>'
        + "".join(
            _header_cell(name, ranked_column)
            for name in ("Impressions", "Clicks", "Spend", "Conversions", "CTR", "CPA")
        )
    )
    body = "\n".join(_row(rank, campaign, ranked_column) for rank, campaign in enumerate(rows, 1))
    return (
        f"<section>\n{heading}\n"
        f'<div class="card table-wrap" role="region" aria-labelledby="{section_id}-title" tabindex="0">\n'
        f'<table aria-labelledby="{section_id}-title">\n<thead><tr>{head}</tr></thead>\n'
        f"<tbody>\n{body}\n</tbody>\n</table>\n</div>\n</section>"
    )


def render_report(summary, top_ctr, top_cpa, ctr_points, cpa_points):
    """Build the report page.

    `top_ctr` / `top_cpa` are ranked campaign records (campaign_id, impressions, clicks, spend,
    conversions, ctr, cpa; spend/ctr/cpa as Fractions). `ctr_points` / `cpa_points` hold
    (value, is_top_10) for every campaign eligible for that ranking.
    """
    charts = "\n".join(
        [
            _chart("chart-ctr", "CTR distribution", format_percent, histogram(ctr_points), lambda v: v * 100),
            _chart("chart-cpa", "CPA distribution", format_currency, histogram(cpa_points), lambda v: v),
        ]
    )
    return PAGE.substitute(
        input_name=escape(summary.input_name),
        rows_read=f"{summary.rows_read:,}",
        generated_at=escape(summary.generated_at),
        ctr_file=CTR_FILE,
        cpa_file=CPA_FILE,
        tiles=_tiles(top_ctr, top_cpa),
        stats=_stats(summary),
        charts=charts,
        ctr_section=_table("top-ctr", "Top 10 campaigns by CTR", top_ctr, "CTR"),
        cpa_section=_table("top-cpa", "Top 10 campaigns by CPA", top_cpa, "CPA"),
    )
