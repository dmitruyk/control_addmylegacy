from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_device_access_control"),
    ]

    operations = [
        migrations.CreateModel(
            name="IcloudAlbumConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Show the iCloud photo slideshow in the lower-left HUD corner.",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        default="Shared Album",
                        help_text="Label shown above the photo slideshow.",
                        max_length=80,
                    ),
                ),
                (
                    "shared_album_url",
                    models.URLField(
                        default="https://www.icloud.com/sharedalbum/#B29JtdOXmok8Aj",
                        help_text="Public iCloud shared album link (hash or share.icloud.com format).",
                        max_length=512,
                    ),
                ),
                (
                    "slide_duration_seconds",
                    models.PositiveIntegerField(
                        default=8,
                        help_text="Seconds each photo stays visible in the widget.",
                    ),
                ),
                (
                    "transition_seconds",
                    models.DecimalField(
                        decimal_places=1,
                        default=1.5,
                        help_text="Crossfade duration between widget photos.",
                        max_digits=4,
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "iCloud album widget",
                "verbose_name_plural": "iCloud album widget",
            },
        ),
    ]
