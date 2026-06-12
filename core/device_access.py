"""Device fingerprinting and access control for restricted TV widgets."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.http import HttpRequest
from django.utils import timezone

# Stable client headers used for device identity (must not include IP/network).
STABLE_FINGERPRINT_HEADERS = (
    "HTTP_USER_AGENT",
    "HTTP_ACCEPT_LANGUAGE",
    "HTTP_ACCEPT_ENCODING",
    "HTTP_SEC_CH_UA",
    "HTTP_SEC_CH_UA_MOBILE",
    "HTTP_SEC_CH_UA_PLATFORM",
    "HTTP_SEC_CH_UA_PLATFORM_VERSION",
    "HTTP_SEC_CH_UA_MODEL",
    "HTTP_SEC_CH_UA_FULL_VERSION_LIST",
    "HTTP_DNT",
)

# Network / session headers logged for review only — never hashed.
NETWORK_LOG_HEADERS = (
    "REMOTE_ADDR",
    "HTTP_X_FORWARDED_FOR",
    "HTTP_X_REAL_IP",
    "HTTP_CF_CONNECTING_IP",
    "HTTP_VIA",
    "HTTP_X_FORWARDED_HOST",
    "HTTP_X_FORWARDED_PROTO",
    "HTTP_HOST",
    "HTTP_CONNECTION",
    "HTTP_FORWARDED",
)

PUBLIC_WIDGET_PATHS = frozenset(
    {
        "/api/tv/widgets/weather/",
        "/api/tv/widgets/earthquakes/",
    }
)

RESTRICTED_WIDGET_PATHS = frozenset(
    {
        "/api/tv/widgets/wealth/",
        "/api/tv/widgets/binance/",
    }
)

PAGE_ACCESS_LOG_PATHS = frozenset(
    {
        "/",
        "/updating/",
    }
)


def _header_value(request: HttpRequest, key: str) -> str:
    value = request.META.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def stable_headers_snapshot(request: HttpRequest) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for key in STABLE_FINGERPRINT_HEADERS:
        value = _header_value(request, key)
        if value:
            snapshot[key.removeprefix("HTTP_").replace("_", "-")] = value
    return snapshot


def network_headers_snapshot(request: HttpRequest) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for key in NETWORK_LOG_HEADERS:
        value = _header_value(request, key)
        if value:
            snapshot[key.removeprefix("HTTP_").replace("_", "-")] = value
    return snapshot


def device_fingerprint(request: HttpRequest) -> str:
    """SHA-256 hash from stable request headers (no IP or network fields)."""
    parts: list[str] = []
    for key in STABLE_FINGERPRINT_HEADERS:
        value = _header_value(request, key)
        if value:
            parts.append(f"{key}={value}")
    payload = "\n".join(parts) or "empty-fingerprint"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _label_from_user_agent(user_agent: str) -> str:
    cleaned = " ".join(user_agent.split())
    if not cleaned:
        return "Unknown device"
    if len(cleaned) <= 80:
        return cleaned
    return f"{cleaned[:77]}..."


def ensure_device_record(request: HttpRequest, device_hash: str):
    from core.models import AllowedDevice

    user_agent = _header_value(request, "HTTP_USER_AGENT")
    now = timezone.now()
    device, created = AllowedDevice.objects.get_or_create(
        device_hash=device_hash,
        defaults={
            "label": _label_from_user_agent(user_agent),
            "user_agent": user_agent,
            "is_allowed": False,
            "first_seen_at": now,
            "last_seen_at": now,
        },
    )
    if created:
        return device

    device.last_seen_at = now
    if user_agent and device.user_agent != user_agent:
        device.user_agent = user_agent
        device.save(update_fields=["last_seen_at", "user_agent"])
    else:
        device.save(update_fields=["last_seen_at"])
    return device


def is_device_allowed(request: HttpRequest) -> bool:
    device_hash = getattr(request, "aml_device_hash", None)
    if not device_hash:
        device_hash = device_fingerprint(request)
    from core.models import AllowedDevice

    return AllowedDevice.objects.filter(device_hash=device_hash, is_allowed=True).exists()


def attach_device_context(request: HttpRequest) -> None:
    device_hash = device_fingerprint(request)
    device = ensure_device_record(request, device_hash)
    request.aml_device_hash = device_hash
    request.aml_device_allowed = device.is_allowed
    request.aml_device = device


def log_device_access(
    request: HttpRequest,
    *,
    path: str,
    access_type: str,
    is_allowed: bool | None = None,
) -> None:
    from core.models import DeviceAccessLog

    device_hash = getattr(request, "aml_device_hash", None) or device_fingerprint(request)
    device = getattr(request, "aml_device", None)
    if device is None:
        device = ensure_device_record(request, device_hash)

    if is_allowed is None:
        is_allowed = bool(getattr(request, "aml_device_allowed", device.is_allowed))

    network = network_headers_snapshot(request)
    ip_address = network.get("REMOTE-ADDR") or network.get("X-FORWARDED-FOR", "")[:255]

    DeviceAccessLog.objects.create(
        device_hash=device_hash,
        allowed_device=device,
        path=path[:255],
        access_type=access_type,
        request_method=request.method,
        ip_address=ip_address[:64] if ip_address else "",
        forwarded_for=network.get("X-FORWARDED-FOR", "")[:512],
        network_headers=network,
        stable_headers=stable_headers_snapshot(request),
        user_agent=_header_value(request, "HTTP_USER_AGENT")[:2000],
        is_allowed_at_access=is_allowed,
    )


def should_log_page_access(path: str) -> bool:
    return path in PAGE_ACCESS_LOG_PATHS


def is_restricted_widget_path(path: str) -> bool:
    return path in RESTRICTED_WIDGET_PATHS


def headers_json_pretty(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
