"""Number formatting shared by the CSV writer and the HTML report. All values come from exact Fractions."""

from fractions import Fraction


def round_half_up(value: Fraction, places: int) -> str:
    """Format a non-negative Fraction with `places` decimals, rounding half up, using only int math."""
    scale = 10**places
    n = (2 * value.numerator * scale + value.denominator) // (2 * value.denominator)
    whole, frac = divmod(n, scale)
    return f"{whole}.{frac:0{places}d}"


def group_thousands(cell: str) -> str:
    """Add thousands separators to the integer part of a numeric string; an empty string stays empty."""
    if cell == "":
        return ""
    whole, dot, frac = cell.partition(".")
    return f"{int(whole):,}{dot}{frac}"


def format_percent(ratio: Fraction, places: int) -> str:
    return f"{round_half_up(ratio * 100, places)}%"


def format_currency(amount: Fraction, places: int) -> str:
    return f"${group_thousands(round_half_up(amount, places))}"


def format_row(campaign) -> list[str]:
    """The 7 CSV cells for a campaign (campaign_id, impressions, clicks, spend, conversions, CTR, CPA)."""
    return [
        campaign.campaign_id,
        str(campaign.impressions),
        str(campaign.clicks),
        round_half_up(campaign.spend, 2),
        str(campaign.conversions),
        "" if campaign.ctr is None else round_half_up(campaign.ctr, 4),
        "" if campaign.cpa is None else round_half_up(campaign.cpa, 2),
    ]
