from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class OwnerGrantMigrationTests(TransactionTestCase):
    def test_existing_ownership_is_preserved_without_custodian_escalation(self):
        old = [('patients', '0009_backfill_patient_organization')]
        latest = [('patients', '0010_scoped_owner_grants')]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            User = apps.get_model('auth', 'User')
            Contact = apps.get_model('patients', 'Contact')
            Patient = apps.get_model('patients', 'Patient')
            Relation = apps.get_model('patients', 'PatientContact')
            Link = apps.get_model('patients', 'OwnerAccountLink')
            owner = User.objects.create(username='historic-owner')
            contact = Contact.objects.create(full_name='Historic identity')
            link = Link.objects.create(user=owner, contact=contact)
            expected = set()
            for role in ['responsible', 'adopter', 'custodian']:
                patient = Patient.objects.create(name=role, species='dog', active=False)
                Relation.objects.create(patient=patient, contact=contact, role=role)
                if role != 'custodian':
                    expected.add(patient.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            migrated = apps.get_model('patients', 'OwnerAccountLink').objects.get(pk=link.pk)
            self.assertEqual(set(migrated.patients.values_list('pk', flat=True)), expected)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
