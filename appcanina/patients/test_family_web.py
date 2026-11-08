from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
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
