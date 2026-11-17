from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from lost_pets.models import LostPetReport
from .models import Organization


class PlatformDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('dashboard-admin', is_staff=True)
        self.owner = User.objects.create_user('dashboard-owner')
        self.client.force_login(self.admin)
        self.url = reverse('platform_dashboard')

    def report(self, status, requested=True, name='Animal pendiente'):
        return LostPetReport.objects.create(
            reporter=self.owner, name=name, species='dog', last_seen_at=timezone.now(),
            area_label='Zona de prueba', status=status, requested_via_mobile=requested,
        )

    def test_counts_and_links_match_review_queues(self):
        org = Organization.objects.create(name='Institución pendiente', kind='shelter')
        pending = self.report('hidden')
        self.report('hidden', requested=False, name='Oculto por moderación')
        self.report('rejected')
        self.report('archived')
        self.report('published')
        self.report('resolved')
        response = self.client.get(self.url)
        self.assertEqual([m['value'] for m in response.context['metrics']], [1, 1, 1, 1])
        self.assertEqual(list(response.context['search_requests']), [pending])
        self.assertContains(response, reverse('lost_pet_detail', args=[pending.pk]))
        self.assertContains(response, reverse('organization_verification_list') + f'#institution-{org.pk}')
        for metric in response.context['metrics']:
            self.assertEqual(self.client.get(metric['href']).status_code, 200)
        self.assertNotContains(response, 'Oculto por moderación')

    def test_refresh_reads_changes_and_is_not_cached(self):
        report = self.report('hidden')
        org = Organization.objects.create(name='Revisada', kind='veterinary')
        first = self.client.get(self.url, {'summary': '1'})
        self.assertEqual([m['value'] for m in first.context['metrics']][:2], [1, 1])
        report.status = 'published'
        report.save()
        org.verification_status = 'approved'
        org.save()
        response = self.client.get(self.url, {'summary': '1'})
        self.assertEqual([m['value'] for m in response.context['metrics']], [0, 0, 1, 0])
        self.assertContains(response, 'data-platform-summary')
        self.assertNotContains(response, '<html')
        self.assertContains(response, 'No hay búsquedas esperando aprobación.')
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertIn('no-store', self.client.get(self.url).headers['Cache-Control'])

    def test_summary_and_page_are_staff_only(self):
        for user in (self.owner, None):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            for query in ({}, {'summary': '1'}):
                response = self.client.get(self.url, query)
                self.assertEqual(response.status_code, 403 if user else 302)
                self.assertNotContains(response, 'data-platform-summary', status_code=response.status_code)

    def test_preview_is_bounded_but_count_includes_all_requests(self):
        reports = [self.report('hidden', name=f'Animal {i}') for i in range(8)]
        response = self.client.get(self.url)
        self.assertEqual(response.context['metrics'][1]['value'], 8)
        self.assertEqual(list(response.context['search_requests']), reports[:6])

    def test_names_are_escaped_and_post_is_not_supported(self):
        self.report('hidden', name='<script>alert(1)</script>')
        response = self.client.get(self.url, {'summary': '1'})
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertEqual(self.client.post(self.url).status_code, 405)
