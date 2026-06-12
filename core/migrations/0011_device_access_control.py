from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_artslide_image_upload"),
    ]

    operations = [
        migrations.CreateModel(
            name="AllowedDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "device_hash",
                    models.CharField(
                        db_index=True,
                        help_text="SHA-256 fingerprint from stable request headers (no IP).",
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        help_text="Friendly name shown in admin (e.g. Living room TV).",
                        max_length=120,
                    ),
                ),
                ("user_agent", models.TextField(blank=True, help_text="Last seen User-Agent.")),
                (
                    "is_allowed",
                    models.BooleanField(
                        default=False,
                        help_text="When off, wealth and Binance widgets are hidden and API calls return 403.",
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "allowed device",
                "verbose_name_plural": "allowed devices",
                "ordering": ["-last_seen_at"],
            },
        ),
        migrations.CreateModel(
            name="DeviceAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_hash", models.CharField(db_index=True, max_length=64)),
                ("path", models.CharField(max_length=255)),
                (
                    "access_type",
                    models.CharField(
                        choices=[("page", "Page view"), ("restricted_widget", "Restricted widget API")],
                        max_length=32,
                    ),
                ),
                ("request_method", models.CharField(default="GET", max_length=8)),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("forwarded_for", models.CharField(blank=True, max_length=512)),
                ("network_headers", models.JSONField(blank=True, default=dict)),
                ("stable_headers", models.JSONField(blank=True, default=dict)),
                ("user_agent", models.TextField(blank=True)),
                ("is_allowed_at_access", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "allowed_device",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="access_logs",
                        to="core.alloweddevice",
                    ),
                ),
            ],
            options={
                "verbose_name": "device access log",
                "verbose_name_plural": "device access logs",
                "ordering": ["-created_at"],
            },
        ),
    ]
