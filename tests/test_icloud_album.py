from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.icloud_album import (
    IcloudAlbumWidget,
    IcloudPhoto,
    extract_album_id,
    icloud_album_widget,
    icloud_album_widget_payload,
    icloud_photo_frame_size,
    icloud_scaled_max_bounds,
    normalize_size_scale_percent,
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


class IcloudPhotoFrameSizeTests(SimpleTestCase):
    def test_landscape_photo_uses_max_width(self):
        self.assertEqual(icloud_photo_frame_size(1600, 1200), (336, 252))

    def test_portrait_photo_fits_max_height(self):
        width, height = icloud_photo_frame_size(1200, 1600)
        self.assertEqual(height, 252)
        self.assertLess(width, 336)

    def test_missing_dimensions_use_default(self):
        self.assertEqual(icloud_photo_frame_size(None, None), (336, 189))

    def test_portrait_1537_by_2049(self):
        width, height = icloud_photo_frame_size(1537, 2049)
        self.assertEqual(width, 189)
        self.assertEqual(height, 252)
        self.assertAlmostEqual(width / height, 1537 / 2049, places=3)

    def test_scale_doubles_portrait_frame(self):
        width, height = icloud_photo_frame_size(1537, 2049, scale_percent=200)
        self.assertEqual(width, 378)
        self.assertEqual(height, 504)

    def test_scale_zero_hides_frame(self):
        self.assertEqual(icloud_scaled_max_bounds(0), (0, 0))
        self.assertEqual(icloud_photo_frame_size(1537, 2049, scale_percent=0), (0, 0))

    def test_normalize_size_scale_percent(self):
        self.assertEqual(normalize_size_scale_percent(150), 150)
        self.assertEqual(normalize_size_scale_percent(999), 300)
        self.assertEqual(normalize_size_scale_percent(-5), 0)


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
        self.assertEqual(payload["size_scale_percent"], 100)
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
        self.assertEqual(data["size_scale_percent"], 100)
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
            size_scale_percent=100,
            error_label="",
        )

        response = self.client.get(reverse("core:tv_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="tv-widget-icloud"')
        self.assertContains(response, 'id="tv-icloud-widget"')
        self.assertContains(response, 'data-icloud-size-scale-percent="100"')
        self.assertContains(response, reverse("core:tv_widget_icloud"))
