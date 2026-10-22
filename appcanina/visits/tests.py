from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from patients.models import Patient
from organizations.models import Organization, OrganizationMembership
from .models import HomeVisit


class HomeVisitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("visits-user", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="add_homevisit"), Permission.objects.get(codename="view_homevisit"))
        self.organization = Organization.objects.create(name="Veterinaria Visitas", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.patient = Patient.objects.create(name="Mora", species="dog", organization=self.organization)
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
        self.assertEqual(visit.patient.organization, self.organization)

    def test_visits_from_other_organizations_are_not_listed_or_editable(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_homevisit"))
        other_organization = Organization.objects.create(name="Otra veterinaria", kind=Organization.Kind.VETERINARY)
        other_patient = Patient.objects.create(name="Oculto", species="cat", organization=other_organization)
        foreign_visit = HomeVisit.objects.create(
            patient=other_patient,
            scheduled_for=timezone.localtime() + timedelta(hours=1),
            visit_type="clinical",
            address="Calle ajena 1",
            reason="Control",
        )

        response = self.client.get(reverse("home_visit_list"))

        self.assertNotContains(response, foreign_visit.patient.name)
        self.assertEqual(self.client.get(reverse("home_visit_edit", args=[foreign_visit.id])).status_code, 404)
