from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from .models import Organization, OrganizationMembership
from .roles import COMMUNITY_COLLABORATOR_GROUP, ensure_base_roles


class PersonalProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("profile-user", email="original@example.com")
        self.client.force_login(self.user)

    def test_community_menu_and_legacy_business_url_do_not_show_unrelated_business(self):
        Organization.objects.create(name="Unrelated private business", kind="veterinary", is_business_profile=True)
        response = self.client.get(reverse("personal_profile"))
        self.assertContains(response, "Mi perfil")
        self.assertNotContains(response, "Mi perfil y negocio")
        self.assertNotContains(response, "Unrelated private business")
        self.assertRedirects(self.client.get(reverse("business_profile")), reverse("personal_profile"))
        self.assertRedirects(self.client.post(reverse("business_profile"), {"name": "Changed"}), reverse("personal_profile"))
        self.assertTrue(Organization.objects.filter(name="Unrelated private business").exists())

    def test_menu_matches_institution_even_before_approval(self):
        for kind, label in (("shelter", "Mi institución"), ("veterinary", "Mi negocio")):
            with self.subTest(kind=kind):
                organization = Organization.objects.create(name=kind, kind=kind)
                membership = OrganizationMembership.objects.create(user=self.user, organization=organization)
                response = self.client.get(reverse("personal_profile"))
                self.assertContains(response, label)
                self.assertContains(response, reverse("business_profile"))
                membership.delete()

    def test_profile_updates_only_current_users_personal_fields(self):
        other = User.objects.create_user("other-profile", email="other@example.com")
        self.client.post(reverse("personal_profile"), {
            "first_name": "Ana", "last_name": "Pérez", "email": "ana@example.com",
            "id": other.pk, "is_staff": "on", "is_superuser": "on", "username": "changed",
        })
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.email, "ana@example.com")
        self.assertEqual(other.email, "other@example.com")
        self.assertEqual(self.user.username, "profile-user")
        self.assertFalse(self.user.is_staff or self.user.is_superuser)
        response = self.client.post(reverse("personal_profile"), {"email": "OTHER@example.com"})
        self.assertContains(response, "ya está asociado")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ana@example.com")

    def test_profile_requires_login_and_csrf(self):
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(reverse("personal_profile"), {"email": "new@example.com"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("personal_profile")).status_code, 302)


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


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordRecoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "recuperacion",
            email="recuperacion@example.test",
            password="clave-anterior",
        )

    def test_password_recovery_sends_a_single_use_reset_link(self):
        response = self.client.post(reverse("password_reset"), {"email": self.user.email})

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Restablecé tu contraseña", mail.outbox[0].subject)
        self.assertIn("cuenta/restablecer/", mail.outbox[0].body)

    def test_password_recovery_does_not_disclose_unknown_email_addresses(self):
        response = self.client.post(reverse("password_reset"), {"email": "no-existe@example.test"})

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)


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


class EmailLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("zeqe-test", email="owner@example.test", password="old-password")

    def test_reset_password_then_login_by_email_and_username(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.get(reverse("password_reset_confirm", args=[uid, token]))
        response = self.client.post(response.url, {"new_password1": "new-strong-password-739!", "new_password2": "new-strong-password-739!"})
        self.assertRedirects(response, reverse("password_reset_complete"))
        for identifier in ("zeqe-test", "OWNER@EXAMPLE.TEST"):
            self.client.logout()
            response = self.client.post(reverse("login"), {"username": identifier, "password": "new-strong-password-739!"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_duplicate_email_is_rejected_but_username_still_works(self):
        from django.contrib.auth import authenticate
        User.objects.create_user("another", email="OWNER@example.test", password="another-password")
        self.assertIsNone(authenticate(username="owner@example.test", password="old-password"))
        self.assertEqual(authenticate(username="zeqe-test", password="old-password"), self.user)

    def test_email_cannot_override_another_accounts_username(self):
        from django.contrib.auth import authenticate
        other = User.objects.create_user("owner@example.test", password="another-password")
        self.assertIsNone(authenticate(username="owner@example.test", password="old-password"))
        self.assertEqual(authenticate(username="owner@example.test", password="another-password"), other)

    def test_inactive_user_and_wrong_password_are_rejected(self):
        from django.contrib.auth import authenticate
        self.assertIsNone(authenticate(username=self.user.email, password="wrong"))
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(username=self.user.email, password="old-password"))

    def test_existing_mobile_api_accepts_email(self):
        from django.core.cache import cache
        cache.clear()
        self.user.groups.add(ensure_base_roles()["collaborator"])
        response = self.client.post(reverse("mobile_login"), {"username": "OWNER@example.test", "password": "old-password"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], self.user.username)
