from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.binance_us import binance_us_portfolio
from core.earthquakes import bay_area_earthquakes
from core.models import ArtSlide, TvDisplayConfig
from core.weather import bay_area_weather

STANDALONE_WAIT_PATH = Path(settings.BASE_DIR) / "deploy" / "updating.html"


def _no_store(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def _standalone_wait_response() -> HttpResponse:
    content = STANDALONE_WAIT_PATH.read_text(encoding="utf-8")
    return _no_store(HttpResponse(content, content_type="text/html; charset=utf-8"))


def _slide_url(request, static_path: str) -> str:
    url = static(static_path)
    build_id = getattr(settings, "STATIC_BUILD_ID", "1")
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}v={build_id}"

    if request:
        return request.build_absolute_uri(url)

    return url


def _page_refresh_seconds(display_config, slide_count: int) -> int:
    configured = getattr(settings, "TV_REFRESH_SECONDS", 0) or 0
    if configured < 1:
        return 0

    slide_duration = display_config.slide_duration_seconds or 12
    full_cycle = slide_duration * max(slide_count, 1)
    return max(configured, full_cycle)


TV_THEME_DAY_START_HOUR = 7
TV_THEME_DAY_END_HOUR = 19


def _theme_brightness(local_moment) -> str:
    """Gallery HUD always renders in high-contrast dark mode."""
    return "night"


def _dashboard_context(request):
    display_config = TvDisplayConfig.load()
    now = timezone.localtime(timezone.now())
    slides = []

    for slide in ArtSlide.objects.filter(is_active=True):
        slides.append(
            {
                "url": _slide_url(request, slide.static_path),
                "title": slide.title,
                "category": slide.category,
            }
        )

    return {
        "now": now,
        "theme_brightness": _theme_brightness(now),
        "TIME_ZONE": settings.TIME_ZONE,
        "refresh_seconds": _page_refresh_seconds(display_config, len(slides)),
        "display_config": display_config,
        "slides": slides,
        "weather": bay_area_weather(),
        "earthquakes": bay_area_earthquakes(),
        "binance": binance_us_portfolio(),
    }


@require_GET
def tv_dashboard(request):
    return _no_store(render(request, "core/tv_dashboard.html", _dashboard_context(request)))


@require_GET
def updating_page(request):
    return _no_store(render(request, "core/tv_dashboard.html", _dashboard_context(request)))


@require_GET
def wait_page(request):
    response = render(
        request,
        "core/wait_shell.html",
        {
            "poll_seconds": settings.TV_HEALTH_POLL_SECONDS,
        },
    )
    return _no_store(response)


@require_GET
def missing_page(request):
    """Synology 404 pages XHR GET /missing and replace themselves when this returns 200."""
    return wait_page(request)


@require_GET
def service_worker_unregister(request):
    path = Path(settings.BASE_DIR) / "static" / "js" / "tv-sw-unregister.js"
    response = HttpResponse(path.read_text(encoding="utf-8"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return _no_store(response)


def page_not_found(request, exception):
    response = wait_page(request)
    response.status_code = 404
    return response


@require_GET
def health(request):
    return _no_store(HttpResponse("ok", content_type="text/plain"))


@require_GET
def favicon(request):
    return HttpResponse(status=204)
