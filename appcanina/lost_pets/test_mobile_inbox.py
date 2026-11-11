import json
from unittest.mock import patch
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from organizations.models import Organization, OrganizationMembership
from .models import AdoptionInterest, AdoptionPost, MobileAccessToken


class MobileInboxTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("manager")
        self.applicant = User.objects.create_user("applicant")
        self.manager.user_permissions.add(Permission.objects.get(codename="view_lostpetreport"))
        self.token, _ = MobileAccessToken.issue(self.manager, "test")
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.shelter = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        self.membership = OrganizationMembership.objects.create(user=self.manager, organization=self.shelter, role="manager")
        self.post = AdoptionPost.objects.create(publisher=self.manager, organization=self.shelter,
                                               name="Mía", species="dog", area_label="Centro", status="published")
        self.interest = AdoptionInterest.objects.create(post=self.post, applicant=self.applicant,
                                                       message="Mensaje privado", visit_status="requested")
        self.url = reverse("mobile_adoption_inbox")
        self.update_url = reverse("mobile_adoption_inbox_update", args=[self.interest.pk])

    def update(self, **data):
        payload = {"expected_updated_at": self.interest.updated_at.isoformat(), **data}
        return self.client.post(self.update_url, payload, content_type="application/json", **self.headers)

    def test_scoped_list_counts_filters_and_pagination(self):
        other = Organization.objects.create(name="Otro", kind="shelter", is_verified=True)
        post = AdoptionPost.objects.create(publisher=self.manager, organization=other, name="Otro animal", species="cat")
        AdoptionInterest.objects.create(post=post, applicant=self.applicant, message="Invisible")
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response.json()["counts"], {"all": 1, "received": 1, "visits": 1})
        self.assertEqual(response.json()["interests"][0]["applicant_name"], "applicant")
        self.assertNotIn("email", response.json()["interests"][0])
        for number in range(20):
            user = User.objects.create_user(f"applicant-{number}")
            AdoptionInterest.objects.create(post=self.post, applicant=user, status="closed", message="Closed")
        self.assertTrue(self.client.get(self.url, **self.headers).json()["has_next"])
        self.assertEqual(len(self.client.get(self.url, {"page": 2}, **self.headers).json()["interests"]), 1)
        for view in ("visits", "received"):
            self.assertEqual(len(self.client.get(self.url, {"view": view}, **self.headers).json()["interests"]), 1)
        for params in ({"page": "bad"}, {"page": 0}, {"view": "bad"}):
            self.assertEqual(self.client.get(self.url, params, **self.headers).status_code, 400)

    def test_staff_without_membership_cannot_access(self):
        self.membership.delete()
        self.manager.is_staff = True
        self.manager.save()
        self.assertEqual(self.client.get(self.url, **self.headers).status_code, 403)
        self.assertEqual(self.update(action="status", status="contact").status_code, 404)

    def test_revocation_and_verification_checked_on_every_operation(self):
        self.assertEqual(self.client.get(self.url, **self.headers).status_code, 200)
        self.shelter.is_verified = False
        self.shelter.save()
        self.assertEqual(self.client.get(self.url, **self.headers).status_code, 403)
        self.assertEqual(self.update(action="accept", visit_address="Calle 123").status_code, 404)
        self.shelter.is_verified = True
        self.shelter.save()
        self.membership.role = "member"
        self.membership.save()
        self.assertEqual(self.client.get(self.url, **self.headers).status_code, 403)
        self.assertEqual(self.update(action="decline").status_code, 404)

    @patch("lost_pets.mobile_inbox.notify_visit", return_value=True)
    def test_accept_visible_to_applicant_and_retry_does_not_email_again(self, notify):
        result = self.update(action="accept", visit_address="Calle 123, Ciudad", visit_instructions="Sábado a las 10")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["interest"]["visit_status"], "accepted")
        self.assertEqual(self.update(action="accept", visit_address="Otra dirección").status_code, 409)
        notify.assert_called_once()
        self.applicant.user_permissions.add(Permission.objects.get(codename="view_lostpetreport"))
        token, _ = MobileAccessToken.issue(self.applicant, "reader")
        data = self.client.get(reverse("mobile_my_adoption_interests"), HTTP_AUTHORIZATION=f"Bearer {token}").json()
        self.assertFalse(data["can_manage_adoption_requests"])
        self.assertEqual(data["interests"][0]["visit_address"], "Calle 123, Ciudad")
        self.assertEqual(data["interests"][0]["visit_instructions"], "Sábado a las 10")

    @patch("lost_pets.mobile_inbox.notify_visit", return_value=False)
    def test_decline_persists_on_mail_failure_and_clears_location(self, notify):
        response = self.update(action="decline", visit_address="Not shared", visit_instructions="No podemos este día")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no pudimos enviar el correo", response.json()["detail"])
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "declined")
        self.assertEqual(self.interest.visit_address, "")

    @patch("lost_pets.mobile_inbox.notify_visit")
    def test_status_updates_are_private_and_detect_stale_changes(self, notify):
        result = self.update(action="status", status="interview", staff_note="Coordinamos pronto")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.update(action="status", status="closed").status_code, 409)
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.status, "interview")
        self.assertIsNotNone(self.interest.applicant_activity_at)
        self.assertEqual(self.interest.staff_note, "Coordinamos pronto")
        notify.assert_not_called()
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, "published")

    @patch("lost_pets.mobile_inbox.notify_visit")
    def test_validation_and_unavailable_adoption(self, notify):
        for data in ({"action": "accept"}, {"action": "invalid"}, {"action": "status", "status": []},
                     {"action": "status", "status": "closed", "staff_note": "a" * 281},
                     {"action": "accept", "visit_address": 12}, {"action": "decline", "visit_instructions": "a" * 281}):
            self.assertEqual(self.update(**data).status_code, 400)
        self.post.status = "archived"
        self.post.save()
        self.assertEqual(self.update(action="accept", visit_address="Calle 123").status_code, 400)
        for body in ([], None, "invalid"):
            self.assertEqual(self.client.post(self.update_url, json.dumps(body), content_type="application/json", **self.headers).status_code, 400)
        notify.assert_not_called()

    def test_auth_and_other_shelter_interest(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.get(self.update_url, **self.headers).status_code, 405)
        other = Organization.objects.create(name="Other", kind="shelter", is_verified=True)
        self.post.organization = other
        self.post.save()
        self.assertEqual(self.update(action="status", status="closed").status_code, 404)
        self.assertEqual(self.client.get(self.url, **self.headers).json()["interests"], [])
