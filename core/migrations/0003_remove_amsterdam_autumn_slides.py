from django.db import migrations


def remove_slides(apps, schema_editor):
    ArtSlide = apps.get_model("core", "ArtSlide")
    ArtSlide.objects.filter(
        static_path__in=[
            "art/slides/city-amsterdam.jpg",
            "art/slides/nature-autumn.jpg",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_add_art_slides"),
    ]

    operations = [
        migrations.RunPython(remove_slides, migrations.RunPython.noop),
    ]
