from django.db import migrations


def add_art_slides(apps, schema_editor):
    ArtSlide = apps.get_model("core", "ArtSlide")

    slides = [
        ("Hong Kong", "city", "art/slides/city-hong-kong.jpg", 65),
        ("Venice", "city", "art/slides/city-venice.jpg", 70),
        ("Dubai", "city", "art/slides/city-dubai.jpg", 75),
        ("Barcelona", "city", "art/slides/city-barcelona.jpg", 80),
        ("Rome", "city", "art/slides/city-rome.jpg", 85),
        ("Sydney", "city", "art/slides/city-sydney.jpg", 90),
        ("Amsterdam", "city", "art/slides/city-amsterdam.jpg", 95),
        ("Sunlit Forest", "nature", "art/slides/nature-sunlit-forest.jpg", 125),
        ("Misty Peaks", "nature", "art/slides/nature-misty-peaks.jpg", 165),
        ("Waterfall", "nature", "art/slides/nature-waterfall.jpg", 170),
        ("Misty Hills", "nature", "art/slides/nature-mist.jpg", 175),
        ("Aurora", "nature", "art/slides/nature-aurora.jpg", 180),
        ("Tropical Beach", "nature", "art/slides/nature-beach.jpg", 185),
        ("Red Canyon", "nature", "art/slides/nature-canyon.jpg", 190),
        ("Autumn Trail", "nature", "art/slides/nature-autumn.jpg", 195),
        ("Glacier Peaks", "nature", "art/slides/nature-glacier.jpg", 200),
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
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_art_slides, migrations.RunPython.noop),
    ]
