from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from core.models import PropertyWatchConfig, Retirement401kConfig, Retirement401kSnapshot
from core.zillow import property_zestimate


@dataclass(frozen=True)
class WealthWidget:
    retirement_is_available: bool
    retirement_balance: float | None
    retirement_balance_display: str
    retirement_change_usd: float | None
    retirement_change_usd_display: str
    retirement_change_pct: float | None
    retirement_change_display: str
    retirement_contributions_display: str
    retirement_last_date_label: str
    retirement_period_label: str
    retirement_chart_points: str
    retirement_chart_area_points: str
    retirement_chart_date_labels: tuple[str, ...]
    retirement_target_amount: float | None
    retirement_target_display: str
    retirement_target_delta: float | None
    retirement_target_delta_display: str
    retirement_chart_target_y: float | None
    property_is_available: bool
    property_address: str
    property_price: float | None
    property_price_display: str
    property_purchase_display: str
    property_mortgage_display: str
    property_equity_display: str
    property_equity_purchase_pct: float | None
    property_equity_purchase_pct_display: str
    property_equity_estimate_pct: float | None
    property_equity_estimate_pct_display: str
    property_change_usd: float | None
    property_change_usd_display: str
    property_change_pct: float | None
    property_change_display: str
    property_source_label: str
    property_updated_label: str
    property_error_label: str
    chart_width: int
    chart_height: int


def _format_usd(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.0f}" if value >= 1000 else f"${value:,.2f}"


def _format_change_usd(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else "-"
    amount = abs(value)
    if amount >= 1000:
        return f"{sign}${amount:,.0f}"
    return f"{sign}${amount:,.2f}"


def _format_change_pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def _chart_scale(values: list[float], extra_values: list[float] | None = None) -> tuple[float, float]:
    scale_values = list(values)
    if extra_values:
        scale_values.extend(extra_values)

    min_value = min(scale_values)
    max_value = max(scale_values)
    span = max_value - min_value or 1.0
    return min_value, span


def _value_to_chart_y(value: float, min_value: float, span: float, height: int = 40) -> float:
    return height - ((value - min_value) / span) * (height - 4) - 2


def _build_chart_points(
    values: list[float],
    width: int = 100,
    height: int = 40,
    extra_scale_values: list[float] | None = None,
) -> tuple[str, str]:
    if len(values) < 2:
        return "", ""

    min_value, span = _chart_scale(values, extra_scale_values)
    line_points: list[str] = []
    last_index = len(values) - 1

    for index, value in enumerate(values):
        x = (index / last_index) * width
        y = _value_to_chart_y(value, min_value, span, height)
        line_points.append(f"{x:.1f},{y:.1f}")

    first_point = line_points[0]
    area_points = (
        f"0.0,{height:.1f} {first_point} "
        + " ".join(line_points[1:])
        + f" {width:.1f},{height:.1f}"
    )
    return " ".join(line_points), area_points


def _chart_target_y(
    target_amount: float,
    values: list[float],
    height: int = 40,
) -> float | None:
    if len(values) < 2:
        return None

    min_value, span = _chart_scale(values, [target_amount])
    return _value_to_chart_y(target_amount, min_value, span, height)


def _format_target_delta(target_amount: float, current_balance: float) -> tuple[float, str]:
    delta = target_amount - current_balance
    remaining = abs(delta)
    if remaining >= 1000:
        amount_display = f"${remaining:,.0f}"
    else:
        amount_display = f"${remaining:,.2f}"

    if delta > 0:
        return delta, f"{amount_display} to goal"
    if delta < 0:
        return delta, f"{amount_display} over goal"
    return delta, "At goal"


def _chart_date_labels(dates: list, label_count: int = 5) -> tuple[str, ...]:
    if len(dates) < 2:
        return ()

    labels: list[str] = []
    last_index = label_count - 1
    total = len(dates) - 1

    for index in range(label_count):
        if last_index == 0:
            when = dates[-1]
        else:
            offset = int(round(total * (index / last_index)))
            when = dates[offset]
        labels.append(when.strftime("%b %d").replace(" 0", " "))

    return tuple(labels)


def _period_label(snapshot_count: int) -> str:
    if snapshot_count < 2:
        return "—"
    if snapshot_count <= 3:
        return "Recent"
    if snapshot_count <= 6:
        return "6M"
    if snapshot_count <= 12:
        return "1Y"
    return "All"


def _load_retirement_section() -> dict:
    config = Retirement401kConfig.load()
    target_amount = float(config.target_amount) if config.target_amount else None

    empty_target = {
        "retirement_target_amount": None,
        "retirement_target_display": "—",
        "retirement_target_delta": None,
        "retirement_target_delta_display": "—",
        "retirement_chart_target_y": None,
    }

    snapshots = list(Retirement401kSnapshot.objects.all())
    if not snapshots:
        return {
            "retirement_is_available": False,
            "retirement_balance": None,
            "retirement_balance_display": "—",
            "retirement_change_usd": None,
            "retirement_change_usd_display": "—",
            "retirement_change_pct": None,
            "retirement_change_display": "—",
            "retirement_contributions_display": "—",
            "retirement_last_date_label": "Add snapshots in admin",
            "retirement_period_label": "—",
            "retirement_chart_points": "",
            "retirement_chart_area_points": "",
            "retirement_chart_date_labels": (),
            **empty_target,
        }

    values = [float(row.balance) for row in snapshots]
    dates = [row.snapshot_date for row in snapshots]
    latest = snapshots[-1]
    first = snapshots[0]

    total_contributions = sum(
        float(row.employee_contribution) + float(row.employer_match) for row in snapshots[1:]
    )

    change_usd = None
    change_pct = None
    if len(values) >= 2:
        gross_change = values[-1] - values[0]
        change_usd = gross_change - total_contributions
        invested_start = values[0] + total_contributions
        if invested_start > 0:
            change_pct = (change_usd / invested_start) * 100.0

    extra_scale_values = [target_amount] if target_amount is not None else None
    chart_points, chart_area_points = _build_chart_points(values, extra_scale_values=extra_scale_values)

    target_fields = dict(empty_target)
    if target_amount is not None:
        delta, delta_display = _format_target_delta(target_amount, values[-1])
        target_fields = {
            "retirement_target_amount": target_amount,
            "retirement_target_display": _format_usd(target_amount),
            "retirement_target_delta": delta,
            "retirement_target_delta_display": delta_display,
            "retirement_chart_target_y": _chart_target_y(target_amount, values),
        }

    return {
        "retirement_is_available": True,
        "retirement_balance": values[-1],
        "retirement_balance_display": _format_usd(values[-1]),
        "retirement_change_usd": change_usd,
        "retirement_change_usd_display": _format_change_usd(change_usd),
        "retirement_change_pct": change_pct,
        "retirement_change_display": _format_change_pct(change_pct),
        "retirement_contributions_display": _format_usd(total_contributions) if total_contributions else "—",
        "retirement_last_date_label": latest.snapshot_date.strftime("As of %b %d, %Y").replace(" 0", " "),
        "retirement_period_label": _period_label(len(snapshots)),
        "retirement_chart_points": chart_points,
        "retirement_chart_area_points": chart_area_points,
        "retirement_chart_date_labels": _chart_date_labels(dates),
        **target_fields,
    }


def _load_property_section() -> dict:
    config = PropertyWatchConfig.load()
    quote = property_zestimate()
    purchase_price = float(config.purchase_price)
    mortgage_balance = _mortgage_balance_for_now(config)
    stored_balance = float(config.mortgage_balance)
    if abs(stored_balance - mortgage_balance) >= 0.01:
        config.mortgage_balance = mortgage_balance
        config.save(update_fields=["mortgage_balance", "updated_at"])

    effective_price = quote.zestimate
    source_label = quote.source_label
    updated_label = quote.updated_label
    is_available = quote.is_available
    error_label = quote.error_label

    if effective_price is None:
        # Keep the widget usable when Zillow blocks automation (HTTP 403).
        effective_price = purchase_price
        source_label = "Cost"
        updated_label = "Manual"
        is_available = True
        error_label = ""

    change_usd = None
    change_pct = None
    equity_usd = None
    equity_purchase_pct = None
    equity_estimate_pct = None
    if effective_price is not None:
        change_usd = effective_price - purchase_price
        if purchase_price > 0:
            change_pct = (change_usd / purchase_price) * 100.0
        equity_usd = effective_price - mortgage_balance
        if purchase_price > 0:
            equity_purchase_pct = (equity_usd / purchase_price) * 100.0
        if effective_price > 0:
            equity_estimate_pct = (equity_usd / effective_price) * 100.0

    return {
        "property_is_available": is_available,
        "property_address": config.address_label,
        "property_price": effective_price,
        "property_price_display": _format_usd(effective_price),
        "property_purchase_display": _format_usd(purchase_price),
        "property_mortgage_display": _format_usd(mortgage_balance),
        "property_equity_display": _format_usd(equity_usd),
        "property_equity_purchase_pct": equity_purchase_pct,
        "property_equity_purchase_pct_display": _format_change_pct(equity_purchase_pct),
        "property_equity_estimate_pct": equity_estimate_pct,
        "property_equity_estimate_pct_display": _format_change_pct(equity_estimate_pct),
        "property_change_usd": change_usd,
        "property_change_usd_display": _format_change_usd(change_usd),
        "property_change_pct": change_pct,
        "property_change_display": _format_change_pct(change_pct),
        "property_source_label": source_label,
        "property_updated_label": updated_label,
        "property_error_label": error_label,
    }


def _elapsed_months(start_date: date, end_date: date) -> int:
    if end_date <= start_date:
        return 0

    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day < start_date.day:
        months -= 1
    return max(months, 0)


def _mortgage_balance_for_now(config: PropertyWatchConfig) -> float:
    start_balance = float(config.mortgage_start_balance)
    payment = float(config.mortgage_monthly_payment)
    annual_rate = float(config.mortgage_interest_rate) / 100.0
    start_date = config.mortgage_start_date
    now_date = timezone.localdate()
    months = _elapsed_months(start_date, now_date)

    if start_balance <= 0 or payment <= 0 or months <= 0:
        return max(start_balance, 0.0)

    monthly_rate = annual_rate / 12.0
    balance = start_balance

    for _ in range(months):
        interest_portion = balance * monthly_rate
        principal_portion = payment - interest_portion

        # If payment is too small for amortization, treat it as direct principal reduction.
        if principal_portion <= 0:
            principal_portion = payment

        balance = max(balance - principal_portion, 0.0)
        if balance <= 0:
            break

    return balance


def wealth_widget() -> WealthWidget:
    retirement = _load_retirement_section()
    property_section = _load_property_section()

    return WealthWidget(
        chart_width=100,
        chart_height=40,
        **retirement,
        **property_section,
    )
