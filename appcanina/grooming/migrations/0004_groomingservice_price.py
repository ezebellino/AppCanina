# Generated manually for the service-to-sale flow.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("grooming", "0003_groomingappointment_additional_services")]

    operations = [
        migrations.AddField(
            model_name="groomingservice",
            name="price",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12, verbose_name="precio sugerido"),
        ),
    ]
