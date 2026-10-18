from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0007_travel_access_audit"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientFamilyInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("digest", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("accepted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accepted_patient_family_invites", to=settings.AUTH_USER_MODEL)),
                ("invited_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issued_patient_family_invites", to=settings.AUTH_USER_MODEL)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="family_invites", to="patients.patient")),
            ],
        ),
        migrations.CreateModel(
            name="PatientFamilyAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("contact", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="family_patient_accesses", to="patients.contact")),
                ("granted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="granted_family_patient_accesses", to=settings.AUTH_USER_MODEL)),
                ("invitation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accesses", to="patients.patientfamilyinvite")),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="family_accesses", to="patients.patient")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="family_patient_accesses", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="patientfamilyaccess",
            constraint=models.UniqueConstraint(fields=("patient", "user"), name="unique_patient_family_access"),
        ),
    ]
