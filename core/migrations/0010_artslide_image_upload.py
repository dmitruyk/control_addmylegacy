from django.db import migrations, models

import core.art_slides


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_remove_interacting_galaxies_slide"),
    ]

    operations = [
        migrations.AddField(
            model_name="artslide",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Upload a photo from your phone or computer (auto-resized to 1920×1080).",
                upload_to=core.art_slides.art_slide_upload_to,
            ),
        ),
        migrations.AlterField(
            model_name="artslide",
            name="static_path",
            field=models.CharField(
                blank=True,
                help_text="Legacy bundled path under static/, e.g. art/slides/city-paris.jpg",
                max_length=255,
            ),
        ),
    ]
