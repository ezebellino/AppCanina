from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .models import Organization


class PublicRegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.data = {"username": "new-family", "email": "family@example.test",
                     "password1": "Safe-family-438!", "password2": "Safe-family-438!",
                     "account_type": "community"}

    def tearDown(self):
        cache.clear()

    def test_login_links_to_public_registration(self):
        self.assertContains(self.client.get(reverse("login")), reverse("register"))
        response = self.client.get(reverse("register"))
        for label in ("Colaborador", "Institución", "Negocio", "avistamientos", "historial"):
            self.assertContains(response, label)

    def test_community_registration_does_not_grant_staff_access(self):
        self.data.update(is_staff="1", is_superuser="1")
        self.assertRedirects(self.client.post(reverse("register"), self.data), reverse("login"))
        user = User.objects.get(username="new-family")
        self.assertTrue(user.check_password(self.data["password1"]))
        self.assertTrue(user.has_perm("lost_pets.add_sighting"))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertFalse(user.has_perm("patients.view_patient"))
        self.assertFalse(Organization.objects.exists())

    def test_institution_and_business_require_validation(self):
        for kind in ("shelter", "veterinary"):
            with self.subTest(kind=kind):
                data = dict(self.data, username=kind, email=f"{kind}@example.test",
                            account_type=kind, organization_name="Patitas", locality="Rosario")
                self.assertRedirects(self.client.post(reverse("register"), data), reverse("login"))
                user = User.objects.get(username=kind)
                organization = Organization.objects.get(memberships__user=user)
                self.assertEqual(organization.kind, kind)
                self.assertEqual(organization.verification_status, "pending")
                self.assertFalse(organization.is_verified)
                self.assertFalse(user.is_staff or user.has_perm("patients.add_patient"))

    def test_invalid_form_creates_neither_user_nor_organization(self):
        for changes in ({"account_type": "admin"}, {"account_type": "shelter"},
                        {"email": ""}, {"password2": "different"}):
            response = self.client.post(reverse("register"), dict(self.data, **changes))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Organization.objects.exists())

    def test_existing_email_is_rejected_case_insensitively(self):
        User.objects.create_user("existing", email="FAMILY@example.test")
        response = self.client.post(reverse("register"), self.data)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_is_throttled_and_csrf_protected(self):
        cache.set("mobile-register:127.0.0.1", 3)
        self.assertEqual(self.client.post(reverse("register"), self.data).status_code, 429)
        cache.clear()
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse("register"), self.data).status_code, 403)
        self.assertFalse(User.objects.exists())
