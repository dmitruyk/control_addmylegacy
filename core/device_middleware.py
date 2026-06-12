"""Attach device fingerprint and log TV page / restricted widget access."""

from core.device_access import (
    attach_device_context,
    is_restricted_widget_path,
    log_device_access,
    should_log_page_access,
)


class DeviceAccessMiddleware:
    TV_PATH_PREFIXES = ("/api/tv/",)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if not self._is_tv_path(path):
            return self.get_response(request)

        attach_device_context(request)

        if should_log_page_access(path):
            log_device_access(request, path=path, access_type="page")

        response = self.get_response(request)

        if is_restricted_widget_path(path):
            log_device_access(
                request,
                path=path,
                access_type="restricted_widget",
                is_allowed=response.status_code == 200,
            )

        return response

    @classmethod
    def _is_tv_path(cls, path: str) -> bool:
        if path in {"/", "/updating/"}:
            return True
        return any(path.startswith(prefix) for prefix in cls.TV_PATH_PREFIXES)
