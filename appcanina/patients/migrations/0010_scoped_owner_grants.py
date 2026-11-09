from django.db import migrations, models


def preserve_existing_ownership(apps, schema_editor):
    Link = apps.get_model('patients', 'OwnerAccountLink')
    Relation = apps.get_model('patients', 'PatientContact')
    Grant = Link.patients.through
    alias = schema_editor.connection.alias
    # Snapshot existing ownership, including archived animals. New contact
    # relationships must never implicitly extend this authority afterward.
    for link in Link.objects.using(alias).iterator():
        patient_ids = Relation.objects.using(alias).filter(
            contact_id=link.contact_id, role__in=['responsible', 'adopter'],
        ).values_list('patient_id', flat=True).distinct()
        Grant.objects.using(alias).bulk_create([
            Grant(owneraccountlink_id=link.pk, patient_id=pk) for pk in patient_ids
        ], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [('patients', '0009_backfill_patient_organization')]
    operations = [
        migrations.AddField(
            model_name='owneraccountlink', name='patients',
            field=models.ManyToManyField(blank=True, related_name='owner_account_links', to='patients.patient'),
        ),
        migrations.RunPython(preserve_existing_ownership, migrations.RunPython.noop),
    ]
