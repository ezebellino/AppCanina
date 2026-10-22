from django.db import migrations, models
from django.db.models import Q


def mark_existing_operational_profiles_as_approved(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Organization.objects.filter(Q(is_verified=True) | Q(is_business_profile=True)).update(
        is_verified=True,
        verification_status="approved",
    )


class Migration(migrations.Migration):
    dependencies = [("organizations", "0005_organization_verification")]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente de validación"),
                    ("approved", "Aprobada"),
                    ("rejected", "Rechazada"),
                ],
                default="pending",
                max_length=16,
                verbose_name="estado de validación",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="verification_note",
            field=models.TextField(blank=True, verbose_name="nota de validación"),
        ),
        migrations.AddField(
            model_name="organization",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="revisado el"),
        ),
        migrations.AddField(
            model_name="organization",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="reviewed_organizations",
                to="auth.user",
                verbose_name="revisado por",
            ),
        ),
        migrations.RunPython(mark_existing_operational_profiles_as_approved, migrations.RunPython.noop),
    ]
