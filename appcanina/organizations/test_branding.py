from django.contrib.auth.models import User
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from config.public_urls import public_url


@override_settings(PUBLIC_BASE_URL="https://lazuna.up.railway.app", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PublicBrandingTests(TestCase):
    def test_links_use_new_origin_even_from_legacy_host(self):
        request = RequestFactory().get("/", HTTP_HOST="testserver")
        self.assertEqual(public_url(request, "/mis-animales/"), "https://lazuna.up.railway.app/mis-animales/")
        with override_settings(PUBLIC_BASE_URL=""):
            self.assertEqual(public_url(request, "/mis-animales/"), "http://testserver/mis-animales/")

    def test_login_shows_lazuna(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Lazuna")
        self.assertNotContains(response, "Tu Veterinaria")
        self.assertNotContains(response, "AppCanina")

    def test_password_reset_uses_canonical_domain(self):
        from django.contrib.auth.views import PasswordResetView
        User.objects.create_user("reset-family", email="family@example.test", password="A-valid-password-432")
        request = RequestFactory().post("/cuenta/recuperar/", {"email": "family@example.test"})
        request._dont_enforce_csrf_checks = True
        response = PasswordResetView.as_view(
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            extra_email_context={"app_name": "Lazuna", "public_base_url": "https://lazuna.up.railway.app"},
        )(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Lazuna", mail.outbox[0].subject)
        self.assertIn("https://lazuna.up.railway.app/cuenta/restablecer/", mail.outbox[0].body)
        self.assertNotIn("testserver", mail.outbox[0].body)
