from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.binance_us import BinancePortfolio, binance_us_portfolio
from core.earthquakes import (
    BayAreaEarthquakes,
    EarthquakeEvent,
    _format_time_label,
    _parse_feature,
    bay_area_earthquakes,
)
from core.weather import CityWeather, HourlyWeather


def _sample_weather():
    hourly = (
        HourlyWeather("2pm", 19, "clear", "☀", "Clear"),
        HourlyWeather("3pm", 18, "partly-cloudy", "⛅", "Partly cloudy"),
        HourlyWeather("4pm", 17, "clear", "☀", "Clear"),
    )
    return [
        CityWeather("Palo Alto", 20, "clear", "☀", "Clear", hourly, True),
        CityWeather("San Francisco", 17, "partly-cloudy", "⛅", "Partly cloudy", hourly, True),
    ]


def _sample_binance() -> BinancePortfolio:
    return BinancePortfolio(
        is_configured=True,
        is_available=True,
        total_usd=10410.19,
        total_display="$10,410.19",
        change_usd=-1324.10,
        change_usd_display="-$1,324.10",
        change_pct=-7.8,
        change_display="-7.80%",
        crypto_usd_display="$1,924.77",
        staking_usd_display="$8,481.60",
        cash_usd_display="$3.12",
        top_assets=("BTC", "ETC", "ZEC", "RENDER"),
        chart_points="0.0,30.0 50.0,20.0 100.0,10.0",
        chart_area_points="0.0,40.0 0.0,30.0 50.0,20.0 100.0,10.0 100.0,40.0",
        chart_start_display="$11,734.29",
        chart_end_display="$10,410.19",
        chart_date_labels=("Mar 1", "Apr 1", "May 1", "May 15", "May 30"),
        chart_width=100,
        chart_height=40,
        period_label="3M",
        status_label="Balance",
        error_label="",
    )


def _sample_earthquakes(recent: bool = True) -> BayAreaEarthquakes:
    return BayAreaEarthquakes(
        events=(
            EarthquakeEvent("5 km NW of San Jose, CA", 4.2, "2 days ago", recent),
            EarthquakeEvent("10 km E of Oakland, CA", 3.1, "May 12", False),
        ),
        is_available=True,
        has_recent=recent,
    )


class EarthquakeServiceTests(SimpleTestCase):
    def test_format_time_label_recent_days(self):
        now = timezone.make_aware(datetime(2026, 5, 30, 12, 0, 0))
        when = now - timedelta(days=2, hours=3)

        label, is_recent = _format_time_label(when, now, 3)

        self.assertEqual(label, "2 days ago")
        self.assertTrue(is_recent)

    def test_format_time_label_older_event(self):
        now = timezone.make_aware(datetime(2026, 5, 30, 12, 0, 0))
        when = now - timedelta(days=8)

        label, is_recent = _format_time_label(when, now, 3)

        self.assertEqual(label, "May 22")
        self.assertFalse(is_recent)

    def test_parse_feature(self):
        now = timezone.make_aware(datetime(2026, 5, 30, 12, 0, 0))
        occurred_ms = int((now - timedelta(hours=5)).timestamp() * 1000)
        feature = {
            "properties": {
                "mag": 3.4,
                "place": "3 km SE of Berkeley, CA",
                "time": occurred_ms,
            }
        }

        event = _parse_feature(feature, now, 3)

        self.assertIsNotNone(event)
        self.assertEqual(event.place, "3 km SE of Berkeley, CA")
        self.assertEqual(event.magnitude, 3.4)
        self.assertTrue(event.is_recent)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "earthquake-tests",
            }
        }
    )
    @patch("core.earthquakes._fetch_usgs_events")
    def test_bay_area_earthquakes_caches_results(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "properties": {
                    "mag": 2.8,
                    "place": "2 km W of Daly City, CA",
                    "time": int(timezone.now().timestamp() * 1000),
                }
            }
        ]

        first = bay_area_earthquakes()
        second = bay_area_earthquakes()

        self.assertTrue(first.is_available)
        self.assertEqual(len(first.events), 1)
        self.assertEqual(first.events[0].place, "2 km W of Daly City, CA")
        self.assertEqual(first, second)
        mock_fetch.assert_called_once()

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "earthquake-limit-tests",
            }
        },
        TV_EARTHQUAKE_LIMIT=3,
    )
    @patch("core.earthquakes._fetch_usgs_events")
    def test_bay_area_earthquakes_limits_to_three_events(self, mock_fetch):
        now_ms = int(timezone.now().timestamp() * 1000)
        mock_fetch.return_value = [
            {
                "properties": {
                    "mag": 3.0 + index,
                    "place": f"{index} km W of Daly City, CA",
                    "time": now_ms - index * 1000,
                }
            }
            for index in range(5)
        ]

        result = bay_area_earthquakes()

        self.assertTrue(result.is_available)
        self.assertEqual(len(result.events), 3)
        self.assertEqual(result.events[0].place, "0 km W of Daly City, CA")
        self.assertEqual(result.events[2].place, "2 km W of Daly City, CA")


class BinanceServiceTests(SimpleTestCase):
    @override_settings(
        BINANCE_US_API_KEY="",
        BINANCE_US_API_SECRET="",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "binance-unconfigured-tests",
            }
        },
    )
    def test_unconfigured_when_keys_missing(self):
        result = binance_us_portfolio()

        self.assertFalse(result.is_configured)
        self.assertFalse(result.is_available)
        self.assertIn("BINANCE_US_API_KEY", result.error_label)

    def test_merge_balances_adds_staking_to_spot(self):
        from core.binance_us import _merge_balances

        merged = _merge_balances({"BTC": 0.1, "USD": 5.0}, {"ETH": 2.0, "BTC": 0.05})

        self.assertAlmostEqual(merged["BTC"], 0.15)
        self.assertEqual(merged["ETH"], 2.0)
        self.assertEqual(merged["USD"], 5.0)

    def test_resolve_symbol_prefers_usdt_over_stale_usd(self):
        from core.binance_us import _asset_usd_price, _resolve_symbol

        prices = {"ZECUSD": 30.5, "ZECUSDT": 548.0, "ETHUSD": 2000.0}

        self.assertEqual(_resolve_symbol("ZEC", prices), "ZECUSDT")
        self.assertAlmostEqual(_asset_usd_price("ZEC", prices), 548.0)
        self.assertEqual(_resolve_symbol("ETH", prices), "ETHUSD")

    @patch("core.binance_us._http_get")
    def test_signed_get_uses_recv_window_and_server_time(self, mock_http):
        from core.binance_us import _signed_get

        mock_http.return_value = {"balances": []}

        with patch("core.binance_us.cache") as mock_cache, patch("core.binance_us.time.time", return_value=1000.0):
            mock_cache.get.return_value = -250
            _signed_get("/api/v3/account", {}, "key", "secret")

        url = mock_http.call_args[0][0]
        self.assertIn("recvWindow=10000", url)
        self.assertIn("timestamp=999750", url)

    @patch("core.binance_us._load_ticker_prices")
    @patch("core.binance_us._load_staking_balances")
    @patch("core.binance_us._load_balances")
    @patch("core.binance_us._fetch_klines_closes")
    def test_portfolio_includes_staking_in_total(
        self, mock_klines, mock_spot, mock_staking, mock_prices
    ):
        from core.binance_us import _load_portfolio

        mock_spot.return_value = {"USD": 10.0}
        mock_staking.return_value = {"ETH": 1.0}
        mock_prices.return_value = {"ETHUSD": 2000.0, "USDUSD": 1.0}
        mock_klines.return_value = [2000.0, 2000.0]

        portfolio = _load_portfolio("key", "secret")

        self.assertEqual(portfolio.total_usd, 2010.0)
        self.assertEqual(portfolio.crypto_usd_display, "$0.00")
        self.assertEqual(portfolio.staking_usd_display, "$2,000.00")
        self.assertEqual(portfolio.cash_usd_display, "$10.00")

    @override_settings(
        BINANCE_US_API_KEY="test-key",
        BINANCE_US_API_SECRET="test-secret",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "binance-tests",
            }
        },
    )
    @patch("core.binance_us._load_portfolio")
    def test_binance_portfolio_caches_results(self, mock_load):
        mock_load.return_value = _sample_binance()

        first = binance_us_portfolio()
        second = binance_us_portfolio()

        self.assertTrue(first.is_available)
        self.assertEqual(first.total_display, "$10,410.19")
        self.assertEqual(first, second)
        mock_load.assert_called_once()


class SiteUrlTests(TestCase):
    @patch("core.views.binance_us_portfolio")
    @patch("core.views.bay_area_earthquakes")
    @patch("core.views.bay_area_weather")
    def test_tv_dashboard_renders(self, mock_weather, mock_earthquakes, mock_binance):
        mock_weather.return_value = _sample_weather()
        mock_earthquakes.return_value = _sample_earthquakes(recent=True)
        mock_binance.return_value = _sample_binance()

        response = self.client.get(reverse("core:tv_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate")
        self.assertContains(response, "tv-gallery")
        self.assertContains(response, "tv-slideshow.js")
        self.assertContains(response, "Palo Alto")
        self.assertContains(response, "San Francisco")
        self.assertContains(response, "20°C")
        self.assertContains(response, "tv-weather-hourly")
        self.assertContains(response, "Bay Area Earthquakes")
        self.assertContains(response, "tv-binance-card")
        self.assertContains(response, "Balance")
        self.assertContains(response, "$10,410.19")
        self.assertContains(response, "-$1,324.10")
        self.assertContains(response, "-7.80%")
        self.assertContains(response, "tv-binance-chart")
        self.assertContains(response, "Crypto")
        self.assertContains(response, "Staking")
        self.assertContains(response, "5 km NW of San Jose, CA")
        self.assertContains(response, "M4.2")
        self.assertContains(response, "tv-earthquake-card-recent")
        self.assertContains(response, "tv-slides-data")
        self.assertContains(response, "Still waiting")
        self.assertContains(response, "tv-boot.js")
        self.assertContains(response, "tv-theme.js")
        self.assertContains(response, "theme-night")
        self.assertContains(response, 'data-brightness="night"')
        self.assertNotContains(response, "theme-auto")
        self.assertNotContains(response, "tv-theme-controls")
        self.assertNotContains(response, "data-theme=\"day\"")
        self.assertContains(response, 'data-theme-timezone="America/Los_Angeles"')
        self.assertNotContains(response, "aml-tv-theme-preference")
        self.assertContains(response, 'name="aml-service-url"')
        self.assertContains(response, 'name="aml-service-mode"')
        self.assertNotContains(response, "tv-info-panels")

        slides = self._parse_slides_json(response.content.decode())
        self.assertEqual(len(slides), 26)
        self.assertIn(".jpg", slides[0]["url"])
        self.assertIn("city-new-york.jpg", slides[0]["url"])

    @patch("core.views.binance_us_portfolio")
    @patch("core.views.bay_area_earthquakes")
    @patch("core.views.bay_area_weather")
    def test_page_refresh_waits_for_full_slideshow_cycle(self, mock_weather, mock_earthquakes, mock_binance):
        from core.models import TvDisplayConfig

        mock_weather.return_value = _sample_weather()
        mock_earthquakes.return_value = _sample_earthquakes(recent=False)
        mock_binance.return_value = _sample_binance()

        config = TvDisplayConfig.load()
        config.slide_duration_seconds = 120
        config.save()

        with self.settings(TV_REFRESH_SECONDS=60):
            response = self.client.get(reverse("core:tv_dashboard"))

        self.assertContains(response, 'data-slide-duration="120"')
        self.assertContains(response, 'data-refresh-seconds="3120"')

    def _parse_slides_json(self, html: str) -> list:
        import json
        import re

        match = re.search(
            r'<script id="tv-slides-data" type="application/json">(.+?)</script>',
            html,
        )
        self.assertIsNotNone(match, "tv-slides-data script tag not found")
        data = json.loads(match.group(1))
        self.assertIsInstance(data, list, "slides JSON must be an array, not a double-encoded string")
        return data

    @patch("core.views.binance_us_portfolio")
    @patch("core.views.bay_area_earthquakes")
    @patch("core.views.bay_area_weather")
    def test_tv_dashboard_info_panels_when_enabled(self, mock_weather, mock_earthquakes, mock_binance):
        from core.models import TvDisplayConfig

        mock_weather.return_value = _sample_weather()
        mock_earthquakes.return_value = _sample_earthquakes(recent=False)
        mock_binance.return_value = _sample_binance()

        config = TvDisplayConfig.load()
        config.show_info_panels = True
        config.save()

        response = self.client.get(reverse("core:tv_dashboard"))
        self.assertContains(response, "tv-info-panels")

        config.show_info_panels = False
        config.save()

    def test_health_endpoint(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate")

    def test_updating_page(self):
        response = self.client.get(reverse("core:updating"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Still waiting")
        self.assertContains(response, "control-addmylegacy")
        self.assertContains(response, "tv-boot.js")

    def test_wait_page(self):
        response = self.client.get(reverse("core:wait"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="wait-page"')
        self.assertContains(response, "Still waiting")
        self.assertContains(response, "tv-boot.js")
        self.assertContains(response, 'name="aml-service-url"')
        self.assertContains(response, 'content="local"')
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate")

    def test_service_base_url_local(self):
        response = self.client.get(reverse("core:tv_dashboard"))
        self.assertContains(response, 'content="local"')
        self.assertContains(response, "http://testserver")

    def test_updating_html_route_uses_wait_shell(self):
        response = self.client.get(reverse("core:updating_html"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="wait-page"')

    def test_missing_page_for_synology_hook(self):
        response = self.client.get(reverse("core:missing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="wait-page"')
        self.assertContains(response, "Synology gateway")
        self.assertContains(response, "tv-boot.js")

    def test_missing_page_slash_route(self):
        response = self.client.get("/missing/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AML")

    def test_unknown_route_shows_wait_shell(self):
        response = self.client.get("/missing-route/")
        self.assertContains(response, 'content="wait-page"', status_code=404)
        self.assertContains(response, "Still waiting", status_code=404)
