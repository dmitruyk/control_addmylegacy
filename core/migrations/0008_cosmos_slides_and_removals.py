from django.db import migrations, models


REMOVED_PATHS = (
    "art/slides/city-mexico-city.jpg",
    "art/slides/city-toronto.jpg",
    "art/slides/nature-rainforest.jpg",
    "art/slides/nature-volcano.jpg",
)

COSMOS_SLIDES = (
    ("Pillars of Creation", "cosmos", "art/slides/cosmos-pillars-of-creation.jpg", 240),
    ("Crab Nebula", "cosmos", "art/slides/cosmos-crab-nebula.jpg", 245),
    ("Milky Way", "cosmos", "art/slides/cosmos-milky-way.jpg", 250),
    ("Galaxy Band", "cosmos", "art/slides/cosmos-galaxy-band.jpg", 255),
    ("Deep Starfield", "cosmos", "art/slides/cosmos-starfield.jpg", 260),
    ("Andromeda Galaxy", "cosmos", "art/slides/cosmos-andromeda-galaxy.jpg", 265),
)


def apply_slide_changes(apps, schema_editor):
    ArtSlide = apps.get_model("core", "ArtSlide")
    ArtSlide.objects.filter(static_path__in=REMOVED_PATHS).delete()

    for title, category, static_path, sort_order in COSMOS_SLIDES:
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
        ("core", "0007_add_more_art_slides"),
    ]

    operations = [
        migrations.AlterField(
            model_name="artslide",
            name="category",
            field=models.CharField(
                choices=[
                    ("city", "City"),
                    ("nature", "Nature"),
                    ("cosmos", "Cosmos"),
                ],
                max_length=16,
            ),
        ),
        migrations.RunPython(apply_slide_changes, migrations.RunPython.noop),
    ]
