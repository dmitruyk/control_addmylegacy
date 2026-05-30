from django.conf import settings

LOCAL_SERVICE_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "testserver"})


def resolve_service_mode(request) -> str:
    host = request.get_host().split(":")[0].lower()
    if host in LOCAL_SERVICE_HOSTS:
        return "local"
    return "production"


def resolve_service_base_url(request) -> str:
    if resolve_service_mode(request) == "local":
        return request.build_absolute_uri("/").rstrip("/")
    return settings.SITE_URL.rstrip("/")


def site_settings(request):
    service_mode = resolve_service_mode(request)
    service_base_url = resolve_service_base_url(request)

    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "MAIN_SITE_URL": settings.MAIN_SITE_URL,
        "GOOGLE_ANALYTICS_ID": getattr(settings, "GOOGLE_ANALYTICS_ID", ""),
        "STATIC_BUILD_ID": getattr(settings, "STATIC_BUILD_ID", "1"),
        "TV_REFRESH_SECONDS": getattr(settings, "TV_REFRESH_SECONDS", 60),
        "TV_HEALTH_POLL_SECONDS": getattr(settings, "TV_HEALTH_POLL_SECONDS", 3),
        "SERVICE_BASE_URL": service_base_url,
        "SERVICE_MODE": service_mode,
    }
