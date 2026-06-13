from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_icloud_album_size_scale"),
    ]

    operations = [
        migrations.CreateModel(
            name="Retirement401kConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "target_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Optional savings goal shown on the 401(k) chart.",
                        max_digits=12,
                        null=True,
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "401(k) configuration",
                "verbose_name_plural": "401(k) configuration",
            },
        ),
    ]
