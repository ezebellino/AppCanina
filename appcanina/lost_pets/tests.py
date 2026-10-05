from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from patients.models import Patient

from .models import LostPetReport, Sighting


class LostPetReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("community-user", password="secret")
        permissions = Permission.objects.filter(codename__in=["view_lostpetreport", "add_lostpetreport", "add_sighting", "change_lostpetreport"])
        self.user.user_permissions.add(*permissions)
        self.patient = Patient.objects.create(name="Toto", species="dog", breed="Mestizo")
        self.client.force_login(self.user)

    def test_report_is_published_immediately_and_can_link_a_patient(self):
        response = self.client.post(reverse("lost_pet_create"), {"patient": self.patient.id, "name": "Toto", "species": "dog", "breed": "Mestizo", "description": "Collar azul", "last_seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "area_label": "Barrio Norte", "latitude": "", "longitude": ""})
        report = LostPetReport.objects.get()
        self.assertRedirects(response, reverse("lost_pet_detail", args=[report.id]))
        self.assertEqual(report.status, LostPetReport.Status.PUBLISHED)
        self.assertEqual(report.patient, self.patient)
        self.assertEqual(report.reporter, self.user)

    def test_sighting_is_published_immediately(self):
        report = LostPetReport.objects.create(reporter=self.user, name="Luna", species="cat", last_seen_at=timezone.now(), area_label="Centro")
        response = self.client.post(reverse("sighting_create", args=[report.id]), {"seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "area_label": "Plaza principal", "description": "Cerca de la fuente", "latitude": "", "longitude": ""})
        sighting = Sighting.objects.get()
        self.assertRedirects(response, reverse("lost_pet_detail", args=[report.id]))
        self.assertEqual(sighting.status, Sighting.Status.PUBLISHED)
        self.assertEqual(sighting.reporter, self.user)

    def test_map_api_returns_only_approximate_coordinates(self):
        LostPetReport.objects.create(reporter=self.user, name="Nube", species="cat", last_seen_at=timezone.now(), area_label="Centro", latitude=Decimal("-34.603700"), longitude=Decimal("-58.381600"))

        response = self.client.get(reverse("lost_pet_map_data"))

        self.assertEqual(response.status_code, 200)
        marker = response.json()["markers"][0]
        self.assertNotIn("latitude", marker)
        self.assertNotIn("longitude", marker)
        self.assertNotEqual(marker["public_latitude"], -34.6037)
        self.assertNotEqual(marker["public_longitude"], -58.3816)
