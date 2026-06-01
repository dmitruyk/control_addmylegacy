import hashlib
import hmac
import json
import ssl
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

STABLE_ASSETS = frozenset({"USD", "USDT", "USDC", "BUSD", "FDUSD"})
USER_AGENT = "AddMyLegacyControl/1.0"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
TIME_OFFSET_CACHE_KEY = "tv_binance_us_time_offset_ms"


@dataclass(frozen=True)
class BinancePortfolio:
    is_configured: bool
    is_available: bool
    total_usd: float | None
    total_display: str
    change_usd: float | None
    change_usd_display: str
    change_pct: float | None
    change_display: str
    crypto_usd_display: str
    staking_usd_display: str
    cash_usd_display: str
    top_assets: tuple[str, ...]
    chart_points: str
    chart_area_points: str
    chart_start_display: str
    chart_end_display: str
    chart_date_labels: tuple[str, ...]
    chart_width: int
    chart_height: int
    period_label: str
    status_label: str
    error_label: str


def _api_base() -> str:
    return getattr(settings, "BINANCE_US_API_BASE", "https://api.binance.us").rstrip("/")


def _credentials() -> tuple[str, str]:
    api_key = getattr(settings, "BINANCE_US_API_KEY", "") or ""
    api_secret = getattr(settings, "BINANCE_US_API_SECRET", "") or ""
    return api_key.strip(), api_secret.strip()


def _history_days() -> int:
    return getattr(settings, "BINANCE_US_HISTORY_DAYS", 90)


def _recv_window() -> int:
    return getattr(settings, "BINANCE_US_RECV_WINDOW", 10000)


def _timestamp_ms() -> int:
    offset = cache.get(TIME_OFFSET_CACHE_KEY)
    if offset is None:
        payload = _public_get("/api/v3/time")
        server_time = int(payload["serverTime"])
        offset = server_time - int(time.time() * 1000)
        cache.set(TIME_OFFSET_CACHE_KEY, offset, 60)

    return int(time.time() * 1000) + int(offset)


def _http_get(url: str, headers: dict | None = None, timeout: int = 10) -> dict | list:
    request = Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_error_message(error: HTTPError) -> str:
    body = error.read().decode("utf-8", errors="replace")

    try:
        payload = json.loads(body)
        message = payload.get("msg") or body
    except json.JSONDecodeError:
        message = body

    return f"Binance US HTTP {error.code}: {str(message)[:160]}"


def _signed_get(path: str, params: dict, api_key: str, api_secret: str) -> dict | list:
    last_error: HTTPError | None = None

    for attempt in range(2):
        payload = dict(params)
        payload["recvWindow"] = _recv_window()
        payload["timestamp"] = _timestamp_ms()
        query = urlencode(payload)
        signature = hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"{_api_base()}{path}?{query}&signature={signature}"

        try:
            return _http_get(url, headers={"X-MBX-APIKEY": api_key})
        except HTTPError as error:
            last_error = error
            if attempt == 0 and error.code == 400:
                body = error.read().decode("utf-8", errors="replace")
                if "recvWindow" in body or "Timestamp" in body:
                    cache.delete(TIME_OFFSET_CACHE_KEY)
                    continue
            raise

    if last_error is not None:
        raise last_error

    raise RuntimeError("Binance US signed request failed")


def _public_get(path: str, params: dict | None = None) -> dict | list:
    query = urlencode(params or {})
    suffix = f"?{query}" if query else ""
    return _http_get(f"{_api_base()}{path}{suffix}")


def _parse_balance(raw_balance: str) -> float:
    try:
        return float(raw_balance)
    except (TypeError, ValueError):
        return 0.0


def _load_balances(api_key: str, api_secret: str) -> dict[str, float]:
    payload = _signed_get("/api/v3/account", {}, api_key, api_secret)
    balances: dict[str, float] = {}

    for row in payload.get("balances") or []:
        asset = (row.get("asset") or "").upper()
        if not asset:
            continue

        total = _parse_balance(row.get("free")) + _parse_balance(row.get("locked"))
        if total <= 0:
            continue

        balances[asset] = balances.get(asset, 0.0) + total

    return balances


def _load_staking_balances(api_key: str, api_secret: str) -> dict[str, float]:
    payload = _signed_get("/sapi/v1/staking/stakingBalance", {}, api_key, api_secret)
    rows = payload.get("data") if isinstance(payload, dict) else payload
    balances: dict[str, float] = {}

    for row in rows or []:
        asset = (row.get("asset") or "").upper()
        if not asset:
            continue

        total = _parse_balance(row.get("stakingAmount")) + _parse_balance(row.get("pendingRewards"))
        if total <= 0:
            continue

        balances[asset] = balances.get(asset, 0.0) + total

    return balances


def _merge_balances(spot: dict[str, float], staking: dict[str, float]) -> dict[str, float]:
    merged = dict(spot)

    for asset, qty in staking.items():
        merged[asset] = merged.get(asset, 0.0) + qty

    return merged


def _load_ticker_prices() -> dict[str, float]:
    payload = _public_get("/api/v3/ticker/price")
    prices: dict[str, float] = {}

    for row in payload:
        symbol = row.get("symbol") or ""
        try:
            prices[symbol] = float(row.get("price"))
        except (TypeError, ValueError):
            continue

    return prices


def _resolve_symbol(asset: str, prices: dict[str, float]) -> str | None:
    # Prefer USDT/USDC over USD: some *USD pairs on Binance US are stale or illiquid
    # (e.g. ZECUSD ~$30 vs ZECUSDT ~$548); the app values holdings like the USDT market.
    for quote in ("USDT", "USDC", "USD"):
        symbol = f"{asset}{quote}"
        if symbol in prices:
            return symbol

    btc_symbol = f"{asset}BTC"
    if btc_symbol in prices and "BTCUSD" in prices:
        return btc_symbol

    return None


def _asset_usd_price(asset: str, prices: dict[str, float]) -> float | None:
    if asset in STABLE_ASSETS:
        return 1.0

    symbol = _resolve_symbol(asset, prices)
    if not symbol:
        return None

    price = prices.get(symbol)
    if price is None:
        return None

    if symbol.endswith("BTC") and "BTCUSD" in prices:
        return price * prices["BTCUSD"]

    return price


def _fetch_klines_closes(symbol: str, days: int) -> list[float]:
    payload = _public_get(
        "/api/v3/klines",
        {
            "symbol": symbol,
            "interval": "1d",
            "limit": min(days, 1000),
        },
    )
    closes: list[float] = []

    for row in payload:
        try:
            closes.append(float(row[4]))
        except (IndexError, TypeError, ValueError):
            continue

    return closes


def _fetch_daily_closes(symbol: str, prices: dict[str, float], days: int) -> list[float]:
    closes = _fetch_klines_closes(symbol, days)

    if symbol.endswith("BTC") and symbol != "BTCUSD" and "BTCUSD" in prices:
        btc_closes = _fetch_klines_closes("BTCUSD", days)
        if btc_closes and len(btc_closes) == len(closes):
            return [closes[index] * btc_closes[index] for index in range(len(closes))]

    return closes


def _build_history_values(balances: dict[str, float], prices: dict[str, float], days: int) -> list[float]:
    stable_total = sum(qty for asset, qty in balances.items() if asset in STABLE_ASSETS)
    crypto_balances: list[tuple[str, float, list[float]]] = []

    for asset, qty in balances.items():
        if asset in STABLE_ASSETS:
            continue

        symbol = _resolve_symbol(asset, prices)
        if not symbol:
            continue

        closes = _fetch_daily_closes(symbol, prices, days)
        if not closes:
            continue

        crypto_balances.append((asset, qty, closes))

    if not crypto_balances:
        return [stable_total] * max(days, 2)

    series_length = max(len(closes) for _, _, closes in crypto_balances)
    values = [stable_total] * series_length

    for _, qty, closes in crypto_balances:
        offset = series_length - len(closes)
        for index, close in enumerate(closes):
            target = offset + index
            if 0 <= target < series_length:
                values[target] += qty * close

    return values


def _build_chart_points(values: list[float], width: int = 100, height: int = 40) -> tuple[str, str]:
    if len(values) < 2:
        return "", ""

    min_value = min(values)
    max_value = max(values)
    span = max_value - min_value or 1.0
    line_points: list[str] = []
    last_index = len(values) - 1

    for index, value in enumerate(values):
        x = (index / last_index) * width
        y = height - ((value - min_value) / span) * (height - 4) - 2
        line_points.append(f"{x:.1f},{y:.1f}")

    first_point = line_points[0]
    last_point = line_points[-1]
    area_points = (
        f"0.0,{height:.1f} {first_point} "
        + " ".join(line_points[1:])
        + f" {width:.1f},{height:.1f}"
    )

    return " ".join(line_points), area_points


def _portfolio_chart(
    history: list[float], total_usd: float, day_count: int
) -> tuple[str, str, str, str, tuple[str, ...]]:
    line_points, area_points = _build_chart_points(history)

    if history:
        start_value = history[0]
        end_value = history[-1]
    else:
        start_value = total_usd
        end_value = total_usd

    return (
        line_points,
        area_points,
        _format_usd(start_value),
        _format_usd(end_value),
        _chart_date_labels(day_count),
    )


def _format_usd(value: float | None) -> str:
    if value is None:
        return "—"

    return f"${value:,.2f}"


def _format_change_usd(value: float | None) -> str:
    if value is None:
        return "—"

    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def _format_change_pct(value: float | None) -> str:
    if value is None:
        return "—"

    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def _chart_date_labels(day_count: int, label_count: int = 5) -> tuple[str, ...]:
    if day_count < 2:
        return ()

    end_date = timezone.localtime(timezone.now()).date()
    start_date = end_date - timedelta(days=max(day_count - 1, 1))
    labels: list[str] = []
    last_index = label_count - 1

    for index in range(label_count):
        if last_index == 0:
            when = end_date
        else:
            offset_days = int(round((day_count - 1) * (index / last_index)))
            when = start_date + timedelta(days=offset_days)
        labels.append(when.strftime("%b %d").replace(" 0", " "))

    return tuple(labels)


def _value_balances(balances: dict[str, float], prices: dict[str, float]) -> tuple[float, list[tuple[str, float]]]:
    total = 0.0
    asset_values: list[tuple[str, float]] = []

    for asset, qty in balances.items():
        price = _asset_usd_price(asset, prices)
        if price is None:
            continue

        value = qty * price
        asset_values.append((asset, value))
        total += value

    asset_values.sort(key=lambda row: row[1], reverse=True)
    return total, asset_values


def _split_balances(
    spot: dict[str, float], staking: dict[str, float], prices: dict[str, float]
) -> tuple[float, float, float, list[tuple[str, float]]]:
    crypto_total = 0.0
    cash_total = 0.0

    for asset, qty in spot.items():
        price = _asset_usd_price(asset, prices)
        if price is None:
            continue

        value = qty * price
        if asset in STABLE_ASSETS:
            cash_total += value
        else:
            crypto_total += value

    staking_total, _ = _value_balances(staking, prices)
    _, asset_values = _value_balances(_merge_balances(spot, staking), prices)
    return crypto_total, staking_total, cash_total, asset_values


def _load_portfolio(api_key: str, api_secret: str) -> BinancePortfolio:
    days = _history_days()
    spot_balances = _load_balances(api_key, api_secret)
    staking_balances = _load_staking_balances(api_key, api_secret)
    merged_balances = _merge_balances(spot_balances, staking_balances)
    prices = _load_ticker_prices()

    crypto_total, staking_total, cash_total, asset_values = _split_balances(
        spot_balances, staking_balances, prices
    )
    total_usd = crypto_total + staking_total + cash_total
    priced_assets = len(asset_values)
    top_assets = tuple(asset for asset, _ in asset_values[:4])

    if priced_assets == 0 and not merged_balances:
        empty_chart = _empty_chart_fields()
        return BinancePortfolio(
            is_configured=True,
            is_available=True,
            total_usd=0.0,
            total_display=_format_usd(0.0),
            change_usd=0.0,
            change_usd_display=_format_change_usd(0.0),
            change_pct=0.0,
            change_display=_format_change_pct(0.0),
            crypto_usd_display=_format_usd(0.0),
            staking_usd_display=_format_usd(0.0),
            cash_usd_display=_format_usd(0.0),
            top_assets=(),
            period_label="3M",
            status_label="Balance",
            error_label="No balances returned",
            **empty_chart,
        )

    history = _build_history_values(merged_balances, prices, days)
    if history:
        history[-1] = total_usd

    change_usd = None
    change_pct = None
    if history:
        change_usd = history[-1] - history[0]
        if history[0] > 0:
            change_pct = (change_usd / history[0]) * 100.0

    chart_points, chart_area_points, chart_start_display, chart_end_display, chart_date_labels = _portfolio_chart(
        history,
        total_usd,
        len(history),
    )

    return BinancePortfolio(
        is_configured=True,
        is_available=True,
        total_usd=total_usd,
        total_display=_format_usd(total_usd),
        change_usd=change_usd,
        change_usd_display=_format_change_usd(change_usd),
        change_pct=change_pct,
        change_display=_format_change_pct(change_pct),
        crypto_usd_display=_format_usd(crypto_total),
        staking_usd_display=_format_usd(staking_total),
        cash_usd_display=_format_usd(cash_total),
        top_assets=top_assets,
        chart_points=chart_points,
        chart_area_points=chart_area_points,
        chart_start_display=chart_start_display,
        chart_end_display=chart_end_display,
        chart_date_labels=chart_date_labels,
        chart_width=100,
        chart_height=40,
        period_label="3M",
        status_label="Balance",
        error_label="",
    )


def _empty_chart_fields() -> dict[str, str | int | tuple[str, ...]]:
    return {
        "chart_points": "",
        "chart_area_points": "",
        "chart_start_display": "—",
        "chart_end_display": "—",
        "chart_date_labels": (),
        "chart_width": 100,
        "chart_height": 40,
    }


def _empty_portfolio_fields() -> dict:
    fields = _empty_chart_fields()
    return {
        "total_usd": None,
        "total_display": "—",
        "change_usd": None,
        "change_usd_display": "—",
        "change_pct": None,
        "change_display": "—",
        "crypto_usd_display": "—",
        "staking_usd_display": "—",
        "cash_usd_display": "—",
        "top_assets": (),
        "period_label": "3M",
        **fields,
    }


def _unconfigured_portfolio() -> BinancePortfolio:
    return BinancePortfolio(
        is_configured=False,
        is_available=False,
        status_label="Balance",
        error_label="Set BINANCE_US_API_KEY and BINANCE_US_API_SECRET in .env",
        **_empty_portfolio_fields(),
    )


def _unavailable_portfolio(message: str) -> BinancePortfolio:
    return BinancePortfolio(
        is_configured=True,
        is_available=False,
        status_label="Balance",
        error_label=message,
        **_empty_portfolio_fields(),
    )


def binance_us_portfolio() -> BinancePortfolio:
    cache_key = "tv_binance_us_portfolio_v6"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    api_key, api_secret = _credentials()
    if not api_key or not api_secret:
        result = _unconfigured_portfolio()
        cache.set(cache_key, result, 60)
        return result

    try:
        result = _load_portfolio(api_key, api_secret)
    except HTTPError as error:
        result = _unavailable_portfolio(_http_error_message(error))
    except URLError as error:
        reason = getattr(error, "reason", error)
        result = _unavailable_portfolio(f"Binance US connection failed: {reason}")
    except (TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError) as error:
        result = _unavailable_portfolio(f"Binance US data temporarily offline ({error.__class__.__name__})")

    cache.set(cache_key, result, getattr(settings, "BINANCE_US_CACHE_SECONDS", 300))
    return result
