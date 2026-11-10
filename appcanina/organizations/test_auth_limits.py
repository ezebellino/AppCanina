import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import DatabaseError, close_old_connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .auth_limits import client_network
from .models import AuthAttemptBucket
from .roles import ensure_base_roles


@override_settings(AUTH_TRUST_RAILWAY_PROXY=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthAttemptTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("limited-user", "owner@example.test", "valid-secret-173!")
        self.user.groups.add(ensure_base_roles()["collaborator"])

    def login(self, identifier="limited-user", password="wrong", ip="192.0.2.1", route="login", **headers):
        payload = {"username": identifier, "password": password}
        if route == "mobile_login":
            return self.client.post(reverse(route), json.dumps(payload), content_type="application/json", REMOTE_ADDR=ip, **headers)
        return self.client.post(reverse(route), payload, REMOTE_ADDR=ip, **headers)

    def test_web_admin_mobile_share_budget_and_block_before_authentication(self):
        for route in ("login", "admin:login", "mobile_login", "login", "mobile_login"):
            self.assertNotEqual(self.login(route=route).status_code, 429)
        with patch("django.contrib.auth.forms.authenticate") as web_auth, patch("lost_pets.api.authenticate") as api_auth:
            for route in ("login", "admin:login", "mobile_login"):
                response = self.login(password="valid-secret-173!", route=route)
                self.assertEqual(response.status_code, 429)
                self.assertGreater(int(response["Retry-After"]), 0)
                self.assertEqual(response["Cache-Control"], "no-store")
            web_auth.assert_not_called()
            api_auth.assert_not_called()

    def test_success_keeps_redirect_and_does_not_clear_budget(self):
        for _ in range(3):
            self.login()
        response = self.client.post(reverse("login") + "?next=/cuenta/perfil/", {
            "username": "limited-user", "password": "valid-secret-173!", "next": "/cuenta/perfil/",
        }, REMOTE_ADDR="192.0.2.1")
        self.assertEqual(response.url, "/cuenta/perfil/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.client.logout()
        self.assertEqual(self.login(password="valid-secret-173!", route="mobile_login").status_code, 200)
        self.assertEqual(self.login().status_code, 429)

    def test_identifier_variants_cache_clear_new_client_and_forged_forwarding_do_not_bypass(self):
        for identifier in ("owner@example.test", "OWNER@EXAMPLE.TEST", " owner@example.test ", "Owner@example.test", "owner@EXAMPLE.test"):
            self.login(identifier=identifier, HTTP_X_FORWARDED_FOR="203.0.113.1", HTTP_X_REAL_IP="203.0.113.1")
        cache.clear()
        self.client = Client()
        response = self.login(identifier="OWNER@example.test", HTTP_X_FORWARDED_FOR="203.0.113.9", HTTP_X_REAL_IP="203.0.113.9")
        self.assertEqual(response.status_code, 429)
        for bucket in AuthAttemptBucket.objects.all():
            self.assertEqual(len(bucket.key), 64)
            self.assertNotIn("owner", bucket.key)

    def test_rotating_ips_cannot_bypass_identifier_and_other_user_can_login(self):
        for i in range(20):
            self.assertNotEqual(self.login(ip=f"192.0.2.{i + 1}").status_code, 429)
        self.assertEqual(self.login(ip="198.51.100.1").status_code, 429)
        get_user_model().objects.create_user("other-user", password="other-secret-173!")
        self.assertEqual(self.login(identifier="other-user", password="other-secret-173!").status_code, 302)

    def test_rotating_identifiers_cannot_bypass_network_budget(self):
        # No password hashing needed to prove the pre-auth request budget.
        with patch("django.contrib.auth.forms.authenticate", return_value=None):
            for i in range(60):
                self.assertEqual(self.login(identifier=f"unknown-{i}").status_code, 200)
            before = list(AuthAttemptBucket.objects.order_by("key").values_list("key", "count"))
            self.assertEqual(self.login(identifier="one-more").status_code, 429)
            self.assertEqual(self.login(identifier="limited-user").status_code, 429)
            self.assertEqual(list(AuthAttemptBucket.objects.order_by("key").values_list("key", "count")), before)

    def test_expiry_releases_budget_without_sliding_on_blocked_attempts(self):
        start = timezone.now()
        with patch("organizations.auth_limits.timezone.now", return_value=start):
            for _ in range(5):
                self.login()
        with patch("organizations.auth_limits.timezone.now", return_value=start + timedelta(seconds=899)):
            self.assertEqual(self.login()["Retry-After"], "1")
        with patch("organizations.auth_limits.timezone.now", return_value=start + timedelta(seconds=900)):
            self.assertEqual(self.login(password="valid-secret-173!").status_code, 302)
            self.assertFalse(AuthAttemptBucket.objects.filter(expires_at__lte=start + timedelta(seconds=900)).exists())

    def test_reset_known_unknown_same_behavior_and_mail_stops(self):
        for index, email in enumerate(("owner@example.test", "absent@example.test")):
            ip = f"192.0.2.{index + 1}"
            for variant in (email, email.upper(), f" {email} "):
                response = self.client.post(reverse("password_reset"), {"email": variant}, REMOTE_ADDR=ip)
                self.assertRedirects(response, reverse("password_reset_done"))
            response = self.client.post(reverse("password_reset"), {"email": email}, REMOTE_ADDR=ip)
            self.assertEqual(response.status_code, 429)
            self.assertNotContains(response, email, status_code=429)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(self.login(password="valid-secret-173!").status_code, 302)

    def test_reset_spray_network_budget_and_distributed_recipient_budget(self):
        for i in range(3):
            self.client.post(reverse("password_reset"), {"email": self.user.email}, REMOTE_ADDR=f"192.0.2.{i + 1}")
        self.assertEqual(self.client.post(reverse("password_reset"), {"email": self.user.email}, REMOTE_ADDR="192.0.2.4").status_code, 429)
        for i in range(10):
            self.assertEqual(self.client.post(reverse("password_reset"), {"email": f"absent{i}@example.test"}, REMOTE_ADDR="198.51.100.1").status_code, 302)
        self.assertEqual(self.client.post(reverse("password_reset"), {"email": "last@example.test"}, REMOTE_ADDR="198.51.100.1").status_code, 429)
        self.assertEqual(len(mail.outbox), 3)

    def test_get_and_csrf_rejection_do_not_spend_budget(self):
        csrf = Client(enforce_csrf_checks=True)
        for route in ("login", "admin:login", "password_reset"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 200)
            self.assertEqual(csrf.post(reverse(route), {}).status_code, 403)
        self.assertFalse(AuthAttemptBucket.objects.exists())

    def test_storage_failure_fails_closed_without_auth_or_mail(self):
        with patch("organizations.auth_limits.consume_budget", side_effect=DatabaseError), patch("django.contrib.auth.forms.authenticate") as auth:
            self.assertEqual(self.login(password="valid-secret-173!").status_code, 503)
            self.assertEqual(self.client.post(reverse("password_reset"), {"email": self.user.email}).status_code, 503)
            auth.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)

    def test_malformed_mobile_payload_is_rejected_without_server_error(self):
        for payload in ([], None, {"username": []}, {"password": {}}, "bad"):
            self.assertEqual(self.client.post(reverse("mobile_login"), json.dumps(payload), content_type="application/json").status_code, 400)

    def test_network_canonicalization_and_explicit_proxy_trust(self):
        factory = RequestFactory()
        request = factory.get("/", REMOTE_ADDR="192.0.2.1", HTTP_X_REAL_IP="198.51.100.1", HTTP_X_FORWARDED_FOR="203.0.113.1")
        self.assertEqual(client_network(request), "192.0.2.1")
        with override_settings(AUTH_TRUST_RAILWAY_PROXY=True):
            self.assertEqual(client_network(request), "198.51.100.1")
            request.META["HTTP_X_REAL_IP"] = "198.51.100.1, 203.0.113.1"
            self.assertEqual(client_network(request), "unknown")
        for address in ("::ffff:192.0.2.1", "192.0.2.1"):
            self.assertEqual(client_network(factory.get("/", REMOTE_ADDR=address)), "192.0.2.1")
        self.assertEqual(client_network(factory.get("/", REMOTE_ADDR="2001:db8::123")), client_network(factory.get("/", REMOTE_ADDR="2001:db8::456")))


@override_settings(AUTH_TRUST_RAILWAY_PROXY=False)
class ConcurrentAuthAttemptTests(TransactionTestCase):
    def test_file_database_concurrency_and_process_restart(self):
        # Exercise the production SQLite file/locking mode, not only Django's
        # shared-memory test database. Child processes have independent connections.
        setup_and_run = '''
import django
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.db import connection, close_old_connections
from organizations.models import AuthAttemptBucket
from organizations.auth_limits import consume_budget
with connection.schema_editor() as editor:
    editor.create_model(AuthAttemptBucket)
def attempt(_):
    close_old_connections()
    try:
        return consume_budget("login", "192.0.2.1", "parallel")
    finally:
        close_old_connections()
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(attempt, range(16)))
assert results.count(0) == 5, results
print("concurrency passed")
'''
        retry = '''
import django
django.setup()
from organizations.auth_limits import consume_budget
assert consume_budget("login", "192.0.2.1", "parallel") > 0
print("restart passed")
'''
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings", "DJANGO_DB_PATH": os.path.join(directory, "limits.sqlite3")}
            for source, marker in ((setup_and_run, "concurrency passed"), (retry, "restart passed")):
                result = subprocess.run([sys.executable, "-c", source], env=env, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(marker, result.stdout)

    def test_parallel_connections_do_not_exceed_budget(self):
        # Shared-memory SQLite may return lock errors immediately; they must fail
        # closed with 503, never admit extra authentication or reset mail.
        def attempt(_):
            close_old_connections()
            try:
                return Client().post(reverse("mobile_login"), json.dumps({"username": "parallel", "password": "bad"}), content_type="application/json").status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(attempt, range(12)))
        self.assertTrue(all(status in {401, 429, 503} for status in statuses), statuses)
        self.assertLessEqual(statuses.count(401), 5)
        self.assertGreater(statuses.count(401), 0)
        self.assertFalse(AuthAttemptBucket.objects.filter(count__gt=12).exists())
