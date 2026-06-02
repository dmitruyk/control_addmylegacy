from django.db import migrations


def remove_interacting_galaxies(apps, schema_editor):
    ArtSlide = apps.get_model("core", "ArtSlide")
    ArtSlide.objects.filter(
        static_path="art/slides/cosmos-interacting-galaxies.jpg",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_cosmos_slides_and_removals"),
    ]

    operations = [
        migrations.RunPython(remove_interacting_galaxies, migrations.RunPython.noop),
    ]
