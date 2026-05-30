import json
from dataclasses import dataclass
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

WMO_LABELS = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Drizzle",
    53: "Drizzle",
    55: "Drizzle",
    61: "Rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}

WMO_ICONS = {
    0: "clear",
    1: "mainly-clear",
    2: "partly-cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "drizzle",
    53: "drizzle",
    55: "drizzle",
    61: "rain",
    63: "rain",
    65: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    80: "showers",
    81: "showers",
    82: "showers",
    95: "thunderstorm",
    96: "thunderstorm",
    99: "thunderstorm",
}

WMO_SYMBOLS = {
    0: "☀",
    1: "🌤",
    2: "⛅",
    3: "☁",
    45: "🌫",
    48: "🌫",
    51: "🌦",
    53: "🌦",
    55: "🌧",
    61: "🌧",
    63: "🌧",
    65: "🌧",
    71: "❄",
    73: "❄",
    75: "❄",
    80: "🌦",
    81: "🌦",
    82: "🌧",
    95: "⛈",
    96: "⛈",
    99: "⛈",
}


@dataclass(frozen=True)
class HourlyWeather:
    hour_label: str
    temperature_c: int | None
    icon: str
    symbol: str
    label: str


@dataclass(frozen=True)
class CityWeather:
    city: str
    temperature_c: int | None
    icon: str
    symbol: str
    label: str
    hourly: tuple[HourlyWeather, ...]
    is_available: bool


def _weather_label(code: int | None) -> str:
    if code is None:
        return "Unavailable"
    return WMO_LABELS.get(code, "Mixed")


def _weather_icon(code: int | None) -> str:
    if code is None:
        return "unknown"
    return WMO_ICONS.get(code, "mixed")


def _weather_symbol(code: int | None) -> str:
    if code is None:
        return "·"
    return WMO_SYMBOLS.get(code, "◌")


def _round_celsius(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value))


def _format_hour_label(iso_time: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_time)
    except ValueError:
        return iso_time[-5:]

    hour = dt.hour
    if hour == 0:
        return "12am"
    if hour < 12:
        return f"{hour}am"
    if hour == 12:
        return "12pm"
    return f"{hour - 12}pm"


def _fetch_forecast(latitude: float, longitude: float) -> dict:
    hourly_count = getattr(settings, "TV_WEATHER_HOURLY_COUNT", 6)
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "hourly": "temperature_2m,weather_code",
            "temperature_unit": "celsius",
            "timezone": settings.TV_WEATHER_TIMEZONE,
            "forecast_hours": max(hourly_count + 1, 12),
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    request = Request(url, headers={"User-Agent": "AddMyLegacyControl/1.0"})
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_hourly(payload: dict) -> tuple[HourlyWeather, ...]:
    hourly_count = getattr(settings, "TV_WEATHER_HOURLY_COUNT", 6)
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    codes = hourly.get("weather_code") or []
    current_time = (payload.get("current") or {}).get("time")
    start_index = 0

    if current_time and current_time in times:
        start_index = times.index(current_time)

    rows: list[HourlyWeather] = []

    for offset in range(hourly_count):
        index = start_index + offset
        if index >= len(times):
            break

        iso_time = times[index]
        code = codes[index] if index < len(codes) else None
        rows.append(
            HourlyWeather(
                hour_label=_format_hour_label(iso_time),
                temperature_c=_round_celsius(temps[index] if index < len(temps) else None),
                icon=_weather_icon(code),
                symbol=_weather_symbol(code),
                label=_weather_label(code),
            )
        )

    return tuple(rows)


def _city_weather(city: str, latitude: float, longitude: float) -> CityWeather:
    try:
        payload = _fetch_forecast(latitude, longitude)
        current = payload.get("current") or {}
        code = current.get("weather_code")
        return CityWeather(
            city=city,
            temperature_c=_round_celsius(current.get("temperature_2m")),
            icon=_weather_icon(code),
            symbol=_weather_symbol(code),
            label=_weather_label(code),
            hourly=_build_hourly(payload),
            is_available=True,
        )
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, OSError):
        return CityWeather(
            city=city,
            temperature_c=None,
            icon="unknown",
            symbol="·",
            label="Unavailable",
            hourly=(),
            is_available=False,
        )


def bay_area_weather() -> list[CityWeather]:
    cache_key = "tv_weather_bay_area_v2"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    locations = settings.TV_WEATHER_LOCATIONS
    results = [_city_weather(name, lat, lon) for name, lat, lon in locations]
    cache.set(cache_key, results, settings.TV_WEATHER_CACHE_SECONDS)
    return results
