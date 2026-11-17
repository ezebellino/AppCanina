from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Organization, OrganizationMembership
from .roles import ensure_base_roles


class VeterinaryNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('vet-navigation')
        self.roles = ensure_base_roles()
        self.user.groups.add(self.roles['admin'])
        self.organization = Organization.objects.create(name='Horizonte prueba', kind='veterinary', is_verified=True)
        self.membership = OrganizationMembership.objects.create(user=self.user, organization=self.organization)
        self.client.force_login(self.user)

    def test_veterinary_pages_show_work_navigation_and_profile(self):
        for route in ('dashboard', 'business_profile', 'lost_pet_list', 'personal_profile'):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, 'Perfil de la veterinaria')
                self.assertContains(response, 'Atención clínica')
                self.assertNotContains(response, 'href="' + reverse('my_animals') + '"')
                for adoption in ('adoption_list', 'my_adoption_interests', 'adoption_interest_list'):
                    self.assertNotContains(response, 'href="' + reverse(adoption))

    def test_groups_respect_permissions_and_profile_is_reachable(self):
        self.user.groups.clear()
        response = self.client.get(reverse('business_profile'))
        self.assertEqual(response.context['veterinary_nav_groups'], [])
        self.assertContains(response, 'Guardar perfil')
        self.assertContains(response, 'Perfil de la veterinaria')

    def test_active_group_opens_and_generated_links_work(self):
        response = self.client.get(reverse('patient_list'))
        groups = response.context['veterinary_nav_groups']
        self.assertTrue(next(group for group in groups if group['label'] == 'Atención clínica')['open'])
        for group in groups:
            for link in group['links']:
                with self.subTest(url=link['url']):
                    self.assertEqual(self.client.get(link['url']).status_code, 200)

    def test_personal_and_shelter_navigation_are_preserved(self):
        self.membership.delete()
        response = self.client.get(reverse('personal_profile'))
        self.assertContains(response, 'href="' + reverse('my_animals') + '"')
        self.assertContains(response, 'href="' + reverse('my_adoption_interests') + '"')
        self.organization.kind = 'shelter'
        self.organization.save()
        OrganizationMembership.objects.create(user=self.user, organization=self.organization)
        response = self.client.get(reverse('business_profile'))
        self.assertContains(response, 'Animales del refugio')
        self.assertContains(response, 'Solicitudes recibidas')
        self.assertNotContains(response, 'href="' + reverse('my_animals') + '"')
