from django.db import migrations, models


def seed_slides(apps, schema_editor):
    ArtSlide = apps.get_model("core", "ArtSlide")
    TvDisplayConfig = apps.get_model("core", "TvDisplayConfig")

    TvDisplayConfig.objects.get_or_create(
        pk=1,
        defaults={
            "show_info_panels": False,
            "slide_duration_seconds": 12,
            "transition_seconds": 2.0,
        },
    )

    slides = [
        ("New York", "city", "art/slides/city-new-york.jpg", 10),
        ("San Francisco", "city", "art/slides/city-san-francisco.jpg", 20),
        ("Tokyo", "city", "art/slides/city-tokyo.jpg", 30),
        ("Paris", "city", "art/slides/city-paris.jpg", 40),
        ("Chicago", "city", "art/slides/city-chicago.jpg", 50),
        ("London", "city", "art/slides/city-london.jpg", 60),
        ("Alpine Peaks", "nature", "art/slides/nature-mountains.jpg", 110),
        ("Forest Light", "nature", "art/slides/nature-forest.jpg", 120),
        ("Ocean Horizon", "nature", "art/slides/nature-ocean.jpg", 130),
        ("Desert Dunes", "nature", "art/slides/nature-desert.jpg", 140),
        ("Mountain Lake", "nature", "art/slides/nature-lake.jpg", 150),
        ("River Valley", "nature", "art/slides/nature-valley.jpg", 160),
    ]

    for title, category, static_path, sort_order in slides:
        ArtSlide.objects.get_or_create(
            static_path=static_path,
            defaults={
                "title": title,
                "category": category,
                "is_active": True,
                "sort_order": sort_order,
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TvDisplayConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("show_info_panels", models.BooleanField(default=False, help_text="Show status/info panels on the TV dashboard.")),
                ("slide_duration_seconds", models.PositiveIntegerField(default=12, help_text="Seconds each artwork slide stays visible.")),
                ("transition_seconds", models.DecimalField(decimal_places=1, default=2.0, help_text="Crossfade duration between slides.", max_digits=4)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "TV display configuration",
                "verbose_name_plural": "TV display configuration",
            },
        ),
        migrations.CreateModel(
            name="ArtSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("category", models.CharField(choices=[("city", "City"), ("nature", "Nature")], max_length=16)),
                ("static_path", models.CharField(help_text="Path under static/, e.g. art/slides/city-paris.jpg", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["sort_order", "title"],
            },
        ),
        migrations.RunPython(seed_slides, migrations.RunPython.noop),
    ]
