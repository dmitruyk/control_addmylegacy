from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

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


class SiteUrlTests(TestCase):
    @patch("core.views.bay_area_weather")
    def test_tv_dashboard_renders(self, mock_weather):
        mock_weather.return_value = _sample_weather()

        response = self.client.get(reverse("core:tv_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tv-gallery")
        self.assertContains(response, "tv-slideshow.js")
        self.assertContains(response, "Palo Alto")
        self.assertContains(response, "San Francisco")
        self.assertContains(response, "20°C")
        self.assertContains(response, "tv-weather-hourly")
        self.assertContains(response, "tv-slides-data")
        self.assertContains(response, "Still waiting")
        self.assertContains(response, "tv-boot.js")
        self.assertNotContains(response, "tv-info-panels")

        slides = self._parse_slides_json(response.content.decode())
        self.assertEqual(len(slides), 12)
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

    @patch("core.views.bay_area_weather")
    def test_tv_dashboard_info_panels_when_enabled(self, mock_weather):
        from core.models import TvDisplayConfig

        mock_weather.return_value = _sample_weather()

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
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate")

    def test_updating_html_route_uses_wait_shell(self):
        response = self.client.get(reverse("core:updating_html"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="wait-page"')

    def test_missing_page_for_synology_hook(self):
        response = self.client.get(reverse("core:missing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="wait-page"')
        self.assertContains(response, "Synology NAS gateway")
        self.assertContains(response, "HEALTH_PATH")
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate")

    def test_missing_page_slash_route(self):
        response = self.client.get("/missing/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AML")

    def test_unknown_route_shows_wait_shell(self):
        response = self.client.get("/missing-route/")
        self.assertContains(response, 'content="wait-page"', status_code=404)
        self.assertContains(response, "Still waiting", status_code=404)
