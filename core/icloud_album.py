import json
import re
import ssl
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi
from django.conf import settings
from django.core.cache import cache

from core.models import IcloudAlbumConfig

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

ICLOUD_HASH_ALBUM_RE = re.compile(r"#([A-Za-z0-9]+)$")
ICLOUD_SHAREDSTREAMS_HOST = "p23-sharedstreams.icloud.com"
# ~2× the 280px widget width for sharp display without oversized downloads.
WIDGET_DERIVATIVE_TARGET_WIDTH = 560


@dataclass(frozen=True)
class IcloudPhoto:
    url: str
    caption: str
    width: int | None
    height: int | None


@dataclass(frozen=True)
class IcloudAlbumWidget:
    is_enabled: bool
    is_available: bool
    title: str
    photos: tuple[IcloudPhoto, ...]
    slide_duration_seconds: int
    transition_seconds: float
    error_label: str


def extract_album_id(shared_url: str) -> str | None:
    url = (shared_url or "").strip()
    if not url:
        return None

    match = ICLOUD_HASH_ALBUM_RE.search(url)
    if match:
        return match.group(1)

    parsed = urlparse(url)
    if parsed.netloc.endswith("share.icloud.com"):
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "photos":
            return parts[1]

    return None


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "Content-Type": "text/plain",
            "Origin": "https://www.icloud.com",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
            return json.loads(response.read())
    except HTTPError as error:
        if error.code != 330:
            raise
        body = json.loads(error.read())
        host = body.get("X-Apple-MMe-Host")
        if not host:
            raise
        redirected = url.replace(ICLOUD_SHAREDSTREAMS_HOST, host, 1)
        return _post_json(redirected, payload)


def _pick_derivative(derivatives: dict) -> dict | None:
    candidates = []
    for derivative in derivatives.values():
        width = derivative.get("width")
        if not width:
            continue
        try:
            width_value = int(width)
        except (TypeError, ValueError):
            continue
        if width_value < 1:
            continue
        candidates.append(derivative)

    if not candidates:
        return None

    at_or_above = [derivative for derivative in candidates if int(derivative["width"]) >= WIDGET_DERIVATIVE_TARGET_WIDTH]
    if at_or_above:
        return min(at_or_above, key=lambda derivative: int(derivative["width"]))

    return max(candidates, key=lambda derivative: int(derivative["width"]))


def _sharedstreams_base(album_id: str) -> str:
    return f"https://{ICLOUD_SHAREDSTREAMS_HOST}/{album_id}/sharedstreams"


def _fetch_album_photos(album_id: str) -> list[IcloudPhoto]:
    base_api = _sharedstreams_base(album_id)
    stream = _post_json(f"{base_api}/webstream", {"streamCtag": None})
    photos = stream.get("photos") or []
    if not photos:
        return []

    checksums: list[str] = []
    metadata: list[tuple[str, int | None, int | None]] = []

    for photo in photos:
        derivative = _pick_derivative(photo.get("derivatives") or {})
        checksum = derivative and derivative.get("checksum")
        if not checksum:
            continue
        checksums.append(checksum)
        metadata.append(
            (
                (photo.get("caption") or "").strip(),
                int(derivative["width"]) if derivative.get("width") else None,
                int(derivative["height"]) if derivative.get("height") else None,
            )
        )

    if not checksums:
        return []

    assets = _post_json(f"{base_api}/webasseturls", {"photoGuids": [p["photoGuid"] for p in photos]})
    items = assets.get("items") or {}

    results: list[IcloudPhoto] = []
    for checksum, (caption, width, height) in zip(checksums, metadata, strict=False):
        item = items.get(checksum)
        if not item:
            continue
        location = item.get("url_location")
        path = item.get("url_path")
        if not location or not path:
            continue
        results.append(
            IcloudPhoto(
                url=f"https://{location}{path}",
                caption=caption,
                width=width,
                height=height,
            )
        )

    return results


def icloud_album_photos(album_id: str) -> list[IcloudPhoto]:
    cache_key = f"tv_icloud_album_{album_id}_v2"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        photos = _fetch_album_photos(album_id)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        photos = []

    cache_seconds = getattr(settings, "TV_ICLOUD_ALBUM_CACHE_SECONDS", 1800)
    cache.set(cache_key, photos, cache_seconds)
    return photos


def invalidate_icloud_album_cache(album_id: str | None = None) -> None:
    if album_id:
        cache.delete(f"tv_icloud_album_{album_id}_v2")
        return

    config = IcloudAlbumConfig.load()
    album_id = extract_album_id(config.shared_album_url)
    if album_id:
        cache.delete(f"tv_icloud_album_{album_id}_v2")


def icloud_album_widget() -> IcloudAlbumWidget:
    config = IcloudAlbumConfig.load()
    if not config.is_enabled:
        return IcloudAlbumWidget(
            is_enabled=False,
            is_available=False,
            title=config.title,
            photos=(),
            slide_duration_seconds=config.slide_duration_seconds,
            transition_seconds=float(config.transition_seconds),
            error_label="",
        )

    album_id = extract_album_id(config.shared_album_url)
    if not album_id:
        return IcloudAlbumWidget(
            is_enabled=True,
            is_available=False,
            title=config.title,
            photos=(),
            slide_duration_seconds=config.slide_duration_seconds,
            transition_seconds=float(config.transition_seconds),
            error_label="Invalid iCloud shared album URL",
        )

    photos = icloud_album_photos(album_id)
    if not photos:
        return IcloudAlbumWidget(
            is_enabled=True,
            is_available=False,
            title=config.title,
            photos=(),
            slide_duration_seconds=config.slide_duration_seconds,
            transition_seconds=float(config.transition_seconds),
            error_label="No photos available from iCloud album",
        )

    return IcloudAlbumWidget(
        is_enabled=True,
        is_available=True,
        title=config.title,
        photos=tuple(photos),
        slide_duration_seconds=config.slide_duration_seconds,
        transition_seconds=float(config.transition_seconds),
        error_label="",
    )


def icloud_album_widget_payload() -> dict:
    widget = icloud_album_widget()
    return {
        "enabled": widget.is_enabled,
        "available": widget.is_available,
        "title": widget.title,
        "slide_duration_seconds": widget.slide_duration_seconds,
        "transition_seconds": widget.transition_seconds,
        "error_label": widget.error_label,
        "photos": [
            {
                "url": photo.url,
                "caption": photo.caption,
                "width": photo.width,
                "height": photo.height,
            }
            for photo in widget.photos
        ],
    }
