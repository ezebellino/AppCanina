from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from organizations.models import Organization
from .api import _mobile_adoption_data
from .models import AdoptionPost


class ShelterDonationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="donation-owner")
        self.organization = Organization.objects.create(
            name="Refugio Esperanza", kind="shelter", is_verified=True,
            donation_alias="refugio.esperanza", donation_message="Cada aporte suma.",
        )
        self.post = AdoptionPost.objects.create(
            publisher=user, organization=self.organization, name="Mía", species="dog",
            area_label="Centro", status="published",
        )

    def output(self):
        return (
            render_to_string("lost_pets/donation.html", {"post": self.post}),
            _mobile_adoption_data(RequestFactory().get("/"), self.post)["organization"],
        )

    def test_verified_refuge_shows_alias_even_with_custom_message(self):
        html, data = self.output()
        self.assertIn('data-copy-donation="refugio.esperanza"', html)
        self.assertIn("Cada aporte suma.", html)
        self.assertEqual(data["donation_alias"], "refugio.esperanza")
        self.assertEqual(data["donation_message"], "Cada aporte suma.")

    def test_missing_alias_unverified_other_kind_and_unpublished_hide_donations(self):
        for field, value in [("donation_alias", ""), ("is_verified", False), ("kind", "veterinary")]:
            with self.subTest(field=field):
                previous = getattr(self.organization, field)
                setattr(self.organization, field, value)
                html, data = self.output()
                self.assertNotIn("data-copy-donation", html)
                self.assertEqual(data["donation_alias"], "")
                self.assertEqual(data["donation_message"], "")
                setattr(self.organization, field, previous)
        self.post.status = "adopted"
        html, data = self.output()
        self.assertNotIn("data-copy-donation", html)
        self.assertEqual(data["donation_alias"], "")

    def test_alias_and_message_are_escaped_in_web(self):
        self.organization.donation_alias = '\"><script>alert(1)</script>'
        self.organization.donation_message = '<img src=x onerror=alert(1)>'
        html, _ = self.output()
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
