from datetime import timedelta
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from organizations.models import Organization, OrganizationMembership
from .models import AdoptionInterest, AdoptionPost, AdoptionReadReceipt, CommunityNotification, LostPetReport, MobileAccessToken, Sighting


class MobileUpdatesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reader")
        self.other = User.objects.create_user("other")
        self.user.user_permissions.add(Permission.objects.get(codename="view_lostpetreport"))
        token, self.session = MobileAccessToken.issue(self.user, "test")
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        self.report = LostPetReport.objects.create(reporter=self.other, name="Luna", species="dog", last_seen_at=timezone.now(), area_label="Centro")
        self.notification = CommunityNotification.objects.create(recipient=self.user, report=self.report, title="Aviso", body="Zona")
        self.key = f"community-{self.notification.pk}"
        self.url = reverse("mobile_updates")

    def feed(self, **params):
        return self.client.get(self.url, params, **self.headers)

    def detail(self, key):
        return self.client.get(reverse("mobile_update_detail", args=[key]), **self.headers)

    def read(self, key, timestamp):
        return self.client.post(reverse("mobile_update_read", args=[key]), {"activity_at": timestamp}, content_type="application/json", **self.headers)

    def adoption(self):
        shelter = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        self.membership = OrganizationMembership.objects.create(user=self.user, organization=shelter, role="manager")
        post = AdoptionPost.objects.create(publisher=self.other, organization=shelter, name="Mía", species="dog", status="published")
        return AdoptionInterest.objects.create(post=post, applicant=self.user, message="Quiero conocerla", applicant_activity_at=timezone.now())

    def test_read_persists_and_list_does_not_mark_read(self):
        self.assertEqual(self.feed().json()["unread_count"], 1)
        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.read_at)
        detail = self.detail(self.key)
        self.assertEqual(detail["Cache-Control"], "no-store")
        self.assertEqual(detail.json()["target"], "report")
        for _ in range(2):
            self.assertEqual(self.read(self.key, detail.json()["activity_at"]).status_code, 200)
        self.assertEqual(self.feed(filter="unread").json()["notifications"], [])
        self.assertFalse(self.feed().json()["notifications"][0]["unread"])
        self.assertEqual(self.feed(count_only="1").json(), {"unread_count": 0})

    def test_ownership_hidden_sightings_and_hidden_reports(self):
        foreign = CommunityNotification.objects.create(recipient=self.other, report=self.report, title="Private")
        self.assertEqual(self.detail(f"community-{foreign.pk}").status_code, 404)
        self.assertEqual(self.read(f"community-{foreign.pk}", foreign.created_at.isoformat()).status_code, 404)
        sighting = Sighting.objects.create(report=self.report, reporter=self.other, area_label="Hidden", status="hidden")
        CommunityNotification.objects.create(recipient=self.user, report=self.report, sighting=sighting, title="Hidden")
        self.assertEqual(self.feed().json()["unread_count"], 1)
        self.report.status = "hidden"
        self.report.save()
        self.assertEqual(self.feed().json()["unread_count"], 0)
        self.assertEqual(self.detail(self.key).status_code, 404)
        self.assertEqual(self.read(self.key, self.notification.created_at.isoformat()).status_code, 404)

    def test_private_review_opens_own_request(self):
        self.report.reporter = self.user
        self.report.requested_via_mobile = True
        self.report.status = "rejected"
        self.report.review_note = "Falta una foto"
        self.report.save()
        data = self.detail(self.key).json()
        self.assertEqual(data["target"], "search_request")
        self.assertEqual(data["request"]["review_note"], "Falta una foto")

    def test_adoption_audiences_are_independent_and_revalidate_membership(self):
        interest = self.adoption()
        applicant = f"applicant-{interest.pk}"
        institution = f"institution-{interest.pk}"
        self.assertEqual(self.feed().json()["unread_count"], 3)
        self.assertEqual(self.detail(applicant).json()["target"], "adoption")
        self.assertEqual(self.detail(institution).json()["target"], "institution")
        self.read(applicant, interest.applicant_activity_at.isoformat())
        self.assertEqual(self.feed().json()["unread_count"], 2)
        self.membership.delete()
        self.assertEqual(self.detail(institution).status_code, 404)
        self.assertEqual(self.read(institution, interest.institution_activity_at.isoformat()).status_code, 404)
        self.assertEqual(self.feed().json()["unread_count"], 1)

    def test_new_activity_is_not_marked_by_an_old_read(self):
        interest = self.adoption()
        key = f"applicant-{interest.pk}"
        old = interest.applicant_activity_at
        interest.applicant_activity_at = old + timedelta(seconds=1)
        interest.save()
        self.assertEqual(self.read(key, old.isoformat()).status_code, 200)
        item = next(item for item in self.feed().json()["notifications"] if item["key"] == key)
        self.assertTrue(item["unread"])
        self.read(key, interest.applicant_activity_at.isoformat())
        self.read(key, old.isoformat())
        self.assertEqual(AdoptionReadReceipt.objects.get(interest=interest, user=self.user, audience="applicant").seen_at, interest.applicant_activity_at)

    def test_pagination_with_tied_dates_has_no_duplicates(self):
        for _ in range(44):
            CommunityNotification.objects.create(recipient=self.user, report=self.report, title="Aviso")
        CommunityNotification.objects.update(created_at=self.notification.created_at)
        keys = []
        for page in (1, 2, 3):
            data = self.feed(page=page).json()
            keys.extend(item["key"] for item in data["notifications"])
            self.assertEqual(data["has_next"], page < 3)
        self.assertEqual(len(keys), 45)
        self.assertEqual(len(set(keys)), 45)

    def test_bad_read_and_revoked_session(self):
        for value in ("bad", "2020-01-01T12:00:00", (timezone.now() + timedelta(days=1)).isoformat()):
            self.assertEqual(self.read(self.key, value).status_code, 400)
        self.assertEqual(self.feed(page="bad").status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.session.revoked_at = timezone.now()
        self.session.save()
        self.assertEqual(self.feed().status_code, 401)

    def test_other_applicant_and_unverified_refuge_excluded(self):
        interest = self.adoption()
        interest.applicant = self.other
        interest.save()
        self.assertEqual(self.detail(f"applicant-{interest.pk}").status_code, 404)
        shelter = interest.post.organization
        shelter.is_verified = False
        shelter.save()
        self.assertEqual(self.detail(f"institution-{interest.pk}").status_code, 404)
        self.assertEqual(self.feed().json()["unread_count"], 1)

    def test_sighting_on_own_mobile_request_opens_public_detail(self):
        self.report.reporter = self.user
        self.report.requested_via_mobile = True
        self.report.save()
        sighting = Sighting.objects.create(report=self.report, reporter=self.other, area_label="Plaza")
        notice = CommunityNotification.objects.create(recipient=self.user, report=self.report, sighting=sighting, title="Avistamiento")
        data = self.detail(f"community-{notice.pk}").json()
        self.assertEqual(data["target"], "report")
        self.assertEqual(data["report_id"], self.report.pk)
