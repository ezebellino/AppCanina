from io import StringIO
from unittest.mock import patch
from getpass import GetPassWarning

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organizations.models import OrganizationMembership
from patients.models import Patient, PatientContact
from .models import AdoptionPost, AdoptionInterest, MobileAccessToken, MobilePushDevice


class DemoSecurityTests(TestCase):
    module = "lost_pets.management.commands.secure_demo_accounts"

    def setUp(self):
        self.admin = User.objects.create_user("real-admin", password="Private!Owner-742", is_staff=True, last_login=timezone.now())
        call_command("seed_community_demo", stdout=StringIO())
        self.demo = User.objects.get(username="demo_refugio")
        self.demo.set_password("Old!Example-582")
        self.demo.save()

    def run_command(self, passwords, **kwargs):
        output = StringIO()
        with patch(f"{self.module}.sys.stdin.isatty", return_value=True), patch(f"{self.module}.getpass", side_effect=passwords):
            call_command("secure_demo_accounts", apply=True, admin="real-admin", stdout=output, **kwargs)
        return output.getvalue()

    def passwords(self):
        return [value for index in range(User.objects.filter(username__in=["demo_usuario", "demo_refugio", "demo_veterinaria", "demo_veterinaria_admin"]).count()) for value in [f"Private!Trial-{index}-498", f"Private!Trial-{index}-498"]]

    def test_seed_has_no_shared_login_and_preserves_private_password_on_rerun(self):
        for username in ("demo_usuario", "demo_veterinaria"):
            user = User.objects.get(username=username)
            self.assertFalse(user.has_usable_password())
            self.assertFalse(user.is_staff or user.is_superuser)
        previous = self.demo.password
        output = StringIO()
        call_command("seed_community_demo", stdout=output)
        self.demo.refresh_from_db()
        self.assertEqual(self.demo.password, previous)
        self.assertNotIn("Old!Example-582", output.getvalue())
        self.assertIn("no tienen clave", output.getvalue())

    def test_default_is_read_only_and_never_prompts(self):
        before = list(User.objects.values_list("id", "password", "is_staff"))
        with patch(f"{self.module}.getpass") as prompt:
            call_command("secure_demo_accounts", stdout=StringIO())
        prompt.assert_not_called()
        self.assertEqual(list(User.objects.values_list("id", "password", "is_staff")), before)

    def test_rotation_preserves_data_and_other_accounts_but_invalidates_demo_sessions(self):
        legacy = User.objects.create_user("demo_veterinaria_admin", password="Legacy!Example-734", is_staff=True, is_superuser=True)
        real = User.objects.create_user("demo_unrelated_real", password="Other!Example-734", is_staff=True)
        unrelated_hash = real.password
        admin_hash = self.admin.password
        self.client.force_login(self.demo)
        old_raw, old_token = MobileAccessToken.issue(self.demo, "old")
        real_raw, _ = MobileAccessToken.issue(self.admin, "real")
        push = MobilePushDevice.objects.create(user=self.demo, token="ExponentPushToken[fixture]", platform="android")
        models = (Patient, PatientContact, OrganizationMembership, AdoptionPost, AdoptionInterest)
        counts = [model.objects.count() for model in models]
        groups = list(self.demo.groups.values_list("pk", flat=True))
        passwords = self.passwords()
        output = self.run_command(passwords)
        for password in passwords:
            self.assertNotIn(password, output)
        self.demo.refresh_from_db()
        self.assertTrue(self.demo.is_active)
        self.assertEqual(list(self.demo.groups.values_list("pk", flat=True)), groups)
        self.assertEqual([model.objects.count() for model in models], counts)
        self.assertEqual(self.client.get(reverse("adoption_interest_list")).status_code, 302)
        self.assertIsNone(MobileAccessToken.from_raw_token(old_raw))
        self.assertIsNotNone(MobileAccessToken.from_raw_token(real_raw))
        old_token.refresh_from_db()
        self.assertIsNotNone(old_token.revoked_at)
        push.refresh_from_db()
        self.assertFalse(push.active)
        legacy.refresh_from_db()
        self.assertFalse(legacy.is_staff or legacy.is_superuser)
        real.refresh_from_db(); self.admin.refresh_from_db()
        self.assertEqual(real.password, unrelated_hash)
        self.assertEqual(self.admin.password, admin_hash)
        self.assertTrue(self.admin.is_staff)
        self.assertIsNotNone(authenticate(username=self.demo.username, password=passwords[0]))
        call_command("seed_community_demo", stdout=StringIO())
        self.assertIsNotNone(authenticate(username=self.demo.username, password=passwords[0]))

    def test_weak_mismatch_reused_and_cancelled_input_never_partially_write(self):
        for inputs in (["short", "short"], ["Private!Trial-498", "different"], ["Old!Example-582"] * 2,
                       ["Private!Trial-498"] * 4, ["Private!Trial-498"] * 2 + [EOFError()],
                       [GetPassWarning("no echo control")], [KeyboardInterrupt()]):
            before = list(User.objects.values_list("id", "password", "is_staff"))
            with self.assertRaises(CommandError):
                self.run_command(inputs)
            self.assertEqual(list(User.objects.values_list("id", "password", "is_staff")), before)

    def test_requires_real_accessible_admin_and_interactive_terminal(self):
        for attrs in ({"is_staff": False}, {"is_active": False}, {"last_login": None}):
            User.objects.filter(pk=self.admin.pk).update(**attrs)
            with self.assertRaises(CommandError):
                self.run_command([])
            User.objects.filter(pk=self.admin.pk).update(is_staff=True, is_active=True, last_login=timezone.now())
        with patch(f"{self.module}.sys.stdin.isatty", return_value=False), self.assertRaises(CommandError):
            call_command("secure_demo_accounts", apply=True, admin="real-admin", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("secure_demo_accounts", apply=True, admin="demo_refugio", stdout=StringIO())

    def test_inactive_accounts_are_not_reactivated(self):
        self.demo.is_active = False
        self.demo.save()
        self.run_command(self.passwords())
        self.demo.refresh_from_db()
        self.assertFalse(self.demo.is_active)

    def test_database_failure_rolls_back_passwords_flags_and_tokens(self):
        raw, token = MobileAccessToken.issue(self.demo, "existing")
        before = list(User.objects.values_list("id", "password", "is_staff"))
        with patch(f"{self.module}.MobilePushDevice.objects.filter") as devices:
            devices.return_value.update.side_effect = RuntimeError("fixture database failure")
            with self.assertRaises(RuntimeError):
                self.run_command(self.passwords())
        self.assertEqual(list(User.objects.values_list("id", "password", "is_staff")), before)
        self.assertIsNotNone(MobileAccessToken.from_raw_token(raw))

    def test_concurrent_account_change_aborts_prepared_rotation(self):
        before = list(User.objects.values_list("id", "password"))
        inputs = iter(self.passwords())
        def concurrent_input(prompt):
            User.objects.filter(pk=self.demo.pk).update(is_staff=True)
            return next(inputs)
        with patch(f"{self.module}.sys.stdin.isatty", return_value=True), patch(f"{self.module}.getpass", side_effect=concurrent_input):
            with self.assertRaises(CommandError):
                call_command("secure_demo_accounts", apply=True, admin="real-admin", stdout=StringIO())
        self.assertEqual(list(User.objects.values_list("id", "password")), before)
