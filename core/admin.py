from django.contrib import admin, messages
from django.templatetags.static import static
from django.utils.html import format_html

from core.icloud_album import extract_album_id, invalidate_icloud_album_cache

from .models import (
    AllowedDevice,
    ArtSlide,
    DeviceAccessLog,
    IcloudAlbumConfig,
    PropertyWatchConfig,
    Retirement401kSnapshot,
    TvDisplayConfig,
)


@admin.register(TvDisplayConfig)
class TvDisplayConfigAdmin(admin.ModelAdmin):
    list_display = ("show_info_panels", "slide_duration_seconds", "transition_seconds", "updated_at")
    fieldsets = (
        (
            "Information panels",
            {
                "fields": ("show_info_panels",),
                "description": "When off, only the art slideshow and weather/time HUD are shown.",
            },
        ),
        (
            "Slideshow",
            {
                "fields": ("slide_duration_seconds", "transition_seconds"),
            },
        ),
    )

    def has_add_permission(self, request):
        return not TvDisplayConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IcloudAlbumConfig)
class IcloudAlbumConfigAdmin(admin.ModelAdmin):
    list_display = ("title", "is_enabled", "size_scale_percent", "shared_album_url", "slide_duration_seconds", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": ("is_enabled", "title", "shared_album_url"),
                "description": (
                    "Paste a public iCloud shared album link. "
                    "Example: https://www.icloud.com/sharedalbum/#B29JtdOXmok8Aj"
                ),
            },
        ),
        (
            "Slideshow",
            {
                "fields": ("slide_duration_seconds", "transition_seconds", "size_scale_percent"),
                "description": (
                    "size_scale_percent sets widget output size relative to the default max frame "
                    "(100 = normal, 200 = double, 0 = hidden). "
                    "The TV reloads this value on every slide change."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return not IcloudAlbumConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        previous_album_id = None
        if change:
            previous = IcloudAlbumConfig.objects.filter(pk=1).first()
            if previous:
                previous_album_id = extract_album_id(previous.shared_album_url)

        super().save_model(request, obj, form, change)
        invalidate_icloud_album_cache(previous_album_id)
        invalidate_icloud_album_cache(extract_album_id(obj.shared_album_url))


@admin.register(Retirement401kSnapshot)
class Retirement401kSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "snapshot_date",
        "balance",
        "employee_contribution",
        "employer_match",
        "notes",
        "created_at",
    )
    list_filter = ("snapshot_date",)
    ordering = ("-snapshot_date",)
    date_hierarchy = "snapshot_date"


@admin.register(PropertyWatchConfig)
class PropertyWatchConfigAdmin(admin.ModelAdmin):
    list_display = (
        "address_label",
        "zillow_zpid",
        "purchase_price",
        "mortgage_start_balance",
        "mortgage_start_date",
        "mortgage_monthly_payment",
        "mortgage_interest_rate",
        "manual_zestimate",
        "cached_zestimate",
        "cached_zestimate_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Property",
            {
                "fields": ("address_label", "purchase_price", "manual_zestimate"),
                "description": (
                    "Set manual Zestimate when Zillow auto-fetch is blocked (403). "
                    "Auto-fetch runs at most once per day."
                ),
            },
        ),
        (
            "Mortgage automation",
            {
                "fields": (
                    "mortgage_start_balance",
                    "mortgage_start_date",
                    "mortgage_monthly_payment",
                    "mortgage_interest_rate",
                    "mortgage_balance",
                ),
                "description": "Current mortgage balance is recalculated monthly from start balance/date, payment, and rate.",
            },
        ),
        (
            "Zillow",
            {
                "fields": ("zillow_zpid", "zillow_url_slug"),
                "description": (
                    "Update zpid and URL slug when tracking a different listing. "
                    "Example slug: 111-Chestnut-St-UNIT-612-San-Francisco-CA-94111"
                ),
            },
        ),
        (
            "Cached feed",
            {
                "fields": ("cached_zestimate", "cached_zestimate_at"),
            },
        ),
    )
    readonly_fields = ("mortgage_balance", "cached_zestimate", "cached_zestimate_at", "updated_at")

    def has_add_permission(self, request):
        return not PropertyWatchConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AllowedDevice)
class AllowedDeviceAdmin(admin.ModelAdmin):
    list_display = ("label", "is_allowed", "device_hash_short", "last_seen_at", "first_seen_at")
    list_filter = ("is_allowed",)
    search_fields = ("label", "device_hash", "user_agent", "notes")
    readonly_fields = (
        "device_hash",
        "user_agent",
        "first_seen_at",
        "last_seen_at",
        "recent_access_logs",
    )
    actions = ("allow_selected_devices", "block_selected_devices")

    def has_add_permission(self, request):
        return False

    fieldsets = (
        (
            None,
            {
                "fields": ("label", "is_allowed", "notes"),
                "description": (
                    "All devices are blocked by default. Enable is_allowed to grant wealth and Binance widgets. "
                    "Device identity uses stable browser headers only — not IP."
                ),
            },
        ),
        (
            "Fingerprint",
            {
                "fields": ("device_hash", "user_agent", "first_seen_at", "last_seen_at"),
            },
        ),
        (
            "Recent access",
            {
                "fields": ("recent_access_logs",),
            },
        ),
    )

    @admin.display(description="Device hash")
    def device_hash_short(self, obj):
        return f"{obj.device_hash[:12]}…"

    @admin.display(description="Recent access logs")
    def recent_access_logs(self, obj):
        logs = obj.access_logs.order_by("-created_at")[:10]
        if not logs:
            return "No access logs yet."

        rows = []
        for log in logs:
            status = "allowed" if log.is_allowed_at_access else "blocked"
            ip = log.ip_address or "—"
            rows.append(
                f"<tr><td>{log.created_at:%Y-%m-%d %H:%M}</td>"
                f"<td>{log.path}</td><td>{log.access_type}</td>"
                f"<td>{status}</td><td>{ip}</td></tr>"
            )
        return format_html(
            '<table style="width:100%"><thead><tr>'
            "<th>When</th><th>Path</th><th>Type</th><th>Status</th><th>IP</th>"
            "</tr></thead><tbody>{}</tbody></table>",
            format_html("".join(rows)),
        )

    @admin.action(description="Allow selected devices")
    def allow_selected_devices(self, request, queryset):
        updated = queryset.update(is_allowed=True)
        self.message_user(request, f"{updated} device(s) allowed.", messages.SUCCESS)

    @admin.action(description="Block selected devices")
    def block_selected_devices(self, request, queryset):
        updated = queryset.update(is_allowed=False)
        self.message_user(request, f"{updated} device(s) blocked.", messages.WARNING)


@admin.register(DeviceAccessLog)
class DeviceAccessLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "path",
        "access_type",
        "is_allowed_at_access",
        "ip_address",
        "device_label",
        "device_hash_short",
    )
    list_filter = ("access_type", "is_allowed_at_access", "created_at")
    search_fields = ("path", "device_hash", "ip_address", "forwarded_for", "user_agent")
    readonly_fields = (
        "device_hash",
        "allowed_device",
        "path",
        "access_type",
        "request_method",
        "ip_address",
        "forwarded_for",
        "network_headers_pretty",
        "stable_headers_pretty",
        "user_agent",
        "is_allowed_at_access",
        "created_at",
    )
    date_hierarchy = "created_at"
    actions = ("allow_device_from_log",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Device")
    def device_label(self, obj):
        if obj.allowed_device_id:
            return obj.allowed_device.label
        return "—"

    @admin.display(description="Device hash")
    def device_hash_short(self, obj):
        return f"{obj.device_hash[:12]}…"

    @admin.display(description="Network headers")
    def network_headers_pretty(self, obj):
        from core.device_access import headers_json_pretty

        return format_html("<pre style='white-space:pre-wrap'>{}</pre>", headers_json_pretty(obj.network_headers))

    @admin.display(description="Stable headers (fingerprint)")
    def stable_headers_pretty(self, obj):
        from core.device_access import headers_json_pretty

        return format_html("<pre style='white-space:pre-wrap'>{}</pre>", headers_json_pretty(obj.stable_headers))

    @admin.action(description="Allow device from selected log entries")
    def allow_device_from_log(self, request, queryset):
        updated = AllowedDevice.objects.filter(
            device_hash__in=queryset.values_list("device_hash", flat=True).distinct()
        ).update(is_allowed=True)
        self.message_user(request, f"{updated} device(s) allowed from log entries.", messages.SUCCESS)


@admin.register(ArtSlide)
class ArtSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "preview_thumb", "source_type", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("category", "is_active")
    search_fields = ("title", "static_path")
    ordering = ("sort_order", "title")
    readonly_fields = ("preview_large",)
    fieldsets = (
        (
            None,
            {
                "fields": ("title", "category", "image", "preview_large", "is_active", "sort_order"),
                "description": (
                    "Upload a photo from iPhone Safari or desktop. "
                    "Images are auto-resized to 1920×1080 for the TV."
                ),
            },
        ),
        (
            "Legacy bundled slide",
            {
                "classes": ("collapse",),
                "fields": ("static_path",),
                "description": "Only for slides shipped in static/art/slides/. Leave empty for uploads.",
            },
        ),
    )

    @admin.display(description="Preview")
    def preview_thumb(self, obj):
        return self._preview_markup(obj, width=72)

    @admin.display(description="Preview")
    def preview_large(self, obj):
        return self._preview_markup(obj, width=320)

    @admin.display(description="Source")
    def source_type(self, obj):
        if obj.image:
            return "Upload"
        if obj.static_path:
            return "Bundled"
        return "Missing"

    def _preview_markup(self, obj, width: int):
        if obj.image:
            return format_html('<img src="{}" alt="" width="{}" style="border-radius:4px;">', obj.image.url, width)
        if obj.static_path:
            return format_html(
                '<img src="{}" alt="" width="{}" style="border-radius:4px;">',
                static(obj.static_path),
                width,
            )
        return "—"
