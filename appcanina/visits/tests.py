from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from patients.models import Patient
from .models import HomeVisit


class HomeVisitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("visits-user", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="add_homevisit"), Permission.objects.get(codename="view_homevisit"))
        self.patient = Patient.objects.create(name="Mora", species="dog")
        self.client.force_login(self.user)

    def test_new_visit_can_link_an_existing_patient(self):
        response = self.client.post(reverse("home_visit_create"), {"patient": self.patient.id, "scheduled_for": (timezone.localtime() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"), "visit_type": "clinical", "status": "requested", "address": "Calle 123", "zone": "Centro", "reason": "Control", "notes": "", "price": "9000"})
        self.assertRedirects(response, reverse("home_visit_list"))
        self.assertEqual(HomeVisit.objects.get().patient, self.patient)

    def test_new_visit_creates_patient_and_responsible_when_needed(self):
        response = self.client.post(reverse("home_visit_create"), {"patient": "", "new_patient_name": "Luna", "new_patient_species": "cat", "new_contact_name": "Ana Gómez", "new_contact_phone": "11-5555-1111", "scheduled_for": (timezone.localtime() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"), "visit_type": "vaccination", "status": "confirmed", "address": "Avenida 456", "zone": "Norte", "reason": "Vacuna anual", "notes": "", "price": "12000"})
        self.assertRedirects(response, reverse("home_visit_list"))
        visit = HomeVisit.objects.get()
        self.assertEqual(visit.patient.name, "Luna")
        self.assertTrue(visit.patient.patientcontact_set.filter(is_primary=True, contact__full_name="Ana Gómez").exists())
