from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_icloud_album_widget"),
    ]

    operations = [
        migrations.AddField(
            model_name="icloudalbumconfig",
            name="size_scale_percent",
            field=models.IntegerField(
                default=100,
                help_text="Widget output size as % of the default max frame (0–300). 100 = normal, 200 = double.",
                validators=[MinValueValidator(0), MaxValueValidator(300)],
            ),
        ),
    ]
