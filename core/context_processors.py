from django.conf import settings


def site_settings(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "MAIN_SITE_URL": settings.MAIN_SITE_URL,
        "GOOGLE_ANALYTICS_ID": getattr(settings, "GOOGLE_ANALYTICS_ID", ""),
        "STATIC_BUILD_ID": getattr(settings, "STATIC_BUILD_ID", "1"),
        "TV_REFRESH_SECONDS": getattr(settings, "TV_REFRESH_SECONDS", 60),
        "TV_HEALTH_POLL_SECONDS": getattr(settings, "TV_HEALTH_POLL_SECONDS", 3),
    }
