from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from organizations.models import Organization, OrganizationMembership
from .adoption_updates import unread_counts
from .models import AdoptionArchive, AdoptionInterest, AdoptionPost, MobileAccessToken


class AdoptionArchiveTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user("applicant")
        self.manager = User.objects.create_user("manager")
        self.colleague = User.objects.create_user("colleague")
        self.stranger = User.objects.create_user("stranger", is_staff=True)
        self.organization = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        for user in (self.manager, self.colleague):
            OrganizationMembership.objects.create(user=user, organization=self.organization, role="manager")
        permission = Permission.objects.get(codename="view_lostpetreport")
        for user in (self.applicant, self.manager, self.colleague, self.stranger):
            user.user_permissions.add(permission)
        post = AdoptionPost.objects.create(publisher=self.manager, organization=self.organization,
                                           name="Mía", species="dog", status="published")
        self.interest = AdoptionInterest.objects.create(post=post, applicant=self.applicant,
            message="Quiero conocerla", status="completed", staff_note="Encontró familia",
            applicant_activity_at=timezone.now(), visit_status="accepted", visit_address="Calle privada")

    def archive(self, user=None, audience="applicant", action="archive", **extra):
        user = user or self.applicant
        token, _ = MobileAccessToken.issue(user, "test")
        return self.client.post(reverse("mobile_adoption_archive", args=[audience, self.interest.pk]),
            {"action": action, "expected_updated_at": self.interest.updated_at.isoformat(), **extra},
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}")

    def mobile_get(self, user, name, **query):
        token, _ = MobileAccessToken.issue(user, "test")
        return self.client.get(reverse(name), query, HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_archive_restore_and_retries_preserve_shared_history(self):
        original = (self.interest.status, self.interest.updated_at, self.interest.staff_note, self.interest.visit_address)
        self.assertEqual(self.archive().status_code, 200)
        self.assertEqual(self.archive().status_code, 200)
        self.assertEqual(AdoptionArchive.objects.count(), 1)
        self.assertEqual(self.mobile_get(self.applicant, "mobile_my_adoption_interests").json()["interests"], [])
        archived = self.mobile_get(self.applicant, "mobile_my_adoption_interests", view="archived").json()
        self.assertEqual(archived["counts"], {"all": 0, "archived": 1})
        self.assertTrue(archived["interests"][0]["is_archived"])
        self.assertEqual(self.archive(action="restore").status_code, 200)
        self.assertEqual(self.archive(action="restore").status_code, 200)
        self.assertEqual(len(self.mobile_get(self.applicant, "mobile_my_adoption_interests").json()["interests"]), 1)
        self.interest.refresh_from_db()
        self.assertEqual(original, (self.interest.status, self.interest.updated_at, self.interest.staff_note, self.interest.visit_address))

    def test_archive_is_private_to_user_and_audience(self):
        self.assertEqual(self.archive(self.manager, "institution").status_code, 200)
        self.assertEqual(self.mobile_get(self.manager, "mobile_adoption_inbox").json()["interests"], [])
        self.assertEqual(len(self.mobile_get(self.colleague, "mobile_adoption_inbox").json()["interests"]), 1)
        self.assertEqual(len(self.mobile_get(self.applicant, "mobile_my_adoption_interests").json()["interests"]), 1)
        self.assertEqual(self.mobile_get(self.manager, "mobile_adoption_inbox", view="archived").json()["counts"]["archived"], 1)

    def test_only_terminal_states_and_current_version_can_be_archived(self):
        for state in ("received", "contact", "interview"):
            self.interest.status = state
            self.interest.save()
            self.assertEqual(self.archive().status_code, 409)
        self.interest.status = "closed"
        self.interest.save()
        self.assertEqual(self.archive(expected_updated_at="old").status_code, 409)
        self.assertEqual(self.archive(action="delete").status_code, 400)
        self.assertEqual(self.archive().status_code, 200)

    def test_strangers_staff_and_revoked_managers_cannot_archive_or_restore(self):
        for audience in ("applicant", "institution", "invalid"):
            self.assertEqual(self.archive(self.stranger, audience).status_code, 404)
        self.archive(self.manager, "institution")
        self.organization.is_verified = False
        self.organization.save()
        self.assertEqual(self.archive(self.manager, "institution", "restore").status_code, 404)

    def test_new_response_and_reopening_automatically_return_to_inbox(self):
        self.archive()
        self.interest.staff_note = "Nueva indicación"
        self.interest.applicant_activity_at = timezone.now()
        self.interest.save()
        data = self.mobile_get(self.applicant, "mobile_my_adoption_interests").json()
        self.assertFalse(data["interests"][0]["is_archived"])
        self.assertEqual(data["counts"]["archived"], 0)
        self.assertEqual(unread_counts(self.applicant)["applicant_unread_count"], 1)
        self.archive()
        AdoptionInterest.objects.filter(pk=self.interest.pk).update(status="contact")
        self.assertEqual(len(self.mobile_get(self.applicant, "mobile_my_adoption_interests").json()["interests"]), 1)

    def test_archived_notifications_disappear_only_for_archiving_user(self):
        self.assertEqual(unread_counts(self.applicant)["applicant_unread_count"], 1)
        self.archive()
        self.assertEqual(unread_counts(self.applicant)["applicant_unread_count"], 0)
        self.assertEqual(unread_counts(self.manager)["institution_unread_count"], 1)
        data = self.mobile_get(self.applicant, "mobile_updates").json()
        self.assertEqual(data["notifications"], [])
        self.assertEqual(data["unread_count"], 0)

    def test_web_archive_buttons_filter_restore_and_csrf(self):
        self.client.force_login(self.applicant)
        url = reverse("adoption_archive", args=["applicant", self.interest.pk])
        self.assertContains(self.client.get(reverse("my_adoption_interests")), "Archivar solicitud")
        self.assertEqual(self.client.get(url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.applicant)
        self.assertEqual(csrf_client.post(url, {"action": "archive"}).status_code, 403)
        data = {"action": "archive", "expected_updated_at": self.interest.updated_at.isoformat()}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertNotContains(self.client.get(reverse("my_adoption_interests")), "Encontró familia")
        self.assertContains(self.client.get(reverse("my_adoption_interests"), {"view": "archived"}), "Restaurar en mi bandeja")
        self.assertEqual(self.client.post(url, {**data, "action": "restore"}).status_code, 302)
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse("adoption_interest_list")), "Archivar solicitud")

    def test_archiving_does_not_discard_an_update_racing_with_it(self):
        from unittest.mock import patch
        from .adoption_archives import set_archive, with_archive_state
        original = AdoptionArchive.objects.update_or_create
        def racing_archive(*args, **kwargs):
            AdoptionInterest.objects.filter(pk=self.interest.pk).update(updated_at=timezone.now(), staff_note="Respuesta nueva")
            return original(*args, **kwargs)
        with patch.object(AdoptionArchive.objects, "update_or_create", side_effect=racing_archive):
            set_archive(AdoptionInterest.objects.all(), self.applicant, "applicant", self.interest.pk,
                        "archive", self.interest.updated_at.isoformat())
        self.assertFalse(with_archive_state(AdoptionInterest.objects.all(), self.applicant, "applicant").get().is_archived)

    def test_web_json_confirmation_only_after_archive_and_no_redirect_on_conflict(self):
        self.client.force_login(self.applicant)
        url = reverse("adoption_archive", args=["applicant", self.interest.pk])
        response = self.client.post(url, {"action": "archive", "expected_updated_at": "stale"}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("redirect_url", response.json())
        self.assertEqual(AdoptionArchive.objects.count(), 0)
        response = self.client.post(url, {"action": "archive", "expected_updated_at": self.interest.updated_at.isoformat()}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect_url"], reverse("my_adoption_interests"))
        self.assertEqual(AdoptionArchive.objects.count(), 1)
