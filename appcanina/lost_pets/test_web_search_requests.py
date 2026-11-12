from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from organizations.models import Organization, OrganizationMembership
from organizations.roles import ensure_base_roles
from patients.models import Patient, Contact, PatientContact
from patients.ownership import grant_ownership
from .models import LostPetReport


class WebSearchRequestTests(TestCase):
    def setUp(self):
        cache.clear()
        self.roles = ensure_base_roles()
        self.user = User.objects.create_user("community")
        self.user.groups.add(self.roles["collaborator"])
        self.other = User.objects.create_user("other")
        self.other.groups.add(self.roles["collaborator"])
        self.client.force_login(self.user)
        self.url = reverse("lost_pet_create")
        self.payload = {"name": "Luna", "species": "dog", "last_seen_at": timezone.now().isoformat(), "area_label": "Centro"}

    def test_profile_links_grouped_before_form_and_useless_search_hidden(self):
        response = self.client.get(reverse("personal_profile"))
        html = response.content.decode()
        self.assertContains(response, "Publicar animal extraviado")
        self.assertContains(response, reverse("my_search_requests"))
        self.assertNotContains(response, 'href="' + reverse("global_search") + '"')
        self.assertLess(html.index("Mis accesos"), html.index("Mis datos personales"))
        self.assertContains(self.client.get(reverse("lost_pet_list")), self.url)

    def test_community_submits_pending_and_cannot_inject_status_or_reporter(self):
        response = self.client.post(self.url, {**self.payload, "status": "published", "reporter": self.other.pk})
        self.assertRedirects(response, reverse("my_search_requests"))
        report = LostPetReport.objects.get()
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.status, "hidden")
        self.assertTrue(report.requested_via_mobile)
        self.assertNotContains(self.client.get(reverse("lost_pet_list")), "Luna")
        self.assertContains(self.client.get(reverse("my_search_requests")), "En revisión")

    def test_list_and_edit_are_private_and_rejected_returns_to_review(self):
        self.client.post(self.url, self.payload)
        report = LostPetReport.objects.get()
        report.status = "rejected"
        report.review_note = "Corregir zona"
        report.save()
        edit = reverse("search_request_edit", args=[report.pk])
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("my_search_requests")), "Luna")
        self.assertEqual(self.client.get(edit).status_code, 404)
        self.assertEqual(self.client.post(edit, self.payload).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(edit, {**self.payload, "area_label": "Plaza"}).status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, "hidden")
        self.assertEqual(report.review_note, "")
        report.status = "published"
        report.save()
        self.assertEqual(self.client.post(edit, self.payload).status_code, 404)

    def test_patient_link_is_scoped_to_explicit_ownership(self):
        patient = Patient.objects.create(name="Propio", species="dog")
        contact = Contact.objects.create(full_name="Responsible")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible")
        grant_ownership(self.user, contact, patient)
        foreign = Patient.objects.create(name="Ajeno", species="dog")
        self.assertEqual(self.client.get(self.url, {"patient": foreign.pk}).status_code, 404)
        self.assertEqual(self.client.post(self.url, {**self.payload, "patient": foreign.pk}).status_code, 200)
        self.assertEqual(LostPetReport.objects.count(), 0)
        self.assertEqual(self.client.post(self.url, {**self.payload, "patient": patient.pk}).status_code, 302)
        self.assertEqual(LostPetReport.objects.get().patient, patient)

    def test_rate_limit_and_csrf(self):
        cache.set("mobile-search-request:127.0.0.1", 3, 3600)
        self.assertContains(self.client.post(self.url, self.payload), "Ya enviaste varias búsquedas")
        self.assertFalse(LostPetReport.objects.exists())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, self.payload).status_code, 403)

    def test_refuge_menu_hides_search_and_veterinary_keeps_it(self):
        self.user.groups.add(self.roles["admin"])
        self.assertContains(self.client.get(reverse("personal_profile")), 'href="' + reverse("global_search") + '"')
        shelter = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        OrganizationMembership.objects.create(user=self.user, organization=shelter, role="manager")
        self.assertNotContains(self.client.get(reverse("personal_profile")), 'href="' + reverse("global_search") + '"')
