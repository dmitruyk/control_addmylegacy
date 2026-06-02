from django.db import migrations


def add_more_art_slides(apps, schema_editor):
    ArtSlide = apps.get_model("core", "ArtSlide")

    slides = [
        ("Singapore", "city", "art/slides/city-singapore.jpg", 91),
        ("Seoul", "city", "art/slides/city-seoul.jpg", 92),
        ("Lisbon", "city", "art/slides/city-lisbon.jpg", 93),
        ("Prague", "city", "art/slides/city-prague.jpg", 94),
        ("Amsterdam", "city", "art/slides/city-amsterdam.jpg", 95),
        ("Mexico City", "city", "art/slides/city-mexico-city.jpg", 96),
        ("Toronto", "city", "art/slides/city-toronto.jpg", 97),
        ("Istanbul", "city", "art/slides/city-istanbul.jpg", 98),
        ("Rainforest", "nature", "art/slides/nature-rainforest.jpg", 201),
        ("African Savanna", "nature", "art/slides/nature-savanna.jpg", 205),
        ("Volcano", "nature", "art/slides/nature-volcano.jpg", 210),
        ("Cherry Blossoms", "nature", "art/slides/nature-cherry-blossoms.jpg", 215),
        ("Starry Sky", "nature", "art/slides/nature-starry-sky.jpg", 220),
        ("Bamboo Grove", "nature", "art/slides/nature-bamboo.jpg", 225),
        ("Tropical Coast", "nature", "art/slides/nature-tropical-coast.jpg", 230),
        ("Autumn Trail", "nature", "art/slides/nature-autumn-trail.jpg", 235),
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
        ("core", "0006_property_mortgage_auto_fields"),
    ]

    operations = [
        migrations.RunPython(add_more_art_slides, migrations.RunPython.noop),
    ]
