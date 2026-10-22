from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Organization, OrganizationMembership
from .roles import COMMUNITY_COLLABORATOR_GROUP, ensure_base_roles


class InitialSetupTests(TestCase):
    def test_first_setup_creates_owner_and_business_profile(self):
        response = self.client.post(reverse("initial_setup"), {"business_name": "Veterinaria Nala", "business_kind": "veterinary", "username": "nala-admin", "email": "nala@example.test", "password1": "clave-segura-123", "password2": "clave-segura-123"})
        self.assertRedirects(response, reverse("platform_dashboard"))
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


class OrganizationVerificationTests(TestCase):
    def setUp(self):
        self.platform_admin = User.objects.create_user("platform-admin", password="secret", is_staff=True)
        self.manager = User.objects.create_user("pending-manager", password="secret")
        self.veterinary = Organization.objects.create(
            name="Veterinaria del Parque",
            kind=Organization.Kind.VETERINARY,
            locality="La Plata",
        )
        OrganizationMembership.objects.create(
            organization=self.veterinary,
            user=self.manager,
            role=OrganizationMembership.Role.MANAGER,
        )

    def test_only_platform_staff_can_access_the_verification_queue(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("organization_verification_list")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("organization_verification_update", args=[self.veterinary.id]), {"action": "approve"}).status_code,
            403,
        )

    def test_platform_admin_has_a_separate_dashboard(self):
        self.client.force_login(self.platform_admin)

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("platform_dashboard"))
        response = self.client.get(reverse("platform_dashboard"))
        self.assertContains(response, "Panel de plataforma")
        self.assertNotContains(response, "Atención animal")

    def test_institution_manager_cannot_open_platform_dashboard(self):
        self.client.force_login(self.manager)

        self.assertEqual(self.client.get(reverse("platform_dashboard")).status_code, 403)

    def test_platform_admin_approves_veterinary_and_enables_manager_role(self):
        self.client.force_login(self.platform_admin)
        response = self.client.post(
            reverse("organization_verification_update", args=[self.veterinary.id]),
            {"action": "approve", "verification_note": "Documentación revisada."},
        )

        self.assertRedirects(response, reverse("organization_verification_list"))
        self.veterinary.refresh_from_db()
        self.assertTrue(self.veterinary.is_verified)
        self.assertEqual(self.veterinary.verification_status, Organization.VerificationStatus.APPROVED)
        self.assertEqual(self.veterinary.reviewed_by, self.platform_admin)
        self.assertTrue(self.manager.groups.filter(name="Administrador").exists())

    def test_platform_admin_rejects_shelter_with_reason(self):
        shelter = Organization.objects.create(name="Refugio Sur", kind=Organization.Kind.SHELTER)
        self.client.force_login(self.platform_admin)
        response = self.client.post(
            reverse("organization_verification_update", args=[shelter.id]),
            {"action": "reject", "verification_note": "Falta constancia institucional."},
        )

        self.assertRedirects(response, reverse("organization_verification_list"))
        shelter.refresh_from_db()
        self.assertFalse(shelter.is_verified)
        self.assertEqual(shelter.verification_status, Organization.VerificationStatus.REJECTED)
        self.assertEqual(shelter.verification_note, "Falta constancia institucional.")

    def test_rejection_requires_a_reason(self):
        self.client.force_login(self.platform_admin)
        response = self.client.post(
            reverse("organization_verification_update", args=[self.veterinary.id]),
            {"action": "reject"},
        )

        self.assertRedirects(response, reverse("organization_verification_list"))
        self.veterinary.refresh_from_db()
        self.assertEqual(self.veterinary.verification_status, Organization.VerificationStatus.PENDING)

    def test_rejection_removes_operational_role_when_manager_has_no_other_approved_institution(self):
        self.manager.groups.add(ensure_base_roles()["admin"])
        self.veterinary.verification_status = Organization.VerificationStatus.APPROVED
        self.veterinary.is_verified = True
        self.veterinary.save()
        self.client.force_login(self.platform_admin)

        self.client.post(
            reverse("organization_verification_update", args=[self.veterinary.id]),
            {"action": "reject", "verification_note": "Habilitación revocada."},
        )

        self.assertFalse(self.manager.groups.filter(name="Administrador").exists())
