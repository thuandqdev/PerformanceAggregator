"""Aggregate a large ad performance CSV by campaign and rank the top 10 by CTR and CPA.

Streams the input once (memory is O(campaigns)), sums spend exactly with Decimal,
ranks on exact Fractions, and rounds half-up only when formatting output.
"""

import argparse
import csv
import datetime
import decimal
import heapq
import io
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple

from formatting import format_row
from report import render_report

try:
    import resource
except ImportError:  # pragma: no cover - Windows
    resource = None

REQUIRED_COLUMNS = ("date", "campaign_id", "impressions", "clicks", "spend", "conversions")
OUTPUT_COLUMNS = (
    "campaign_id",
    "total_impressions",
    "total_clicks",
    "total_spend",
    "total_conversions",
    "CTR",
    "CPA",
)
TOP_N = 10
SPEND_PRECISION = 60
PROGRESS_EVERY = 1_000_000
MB = 1024 * 1024

EPILOG = """\
examples:
  python3 aggregator.py --input ad_data.csv --output results/
  python3 aggregator.py --input ad_data.csv --output results/ --skip-invalid --no-html

exit codes:
  0    success
  1    data error (bad header, invalid row, malformed CSV) or unwritable output
  2    bad arguments or input file not found
  130  interrupted (Ctrl+C)
"""


class InputError(Exception):
    """A problem with the input data. `skippable` marks row-value errors that --skip-invalid can bypass."""

    def __init__(self, line, reason, skippable=False):
        super().__init__(reason)
        self.line = line
        self.reason = reason
        self.skippable = skippable


class Campaign(NamedTuple):
    campaign_id: str
    impressions: int
    clicks: int
    spend: Fraction
    conversions: int
    ctr: Fraction | None
    cpa: Fraction | None


@dataclass(frozen=True)
class RunSummary:
    input_name: str
    generated_at: str
    rows_read: int
    rows_skipped: int
    campaigns: int
    elapsed_seconds: float
    peak_rss_bytes: int | None


def parse_header(header):
    """Return the column indexes (campaign_id, impressions, clicks, spend, conversions) found by name."""
    names = [name.strip() for name in header]
    missing = [column for column in REQUIRED_COLUMNS if column not in names]
    if missing:
        raise InputError(1, f"missing required column(s): {', '.join(missing)}")
    return tuple(names.index(column) for column in REQUIRED_COLUMNS[1:])


def diagnose_row(row, columns, width):
    """Explain why a row failed validation (only called on the slow path)."""
    if len(row) != width:
        return f"expected {width} columns, got {len(row)}"
    campaign_index, *numeric = columns
    if not row[campaign_index]:
        return "campaign_id is empty"
    names = REQUIRED_COLUMNS[2:]
    for name, index in zip(names, numeric):
        value = row[index]
        if name == "spend":
            try:
                spend = Decimal(value)
            except InvalidOperation:
                spend = None
            if spend is None or not spend.is_finite() or spend < 0:
                return f"spend is not a finite non-negative decimal: {value[:40]!r}"
        else:
            try:
                valid = int(value) >= 0
            except ValueError:
                valid = False
            if not valid:
                return f"{name} is not a non-negative integer: {value[:40]!r}"
    return "invalid row"


class Progress:
    """Single-line progress on stderr, rewritten in place with a carriage return."""

    def __init__(self, buffer, total_bytes):
        self._buffer = buffer
        self._total_mb = total_bytes / MB
        self._started = time.perf_counter()
        self._shown = False

    def show(self, rows):
        elapsed = time.perf_counter() - self._started
        done_mb = self._buffer.tell() / MB
        sys.stderr.write(
            f"\r{rows:,} rows | {done_mb:,.0f} / {self._total_mb:,.0f} MB | {rows / elapsed:,.0f} rows/s"
        )
        sys.stderr.flush()
        self._shown = True

    def finish(self):
        if self._shown:
            sys.stderr.write("\n")


def aggregate(reader, columns, width, skip_invalid, progress):
    """Sum impressions, clicks, spend and conversions per campaign in one pass over `reader`."""
    campaign_index, impressions_index, clicks_index, spend_index, conversions_index = columns
    totals = {}
    get = totals.get
    to_int = int
    to_decimal = Decimal
    rows = skipped = 0
    with decimal.localcontext() as context:
        context.prec = SPEND_PRECISION
        context.traps[decimal.Inexact] = True
        for row in reader:
            rows += 1
            if rows % PROGRESS_EVERY == 0 and progress is not None:
                progress.show(rows)
            try:
                if len(row) != width:
                    raise ValueError
                campaign_id = row[campaign_index]
                impressions = to_int(row[impressions_index])
                clicks = to_int(row[clicks_index])
                conversions = to_int(row[conversions_index])
                spend = to_decimal(row[spend_index])
                if (
                    not campaign_id
                    or impressions < 0
                    or clicks < 0
                    or conversions < 0
                    or not spend.is_finite()
                    or spend < 0
                ):
                    raise ValueError
            except (ValueError, InvalidOperation):
                if not skip_invalid:
                    raise InputError(
                        reader.line_num, diagnose_row(row, columns, width), skippable=True
                    ) from None
                skipped += 1
                continue
            acc = get(campaign_id)
            if acc is None:
                totals[campaign_id] = [impressions, clicks, spend, conversions]
            else:
                acc[0] += impressions
                acc[1] += clicks
                acc[2] += spend
                acc[3] += conversions
    return totals, rows, skipped


def structural_reason(exc):
    if isinstance(exc, csv.Error):
        return f"malformed CSV: {exc}"
    if isinstance(exc, UnicodeDecodeError):
        return "input is not valid UTF-8"
    if isinstance(exc, decimal.DecimalException):
        return f"total spend cannot be summed exactly within {SPEND_PRECISION} significant digits"
    return f"cannot read input: {exc.strerror or exc}"


def aggregate_file(path, skip_invalid, show_progress):
    """Open `path`, validate its header and aggregate it. Returns (totals, rows_read, rows_skipped)."""
    reader = None
    progress = None
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if header is None:
                raise InputError(1, "input file is empty (no header row)")
            columns = parse_header(header)
            if show_progress:
                progress = Progress(handle.buffer, os.path.getsize(path))
            return aggregate(reader, columns, len(header), skip_invalid, progress)
    except (csv.Error, UnicodeDecodeError, OSError, decimal.DecimalException) as exc:
        raise InputError(reader.line_num if reader else None, structural_reason(exc)) from exc
    finally:
        if progress is not None:
            progress.finish()


def rank(totals):
    """Return (top by CTR desc, top by CPA asc, CTR points, CPA points).

    Ties break on campaign_id ascending. Each points list holds (value, is_top_10) for every
    eligible campaign and feeds the report's distribution charts.
    """
    campaigns = []
    for campaign_id, (impressions, clicks, spend, conversions) in totals.items():
        exact_spend = Fraction(spend)
        campaigns.append(
            Campaign(
                campaign_id,
                impressions,
                clicks,
                exact_spend,
                conversions,
                Fraction(clicks, impressions) if impressions > 0 else None,
                exact_spend / conversions if conversions > 0 else None,
            )
        )
    top_ctr = heapq.nsmallest(
        TOP_N, (c for c in campaigns if c.ctr is not None), key=lambda c: (-c.ctr, c.campaign_id)
    )
    top_cpa = heapq.nsmallest(
        TOP_N, (c for c in campaigns if c.cpa is not None), key=lambda c: (c.cpa, c.campaign_id)
    )
    top_ctr_ids = {c.campaign_id for c in top_ctr}
    top_cpa_ids = {c.campaign_id for c in top_cpa}
    ctr_points = [(float(c.ctr), c.campaign_id in top_ctr_ids) for c in campaigns if c.ctr is not None]
    cpa_points = [(float(c.cpa), c.campaign_id in top_cpa_ids) for c in campaigns if c.cpa is not None]
    return top_ctr, top_cpa, ctr_points, cpa_points


def render_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(OUTPUT_COLUMNS)
    writer.writerows(rows)
    return buffer.getvalue()


def write_files(files):
    """Write {path: text} atomically: stage every file as a temp file, then rename them all into place."""
    staged = []
    try:
        for path, text in files.items():
            descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
            staged.append((temp_name, path))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
        while staged:
            temp_name, path = staged[0]
            os.replace(temp_name, path)
            staged.pop(0)
    finally:
        for temp_name, _ in staged:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def peak_rss_bytes():
    if resource is None:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024  # macOS reports bytes, Linux KiB


def build_parser():
    parser = argparse.ArgumentParser(
        prog="aggregator.py",
        description=(
            "Aggregate an ad performance CSV by campaign_id and write the top 10 campaigns by "
            "CTR (highest) and by CPA (lowest) as CSV files, plus an HTML report."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True, help="path to the input CSV file")
    parser.add_argument("--output", required=True, help="output directory (created if missing)")
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="skip rows with invalid values instead of stopping (malformed CSV always stops)",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress the progress line and the run summary")
    parser.add_argument("--no-html", action="store_true", help="do not write report.html")
    return parser


def report_input_error(input_path, exc):
    where = f"{input_path}:{exc.line}" if exc.line else str(input_path)
    print(f"error: {where}: {exc.reason}", file=sys.stderr)
    if exc.skippable:
        print("hint: re-run with --skip-invalid to skip invalid rows", file=sys.stderr)


def run(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    output_dir = Path(args.output)
    if not input_path.is_file():
        parser.error(f"input file not found: {input_path}")
    if output_dir.exists() and not output_dir.is_dir():
        parser.error(f"output path is not a directory: {output_dir}")

    started = time.perf_counter()
    show_progress = sys.stderr.isatty() and not args.quiet
    try:
        totals, rows_read, rows_skipped = aggregate_file(input_path, args.skip_invalid, show_progress)
    except InputError as exc:
        report_input_error(input_path, exc)
        return 1
    top_ctr, top_cpa, ctr_points, cpa_points = rank(totals)
    elapsed = time.perf_counter() - started

    if rows_skipped:
        print(f"warning: skipped {rows_skipped:,} invalid row(s)", file=sys.stderr)
    if rows_read == 0:
        print("warning: input has a header but no data rows; wrote empty result files", file=sys.stderr)

    ctr_rows = [format_row(c) for c in top_ctr]
    cpa_rows = [format_row(c) for c in top_cpa]
    summary = RunSummary(
        input_name=input_path.name,
        generated_at=datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        rows_read=rows_read,
        rows_skipped=rows_skipped,
        campaigns=len(totals),
        elapsed_seconds=elapsed,
        peak_rss_bytes=peak_rss_bytes(),
    )
    ctr_path = output_dir / "top10_ctr.csv"
    cpa_path = output_dir / "top10_cpa.csv"
    html_path = output_dir / "report.html"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_files({ctr_path: render_csv(ctr_rows), cpa_path: render_csv(cpa_rows)})
        written = [ctr_path, cpa_path]
        if not args.no_html:
            write_files({html_path: render_report(summary, top_ctr, top_cpa, ctr_points, cpa_points)})
            written.append(html_path)
    except OSError as exc:
        print(f"error: cannot write results to {output_dir}: {exc.strerror or exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"rows read:    {rows_read:,}", file=sys.stderr)
        print(f"rows skipped: {rows_skipped:,}", file=sys.stderr)
        print(f"campaigns:    {len(totals):,}", file=sys.stderr)
        print(f"elapsed:      {elapsed:.2f} s", file=sys.stderr)
        for path in written:
            print(f"wrote:        {path}", file=sys.stderr)
    return 0


def main(argv=None):
    try:
        return run(argv)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
