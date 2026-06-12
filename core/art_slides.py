"""Art slide image processing and URL helpers."""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.templatetags.static import static
from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

TV_SLIDE_WIDTH = getattr(settings, "TV_ART_SLIDE_WIDTH", 1920)
TV_SLIDE_HEIGHT = getattr(settings, "TV_ART_SLIDE_HEIGHT", 1080)
TV_SLIDE_JPEG_QUALITY = getattr(settings, "TV_ART_SLIDE_JPEG_QUALITY", 85)


def art_slide_upload_to(instance, filename: str) -> str:
    token = uuid.uuid4().hex[:10]
    return f"art/slides/{token}.jpg"


def _resize_cover(image: Image.Image, width: int, height: int) -> Image.Image:
    fitted = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    return fitted.convert("RGB")


def normalize_uploaded_slide(uploaded_file) -> ContentFile:
    """Resize and re-encode an uploaded photo for the TV slideshow."""
    uploaded_file.seek(0)
    with Image.open(uploaded_file) as image:
        image = ImageOps.exif_transpose(image)
        prepared = _resize_cover(image, TV_SLIDE_WIDTH, TV_SLIDE_HEIGHT)

    buffer = BytesIO()
    prepared.save(buffer, format="JPEG", quality=TV_SLIDE_JPEG_QUALITY, optimize=True)
    buffer.seek(0)

    original_name = Path(getattr(uploaded_file, "name", "slide.jpg")).stem
    safe_stem = "".join(char for char in original_name if char.isalnum() or char in "-_")[:40] or "slide"
    return ContentFile(buffer.read(), name=f"{safe_stem}.jpg")


def bundled_slide_exists(static_path: str) -> bool:
    if not static_path:
        return False
    return (Path(settings.BASE_DIR) / "static" / static_path).is_file()


def slide_has_source(slide) -> bool:
    if slide.image:
        try:
            return slide.image.storage.exists(slide.image.name)
        except Exception:
            return bool(slide.image.name)
    return bundled_slide_exists(slide.static_path)


def bundled_slide_url(request, static_path: str) -> str:
    url = static(static_path)
    build_id = getattr(settings, "STATIC_BUILD_ID", "1")
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}v={build_id}"

    if request:
        return request.build_absolute_uri(url)

    return url


def uploaded_slide_url(request, slide) -> str:
    url = slide.image.url
    version = int(slide.created_at.timestamp()) if slide.created_at else slide.pk
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}v={version}"

    if request:
        return request.build_absolute_uri(url)

    return url


def slide_url_for(request, slide) -> str | None:
    if slide.image and slide_has_source(slide):
        return uploaded_slide_url(request, slide)
    if bundled_slide_exists(slide.static_path):
        return bundled_slide_url(request, slide.static_path)
    return None
