from decimal import Decimal

from django.db import migrations, models


def seed_property_config(apps, schema_editor):
    PropertyWatchConfig = apps.get_model("core", "PropertyWatchConfig")
    PropertyWatchConfig.objects.get_or_create(
        pk=1,
        defaults={
            "zillow_zpid": "15064292",
            "zillow_url_slug": "111-Chestnut-St-UNIT-612-San-Francisco-CA-94111",
            "address_label": "111 Chestnut St #612, SF",
            "purchase_price": Decimal("635000.00"),
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_remove_amsterdam_autumn_slides"),
    ]

    operations = [
        migrations.CreateModel(
            name="Retirement401kSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("snapshot_date", models.DateField(help_text="Statement or snapshot date.", unique=True)),
                (
                    "balance",
                    models.DecimalField(decimal_places=2, help_text="Total account balance on this date.", max_digits=12),
                ),
                (
                    "employee_contribution",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Your contributions since the previous snapshot (optional).",
                        max_digits=10,
                    ),
                ),
                (
                    "employer_match",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Employer match since the previous snapshot (optional).",
                        max_digits=10,
                    ),
                ),
                ("notes", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "401(k) snapshot",
                "verbose_name_plural": "401(k) snapshots",
                "ordering": ["snapshot_date"],
            },
        ),
        migrations.CreateModel(
            name="PropertyWatchConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "zillow_zpid",
                    models.CharField(
                        default="15064292",
                        help_text="Zillow property ID (from the URL, e.g. 15064292).",
                        max_length=32,
                    ),
                ),
                (
                    "zillow_url_slug",
                    models.CharField(
                        default="111-Chestnut-St-UNIT-612-San-Francisco-CA-94111",
                        help_text="Address slug from the Zillow homedetails URL.",
                        max_length=255,
                    ),
                ),
                (
                    "address_label",
                    models.CharField(
                        default="111 Chestnut St #612, SF",
                        help_text="Short label shown on the TV widget.",
                        max_length=120,
                    ),
                ),
                (
                    "purchase_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=635000,
                        help_text="Your purchase price for P&L comparison.",
                        max_digits=12,
                    ),
                ),
                (
                    "manual_zestimate",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Optional manual override when Zillow auto-fetch is blocked.",
                        max_digits=12,
                        null=True,
                    ),
                ),
                ("cached_zestimate", models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=12, null=True)),
                ("cached_zestimate_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Property watch configuration",
                "verbose_name_plural": "Property watch configuration",
            },
        ),
        migrations.RunPython(seed_property_config, migrations.RunPython.noop),
    ]
