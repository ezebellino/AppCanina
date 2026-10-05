from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Organization


class InitialSetupTests(TestCase):
    def test_first_setup_creates_owner_and_business_profile(self):
        response = self.client.post(reverse("initial_setup"), {"business_name": "Veterinaria Nala", "business_kind": "veterinary", "username": "nala-admin", "email": "nala@example.test", "password1": "clave-segura-123", "password2": "clave-segura-123"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.get(username="nala-admin").is_superuser)
        self.assertEqual(Organization.objects.get(is_business_profile=True).name, "Veterinaria Nala")

    def test_setup_is_unavailable_after_first_user_exists(self):
        User.objects.create_user("existing", password="secret")
        response = self.client.get(reverse("initial_setup"))
        self.assertRedirects(response, reverse("login"))
