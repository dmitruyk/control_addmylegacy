from datetime import date

from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.art_slides import art_slide_upload_to, normalize_uploaded_slide, slide_has_source

ART_SLIDE_UPLOAD_TO = art_slide_upload_to


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


class IcloudAlbumConfig(models.Model):
    """Singleton iCloud shared album widget for the TV HUD (pk=1)."""

    is_enabled = models.BooleanField(
        default=True,
        help_text="Show the iCloud photo slideshow in the lower-left HUD corner.",
    )
    title = models.CharField(
        max_length=80,
        default="Shared Album",
        help_text="Label shown above the photo slideshow.",
    )
    shared_album_url = models.URLField(
        max_length=512,
        default="https://www.icloud.com/sharedalbum/#B29JtdOXmok8Aj",
        help_text="Public iCloud shared album link (hash or share.icloud.com format).",
    )
    slide_duration_seconds = models.PositiveIntegerField(
        default=8,
        help_text="Seconds each photo stays visible in the widget.",
    )
    transition_seconds = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=1.5,
        help_text="Crossfade duration between widget photos.",
    )
    size_scale_percent = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(300)],
        help_text="Widget output size as % of the default max frame (0–300). 100 = normal, 200 = double.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "iCloud album widget"
        verbose_name_plural = "iCloud album widget"

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
                "is_enabled": True,
                "title": "Shared Album",
                "shared_album_url": "https://www.icloud.com/sharedalbum/#B29JtdOXmok8Aj",
                "slide_duration_seconds": 8,
                "transition_seconds": 1.5,
                "size_scale_percent": 100,
            },
        )
        return obj

    def __str__(self):
        return self.title


class ArtSlide(models.Model):
    class Category(models.TextChoices):
        CITY = "city", "City"
        NATURE = "nature", "Nature"
        COSMOS = "cosmos", "Cosmos"

    title = models.CharField(max_length=120)
    category = models.CharField(max_length=16, choices=Category.choices)
    image = models.ImageField(
        upload_to=ART_SLIDE_UPLOAD_TO,
        blank=True,
        help_text="Upload a photo from your phone or computer (auto-resized to 1920×1080).",
    )
    static_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Legacy bundled path under static/, e.g. art/slides/city-paris.jpg",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def save(self, *args, **kwargs):
        if self.image and not getattr(self.image, "_committed", True):
            normalized = normalize_uploaded_slide(self.image.file)
            storage_path = ART_SLIDE_UPLOAD_TO(self, normalized.name)
            self.image.save(storage_path, normalized, save=False)
        super().save(*args, **kwargs)

    @property
    def has_source(self) -> bool:
        return slide_has_source(self)

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


class Retirement401kConfig(models.Model):
    """Singleton 401(k) goal settings for the TV wealth widget (pk=1)."""

    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional savings goal shown on the 401(k) chart.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "401(k) configuration"
        verbose_name_plural = "401(k) configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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


class AllowedDevice(models.Model):
    """TV / kiosk device allowlist. All devices are blocked until is_allowed=True."""

    device_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 fingerprint from stable request headers (no IP).",
    )
    label = models.CharField(
        max_length=120,
        help_text="Friendly name shown in admin (e.g. Living room TV).",
    )
    user_agent = models.TextField(blank=True, help_text="Last seen User-Agent.")
    is_allowed = models.BooleanField(
        default=False,
        help_text="When off, wealth and Binance widgets are hidden and API calls return 403.",
    )
    notes = models.TextField(blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = "allowed device"
        verbose_name_plural = "allowed devices"

    def __str__(self):
        status = "allowed" if self.is_allowed else "blocked"
        return f"{self.label} ({status})"


class DeviceAccessLog(models.Model):
    class AccessType(models.TextChoices):
        PAGE = "page", "Page view"
        RESTRICTED_WIDGET = "restricted_widget", "Restricted widget API"

    device_hash = models.CharField(max_length=64, db_index=True)
    allowed_device = models.ForeignKey(
        AllowedDevice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_logs",
    )
    path = models.CharField(max_length=255)
    access_type = models.CharField(max_length=32, choices=AccessType.choices)
    request_method = models.CharField(max_length=8, default="GET")
    ip_address = models.CharField(max_length=64, blank=True)
    forwarded_for = models.CharField(max_length=512, blank=True)
    network_headers = models.JSONField(default=dict, blank=True)
    stable_headers = models.JSONField(default=dict, blank=True)
    user_agent = models.TextField(blank=True)
    is_allowed_at_access = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "device access log"
        verbose_name_plural = "device access logs"

    def __str__(self):
        return f"{self.path} @ {self.created_at:%Y-%m-%d %H:%M}"
