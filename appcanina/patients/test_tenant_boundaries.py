from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from io import StringIO
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from grooming.models import GroomingAppointment, GroomingService
from inventory.models import Brand, Product, Supplier
from lost_pets.models import MobileAccessToken
from organizations.models import Organization, OrganizationMembership
from organizations.roles import ensure_base_roles
from sales.models import Sale
from .models import Contact, OwnerAccountLink, Patient, PatientContact
from .ownership import grant_ownership, owner_relations


class TenantBoundaryTests(TestCase):
    def setUp(self):
        roles = ensure_base_roles()
        self.staff = User.objects.create_user('tenant-a')
        self.staff.groups.add(roles['admin'])
        self.outsider = User.objects.create_user('tenant-b')
        self.owner = User.objects.create_user('animal-owner')
        self.owner.groups.add(roles['collaborator'])
        self.a = Organization.objects.create(name='Clinic A', kind='veterinary')
        self.b = Organization.objects.create(name='Clinic B', kind='veterinary')
        OrganizationMembership.objects.create(organization=self.a, user=self.staff)
        OrganizationMembership.objects.create(organization=self.b, user=self.outsider)
        self.pa = Patient.objects.create(name='Local animal', species='dog', organization=self.a)
        self.pb = Patient.objects.create(name='FOREIGN ANIMAL', species='cat', organization=self.b)
        self.shared = Contact.objects.create(full_name='Shared guardian')
        self.foreign = Contact.objects.create(full_name='FOREIGN CONTACT')
        for patient in (self.pa, self.pb):
            PatientContact.objects.create(patient=patient, contact=self.shared, role='responsible', is_primary=True)
        PatientContact.objects.create(patient=self.pb, contact=self.foreign, role='adopter')
        self.service = GroomingService.objects.create(name='Bath', duration_minutes=30)
        self.local_turn = GroomingAppointment.objects.create(patient=self.pa, service=self.service, starts_at=timezone.now() + timedelta(hours=2))
        self.foreign_turn = GroomingAppointment.objects.create(patient=self.pb, service=self.service, starts_at=timezone.now() + timedelta(hours=4))
        self.client.force_login(self.staff)

    def test_account_link_grants_only_selected_animal_web_and_mobile(self):
        response = self.client.post(reverse('patient_owner_account_link', args=[self.pa.pk]), {'user': self.owner.pk})
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('my_animal_history', args=[self.pa.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('my_animal_history', args=[self.pb.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('my_animal_credential', args=[self.pb.pk])).status_code, 404)
        token, _ = MobileAccessToken.issue(self.owner, 'test')
        auth = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        listing = self.client.get(reverse('mobile_my_animals'), **auth)
        self.assertEqual([p['id'] for p in listing.json()['animals']], [self.pa.pk])
        self.assertEqual(self.client.get(reverse('mobile_my_animal_detail', args=[self.pb.pk]), **auth).status_code, 404)
        self.assertEqual(self.client.post(reverse('mobile_family_invite_create', args=[self.pb.pk]), **auth).status_code, 404)

    def test_contact_selector_and_forged_contact_reject_foreign(self):
        url = reverse('patient_contact_create', args=[self.pa.pk])
        self.assertNotContains(self.client.get(url), self.foreign.full_name)
        response = self.client.post(url, {'action': 'existing', 'existing-contact': self.foreign.pk, 'existing-role': 'responsible'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PatientContact.objects.filter(patient=self.pa, contact=self.foreign).exists())

    def test_contact_dedup_does_not_reuse_foreign_record(self):
        response = self.client.post(reverse('patient_contact_create', args=[self.pa.pk]), {
            'contact-full_name': self.foreign.full_name, 'contact-kind': 'person',
            'contact-phone': '', 'contact-email': '', 'relation-role': 'adopter',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PatientContact.objects.filter(patient=self.pa, contact=self.foreign).exists())

    def test_shared_contact_edit_does_not_modify_foreign_patient_contact(self):
        response = self.client.post(reverse('patient_edit', args=[self.pa.pk]), {
            'patient-name': self.pa.name, 'patient-species': 'dog', 'patient-active': 'on',
            'contact-full_name': 'Local correction', 'contact-kind': 'person',
            'contact-phone': '', 'contact-email': '',
        })
        self.assertEqual(response.status_code, 302)
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.full_name, 'Shared guardian')
        self.assertEqual(self.pa.patientcontact_set.get(is_primary=True).contact.full_name, 'Local correction')

    def test_agenda_and_mutation_are_scoped(self):
        response = self.client.get(reverse('grooming_agenda'))
        self.assertContains(response, self.pa.name)
        self.assertNotContains(response, self.pb.name)
        self.assertEqual(self.client.get(reverse('grooming_appointment_edit', args=[self.foreign_turn.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('grooming_appointment_status', args=[self.foreign_turn.pk, 'canceled'])).status_code, 404)
        self.foreign_turn.refresh_from_db()
        self.assertEqual(self.foreign_turn.status, 'booked')

    def test_grooming_form_rejects_foreign_patient_and_employee(self):
        url = reverse('grooming_appointment_create')
        response = self.client.get(url)
        self.assertNotContains(response, self.pb.name)
        self.assertNotContains(response, self.outsider.username)
        data = {'patient': self.pb.pk, 'service': self.service.pk, 'starts_at': (timezone.now() + timedelta(days=2)).isoformat(), 'status': 'booked'}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(GroomingAppointment.objects.count(), 2)
        data.update(patient=self.pa.pk, assigned_to=self.outsider.pk)
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(GroomingAppointment.objects.count(), 2)

    def test_overlap_is_checked_only_inside_same_institution(self):
        turn = GroomingAppointment.objects.create(patient=self.pb, service=self.service, starts_at=self.local_turn.starts_at)
        self.assertIsNotNone(turn.pk)
        with self.assertRaises(ValidationError):
            GroomingAppointment.objects.create(patient=self.pa, service=self.service, starts_at=self.local_turn.starts_at)

    def test_search_does_not_project_foreign_patients_or_products(self):
        brand = Brand.objects.create(name='Brand')
        supplier = Supplier.objects.create(name='Supplier')
        Product.objects.create(brand=brand, supplier=supplier, name='PRIVATE STOCK', organization=self.b, price=500)
        Product.objects.create(brand=brand, supplier=supplier, name='Local stock', organization=self.a, price=10)
        response = self.client.get(reverse('global_search'), {'q': 'Shared guardian'})
        self.assertContains(response, self.pa.name)
        self.assertNotContains(response, self.pb.name)
        response = self.client.get(reverse('global_search'), {'q': 'stock'})
        self.assertContains(response, 'Local stock')
        self.assertNotContains(response, 'PRIVATE STOCK')

    def test_sales_totals_and_history_are_scoped(self):
        Sale.objects.create(organization=self.a, patient=self.pa, contact=self.shared, total=10, seller=self.staff, payment_method='transfer')
        Sale.objects.create(organization=self.b, patient=self.pb, contact=self.shared, total=98765, seller=self.outsider, payment_method='transfer')
        response = self.client.get(reverse('patient_detail', args=[self.pa.pk]))
        self.assertEqual(response.context['patient_total'], 10)
        self.assertEqual(response.context['responsible_total'], 0)
        response = self.client.get(reverse('dashboard'))
        metric = next(m for m in response.context['metrics'] if m['label'] == 'ventas de hoy')
        self.assertEqual(metric['value'], '$10')

    def test_linked_checkout_keeps_scoped_dropdowns(self):
        for key, value in [('sale_appointment_id', self.local_turn.pk), ('sale_consultation_patient_id', self.pa.pk)]:
            session = self.client.session
            session.pop('sale_appointment_id', None)
            session.pop('sale_consultation_patient_id', None)
            session[key] = value
            session.save()
            response = self.client.get(reverse('sale_create'))
            self.assertContains(response, self.pa.name)
            self.assertNotContains(response, self.foreign.full_name)
            self.assertNotContains(response, self.pb.name)

    def test_new_relationship_does_not_expand_existing_ownership(self):
        grant_ownership(self.owner, self.shared, self.pa)
        third = Patient.objects.create(name='Later animal', species='dog', organization=self.b)
        PatientContact.objects.create(patient=third, contact=self.shared, role='responsible')
        self.assertEqual(set(owner_relations(self.owner).values_list('patient_id', flat=True)), {self.pa.pk})

    def test_grants_cannot_be_combined_across_users_or_contacts(self):
        grant_ownership(self.owner, self.shared, self.pa)
        grant_ownership(self.outsider, self.shared, self.pb)
        other_contact = Contact.objects.create(full_name='Different identity')
        grant_ownership(self.owner, other_contact, self.pb)
        PatientContact.objects.create(patient=self.pb, contact=other_contact, role='custodian')
        self.assertEqual(set(owner_relations(self.owner).values_list('patient_id', flat=True)), {self.pa.pk})

    def test_shared_contact_edit_preserves_explicit_owners(self):
        grant_ownership(self.owner, self.shared, self.pa)
        grant_ownership(self.owner, self.shared, self.pb)
        self.test_shared_contact_edit_does_not_modify_foreign_patient_contact()
        self.assertEqual(set(owner_relations(self.owner).values_list('patient_id', flat=True)), {self.pa.pk, self.pb.pk})

    def test_shared_contact_edit_preserves_multiple_roles(self):
        grant_ownership(self.owner, self.shared, self.pa)
        self.pa.patientcontact_set.update(is_primary=False)
        PatientContact.objects.create(patient=self.pa, contact=self.shared, role='custodian', is_primary=True)
        self.test_shared_contact_edit_does_not_modify_foreign_patient_contact()
        self.assertTrue(owner_relations(self.owner).filter(patient=self.pa).exists())
        contacts = self.pa.patientcontact_set.values_list('contact_id', flat=True).distinct()
        self.assertEqual(len(contacts), 1)

    def test_mobile_create_with_existing_contact_does_not_grant_other_animals(self):
        grant_ownership(self.owner, self.shared, self.pa)
        token, _ = MobileAccessToken.issue(self.owner, 'test')
        auth = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        response = self.client.post(reverse('mobile_my_animals'), {'name': 'New pet', 'species': 'dog'}, **auth)
        self.assertEqual(response.status_code, 201)
        new_id = response.json()['animal']['id']
        listing = self.client.get(reverse('mobile_my_animals'), **auth)
        self.assertEqual({p['id'] for p in listing.json()['animals']}, {self.pa.pk, new_id})

    def test_local_appointment_create_edit_and_status_still_work(self):
        data = {'patient': self.pa.pk, 'service': self.service.pk,
                'starts_at': (timezone.now() + timedelta(days=3)).isoformat(), 'status': 'booked',
                'assigned_to': self.staff.pk}
        response = self.client.post(reverse('grooming_appointment_create'), data)
        self.assertEqual(response.status_code, 302)
        turn = GroomingAppointment.objects.latest('pk')
        data['notes'] = 'Local update'
        response = self.client.post(reverse('grooming_appointment_edit', args=[turn.pk]), data)
        self.assertEqual(response.status_code, 302)
        turn.refresh_from_db()
        self.assertEqual(turn.notes, 'Local update')
        self.assertEqual(self.client.post(reverse('grooming_appointment_status', args=[turn.pk, 'confirmed'])).status_code, 302)
        turn.refresh_from_db()
        self.assertEqual(turn.status, 'confirmed')

    def test_patient_create_does_not_reuse_foreign_contact(self):
        response = self.client.post(reverse('patient_create'), {
            'patient-name': 'New clinic animal', 'patient-species': 'dog', 'patient-active': 'on',
            'contact-full_name': self.foreign.full_name, 'contact-kind': 'person',
            'contact-phone': '', 'contact-email': '',
        })
        self.assertEqual(response.status_code, 302)
        patient = Patient.objects.get(name='New clinic animal')
        self.assertEqual(patient.organization, self.a)
        self.assertNotEqual(patient.patientcontact_set.get().contact_id, self.foreign.pk)

    def test_duplicate_contact_maintenance_preserves_grants_and_tenant_boundary(self):
        duplicate = Contact.objects.create(full_name=self.foreign.full_name)
        PatientContact.objects.create(patient=self.pa, contact=duplicate, role='responsible')
        grant_ownership(self.owner, duplicate, self.pa)
        call_command('merge_duplicate_contacts', stdout=StringIO())
        self.assertTrue(Contact.objects.filter(pk=duplicate.pk).exists())
        self.assertEqual(set(owner_relations(self.owner).values_list('patient_id', flat=True)), {self.pa.pk})
