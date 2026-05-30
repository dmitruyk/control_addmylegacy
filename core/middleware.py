"""
Optional: redirect / to /updating/ while TV_MAINTENANCE_MODE is enabled.
Both routes render the same dashboard; tv-boot.js keeps waiting until ready.
"""
from django.conf import settings
from django.http import HttpResponseRedirect


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.TV_MAINTENANCE_MODE and request.path == "/":
            return HttpResponseRedirect("/updating/")

        return self.get_response(request)
