from django.contrib import admin

from .models import ArtSlide, TvDisplayConfig


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


@admin.register(ArtSlide)
class ArtSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "static_path", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("category", "is_active")
    search_fields = ("title", "static_path")
    ordering = ("sort_order", "title")
