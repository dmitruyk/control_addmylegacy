import datetime
from decimal import Decimal

from django.db import migrations, models


def seed_mortgage_auto_fields(apps, schema_editor):
    PropertyWatchConfig = apps.get_model("core", "PropertyWatchConfig")
    config = PropertyWatchConfig.objects.filter(pk=1).first()
    if not config:
        PropertyWatchConfig.objects.create(
            pk=1,
            mortgage_start_balance=Decimal("538123.00"),
            mortgage_balance=Decimal("538123.00"),
            mortgage_start_date=datetime.date.today(),
            mortgage_monthly_payment=Decimal("1227.92"),
            mortgage_interest_rate=Decimal("5.75"),
        )
        return

    start_balance = config.mortgage_balance or Decimal("538123.00")
    PropertyWatchConfig.objects.filter(pk=1).update(
        mortgage_start_balance=start_balance,
        mortgage_start_date=datetime.date.today(),
        mortgage_monthly_payment=Decimal("1227.92"),
        mortgage_interest_rate=Decimal("5.75"),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_property_mortgage_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertywatchconfig",
            name="mortgage_start_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=538123,
                help_text="Starting mortgage balance used for monthly auto-calculation.",
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="propertywatchconfig",
            name="mortgage_start_date",
            field=models.DateField(
                default=datetime.date.today,
                help_text="Start date used for monthly mortgage auto-calculation.",
            ),
        ),
        migrations.AddField(
            model_name="propertywatchconfig",
            name="mortgage_monthly_payment",
            field=models.DecimalField(
                decimal_places=2,
                default=1227.92,
                help_text="Monthly principal+interest payment used in auto-calculation.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="propertywatchconfig",
            name="mortgage_interest_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=5.75,
                help_text="Annual mortgage interest rate (%) used in auto-calculation.",
                max_digits=5,
            ),
        ),
        migrations.RunPython(seed_mortgage_auto_fields, migrations.RunPython.noop),
    ]
