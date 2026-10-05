from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Organization
from .roles import COMMUNITY_COLLABORATOR_GROUP


class InitialSetupTests(TestCase):
    def test_first_setup_creates_owner_and_business_profile(self):
        response = self.client.post(reverse("initial_setup"), {"business_name": "Veterinaria Nala", "business_kind": "veterinary", "username": "nala-admin", "email": "nala@example.test", "password1": "clave-segura-123", "password2": "clave-segura-123"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.get(username="nala-admin").is_superuser)
        self.assertEqual(Organization.objects.get(is_business_profile=True).name, "Veterinaria Nala")
        self.assertTrue(User.objects.get(username="nala-admin").groups.filter(name=COMMUNITY_COLLABORATOR_GROUP).exists() is False)

    def test_setup_is_unavailable_after_first_user_exists(self):
        User.objects.create_user("existing", password="secret")
        response = self.client.get(reverse("initial_setup"))
        self.assertRedirects(response, reverse("login"))


class CommunityCollaboratorTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("owner", "owner@example.test", "secret")
        self.client.force_login(self.owner)

    def test_owner_can_create_a_limited_community_collaborator(self):
        response = self.client.post(
            reverse("community_collaborators"),
            {
                "username": "luz-colabora",
                "first_name": "Luz",
                "last_name": "Pérez",
                "email": "luz@example.test",
                "password1": "clave-segura-123",
                "password2": "clave-segura-123",
            },
        )

        collaborator = User.objects.get(username="luz-colabora")
        self.assertRedirects(response, reverse("community_collaborators"))
        self.assertTrue(collaborator.groups.filter(name=COMMUNITY_COLLABORATOR_GROUP).exists())
        self.assertTrue(collaborator.has_perm("lost_pets.view_lostpetreport"))
        self.assertTrue(collaborator.has_perm("lost_pets.add_sighting"))
        self.assertFalse(collaborator.has_perm("lost_pets.add_lostpetreport"))
        self.assertFalse(collaborator.has_perm("patients.view_patient"))
