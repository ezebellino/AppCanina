from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, PushDelivery, Sighting
from .push import process_push_batch
from .resolution import finish_search


class ResolutionNotificationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('found-owner')
        self.helper = User.objects.create_user('found-helper')
        self.outsider = User.objects.create_user('found-outsider')
        self.admin = User.objects.create_user('found-admin', is_staff=True)
        permission = Permission.objects.get(codename='view_lostpetreport')
        for user in (self.owner, self.helper, self.outsider):
            user.user_permissions.add(permission)
        self.report = LostPetReport.objects.create(
            reporter=self.owner, name='Alelí', species='dog', last_seen_at=timezone.now(),
            area_label='Centro', status='published',
        )
        for _ in range(3):
            Sighting.objects.create(report=self.report, reporter=self.helper, area_label='Plaza')
        self.token, session = MobileAccessToken.issue(self.helper, 'test')
        MobilePushDevice.objects.create(user=self.helper, access_token=session,
            platform='android', token='ExpoPushToken[resolution-test]')

    def test_one_notification_per_person_and_durable_push_without_network(self):
        inactive = User.objects.create_user('inactive-helper', is_active=False)
        Sighting.objects.create(report=self.report, reporter=inactive)
        with patch('lost_pets.push.urlopen') as network:
            self.assertEqual(finish_search(self.owner, self.report.pk), 1)
            self.assertEqual(finish_search(self.admin, self.report.pk), 0)
        network.assert_not_called()
        notes = CommunityNotification.objects.filter(kind='search_found')
        self.assertEqual(set(notes.values_list('recipient_id', flat=True)), {self.helper.pk, self.owner.pk})
        self.assertEqual(notes.count(), 2)
        self.assertEqual(PushDelivery.objects.count(), 1)
        with patch('lost_pets.push._post', return_value={'data': [{'status': 'ok', 'id': 'test-ticket'}]}) as send:
            self.assertEqual(process_push_batch(), 1)
        payload = send.call_args.args[1][0]
        self.assertEqual(payload['title'], '¡Alelí fue encontrado!')
        self.assertEqual(payload['data']['report_id'], self.report.pk)

    def test_both_web_closure_routes_and_mobile_enqueue(self):
        routes = [reverse('lost_pet_found', args=[self.report.pk]),
                  reverse('lost_pet_change_status', args=[self.report.pk]),
                  reverse('mobile_report_found', args=[self.report.pk])]
        owner_token, _ = MobileAccessToken.issue(self.owner, 'test')
        self.client.force_login(self.admin)
        for route in routes:
            with self.subTest(route=route):
                LostPetReport.objects.filter(pk=self.report.pk).update(status='published')
                CommunityNotification.objects.all().delete()
                for _ in range(2):
                    response = self.client.post(route, {'status': 'resolved'}, HTTP_AUTHORIZATION=f'Bearer {owner_token}')
                    self.assertIn(response.status_code, (200, 302))
                self.assertEqual(CommunityNotification.objects.filter(kind='search_found').count(), 2)
                self.assertEqual(PushDelivery.objects.count(), 1)

    def test_outsiders_and_non_active_reports_do_not_notify(self):
        self.assertEqual(finish_search(self.outsider, self.report.pk), 0)
        for status in ('hidden', 'rejected', 'archived', 'resolved'):
            LostPetReport.objects.filter(pk=self.report.pk).update(status=status)
            self.assertEqual(finish_search(self.admin, self.report.pk), 0)
        self.assertFalse(CommunityNotification.objects.exists())

    def test_failure_rolls_back_closure_and_inbox(self):
        with patch('lost_pets.notifications.send_expo_push', side_effect=RuntimeError('queue unavailable')):
            with self.assertRaises(RuntimeError):
                finish_search(self.owner, self.report.pk)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'published')
        self.assertFalse(CommunityNotification.objects.exists())
        self.assertFalse(PushDelivery.objects.exists())

    def test_web_inbox_badge_read_and_recipient_isolation(self):
        finish_search(self.owner, self.report.pk)
        note = CommunityNotification.objects.get(recipient=self.helper)
        self.client.force_login(self.helper)
        self.assertContains(self.client.get(reverse('my_search_requests')), '¡Alelí fue encontrado!')
        counts = self.client.get(reverse('adoption_update_counts')).json()
        self.assertEqual(counts['search_unread_count'], 1)
        self.client.post(reverse('search_update_read', args=[note.pk]))
        self.assertEqual(self.client.get(reverse('adoption_update_counts')).json()['search_unread_count'], 0)
        self.client.force_login(self.outsider)
        self.assertNotContains(self.client.get(reverse('my_search_requests')), 'Alelí')
        self.assertEqual(self.client.post(reverse('search_update_read', args=[note.pk])).status_code, 404)

    def test_mobile_feed_and_detail_work_with_existing_apk(self):
        finish_search(self.owner, self.report.pk)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}
        feed = self.client.get(reverse('mobile_updates'), **headers).json()
        self.assertEqual(feed['unread_count'], 1)
        note = feed['notifications'][0]
        self.assertEqual(note['title'], '¡Alelí fue encontrado!')
        detail = self.client.get(reverse('mobile_update_detail', args=[note['key']]), **headers).json()
        self.assertEqual(detail['target'], 'report')
        report = self.client.get(reverse('mobile_report_detail', args=[detail['report_id']]), **headers).json()
        self.assertEqual(report['report']['status'], 'resolved')
