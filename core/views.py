from functools import wraps
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.art_slides import slide_has_source, slide_url_for
from core.binance_us import binance_us_portfolio
from core.earthquakes import bay_area_earthquakes
from core.icloud_album import icloud_album_widget, icloud_album_widget_payload
from core.models import ArtSlide, TvDisplayConfig
from core.weather import bay_area_weather
from core.wealth import wealth_widget

STANDALONE_WAIT_PATH = Path(settings.BASE_DIR) / "deploy" / "updating.html"


def _no_store(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def _standalone_wait_response() -> HttpResponse:
    content = STANDALONE_WAIT_PATH.read_text(encoding="utf-8")
    return _no_store(HttpResponse(content, content_type="text/html; charset=utf-8"))


def _widget_poll_seconds() -> dict[str, int]:
    binance_poll = 0
    if getattr(settings, "BINANCE_US_API_KEY", ""):
        binance_poll = getattr(settings, "BINANCE_US_CACHE_SECONDS", 300)

    return {
        "weather": getattr(settings, "TV_WEATHER_CACHE_SECONDS", 600),
        "earthquake": getattr(settings, "TV_EARTHQUAKE_CACHE_SECONDS", 600),
        "wealth": getattr(settings, "TV_WEALTH_POLL_SECONDS", 600),
        "binance": binance_poll,
        "display": getattr(settings, "TV_DISPLAY_POLL_SECONDS", 60),
        "icloud": getattr(settings, "TV_ICLOUD_ALBUM_POLL_SECONDS", 1800),
    }


def _device_widgets_allowed(request) -> bool:
    return bool(getattr(request, "aml_device_allowed", False))


def _require_allowed_device(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not _device_widgets_allowed(request):
            return HttpResponse(status=403)
        return view_func(request, *args, **kwargs)

    return wrapper


def _dashboard_context(request):
    display_config = TvDisplayConfig.load()
    now = timezone.localtime(timezone.now())
    slides = []
    widgets_allowed = _device_widgets_allowed(request)
    widget_poll = _widget_poll_seconds()

    for slide in ArtSlide.objects.filter(is_active=True):
        url = slide_url_for(request, slide)
        if not url:
            continue
        slides.append(
            {
                "url": url,
                "title": slide.title,
                "category": slide.category,
            }
        )

    icloud = icloud_album_widget()
    context = {
        "now": now,
        "theme_brightness": _theme_brightness(now),
        "TIME_ZONE": settings.TIME_ZONE,
        "widget_poll": widget_poll,
        "display_config": display_config,
        "slides": slides,
        "weather": bay_area_weather(),
        "earthquakes": bay_area_earthquakes(),
        "icloud_album": icloud,
        "icloud_photos": [
            {
                "url": photo.url,
                "caption": photo.caption,
                "width": photo.width,
                "height": photo.height,
            }
            for photo in icloud.photos
        ],
        "device_widgets_allowed": widgets_allowed,
    }

    if widgets_allowed:
        context["wealth"] = wealth_widget()
        context["binance"] = binance_us_portfolio()
    else:
        context["wealth"] = None
        context["binance"] = None
        context["widget_poll"] = {
            **widget_poll,
            "wealth": 0,
            "binance": 0,
        }

    return context


TV_THEME_DAY_START_HOUR = 7
TV_THEME_DAY_END_HOUR = 19


def _theme_brightness(local_moment) -> str:
    """Gallery HUD always renders in high-contrast dark mode."""
    return "night"


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
def tv_display_config(request):
    display_config = TvDisplayConfig.load()
    widgets_allowed = _device_widgets_allowed(request)
    widget_poll = _widget_poll_seconds()
    payload = {
        "static_build_id": getattr(settings, "STATIC_BUILD_ID", "1"),
        "slide_duration_seconds": display_config.slide_duration_seconds,
        "transition_seconds": float(display_config.transition_seconds),
        "slide_count": sum(
            1 for slide in ArtSlide.objects.filter(is_active=True) if slide_has_source(slide)
        ),
        "device_widgets_allowed": widgets_allowed,
        "wealth_poll_seconds": widget_poll["wealth"] if widgets_allowed else 0,
        "binance_poll_seconds": widget_poll["binance"] if widgets_allowed else 0,
    }
    return _no_store(JsonResponse(payload))


@require_GET
def tv_widget_weather(request):
    html = render_to_string(
        "partials/tv_hud_weather_fragment.html",
        {"weather": bay_area_weather()},
        request=request,
    )
    return _no_store(HttpResponse(html, content_type="text/html; charset=utf-8"))


@require_GET
def tv_widget_earthquake(request):
    html = render_to_string(
        "partials/tv_hud_earthquake_fragment.html",
        {"earthquakes": bay_area_earthquakes()},
        request=request,
    )
    return _no_store(HttpResponse(html, content_type="text/html; charset=utf-8"))


@require_GET
@_require_allowed_device
def tv_widget_wealth(request):
    html = render_to_string(
        "partials/tv_hud_wealth_fragment.html",
        {"wealth": wealth_widget()},
        request=request,
    )
    return _no_store(HttpResponse(html, content_type="text/html; charset=utf-8"))


@require_GET
@_require_allowed_device
def tv_widget_binance(request):
    html = render_to_string(
        "partials/tv_hud_binance_fragment.html",
        {"binance": binance_us_portfolio()},
        request=request,
    )
    return _no_store(HttpResponse(html, content_type="text/html; charset=utf-8"))


@require_GET
def tv_widget_icloud(request):
    return _no_store(JsonResponse(icloud_album_widget_payload()))


@require_GET
def health(request):
    return _no_store(HttpResponse("ok", content_type="text/plain"))


@require_GET
def favicon(request):
    return HttpResponse(status=204)
