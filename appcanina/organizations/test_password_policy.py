from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .forms import CommunityCollaboratorForm
from .setup_forms import InitialSetupForm


class PasswordPolicyTests(TestCase):
    weak = ("xY!2", "password", "867530919284", "policy-reader")

    def setUp(self):
        cache.clear()

    def test_user_creation_forms_reject_each_weak_class(self):
        for password in self.weak:
            with self.subTest(password_class=self.weak.index(password)):
                data = {"username": "policy-reader", "email": "policy@example.test", "password1": password, "password2": password}
                self.assertFalse(CommunityCollaboratorForm(data).is_valid())
                self.assertFalse(InitialSetupForm(dict(data, business_name="Example", business_kind="veterinary")).is_valid())
        self.assertFalse(User.objects.exists())

    def test_public_registration_and_mobile_reject_weak_password_without_creating_accounts(self):
        for password in self.weak:
            data = {"username": "policy-reader", "email": "policy@example.test", "password1": password, "password2": password, "account_type": "community"}
            response = self.client.post(reverse("register"), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            response = self.client.post(reverse("mobile_register"), {"username": "policy-reader", "email": "policy@example.test", "password": password, "password_confirmation": password}, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_bootstrap_endpoint_rejects_weak_password(self):
        response = self.client.post(reverse("initial_setup"), {"username": "policy-reader", "business_name": "Example", "business_kind": "veterinary", "password1": "password", "password2": "password"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("password1", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_reset_rejects_weak_password_preserves_old_hash_and_accepts_valid_password(self):
        user = User.objects.create_user("policy-reader", password="Existing!381-Secret", email="policy@example.test")
        old_hash = user.password
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = self.client.get(reverse("password_reset_confirm", args=[uid, token])).url
        for password in self.weak:
            response = self.client.post(reset_url, {"new_password1": password, "new_password2": password})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            user.refresh_from_db()
            self.assertEqual(user.password, old_hash)
        password = "Faro!Colina-Verde-592"
        self.assertEqual(self.client.post(reset_url, {"new_password1": password, "new_password2": password}).status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password(password))

    def test_valid_passwords_preserve_spaces_and_are_accepted_in_bootstrap_and_registration(self):
        password = "  Faro!Colina-Verde-592  "
        data = {"username": "policy-reader", "password1": password, "password2": password, "email": "policy@example.test"}
        setup = InitialSetupForm(dict(data, business_name="Example", business_kind="veterinary"))
        self.assertTrue(setup.is_valid(), setup.errors)
        self.assertEqual(setup.cleaned_data["password1"], password)
        form = CommunityCollaboratorForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.check_password(password.strip()))

    def test_existing_passwords_still_allow_login(self):
        user = User.objects.create_user("legacy-reader", password="short")
        self.assertEqual(authenticate(username=user.username, password="short"), user)
