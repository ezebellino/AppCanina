from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from lost_pets.models import AdoptionInterest, AdoptionPost, MobileAccessToken
from organizations.models import Organization
from patients.models import ClinicalRecord, Patient


class CommunityDemoSeedTests(TestCase):
    def seed(self):
        call_command("seed_community_demo", stdout=StringIO())

    def test_seed_is_idempotent_and_creates_the_three_demo_roles(self):
        self.seed()
        self.seed()

        self.assertTrue(User.objects.filter(username="demo_veterinaria").exists())
        self.assertTrue(User.objects.filter(username="demo_refugio").exists())
        self.assertTrue(User.objects.filter(username="demo_usuario").exists())
        self.assertEqual(Organization.objects.filter(name="[DEMO] Refugio Patitas").count(), 1)
        self.assertEqual(AdoptionPost.objects.filter(organization__name="[DEMO] Refugio Patitas").count(), 9)
        self.assertEqual(Patient.objects.filter(microchip="DEMO-COM-001").count(), 1)

    def test_demo_veterinary_refuge_and_user_interactions_work(self):
        self.seed()
        veterinarian = User.objects.get(username="demo_veterinaria")
        refuge_manager = User.objects.get(username="demo_refugio")
        community_user = User.objects.get(username="demo_usuario")
        patient = Patient.objects.get(microchip="DEMO-COM-001")

        self.client.force_login(veterinarian)
        response = self.client.post(
            reverse("clinical_record_create", args=[patient.id]),
            {"occurred_on": "2026-10-18", "reason": "Seguimiento DEMO", "notes": "Interacción simulada de veterinaria."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClinicalRecord.objects.filter(patient=patient, reason="Seguimiento DEMO").exists())

        post = AdoptionPost.objects.get(organization__name="[DEMO] Refugio Patitas", name="Nilo")
        self.client.force_login(refuge_manager)
        response = self.client.post(reverse("adoption_change_status", args=[post.id]), {"status": "adopted"})
        self.assertEqual(response.status_code, 302)
        post.refresh_from_db()
        self.assertEqual(post.status, AdoptionPost.Status.ADOPTED)
        self.assertTrue(AdoptionInterest.objects.filter(post__name="Mora", applicant=community_user).exists())

        raw_token, _ = MobileAccessToken.issue(community_user, "Prueba DEMO")
        animals = self.client.get(reverse("mobile_my_animals"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        interests = self.client.get(reverse("mobile_my_adoption_interests"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        published = self.client.get(reverse("mobile_adoptions"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        self.assertEqual(animals.status_code, 200)
        self.assertEqual([animal["name"] for animal in animals.json()["animals"]], ["Canela"])
        self.assertEqual(interests.status_code, 200)
        self.assertEqual(interests.json()["interests"][0]["animal_name"], "Mora")
        self.assertNotIn("Nilo", [post["name"] for post in published.json()["adoptions"]])

