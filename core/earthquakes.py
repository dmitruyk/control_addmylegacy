import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


@dataclass(frozen=True)
class EarthquakeEvent:
    place: str
    magnitude: float | None
    time_label: str
    is_recent: bool


@dataclass(frozen=True)
class BayAreaEarthquakes:
    events: tuple[EarthquakeEvent, ...]
    is_available: bool
    has_recent: bool



def _format_time_label(when: datetime, now: datetime, recent_days: int) -> tuple[str, bool]:
    when_local = timezone.localtime(when)
    now_local = timezone.localtime(now)
    delta = now_local - when_local

    if delta.total_seconds() < 0:
        return when_local.strftime("%b %d"), False

    if delta < timedelta(hours=1):
        minutes = max(1, int(delta.total_seconds() // 60))
        label = "1 min ago" if minutes == 1 else f"{minutes} min ago"
        return label, True

    if delta < timedelta(hours=24):
        hours = max(1, int(delta.total_seconds() // 3600))
        label = "1 hr ago" if hours == 1 else f"{hours} hr ago"
        return label, True

    days = delta.days
    if days <= recent_days:
        label = "1 day ago" if days == 1 else f"{days} days ago"
        return label, True

    return when_local.strftime("%b %d"), False


def _parse_feature(feature: dict, now: datetime, recent_days: int) -> EarthquakeEvent | None:
    properties = feature.get("properties") or {}
    place = (properties.get("place") or "").strip()
    if not place:
        return None

    magnitude = properties.get("mag")
    if magnitude is not None:
        try:
            magnitude = float(magnitude)
        except (TypeError, ValueError):
            magnitude = None

    occurred_ms = properties.get("time")
    if occurred_ms is None:
        return None

    try:
        occurred_at = datetime.fromtimestamp(float(occurred_ms) / 1000.0, tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None

    time_label, is_recent = _format_time_label(occurred_at, now, recent_days)
    return EarthquakeEvent(
        place=place,
        magnitude=magnitude,
        time_label=time_label,
        is_recent=is_recent,
    )


def _fetch_usgs_events() -> list[dict]:
    lookback_days = getattr(settings, "TV_EARTHQUAKE_LOOKBACK_DAYS", 30)
    min_magnitude = getattr(settings, "TV_EARTHQUAKE_MIN_MAGNITUDE", 2.5)
    limit = getattr(settings, "TV_EARTHQUAKE_LIMIT", 3)
    bbox = getattr(settings, "TV_EARTHQUAKE_BBOX", {})

    start_time = (timezone.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    params = urlencode(
        {
            "format": "geojson",
            "starttime": start_time,
            "minlatitude": bbox.get("min_lat", 36.5),
            "maxlatitude": bbox.get("max_lat", 38.8),
            "minlongitude": bbox.get("min_lon", -123.5),
            "maxlongitude": bbox.get("max_lon", -121.0),
            "minmagnitude": min_magnitude,
            "orderby": "time",
            "limit": limit,
        }
    )
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?{params}"
    request = Request(url, headers={"User-Agent": "AddMyLegacyControl/1.0"})
    with urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))

    features = payload.get("features") or []
    if not isinstance(features, list):
        return []
    return features


def bay_area_earthquakes() -> BayAreaEarthquakes:
    cache_key = "tv_earthquakes_bay_area_v1"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    recent_days = getattr(settings, "TV_EARTHQUAKE_RECENT_DAYS", 3)
    limit = getattr(settings, "TV_EARTHQUAKE_LIMIT", 3)
    now = timezone.now()
    events: list[EarthquakeEvent] = []

    try:
        for feature in _fetch_usgs_events():
            event = _parse_feature(feature, now, recent_days)
            if event is not None:
                events.append(event)
            if len(events) >= limit:
                break

        result = BayAreaEarthquakes(
            events=tuple(events[:limit]),
            is_available=True,
            has_recent=any(event.is_recent for event in events),
        )
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError):
        result = BayAreaEarthquakes(events=(), is_available=False, has_recent=False)

    cache.set(cache_key, result, getattr(settings, "TV_EARTHQUAKE_CACHE_SECONDS", 600))
    return result
