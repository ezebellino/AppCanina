from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Contact, OwnerAccountLink, Patient, PatientContact, PatientFamilyAccess, PatientFamilyInvite


class WebFamilyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user("family-owner")
        self.partner = User.objects.create_user("family-partner")
        self.stranger = User.objects.create_user("stranger")
        contact = Contact.objects.create(full_name="Responsable")
        OwnerAccountLink.objects.create(contact=contact, user=self.owner)
        self.animal = Patient.objects.create(name="Evaristo", species="dog")
        self.other = Patient.objects.create(name="Otro", species="cat")
        for animal in (self.animal, self.other):
            PatientContact.objects.create(patient=animal, contact=contact, role="responsible")
        self.manage = reverse("family_manage", args=[self.animal.id])

    def tearDown(self):
        cache.clear()

    def create_invite(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.manage)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(response, "Enviar invitación por WhatsApp")
        return response.context["code"]

    def test_link_is_single_use_scoped_and_revocable(self):
        code = self.create_invite()
        self.client.force_login(self.partner)
        self.assertRedirects(self.client.post(reverse("family_accept"), {"code": code}), reverse("my_animals"))
        response = self.client.get(reverse("my_animals"))
        self.assertContains(response, "Evaristo")
        self.assertNotContains(response, "Otro")
        self.assertNotContains(response, "data-credential-url")
        self.assertEqual(Patient.objects.count(), 2)
        history = reverse("my_animal_history", args=[self.animal.id])
        self.assertEqual(self.client.get(history).status_code, 200)
        self.assertEqual(self.client.post(self.manage).status_code, 403)
        self.assertEqual(self.client.get(reverse("my_animal_credential", args=[self.animal.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("my_animal_sharing", args=[self.animal.id]), {"enabled": "on"}).status_code, 404)
        self.assertContains(self.client.post(reverse("family_accept"), {"code": code}), "ya fue utilizado")
        access = PatientFamilyAccess.objects.get(user=self.partner)
        self.client.force_login(self.owner)
        self.client.post(reverse("family_revoke", args=[self.animal.id]), {"access_id": access.id})
        self.client.force_login(self.partner)
        self.assertEqual(self.client.get(history).status_code, 404)
        self.assertNotContains(self.client.get(reverse("my_animals")), "Evaristo")

    def test_expired_revoked_self_and_unknown_invites_fail(self):
        code = self.create_invite()
        self.assertContains(self.client.post(reverse("family_accept"), {"code": code}), "propio código")
        self.client.force_login(self.partner)
        PatientFamilyInvite.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertContains(self.client.post(reverse("family_accept"), {"code": code}), "venció")
        self.assertContains(self.client.post(reverse("family_accept"), {"code": "FAM-unknown"}), "no es válido")
        self.assertFalse(PatientFamilyAccess.objects.exists())

    def test_invite_authorization_and_limit(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(self.manage).status_code, 404)
        self.client.force_login(self.owner)
        for _ in range(3):
            self.client.post(self.manage)
        self.assertContains(self.client.post(self.manage), "tres invitaciones activas")
        self.assertEqual(PatientFamilyInvite.objects.count(), 3)
        invite = PatientFamilyInvite.objects.first()
        self.client.post(reverse("family_revoke", args=[self.animal.id]), {"invite_id": invite.id})
        self.client.post(self.manage)
        self.assertEqual(PatientFamilyInvite.objects.count(), 4)

    def test_owner_sees_share_actions_without_issuing_credential_on_page_load(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("my_animals"))
        self.assertContains(response, "Compartir credencial")
        self.assertContains(response, "Agregar con código familiar")
        self.assertContains(response, "Responsables familiares")
        self.assertFalse(self.animal.travel_credentials.exists())

    @override_settings(PUBLIC_BASE_URL="https://lazuna.example")
    def test_web_and_api_share_the_same_fragment_link(self):
        from urllib.parse import parse_qs, urlsplit
        from lost_pets.models import MobileAccessToken
        from organizations.roles import ensure_base_roles
        self.owner.groups.add(ensure_base_roles()["collaborator"])
        self.client.force_login(self.owner)
        response = self.client.post(self.manage)
        url = urlsplit(response.context["share_url"])
        self.assertEqual(url.netloc, "lazuna.example")
        self.assertEqual(url.path, reverse("family_accept"))
        self.assertEqual(url.query, "")
        self.assertEqual(parse_qs(url.fragment)["code"], [response.context["code"]])
        self.assertIn(response.context["share_url"], response.context["share_text"])
        token, _ = MobileAccessToken.issue(self.owner, "test")
        data = self.client.post(reverse("mobile_family_invite_create", args=[self.animal.pk]),
                                HTTP_AUTHORIZATION=f"Bearer {token}").json()
        self.assertEqual(parse_qs(urlsplit(data["share_url"]).fragment)["code"], [data["code"]])
        self.assertIn(data["share_url"], data["share_text"])

    def test_invitation_survives_signup_login_and_requires_explicit_acceptance(self):
        code = self.create_invite()
        self.client.logout()
        target = reverse("family_accept")
        preview = self.client.get(target)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview["Referrer-Policy"], "no-referrer")
        self.assertIn("no-store", preview["Cache-Control"])
        self.assertFalse(PatientFamilyAccess.objects.exists())
        response = self.client.post(target, {"action": "prepare", "code": code})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(code, response.url)
        self.assertFalse(PatientFamilyInvite.objects.get().accepted_at)
        password = "Only-for-family-test-846!"
        self.client.post(reverse("register"), {
            "username": "new-partner", "email": "partner@example.test", "account_type": "community",
            "password1": password, "password2": password, "next": target,
        })
        response = self.client.post(reverse("login"), {"username": "new-partner", "password": password, "next": target}, follow=True)
        self.assertEqual(response.context["form"].initial["code"], code)
        self.assertFalse(PatientFamilyAccess.objects.exists())
        response = self.client.post(target, {"code": code})
        self.assertRedirects(response, reverse("my_animals"))
        self.assertEqual(PatientFamilyAccess.objects.get().user.username, "new-partner")
        self.assertNotIn("pending_family_invitation", self.client.session)

    def test_prepare_authenticated_does_not_accept_and_new_link_replaces_old(self):
        code = self.create_invite()
        self.client.force_login(self.partner)
        target = reverse("family_accept")
        response = self.client.post(target, {"action": "prepare", "code": code}, follow=True)
        self.assertEqual(response.context["form"].initial["code"], code)
        self.assertFalse(PatientFamilyInvite.objects.get().accepted_at)
        self.client.post(target, {"action": "prepare", "code": "FAM-replacement"})
        self.assertEqual(self.client.get(target).context["form"].initial["code"], "FAM-replacement")
        self.assertFalse(PatientFamilyAccess.objects.exists())

    def test_prepare_is_csrf_protected_and_does_not_accept_query_codes(self):
        code = self.create_invite()
        browser = Client(enforce_csrf_checks=True)
        target = reverse("family_accept")
        self.assertEqual(browser.post(target, {"action": "prepare", "code": code}).status_code, 403)
        response = browser.get(target, {"code": code})
        self.assertEqual(response.context["form"].initial["code"], "")
        csrf = browser.cookies["csrftoken"].value
        response = browser.post(target, {"action": "prepare", "code": code, "csrfmiddlewaretoken": csrf})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PatientFamilyInvite.objects.get().accepted_at)
        self.assertFalse(PatientFamilyAccess.objects.exists())

    def test_expired_pending_code_is_discarded_and_invite_expiry_still_enforced(self):
        code = self.create_invite()
        self.client.force_login(self.partner)
        target = reverse("family_accept")
        self.client.post(target, {"action": "prepare", "code": code})
        session = self.client.session
        session["pending_family_invitation"] = {"code": code, "expires_at": 1}
        session.save()
        self.assertEqual(self.client.get(target).context["form"].initial["code"], "")
        self.assertNotIn("pending_family_invitation", self.client.session)
        self.client.post(target, {"action": "prepare", "code": code})
        PatientFamilyInvite.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertContains(self.client.post(target, {"code": code}), "venció")
        self.assertFalse(PatientFamilyAccess.objects.exists())
        self.assertNotIn("pending_family_invitation", self.client.session)
