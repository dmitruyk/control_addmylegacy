import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.art_slides import normalize_uploaded_slide, slide_has_source, slide_url_for
from core.models import ArtSlide
from tests.test_site_urls import _sample_binance, _sample_earthquakes, _sample_weather, _sample_wealth


def _make_test_jpeg(width: int = 2400, height: int = 1600) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(32, 96, 180)).save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile("iphone-photo.jpg", buffer.read(), content_type="image/jpeg")


class ArtSlideUploadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp()
        cls._settings_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._settings_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    def test_normalize_uploaded_slide_resizes_to_tv_dimensions(self):
        uploaded = _make_test_jpeg()
        normalized = normalize_uploaded_slide(uploaded)

        with Image.open(normalized) as image:
            self.assertEqual(image.size, (1920, 1080))
            self.assertEqual(image.format, "JPEG")

    @patch("core.views.wealth_widget")
    @patch("core.views.binance_us_portfolio")
    @patch("core.views.bay_area_earthquakes")
    @patch("core.views.bay_area_weather")
    def test_uploaded_slide_appears_on_tv_dashboard(
        self, mock_weather, mock_earthquakes, mock_binance, mock_wealth
    ):
        mock_weather.return_value = _sample_weather()
        mock_earthquakes.return_value = _sample_earthquakes(recent=False)
        mock_binance.return_value = _sample_binance()
        mock_wealth.return_value = _sample_wealth()

        slide = ArtSlide.objects.create(
            title="Family Trip",
            category=ArtSlide.Category.NATURE,
            image=_make_test_jpeg(),
            is_active=True,
            sort_order=1,
        )

        self.assertTrue(slide_has_source(slide))

        response = self.client.get(reverse("core:tv_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Family Trip")
        self.assertContains(response, slide.image.url.split("?")[0])

    def test_slide_url_for_prefers_upload_over_bundled_path(self):
        slide = ArtSlide.objects.create(
            title="Uploaded",
            category=ArtSlide.Category.CITY,
            static_path="art/slides/city-new-york.jpg",
            image=_make_test_jpeg(),
            is_active=True,
        )

        request = self.client.get("/").wsgi_request
        url = slide_url_for(request, slide)

        self.assertIsNotNone(url)
        self.assertIn("/media/", url)

    def test_model_save_stores_normalized_upload(self):
        slide = ArtSlide.objects.create(
            title="From iPhone",
            category=ArtSlide.Category.NATURE,
            image=_make_test_jpeg(),
            is_active=True,
            sort_order=500,
        )

        self.assertTrue(slide.image.name.startswith("art/slides/"))
        self.assertTrue(slide_has_source(slide))

        with Image.open(slide.image.path) as image:
            self.assertEqual(image.size, (1920, 1080))
