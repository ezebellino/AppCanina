from datetime import timedelta
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import LostPetReport, MobileAccessToken, Sighting


class MobileSearchMapTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('map-reader')
        self.user.user_permissions.add(Permission.objects.get(codename='view_lostpetreport'))
        self.raw, _ = MobileAccessToken.issue(self.user, 'map-test')
        self.now = timezone.now()
        self.report = LostPetReport.objects.create(
            reporter=self.user, name='Luna', species='dog', area_label='Initial area',
            last_seen_at=self.now - timedelta(days=3), latitude='-34.600000', longitude='-58.400000')
        self.url = reverse('mobile_report_detail', args=[self.report.pk])

    def get(self):
        return self.client.get(self.url, HTTP_AUTHORIZATION=f'Bearer {self.raw}')

    def sighting(self, **values):
        defaults = dict(report=self.report, reporter=self.user, seen_at=self.now,
                        area_label='Public area', latitude='-34.610000', longitude='-58.410000')
        defaults.update(values)
        return Sighting.objects.create(**defaults)

    def test_only_approximate_coordinates_and_published_sightings(self):
        visible = self.sighting()
        self.sighting(status='hidden', area_label='PRIVATE', seen_at=self.now + timedelta(hours=1))
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        data = response.json()['report']['search_map']
        self.assertEqual(len(data['points']), 2)
        self.assertEqual(data['points'][0]['public_latitude'], visible.public_coordinates[0])
        self.assertNotEqual(data['points'][0]['public_latitude'], float(visible.latitude))
        self.assertNotContains(response, 'PRIVATE')
        self.assertNotIn('latitude', data['points'][0])
        self.assertNotIn('longitude', data['points'][0])
        self.user.is_staff = True
        self.user.save()
        self.assertNotContains(self.get(), 'PRIVATE')

    def test_latest_without_coordinates_is_not_replaced_by_an_older_point(self):
        self.sighting(area_label='Latest without GPS', latitude=None, longitude=None)
        data = self.get().json()['report']['search_map']
        self.assertEqual(data['latest_observation']['area'], 'Latest without GPS')
        self.assertIsNone(data['latest_observation']['public_latitude'])
        self.assertEqual(data['points'][0]['source'], 'report')

    def test_initial_location_and_missing_location(self):
        data = self.get().json()['report']['search_map']
        self.assertEqual(len(data['points']), 1)
        self.report.latitude = self.report.longitude = None
        self.report.save()
        self.assertEqual(self.get().json()['report']['search_map']['points'], [])

    def test_visibility_and_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        for state in ['hidden', 'rejected', 'archived']:
            self.report.status = state
            self.report.save()
            self.assertEqual(self.get().status_code, 404)
        self.report.status = 'resolved'
        self.report.save()
        self.assertEqual(self.get().status_code, 200)

    def test_bounded_history_and_seen_time_order(self):
        for index in range(24):
            self.sighting(seen_at=self.now - timedelta(hours=index), area_label=f'Point {index}')
        data = self.get().json()['report']['search_map']
        self.assertEqual(len(data['points']), 20)
        self.assertEqual(data['points'][0]['area'], 'Point 0')
        self.assertEqual(data['points'][-1]['area'], 'Point 19')
