from datetime import timedelta
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from organizations.models import Organization
from .models import Patient, Contact, PatientContact
from .ownership import owner_relations


class MyAnimalCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('animal-owner')
        self.other = User.objects.create_user('other-owner')
        self.client.force_login(self.user)
        self.url = reverse('my_animal_create')

    def test_registers_own_animal_without_clinical_permissions(self):
        self.assertContains(self.client.get(reverse('my_animals')), self.url)
        response = self.client.post(self.url, {'name': 'Luna', 'species': 'cat'})
        self.assertRedirects(response, reverse('my_animals'))
        patient = Patient.objects.get()
        self.assertTrue(patient.active)
        self.assertIsNone(patient.organization_id)
        self.assertTrue(owner_relations(self.user).filter(patient=patient, role='responsible', is_primary=True).exists())
        self.assertFalse(owner_relations(self.other).exists())
        self.assertContains(self.client.get(reverse('my_animals')), 'Luna')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('my_animals')), 'Luna')
        self.assertEqual(self.client.get(reverse('my_animal_history', args=[patient.pk])).status_code, 404)

    def test_cannot_assign_other_contact_organization_or_existing_patient(self):
        contact = Contact.objects.create(full_name='Privado')
        org = Organization.objects.create(name='Otra institución', kind='shelter')
        existing = Patient.objects.create(name='Existente', species='dog', organization=org)
        self.client.post(self.url, {'name': 'Nuevo', 'species': 'dog', 'id': existing.pk,
            'organization': org.pk, 'contact': contact.pk, 'user': self.other.pk, 'active': '', 'notes': 'Injected'})
        patient = Patient.objects.get(name='Nuevo')
        self.assertIsNone(patient.organization_id)
        self.assertTrue(patient.active)
        self.assertEqual(patient.notes, '')
        self.assertFalse(PatientContact.objects.filter(patient=patient, contact=contact).exists())
        existing.refresh_from_db()
        self.assertEqual(existing.name, 'Existente')

    def test_validation_keeps_values_and_creates_nothing(self):
        for fields in ({'name': '', 'species': 'dog'}, {'name': 'Luna', 'species': 'invalid'},
                       {'name': 'Luna', 'species': 'cat', 'birth_date': (timezone.localdate()+timedelta(days=1)).isoformat()}):
            response = self.client.post(self.url, fields)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(Patient.objects.exists())
        self.assertFalse(Contact.objects.exists())
        response = self.client.post(self.url, {'name': 'Luna', 'species': 'cat',
            'photo': SimpleUploadedFile('fake.jpg', b'not an image', content_type='image/jpeg')})
        self.assertIn('photo', response.context['form'].errors)
        self.assertFalse(Patient.objects.exists())

    def test_requires_login_csrf_and_allowed_method(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.url, {'name': 'Luna', 'species': 'cat'}).status_code, 403)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertFalse(Patient.objects.exists())
