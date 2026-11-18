from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from organizations.models import Organization, OrganizationMembership
from organizations.roles import ensure_base_roles
from .models import AdoptionPost, MobileAccessToken
from .adoption_discovery import discover, AdoptionLocationForm


class AdoptionDiscoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('adopter')
        self.user.groups.add(ensure_base_roles()['collaborator'])
        self.owner = User.objects.create_user('shelter-manager')
        self.shelter = Organization.objects.create(name='Refugio Norte', kind='shelter', locality='La Plata', is_verified=True)
        OrganizationMembership.objects.create(user=self.owner, organization=self.shelter)
        self.other = Organization.objects.create(name='Refugio Norte', kind='shelter', locality='Córdoba', is_verified=True)
        self.near = self.post('Cerca', location_latitude='0.00', location_longitude='0.01')
        self.far = self.post('Lejos', location_latitude='0.00', location_longitude='1.00', organization=self.other)
        self.unknown = self.post('Sin ubicación')
        self.post('Privado', status='pending')
        self.client.force_login(self.user)

    def post(self, name, **kwargs):
        return AdoptionPost.objects.create(**{'publisher': self.owner, 'organization': self.shelter,
            'name': name, 'species': 'dog', 'status': 'published', 'area_label': 'Centro', 'locality': 'Avellaneda', **kwargs})

    def test_combined_filters_and_radius_sort_before_pagination(self):
        query = AdoptionPost.objects.filter(status='published')
        form, page, missing = discover(query, {'lat': '0', 'lon': '0', 'radius': '10', 'locality': 'Avellaneda', 'species': 'dog', 'shelter': str(self.shelter.pk)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual([p.pk for p in page], [self.near.pk])
        self.assertEqual(missing, 1)
        form, page, _ = discover(query, {'lat': '0', 'lon': '0'}, 1)
        self.assertEqual(page[0].pk, self.near.pk)
        self.assertTrue(page.has_next())
        self.assertEqual(page.paginator.count, 3)

    def test_invalid_filters_fail_explicitly_instead_of_widening(self):
        for params in ({'radius': '25'}, {'lat': '91', 'lon': '0'}, {'lat': 'NaN', 'lon': '0'},
                       {'lat': '0'}, {'radius': '999', 'lat': '0', 'lon': '0'}, {'species': 'invalid'}, {'shelter': '999999'}):
            with self.subTest(params=params):
                form, page, _ = discover(AdoptionPost.objects.all(), params)
                self.assertFalse(form.is_valid())
                self.assertEqual(page.paginator.count, 0)

    def test_web_pool_locality_without_gps_and_private_statuses(self):
        response = self.client.get(reverse('adoption_list'), {'locality': 'Avellaneda'})
        self.assertEqual(response.context['page_obj'].paginator.count, 3)
        self.assertNotContains(response, 'Privado')
        self.assertContains(response, 'Refugio Norte · Córdoba')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.get(reverse('adoption_list'), {'locality': 'No existe'}).context['page_obj'].paginator.count, 0)

    def test_mobile_api_same_filters_and_no_reference_coordinates(self):
        token, _ = MobileAccessToken.issue(self.user, 'test')
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        response = self.client.get(reverse('mobile_adoptions'), {'lat': '0', 'lon': '0', 'radius': '10'}, **headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([p['id'] for p in data['adoptions']], [self.near.pk])
        self.assertEqual(data['adoptions'][0]['distance_km'], 1)
        self.assertEqual(data['missing_locations'], 1)
        self.assertNotIn('latitude', response.content.decode())
        self.assertNotIn('longitude', response.content.decode())
        self.assertEqual(self.client.get(reverse('mobile_adoptions'), {'radius': '10'}, **headers).status_code, 400)

    def test_location_management_is_scoped_and_accepts_only_coarse_pairs(self):
        url = reverse('adoption_location', args=[self.near.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.post(url, {'locality': 'Hogar de tránsito', 'location_latitude': '-34.60', 'location_longitude': '-58.40'})
        self.assertEqual(response.status_code, 302)
        self.near.refresh_from_db()
        self.assertEqual(self.near.locality, 'Hogar de tránsito')
        self.assertEqual(self.client.get(reverse('adoption_location', args=[self.far.pk])).status_code, 404)
        for coords in ({'location_latitude': '1'}, {'location_latitude': '1.12345', 'location_longitude': '2'}, {'location_latitude': '91', 'location_longitude': '1'}):
            self.assertFalse(AdoptionLocationForm(coords, instance=self.near).is_valid())

    def test_existing_apk_payload_and_pagination(self):
        for i in range(61):
            self.post(f'Animal {i}')
        token, _ = MobileAccessToken.issue(self.user, 'test')
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        response = self.client.get(reverse('mobile_adoptions'), **headers).json()
        next_page = self.client.get(reverse('mobile_adoptions'), {'page': '2'}, **headers).json()
        self.assertEqual(len(response['adoptions']), 60)
        self.assertTrue(response['has_next'])
        self.assertEqual(len(next_page['adoptions']), 4)
        self.assertFalse(set(p['id'] for p in response['adoptions']) & set(p['id'] for p in next_page['adoptions']))
