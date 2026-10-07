from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from patients.models import Patient

from .models import CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, Sighting
from organizations.roles import ensure_base_roles


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

    def test_community_collaborator_can_only_assist_on_published_reports(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("luz-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        published = LostPetReport.objects.create(reporter=self.user, name="Nube", species="cat", last_seen_at=timezone.now(), area_label="Centro")
        hidden = LostPetReport.objects.create(reporter=self.user, name="Tango", species="dog", last_seen_at=timezone.now(), area_label="Barrio Sur", status=LostPetReport.Status.HIDDEN)

        self.client.force_login(collaborator)

        response = self.client.get(reverse("lost_pet_list", query={"view": "all"}))
        self.assertContains(response, "Nube")
        self.assertNotContains(response, "Tango")
        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[hidden.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("lost_pet_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("patient_list")).status_code, 403)

        response = self.client.post(
            reverse("sighting_create", args=[published.id]),
            {"seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "area_label": "Plaza", "description": "Lo vi cerca de la fuente", "latitude": "", "longitude": ""},
        )
        self.assertRedirects(response, reverse("lost_pet_detail", args=[published.id]))
        self.assertEqual(Sighting.objects.latest("id").reporter, collaborator)

    def test_community_user_receives_report_notification_with_animal_details(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("luz-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        self.client.force_login(self.user)

        self.client.post(
            reverse("lost_pet_create"),
            {
                "patient": "",
                "name": "Mora",
                "species": "dog",
                "breed": "Mestiza",
                "description": "Tiene collar violeta y una mancha blanca en el pecho.",
                "last_seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "area_label": "Barrio Norte",
                "latitude": "",
                "longitude": "",
            },
        )
        notification = CommunityNotification.objects.get(recipient=collaborator)
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")

        response = self.client.get(
            reverse("mobile_notifications"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(notification.title, "Alerta: Mora está extraviado")
        self.assertEqual(response.status_code, 200)
        item = response.json()["notifications"][0]
        self.assertEqual(item["animal_name"], "Mora")
        self.assertEqual(item["description"], "Tiene collar violeta y una mancha blanca en el pecho.")
        self.assertEqual(item["area"], "Barrio Norte")
        self.assertIsNone(item["photo_url"])

    def test_mobile_user_can_register_a_push_device(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("push-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Android de prueba")

        response = self.client.post(
            reverse("mobile_push_device_register"),
            data='{"push_token":"ExponentPushToken[abc123]","platform":"android"}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["registered"])
        self.assertTrue(MobilePushDevice.objects.filter(user=collaborator, platform="android").exists())

    def test_mobile_registration_creates_only_a_community_collaborator(self):
        response = self.client.post(
            reverse("mobile_register"),
            data='{"username":"sofia-colabora","first_name":"Sofía","password":"ClaveSegura123","password_confirmation":"ClaveSegura123","device_name":"Android de Sofía"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        collaborator = User.objects.get(username="sofia-colabora")
        self.assertTrue(collaborator.groups.filter(name="Colaborador comunitario").exists())
        self.assertTrue(collaborator.has_perm("lost_pets.view_lostpetreport"))
        self.assertTrue(collaborator.has_perm("lost_pets.add_sighting"))
        self.assertFalse(collaborator.has_perm("patients.view_patient"))
        self.assertIn("token", response.json())
