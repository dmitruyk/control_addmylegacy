import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.models import ArtSlide, TvDisplayConfig
from core.weather import bay_area_weather


def _slide_url(request, static_path: str) -> str:
    url = static(static_path)
    build_id = getattr(settings, "STATIC_BUILD_ID", "1")
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}v={build_id}"

    if request:
        return request.build_absolute_uri(url)

    return url


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
        "refresh_seconds": settings.TV_REFRESH_SECONDS,
        "display_config": display_config,
        "slides_json": json.dumps(slides),
        "slides": slides,
        "weather": bay_area_weather(),
    }


@require_GET
def tv_dashboard(request):
    return render(request, "core/tv_dashboard.html", _dashboard_context(request))


@require_GET
def updating_page(request):
    return render(request, "core/tv_dashboard.html", _dashboard_context(request))


@require_GET
def wait_page(request):
    response = render(
        request,
        "core/wait_shell.html",
        {
            "poll_seconds": settings.TV_HEALTH_POLL_SECONDS,
        },
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


def page_not_found(request, exception):
    response = wait_page(request)
    response.status_code = 404
    return response


@require_GET
def health(request):
    response = HttpResponse("ok", content_type="text/plain")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@require_GET
def favicon(request):
    return HttpResponse(status=204)
