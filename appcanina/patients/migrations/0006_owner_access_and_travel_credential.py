from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("patients", "0005_carereminder"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="OwnerAccountLink", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("verified_at", models.DateTimeField(auto_now_add=True)), ("contact", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="account_links", to="patients.contact")), ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="owner_contact_links", to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="PatientSharingConsent", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("enabled", models.BooleanField(default=False, verbose_name="autoriza compartir historial clínico")), ("updated_at", models.DateTimeField(auto_now=True)), ("contact", models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="sharing_consents", to="patients.contact")), ("patient", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="sharing_consents", to="patients.patient"))]),
        migrations.CreateModel(name="TravelCredential", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("digest", models.CharField(max_length=64, unique=True)), ("expires_at", models.DateTimeField()), ("revoked_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("contact", models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="travel_credentials", to="patients.contact")), ("patient", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="travel_credentials", to="patients.patient"))]),
        migrations.AddConstraint(model_name="owneraccountlink", constraint=models.UniqueConstraint(fields=("contact", "user"), name="unique_owner_account_link")),
        migrations.AddConstraint(model_name="patientsharingconsent", constraint=models.UniqueConstraint(fields=("patient", "contact"), name="unique_patient_sharing_consent")),
    ]
