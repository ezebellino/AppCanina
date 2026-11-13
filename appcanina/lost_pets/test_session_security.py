import importlib
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from organizations.roles import ensure_base_roles
from .models import MobileAccessToken, MobilePushDevice, CommunityNotification, LostPetReport
from .push import send_expo_push


class MobileSessionSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("session-owner", password="Original!Secret-372", email="owner@example.test")
        self.user.groups.add(ensure_base_roles()["collaborator"])
        self.raw, self.token = MobileAccessToken.issue(self.user, "Phone A")
        self.other_raw, self.other_token = MobileAccessToken.issue(self.user, "Phone B")

    def request(self, raw=None):
        return self.client.get(reverse("mobile_my_animals"), HTTP_AUTHORIZATION=f"Bearer {raw or self.raw}")

    def test_expiry_is_absolute_and_rejects_boundary(self):
        self.assertEqual(self.request().status_code, 200)
        self.assertAlmostEqual((self.token.expires_at - self.token.created_at).total_seconds(), 30 * 86400, delta=2)
        with patch("lost_pets.models.timezone.now", return_value=self.token.expires_at):
            self.assertEqual(self.request().status_code, 401)
        self.token.refresh_from_db()
        self.assertLess(self.token.last_used_at, self.token.expires_at)

    def test_password_change_invalidates_all_devices_even_when_password_reused(self):
        self.user.set_password("Original!Secret-372")
        self.user.save(update_fields=["password"])
        self.assertEqual(self.request().status_code, 401)
        self.assertEqual(self.request(self.other_raw).status_code, 401)
        raw, _ = MobileAccessToken.issue(self.user, "New session")
        self.assertEqual(self.request(raw).status_code, 200)

    def test_real_password_reset_flow_invalidates_mobile_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_token = default_token_generator.make_token(self.user)
        response = self.client.get(reverse("password_reset_confirm", args=[uid, reset_token]))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(response.url, {"new_password1": "Replacement!Secret-948", "new_password2": "Replacement!Secret-948"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Replacement!Secret-948"))
        self.assertEqual(self.request().status_code, 401)

    def test_inactive_revoked_missing_binding_and_unknown_tokens_fail_closed(self):
        for change in ({"is_active": False},):
            get_user_model().objects.filter(pk=self.user.pk).update(**change)
            self.assertEqual(self.request().status_code, 401)
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=True)
        MobileAccessToken.objects.filter(pk=self.token.pk).update(password_fingerprint="")
        self.assertEqual(self.request().status_code, 401)
        MobileAccessToken.objects.filter(pk=self.other_token.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.request(self.other_raw).status_code, 401)
        self.assertEqual(self.request("unknown").status_code, 401)

    def test_permission_denial_is_not_an_expired_session(self):
        self.user.groups.clear()
        self.assertEqual(self.request().status_code, 403)
        self.assertIsNotNone(MobileAccessToken.from_raw_token(self.raw))

    def test_logout_is_post_only_idempotent_and_scoped_without_permissions(self):
        url = reverse("mobile_logout")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 401)
        self.user.groups.clear()
        for _ in range(2):
            self.assertEqual(self.client.post(url, HTTP_AUTHORIZATION=f"Bearer {self.raw}").status_code, 200)
        self.assertIsNone(MobileAccessToken.from_raw_token(self.raw))
        self.assertIsNotNone(MobileAccessToken.from_raw_token(self.other_raw))

    def test_login_keeps_legacy_contract_and_adds_expiry(self):
        response = self.client.post(reverse("mobile_login"), {"username": self.user.username, "password": "Original!Secret-372"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token_type"], "Bearer")
        self.assertIn("expires_at", response.json())
        self.assertEqual(self.request(response.json()["token"]).status_code, 200)

    def test_push_delivery_requires_its_own_valid_session(self):
        report = LostPetReport.objects.create(reporter=self.user, name="Example", species="dog", last_seen_at=timezone.now(), area_label="Centro")
        notification = CommunityNotification.objects.create(recipient=self.user, report=report, title="Example", body="Example")
        device = MobilePushDevice.objects.create(user=self.user, token="ExponentPushToken[test]", platform="android", access_token=self.token)
        with patch("lost_pets.push.urlopen") as send:
            send_expo_push([notification])
            from .push import process_push_batch
            process_push_batch()
            send.assert_called_once()
            send.reset_mock()
            self.client.post(reverse("mobile_logout"), HTTP_AUTHORIZATION=f"Bearer {self.raw}")
            send_expo_push([notification])
            send.assert_not_called()
            device.access_token = self.other_token
            device.active = True
            device.save()
            # A new session gets new notifications, never an old queued payload.
            notification = CommunityNotification.objects.create(recipient=self.user, report=report, title="New", body="New")
            from .models import PushWorkerLease
            PushWorkerLease.objects.update(available_at=timezone.now())
            send_expo_push([notification])
            from .push import process_push_batch
            process_push_batch()
            send.assert_called_once()
            send.reset_mock()
            self.user.set_password("Replacement!Secret-948")
            self.user.save()
            send_expo_push([notification])
            send.assert_not_called()

    def test_migration_revokes_legacy_sessions_and_disables_unbound_push(self):
        device = MobilePushDevice.objects.create(user=self.user, token="ExponentPushToken[legacy]", platform="android")
        migration = importlib.import_module("lost_pets.migrations.0013_mobile_session_security")
        migration.revoke_legacy_sessions(apps, SimpleNamespace(connection=connection))
        self.assertIsNone(MobileAccessToken.from_raw_token(self.raw))
        device.refresh_from_db()
        self.assertFalse(device.active)
