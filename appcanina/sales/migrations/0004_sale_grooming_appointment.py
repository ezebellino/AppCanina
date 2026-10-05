# Generated manually for the appointment checkout flow.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("grooming", "0004_groomingservice_price"), ("sales", "0003_cashsession_cashmovement_sale_cash_session")]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="grooming_appointment",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sale", to="grooming.groomingappointment", verbose_name="turno de peluquería"),
        ),
    ]
