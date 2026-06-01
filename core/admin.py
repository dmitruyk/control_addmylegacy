from django.contrib import admin

from .models import ArtSlide, PropertyWatchConfig, Retirement401kSnapshot, TvDisplayConfig


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


@admin.register(ArtSlide)
class ArtSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "static_path", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("category", "is_active")
    search_fields = ("title", "static_path")
    ordering = ("sort_order", "title")
