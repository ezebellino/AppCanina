from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from organizations.models import Organization, OrganizationMembership
from patients.models import Patient
from .models import LostPetReport, MobileAccessToken, Sighting


class SearchResolutionTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user("author")
        self.other = User.objects.create_user("other")
        permission = Permission.objects.get(codename="view_lostpetreport")
        self.author.user_permissions.add(permission)
        self.other.user_permissions.add(permission)
        self.report = LostPetReport.objects.create(reporter=self.author, name="Alelí", species="dog",
                                                 last_seen_at=timezone.now(), area_label="Centro")
        self.sighting = Sighting.objects.create(report=self.report, reporter=self.other, area_label="Plaza", seen_at=timezone.now())
        self.url = reverse("lost_pet_found", args=[self.report.pk])
        self.api = reverse("mobile_report_found", args=[self.report.pk])

    def test_author_confirmation_then_close_preserves_history(self):
        self.client.force_login(self.author)
        self.assertContains(self.client.get(reverse("lost_pet_detail", args=[self.report.pk])), "Se encontró · Finalizar búsqueda")
        self.assertContains(self.client.get(reverse("lost_pet_list")), self.url)
        self.assertContains(self.client.get(self.url), "¿Se encontró a Alelí?")
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "published")
        self.assertRedirects(self.client.post(self.url), reverse("lost_pet_list"))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "resolved")
        self.assertTrue(Sighting.objects.filter(pk=self.sighting.pk).exists())
        self.assertNotContains(self.client.get(reverse("lost_pet_list")), self.url)
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertEqual(self.client.post(reverse("sighting_create", args=[self.report.pk])).status_code, 403)

    def test_success_motion_only_on_first_resolution(self):
        self.client.force_login(self.author)
        first = self.client.post(self.url, follow=True)
        self.assertContains(first, 'data-success-motion="found"')
        repeat = self.client.post(self.url, follow=True)
        self.assertNotContains(repeat, 'data-success-motion="found"')

    def test_other_user_cannot_close_or_see_button(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("lost_pet_detail", args=[self.report.pk])), "Se encontró · Finalizar búsqueda")
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_manager_only_for_linked_verified_shelter(self):
        shelter = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        patient = Patient.objects.create(name="Alelí", species="dog", organization=shelter)
        self.report.patient = patient
        self.report.save()
        membership = OrganizationMembership.objects.create(user=self.other, organization=shelter, role="manager")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        shelter.is_verified = False
        shelter.save()
        self.assertEqual(self.client.post(self.url).status_code, 404)
        shelter.is_verified = True
        shelter.save()
        membership.delete()
        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_staff_can_close_but_hidden_reports_cannot_be_resolved(self):
        self.other.is_staff = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        for state in ("hidden", "rejected", "archived"):
            self.report.status = state
            self.report.save()
            self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_mobile_permissions_idempotency_and_active_feed(self):
        token, _ = MobileAccessToken.issue(self.author, "test")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        detail = reverse("mobile_report_detail", args=[self.report.pk])
        self.assertTrue(self.client.get(detail, **headers).json()["report"]["can_finish_search"])
        self.assertEqual(self.client.get(self.api, **headers).status_code, 405)
        self.assertEqual(self.client.post(self.api).status_code, 401)
        for _ in range(2):
            self.assertEqual(self.client.post(self.api, **headers).json()["status"], "resolved")
        self.assertFalse(self.client.get(detail, **headers).json()["report"]["can_finish_search"])
        self.assertEqual(self.client.get(reverse("mobile_reports"), **headers).json()["reports"], [])
        self.assertEqual(len(self.client.get(reverse("mobile_reports"), {"estado": "encontrados"}, **headers).json()["reports"]), 1)
        self.author.user_permissions.add(Permission.objects.get(codename="add_sighting"))
        self.assertEqual(self.client.post(reverse("mobile_sighting_create", args=[self.report.pk]),
                                         {"area": "Centro"}, **headers).status_code, 404)

    def test_mobile_outsider_cannot_close(self):
        token, _ = MobileAccessToken.issue(self.other, "test")
        self.assertEqual(self.client.post(self.api, HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 404)

    def test_web_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.author)
        self.assertEqual(client.post(self.url).status_code, 403)
