from django.db import models


class TvDisplayConfig(models.Model):
    """Singleton TV display settings (admin → one row, pk=1)."""

    show_info_panels = models.BooleanField(
        default=False,
        help_text="Show status/info panels on the TV dashboard.",
    )
    slide_duration_seconds = models.PositiveIntegerField(
        default=12,
        help_text="Seconds each artwork slide stays visible.",
    )
    transition_seconds = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=2.0,
        help_text="Crossfade duration between slides.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TV display configuration"
        verbose_name_plural = "TV display configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "show_info_panels": False,
                "slide_duration_seconds": 12,
                "transition_seconds": 2.0,
            },
        )
        return obj

    def __str__(self):
        return "TV display configuration"


class ArtSlide(models.Model):
    class Category(models.TextChoices):
        CITY = "city", "City"
        NATURE = "nature", "Nature"

    title = models.CharField(max_length=120)
    category = models.CharField(max_length=16, choices=Category.choices)
    static_path = models.CharField(
        max_length=255,
        help_text="Path under static/, e.g. art/slides/city-paris.jpg",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title
