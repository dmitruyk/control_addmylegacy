import json
import re
import ssl
from dataclasses import dataclass
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from core.models import PropertyWatchConfig

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
NEXT_DATA_PATTERN = re.compile(
    r'<script[^>]+id="__NEXT_DATA__"[^>]*>(?P<payload>.*?)</script>',
    re.DOTALL,
)
PRICE_PATTERN = re.compile(r'"price"\s*:\s*(?P<value>\d+)')
ZESTIMATE_PATTERN = re.compile(r'"zestimate"\s*:\s*(?P<value>\d+)')


@dataclass(frozen=True)
class ZillowQuote:
    zestimate: float | None
    source_label: str
    updated_label: str
    is_available: bool
    error_label: str


def _cache_seconds() -> int:
    return getattr(settings, "ZILLOW_CACHE_SECONDS", 86400)


def _cache_key(zpid: str) -> str:
    return f"tv_zillow_zestimate_{zpid}_v1"


def _fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=12, context=SSL_CONTEXT) as response:
        return response.read().decode("utf-8", errors="replace")


def _scraperapi_key() -> str:
    return (getattr(settings, "ZILLOW_SCRAPER_API_KEY", "") or "").strip()


def _fetch_html_via_scraperapi(url: str) -> str:
    api_key = _scraperapi_key()
    if not api_key:
        raise RuntimeError("missing scraper api key")

    query = urlencode(
        {
            "api_key": api_key,
            "url": url,
            "render": "true",
            "keep_headers": "true",
        }
    )
    proxy_url = f"https://api.scraperapi.com/?{query}"
    request = Request(
        proxy_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=25, context=SSL_CONTEXT) as response:
        return response.read().decode("utf-8", errors="replace")


def _price_from_next_data(html: str) -> float | None:
    match = NEXT_DATA_PATTERN.search(html)
    if not match:
        return None

    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return None

    page_props = payload.get("props", {}).get("pageProps", {})
    component_props = page_props.get("componentProps") or {}
    cache_blob = component_props.get("gdpClientCache")

    if isinstance(cache_blob, str):
        try:
            cache_blob = json.loads(cache_blob)
        except json.JSONDecodeError:
            cache_blob = None

    if isinstance(cache_blob, dict):
        for entry in cache_blob.values():
            if not isinstance(entry, dict):
                continue
            property_data = entry.get("property")
            if not isinstance(property_data, dict):
                continue
            price = property_data.get("price") or property_data.get("zestimate")
            if price is not None:
                return float(price)

    return None


def _price_from_regex(html: str) -> float | None:
    for pattern in (ZESTIMATE_PATTERN, PRICE_PATTERN):
        match = pattern.search(html)
        if match:
            return float(match.group("value"))
    return None


def _parse_zestimate(html: str) -> float | None:
    return _price_from_next_data(html) or _price_from_regex(html)


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _format_updated_label(when) -> str:
    if when is None:
        return "Not updated yet"
    local = timezone.localtime(when)
    return local.strftime("Updated %b %d, %Y").replace(" 0", " ")


def _should_fetch(config: PropertyWatchConfig) -> bool:
    if config.cached_zestimate_at is None:
        return True

    elapsed = timezone.now() - config.cached_zestimate_at
    return elapsed.total_seconds() >= _cache_seconds()


def _persist_quote(config: PropertyWatchConfig, zestimate: float, source_label: str) -> ZillowQuote:
    config.cached_zestimate = Decimal(str(round(zestimate, 2)))
    config.cached_zestimate_at = timezone.now()
    config.save(update_fields=["cached_zestimate", "cached_zestimate_at", "updated_at"])

    quote = ZillowQuote(
        zestimate=zestimate,
        source_label=source_label,
        updated_label=_format_updated_label(config.cached_zestimate_at),
        is_available=True,
        error_label="",
    )
    cache.set(_cache_key(config.zillow_zpid), quote, _cache_seconds())
    return quote


def _quote_from_config(config: PropertyWatchConfig, source_label: str) -> ZillowQuote | None:
    manual = _decimal_to_float(config.manual_zestimate)
    if manual is not None:
        return ZillowQuote(
            zestimate=manual,
            source_label=source_label,
            updated_label=_format_updated_label(config.cached_zestimate_at),
            is_available=True,
            error_label="",
        )

    cached = _decimal_to_float(config.cached_zestimate)
    if cached is not None:
        return ZillowQuote(
            zestimate=cached,
            source_label="Cached Zestimate",
            updated_label=_format_updated_label(config.cached_zestimate_at),
            is_available=True,
            error_label="",
        )

    return None


def _try_fetch_zillow(config: PropertyWatchConfig) -> ZillowQuote | None:
    if not _should_fetch(config):
        return _quote_from_config(config, "Cached Zestimate")

    cached = cache.get(_cache_key(config.zillow_zpid))
    if cached is not None:
        return cached

    html = None
    try:
        html = _fetch_html(config.zillow_url)
    except HTTPError as error:
        if error.code == 403 and _scraperapi_key():
            try:
                html = _fetch_html_via_scraperapi(config.zillow_url)
            except (HTTPError, URLError, TimeoutError, OSError):
                html = None
        if html is None:
            fallback = _quote_from_config(config, "Manual estimate")
            if fallback is not None:
                cache.set(_cache_key(config.zillow_zpid), fallback, _cache_seconds())
                return fallback
            helper = "set manual Zestimate in admin"
            if not _scraperapi_key():
                helper = "set manual Zestimate in admin or configure ZILLOW_SCRAPER_API_KEY"
            return ZillowQuote(
                zestimate=None,
                source_label="Zestimate",
                updated_label=_format_updated_label(config.cached_zestimate_at),
                is_available=False,
                error_label=f"Zillow blocked request (HTTP {error.code}); {helper}",
            )
    except URLError as error:
        reason = getattr(error, "reason", error)
        fallback = _quote_from_config(config, "Manual estimate")
        if fallback is not None:
            cache.set(_cache_key(config.zillow_zpid), fallback, _cache_seconds())
            return fallback
        return ZillowQuote(
            zestimate=None,
            source_label="Zestimate",
            updated_label=_format_updated_label(config.cached_zestimate_at),
            is_available=False,
            error_label=f"Zillow connection failed: {reason}",
        )
    except (TimeoutError, OSError) as error:
        fallback = _quote_from_config(config, "Manual estimate")
        if fallback is not None:
            cache.set(_cache_key(config.zillow_zpid), fallback, _cache_seconds())
            return fallback
        return ZillowQuote(
            zestimate=None,
            source_label="Zestimate",
            updated_label=_format_updated_label(config.cached_zestimate_at),
            is_available=False,
            error_label=f"Zillow fetch failed ({error.__class__.__name__})",
        )

    zestimate = _parse_zestimate(html)
    if zestimate is None:
        fallback = _quote_from_config(config, "Manual estimate")
        if fallback is not None:
            cache.set(_cache_key(config.zillow_zpid), fallback, _cache_seconds())
            return fallback
        return ZillowQuote(
            zestimate=None,
            source_label="Zestimate",
            updated_label=_format_updated_label(config.cached_zestimate_at),
            is_available=False,
            error_label="Could not parse Zillow price; set manual Zestimate in admin",
        )

    return _persist_quote(config, zestimate, "Zillow Zestimate")


def property_zestimate() -> ZillowQuote:
    config = PropertyWatchConfig.load()

    manual = _decimal_to_float(config.manual_zestimate)
    if manual is not None:
        quote = ZillowQuote(
            zestimate=manual,
            source_label="Manual estimate",
            updated_label=_format_updated_label(config.cached_zestimate_at),
            is_available=True,
            error_label="",
        )
        cache.set(_cache_key(config.zillow_zpid), quote, _cache_seconds())
        return quote

    quote = _try_fetch_zillow(config)
    if quote is not None:
        return quote

    return ZillowQuote(
        zestimate=None,
        source_label="Zestimate",
        updated_label="Not updated yet",
        is_available=False,
        error_label="Add manual Zestimate or wait for daily Zillow refresh",
    )
