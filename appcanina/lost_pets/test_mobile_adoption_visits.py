from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from organizations.models import Organization, OrganizationMembership
from .models import AdoptionInterest, AdoptionPost, MobileAccessToken


class MobileAdoptionVisitTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user("applicant", email="applicant@example.com")
        self.manager = User.objects.create_user("manager")
        self.applicant.user_permissions.add(Permission.objects.get(codename="view_lostpetreport"))
        self.token, self.session = MobileAccessToken.issue(self.applicant, "test")
        self.shelter = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        OrganizationMembership.objects.create(user=self.manager, organization=self.shelter, role="manager")
        self.post = AdoptionPost.objects.create(publisher=self.manager, organization=self.shelter,
                                               name="Mía", species="dog", area_label="Centro", status="published")
        self.interest = AdoptionInterest.objects.create(post=self.post, applicant=self.applicant, message="Quiero conocerla")
        self.url = reverse("mobile_adoption_visit_request", args=[self.interest.pk])
        self.list_url = reverse("mobile_my_adoption_interests")

    def post_visit(self):
        return self.client.post(self.url, HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def activity(self):
        return self.client.get(self.list_url, HTTP_AUTHORIZATION=f"Bearer {self.token}")

    @patch("lost_pets.api.notify_visit", return_value=True)
    def test_request_and_retry_only_send_one_email(self, notify):
        self.assertTrue(self.activity().json()["interests"][0]["can_request_visit"])
        first = self.post_visit()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["interest"]["visit_status"], "requested")
        self.assertFalse(first.json()["interest"]["can_request_visit"])
        self.interest.refresh_from_db()
        requested_at = self.interest.visit_requested_at
        self.assertIsNotNone(self.interest.institution_activity_at)
        self.assertEqual(self.post_visit().status_code, 200)
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_requested_at, requested_at)
        notify.assert_called_once()

    @patch("lost_pets.api.notify_visit", return_value=False)
    def test_mail_failure_keeps_request_and_reports_warning(self, notify):
        response = self.post_visit()
        self.assertEqual(response.status_code, 200)
        self.assertIn("no pudimos enviar el correo", response.json()["detail"])
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "requested")

    @patch("lost_pets.api.notify_visit")
    def test_ineligible_requests_are_rejected(self, notify):
        for field, value in [("status", "closed"), ("status", "completed")]:
            setattr(self.interest, field, value)
            self.interest.save()
            self.assertEqual(self.post_visit().status_code, 409)
        self.interest.status = "received"
        self.interest.save()
        for state in ("pending", "rejected", "adopted", "archived"):
            self.post.status = state
            self.post.save()
            self.assertEqual(self.post_visit().status_code, 409)
        self.post.status = "published"
        self.post.save()
        self.shelter.is_verified = False
        self.shelter.save()
        self.assertEqual(self.post_visit().status_code, 409)
        self.shelter.is_verified = True
        self.shelter.kind = "veterinary"
        self.shelter.save()
        self.assertEqual(self.post_visit().status_code, 409)
        self.post.organization = None
        self.post.save()
        self.assertEqual(self.post_visit().status_code, 409)
        notify.assert_not_called()

    def test_location_is_shared_only_after_acceptance(self):
        self.interest.visit_address = "Dirección privada 123"
        self.interest.visit_instructions = "Sábado a las 10"
        for status in ("none", "requested", "declined", "accepted"):
            self.interest.visit_status = status
            self.interest.save()
            response = self.activity()
            self.assertEqual(response["Cache-Control"], "no-store")
            item = response.json()["interests"][0]
            self.assertEqual(item["visit_address"], self.interest.visit_address if status == "accepted" else "")
            self.assertEqual(item["visit_instructions"], self.interest.visit_instructions if status in ("accepted", "declined") else "")

    @patch("lost_pets.api.notify_visit")
    def test_other_account_cannot_read_or_request_even_if_staff(self, notify):
        self.manager.is_staff = True
        self.manager.save()
        self.manager.user_permissions.add(Permission.objects.get(codename="view_lostpetreport"))
        self.token, _ = MobileAccessToken.issue(self.manager, "outsider")
        self.assertEqual(self.activity().json()["interests"], [])
        self.assertEqual(self.post_visit().status_code, 404)
        notify.assert_not_called()

    def test_authentication_and_http_methods(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)
        self.assertEqual(self.client.get(self.url, HTTP_AUTHORIZATION=f"Bearer {self.token}").status_code, 405)
        self.applicant.user_permissions.clear()
        self.assertEqual(self.post_visit().status_code, 403)

    @patch("lost_pets.api.notify_visit")
    def test_answered_visit_cannot_be_requested_again(self, notify):
        for status in ("accepted", "declined"):
            self.interest.visit_status = status
            self.interest.save()
            self.assertEqual(self.post_visit().json()["interest"]["visit_status"], status)
        notify.assert_not_called()

    @patch("lost_pets.adoption_email.EmailMessage.send", return_value=1)
    @patch("lost_pets.api.notify_visit", return_value=True)
    def test_web_acceptance_is_visible_in_mobile(self, notify, send):
        self.post_visit()
        self.client.force_login(self.manager)
        response = self.client.post(reverse("adoption_visit_respond", args=[self.interest.pk]), {
            "action": "accept", "visit_address": "Calle 123, Avellaneda", "visit_instructions": "Sábado a las 10",
        })
        self.assertEqual(response.status_code, 302)
        item = self.activity().json()["interests"][0]
        self.assertEqual(item["visit_status"], "accepted")
        self.assertEqual(item["visit_address"], "Calle 123, Avellaneda")
        self.assertEqual(item["visit_instructions"], "Sábado a las 10")
