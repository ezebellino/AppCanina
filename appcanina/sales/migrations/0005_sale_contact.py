# Generated manually for commercial history by responsible.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("patients", "0003_patient_photo"), ("sales", "0004_sale_grooming_appointment")]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="contact",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="patients.contact", verbose_name="cliente o responsable"),
        ),
    ]
