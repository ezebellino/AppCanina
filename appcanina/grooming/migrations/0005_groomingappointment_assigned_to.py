# Generated manually for appointment assignment.

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("grooming", "0004_groomingservice_price"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.AddField(
            model_name="groomingappointment",
            name="assigned_to",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assigned_grooming_appointments", to=settings.AUTH_USER_MODEL, verbose_name="profesional asignado"),
        ),
    ]
