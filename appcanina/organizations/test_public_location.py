from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from patients.veterinary_views import AuthorizationForm
from .forms import BusinessProfileForm
from .models import Organization, OrganizationMembership


class PublicLocationTests(TestCase):
    def data(self, **overrides):
        return {'name': 'Veterinaria Sol', 'kind': 'veterinary', 'address': 'Mitre 20',
                'locality': 'Avellaneda', 'latitude': '-34.660000', 'longitude': '-58.360000', **overrides}

    def test_coordinates_and_locality_can_be_saved(self):
        form = BusinessProfileForm(data=self.data())
        self.assertTrue(form.is_valid(), form.errors)
        org = form.save()
        self.assertEqual(org.latitude, Decimal('-34.660000'))
        self.assertEqual(org.locality, 'Avellaneda')

    def test_coordinates_must_be_complete_and_valid_but_optional(self):
        for lat, lon in [('91','0'), ('0','181'), ('NaN','0'), ('','1')]:
            form = BusinessProfileForm(data=self.data(latitude=lat, longitude=lon))
            self.assertFalse(form.is_valid())
        self.assertTrue(BusinessProfileForm(data=self.data(latitude='', longitude='')).is_valid())
        self.assertTrue(BusinessProfileForm(data=self.data(latitude='0', longitude='0')).is_valid())

    def test_changed_address_requires_location_confirmation(self):
        org = Organization.objects.create(**self.data())
        form = BusinessProfileForm(data=self.data(address='Other street'), instance=org)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save().latitude)
        org.refresh_from_db()
        form = BusinessProfileForm(data=self.data(location_confirmed='true'), instance=org)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNotNone(form.save().latitude)

    def test_only_verified_vets_have_coordinates_in_selector(self):
        local = Organization.objects.create(**self.data(), is_verified=True)
        Organization.objects.create(name='Hidden clinic', kind='veterinary', latitude=10, longitude=10)
        Organization.objects.create(name='Hidden shelter', kind='shelter', is_verified=True, latitude=10, longitude=10)
        html = str(AuthorizationForm()['organization'])
        self.assertIn('data-latitude="-34.660000"', html)
        self.assertIn('Avellaneda', html)
        self.assertIn('Mitre 20', html)
        self.assertNotIn('Hidden', html)
        self.assertEqual(list(AuthorizationForm().fields['organization'].queryset), [local])

    def test_manager_updates_own_profile_not_other_institution(self):
        user = User.objects.create_user('manager')
        org = Organization.objects.create(name='Own', kind='veterinary')
        other = Organization.objects.create(name='Other', kind='veterinary')
        OrganizationMembership.objects.create(user=user, organization=org, role='manager')
        self.client.force_login(user)
        response = self.client.post(reverse('business_profile'), {**self.data(), 'id':other.pk, 'location_confirmed':'true'})
        self.assertEqual(response.status_code,302)
        org.refresh_from_db(); other.refresh_from_db()
        self.assertIsNotNone(org.latitude)
        self.assertIsNone(other.latitude)
