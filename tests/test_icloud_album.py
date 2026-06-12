from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.icloud_album import (
    IcloudAlbumWidget,
    IcloudPhoto,
    extract_album_id,
    icloud_album_widget,
    icloud_album_widget_payload,
)
from core.models import IcloudAlbumConfig


class ExtractAlbumIdTests(SimpleTestCase):
    def test_hash_url(self):
        self.assertEqual(
            extract_album_id("https://www.icloud.com/sharedalbum/#B29JtdOXmok8Aj"),
            "B29JtdOXmok8Aj",
        )

    def test_share_url(self):
        self.assertEqual(
            extract_album_id("https://share.icloud.com/photos/02cD9okNHvVd-uuDnPCH3ZEEA"),
            "02cD9okNHvVd-uuDnPCH3ZEEA",
        )

    def test_empty(self):
        self.assertIsNone(extract_album_id(""))
        self.assertIsNone(extract_album_id("https://example.com/album"))


class IcloudAlbumWidgetTests(TestCase):
    def setUp(self):
        config = IcloudAlbumConfig.load()
        config.is_enabled = True
        config.shared_album_url = "https://www.icloud.com/sharedalbum/#B29JtdOXmok8Aj"
        config.save()

    @patch("core.icloud_album.icloud_album_photos")
    def test_widget_returns_photos(self, mock_photos):
        mock_photos.return_value = [
            IcloudPhoto(url="https://example.com/photo.jpg", caption="Sunset", width=800, height=600),
        ]

        widget = icloud_album_widget()

        self.assertTrue(widget.is_enabled)
        self.assertTrue(widget.is_available)
        self.assertEqual(len(widget.photos), 1)
        self.assertEqual(widget.photos[0].caption, "Sunset")

    @patch("core.icloud_album.icloud_album_photos")
    def test_widget_disabled(self, mock_photos):
        config = IcloudAlbumConfig.load()
        config.is_enabled = False
        config.save(update_fields=["is_enabled"])

        widget = icloud_album_widget()

        self.assertFalse(widget.is_enabled)
        self.assertFalse(widget.is_available)
        mock_photos.assert_not_called()

    @patch("core.icloud_album.icloud_album_photos")
    def test_widget_invalid_url(self, mock_photos):
        config = IcloudAlbumConfig.load()
        config.shared_album_url = "https://example.com/not-icloud"
        config.save(update_fields=["shared_album_url"])

        widget = icloud_album_widget()

        self.assertTrue(widget.is_enabled)
        self.assertFalse(widget.is_available)
        self.assertIn("Invalid", widget.error_label)
        mock_photos.assert_not_called()

    @patch("core.icloud_album.icloud_album_photos")
    def test_payload_shape(self, mock_photos):
        mock_photos.return_value = [
            IcloudPhoto(url="https://example.com/photo.jpg", caption="", width=800, height=600),
        ]

        payload = icloud_album_widget_payload()

        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["available"])
        self.assertEqual(payload["photos"][0]["url"], "https://example.com/photo.jpg")


class IcloudWidgetUrlTests(TestCase):
    @patch("core.icloud_album.icloud_album_photos")
    def test_api_endpoint(self, mock_photos):
        mock_photos.return_value = [
            IcloudPhoto(url="https://example.com/photo.jpg", caption="Test", width=800, height=600),
        ]

        response = self.client.get(reverse("core:tv_widget_icloud"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["available"])
        self.assertEqual(data["photos"][0]["caption"], "Test")

    @patch("core.views.icloud_album_widget")
    def test_dashboard_includes_widget(self, mock_widget):
        mock_widget.return_value = IcloudAlbumWidget(
            is_enabled=True,
            is_available=True,
            title="Family",
            photos=(
                IcloudPhoto(url="https://example.com/photo.jpg", caption="", width=800, height=600),
            ),
            slide_duration_seconds=8,
            transition_seconds=1.5,
            error_label="",
        )

        response = self.client.get(reverse("core:tv_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="tv-widget-icloud"')
        self.assertContains(response, 'id="tv-icloud-widget"')
        self.assertContains(response, reverse("core:tv_widget_icloud"))
