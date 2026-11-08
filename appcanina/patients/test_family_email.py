from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db import transaction
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .family import accept_invitation
from .models import Contact, OwnerAccountLink, Patient, PatientContact, PatientFamilyAccess, PatientFamilyInvite


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class FamilyEmailTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", email="owner@example.test")
        self.partner = User.objects.create_user("partner", email="partner@example.test")
        contact = Contact.objects.create(full_name="Owner")
        OwnerAccountLink.objects.create(contact=contact, user=self.owner)
        self.patient = Patient.objects.create(name="Evaristo", species="dog", microchip="PRIVATE-CHIP")
        PatientContact.objects.create(patient=self.patient, contact=contact, role="responsible")
        self.code, self.invite = PatientFamilyInvite.issue(self.patient, self.owner, timezone.now() + timedelta(minutes=15))
        self.request = RequestFactory().get("/", secure=True)

    def test_confirmation_is_after_commit_private_and_not_repeated(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            accept_invitation(self.partner, self.code, request=self.request)
            self.assertEqual(len(mail.outbox), 0)
            self.assertTrue(PatientFamilyAccess.objects.filter(user=self.partner).exists())
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, [self.owner.email])
        self.assertEqual(mail.outbox[1].to, [self.partner.email])
        self.assertIn(reverse("family_manage", args=[self.patient.id]), mail.outbox[0].body)
        self.assertIn(reverse("my_animals"), mail.outbox[1].body)
        for message in mail.outbox:
            self.assertNotIn(self.code, message.body)
            self.assertNotIn("PRIVATE-CHIP", message.body)
        with self.assertRaises(ValueError):
            accept_invitation(self.partner, self.code, request=self.request)
        self.assertEqual(len(mail.outbox), 2)

    def test_failure_does_not_undo_access_or_prevent_second_notice(self):
        with patch("patients.family_email.EmailMessage.send", side_effect=[OSError("private SMTP password"), 1]) as send:
            with self.assertLogs("patients.family_email", level="INFO") as logs:
                with self.captureOnCommitCallbacks(execute=True):
                    accept_invitation(self.partner, self.code, request=self.request)
        self.assertTrue(PatientFamilyAccess.objects.filter(user=self.partner).exists())
        self.assertEqual(send.call_count, 2)
        self.assertNotIn("private SMTP password", str(logs.output))
        self.assertIn("family_email_failed", str(logs.output))

    def test_missing_email_still_notifies_other_recipient(self):
        self.owner.email = ""
        self.owner.save()
        with self.captureOnCommitCallbacks(execute=True):
            accept_invitation(self.partner, self.code, request=self.request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.partner.email])

    def test_rollback_does_not_send_or_keep_access(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    accept_invitation(self.partner, self.code, request=self.request)
                    raise RuntimeError("rollback")
        self.assertEqual(callbacks, [])
        self.assertFalse(PatientFamilyAccess.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_web_acceptance_schedules_both_notices(self):
        self.client.force_login(self.partner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("family_accept"), {"code": self.code})
        self.assertRedirects(response, reverse("my_animals"))
        self.assertEqual(len(mail.outbox), 2)
