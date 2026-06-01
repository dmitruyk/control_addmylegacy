from decimal import Decimal

from django.db import migrations, models


def seed_mortgage_balance(apps, schema_editor):
    PropertyWatchConfig = apps.get_model("core", "PropertyWatchConfig")
    PropertyWatchConfig.objects.update_or_create(
        pk=1,
        defaults={"mortgage_balance": Decimal("538123.00")},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_wealth_widget"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertywatchconfig",
            name="mortgage_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=538123,
                help_text="Current 20-year fixed mortgage balance.",
                max_digits=12,
            ),
        ),
        migrations.RunPython(seed_mortgage_balance, migrations.RunPython.noop),
    ]
