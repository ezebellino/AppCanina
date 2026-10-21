from django.db import migrations


def assign_legacy_patients_to_primary_business(apps, schema_editor):
    """Give pre-multitenant clinical files an explicit organization boundary.

    Early installations had one business profile and patients were created
    without an organization.  Moving those files to that profile is safer than
    keeping a permissive ``NULL`` fallback once staff access is scoped.
    Installations without a primary business profile intentionally retain the
    records for a superuser-led manual assignment instead of guessing a tenant.
    """
    Organization = apps.get_model("organizations", "Organization")
    Patient = apps.get_model("patients", "Patient")
    primary_business = Organization.objects.filter(is_business_profile=True).order_by("id").first()
    if primary_business:
        Patient.objects.filter(organization__isnull=True).update(organization=primary_business)


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0004_organization_locality"),
        ("patients", "0008_patient_family_access"),
    ]

    operations = [
        migrations.RunPython(assign_legacy_patients_to_primary_business, migrations.RunPython.noop),
    ]
