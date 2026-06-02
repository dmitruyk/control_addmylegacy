from datetime import date

from django.core.cache import cache
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
        COSMOS = "cosmos", "Cosmos"

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


class Retirement401kSnapshot(models.Model):
    """Manual 401(k) balance history for the TV wealth widget."""

    snapshot_date = models.DateField(unique=True, help_text="Statement or snapshot date.")
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total account balance on this date.",
    )
    employee_contribution = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Your contributions since the previous snapshot (optional).",
    )
    employer_match = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Employer match since the previous snapshot (optional).",
    )
    notes = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["snapshot_date"]
        verbose_name = "401(k) snapshot"
        verbose_name_plural = "401(k) snapshots"

    def __str__(self):
        return f"{self.snapshot_date}: ${self.balance:,.2f}"


class PropertyWatchConfig(models.Model):
    """Singleton Zillow property watch for the TV wealth widget (pk=1)."""

    zillow_zpid = models.CharField(
        max_length=32,
        default="15064292",
        help_text="Zillow property ID (from the URL, e.g. 15064292).",
    )
    zillow_url_slug = models.CharField(
        max_length=255,
        default="111-Chestnut-St-UNIT-612-San-Francisco-CA-94111",
        help_text="Address slug from the Zillow homedetails URL.",
    )
    address_label = models.CharField(
        max_length=120,
        default="111 Chestnut St #612, SF",
        help_text="Short label shown on the TV widget.",
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=635_000,
        help_text="Your purchase price for P&L comparison.",
    )
    mortgage_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=538_123,
        help_text="Current 20-year fixed mortgage balance.",
    )
    mortgage_start_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=538_123,
        help_text="Starting mortgage balance used for monthly auto-calculation.",
    )
    mortgage_start_date = models.DateField(
        default=date.today,
        help_text="Start date used for monthly mortgage auto-calculation.",
    )
    mortgage_monthly_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1227.92,
        help_text="Monthly principal+interest payment used in auto-calculation.",
    )
    mortgage_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.75,
        help_text="Annual mortgage interest rate (%) used in auto-calculation.",
    )
    manual_zestimate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional manual override when Zillow auto-fetch is blocked.",
    )
    cached_zestimate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )
    cached_zestimate_at = models.DateTimeField(null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Property watch configuration"
        verbose_name_plural = "Property watch configuration"

    def save(self, *args, **kwargs):
        previous = None
        if self.pk:
            previous = PropertyWatchConfig.objects.filter(pk=1).first()

        self.pk = 1
        super().save(*args, **kwargs)

        if previous and previous.zillow_zpid != self.zillow_zpid:
            cache.delete(f"tv_zillow_zestimate_{previous.zillow_zpid}_v1")
            cache.delete(f"tv_zillow_zestimate_{self.zillow_zpid}_v1")
            PropertyWatchConfig.objects.filter(pk=1).update(
                cached_zestimate=None,
                cached_zestimate_at=None,
            )

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "zillow_zpid": "15064292",
                "zillow_url_slug": "111-Chestnut-St-UNIT-612-San-Francisco-CA-94111",
                "address_label": "111 Chestnut St #612, SF",
                "purchase_price": 635_000,
                "mortgage_balance": 538_123,
                "mortgage_start_balance": 538_123,
            },
        )
        return obj

    @property
    def zillow_url(self) -> str:
        return (
            f"https://www.zillow.com/homedetails/"
            f"{self.zillow_url_slug}/{self.zillow_zpid}_zpid/"
        )

    def __str__(self):
        return self.address_label
