from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

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


class SiteUrlTests(TestCase):
    @patch("core.views.bay_area_earthquakes")
    @patch("core.views.bay_area_weather")
    def test_tv_dashboard_renders(self, mock_weather, mock_earthquakes):
        mock_weather.return_value = _sample_weather()
        mock_earthquakes.return_value = _sample_earthquakes(recent=True)

        response = self.client.get(reverse("core:tv_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tv-gallery")
        self.assertContains(response, "tv-slideshow.js")
        self.assertContains(response, "Palo Alto")
        self.assertContains(response, "San Francisco")
        self.assertContains(response, "20°C")
        self.assertContains(response, "tv-weather-hourly")
        self.assertContains(response, "Bay Area Earthquakes")
        self.assertContains(response, "5 km NW of San Jose, CA")
        self.assertContains(response, "M4.2")
        self.assertContains(response, "tv-earthquake-card-recent")
        self.assertContains(response, "tv-slides-data")
        self.assertContains(response, "Still waiting")
        self.assertContains(response, "tv-boot.js")
        self.assertContains(response, 'name="aml-service-url"')
        self.assertContains(response, 'name="aml-service-mode"')
        self.assertNotContains(response, "tv-info-panels")

        slides = self._parse_slides_json(response.content.decode())
        self.assertEqual(len(slides), 26)
        self.assertIn(".jpg", slides[0]["url"])
        self.assertIn("city-new-york.jpg", slides[0]["url"])

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

    @patch("core.views.bay_area_earthquakes")
    @patch("core.views.bay_area_weather")
    def test_tv_dashboard_info_panels_when_enabled(self, mock_weather, mock_earthquakes):
        from core.models import TvDisplayConfig

        mock_weather.return_value = _sample_weather()
        mock_earthquakes.return_value = _sample_earthquakes(recent=False)

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
