import json
import tempfile
import time
from urllib.parse import urlsplit
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from organizations.roles import ensure_base_roles
from .models import CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, Sighting
from .notifications import notify_new_report, notify_new_sighting, notify_request_review
from .push import send_expo_push


class HiddenVisibilityTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.owner = User.objects.create_user("report-owner")
        self.reader = User.objects.create_user("community-reader")
        self.reader.groups.add(ensure_base_roles()["collaborator"])
        self.owner.groups.add(ensure_base_roles()["collaborator"])
        self.staff = User.objects.create_user("reviewer", is_staff=True)
        self.report = LostPetReport.objects.create(reporter=self.owner, name="Public animal", species="dog", area_label="Public area", last_seen_at=timezone.now(), requested_via_mobile=True)
        self.report.photo.save("animal.jpg", ContentFile(b"report-photo"))
        self.visible = Sighting.objects.create(report=self.report, reporter=self.owner, area_label="Public sighting", description="Public description", latitude="-34.6", longitude="-58.3")
        self.hidden = Sighting.objects.create(report=self.report, reporter=self.owner, area_label="PRIVATE AREA", description="PRIVATE DESCRIPTION", status="hidden", latitude="-34.7", longitude="-58.4")
        self.hidden.photo.save("hidden.jpg", ContentFile(b"hidden-photo"))
        self.raw, self.session = MobileAccessToken.issue(self.reader, "test")
        self.owner_raw, _ = MobileAccessToken.issue(self.owner, "owner")
        self.client.force_login(self.reader)

    def notifications(self, token=None):
        return self.client.get(reverse("mobile_notifications"), HTTP_AUTHORIZATION=f"Bearer {token or self.raw}")

    def notification(self, sighting=None, recipient=None, **kwargs):
        return CommunityNotification.objects.create(recipient=recipient or self.reader, report=self.report, sighting=sighting, title="notice", body="notice body", **kwargs)

    def test_detail_counts_and_latest_hide_private_sightings(self):
        response = self.client.get(reverse("lost_pet_detail", args=[self.report.pk]))
        self.assertEqual(list(response.context["sightings"]), [self.visible])
        self.assertNotContains(response, "PRIVATE")
        self.assertNotContains(response, self.hidden.photo.url)
        response = self.client.get(reverse("lost_pet_list"))
        self.assertEqual(response.context["reports"][0].sightings.count(), 1)
        self.assertEqual(response.context["latest_sighting"], self.visible)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("lost_pet_detail", args=[self.report.pk]))
        self.assertContains(response, "PRIVATE DESCRIPTION")

    def test_hidden_reports_are_not_revealed_by_latest_counts_or_direct_urls(self):
        for status in ("hidden", "rejected", "archived"):
            self.report.status = status
            self.report.save()
            response = self.client.get(reverse("lost_pet_list"), {"view": "all"})
            self.assertNotContains(response, self.report.name)
            self.assertIsNone(response.context["latest_sighting"])
            self.assertEqual(response.context["pending_request_count"], 0)
            self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[self.report.pk])).status_code, 404)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[self.report.pk])).status_code, 200)

    def test_read_permission_alone_does_not_grant_moderation(self):
        reader = User.objects.create_user("read-only")
        reader.user_permissions.add(Permission.objects.get(codename="view_lostpetreport"))
        self.client.force_login(reader)
        self.assertNotContains(self.client.get(reverse("lost_pet_detail", args=[self.report.pk])), "PRIVATE DESCRIPTION")
        self.report.status = "hidden"
        self.report.save()
        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[self.report.pk])).status_code, 404)

    def test_map_uses_published_sighting_and_does_not_leak_exact_coordinates(self):
        response = self.client.get(reverse("lost_pet_map_data"))
        marker = response.json()["markers"][0]
        self.assertEqual(marker["area"], "Public sighting")
        self.assertNotEqual(marker["public_latitude"], float(self.visible.latitude))
        self.report.status = "hidden"
        self.report.save()
        self.assertEqual(self.client.get(reverse("lost_pet_map_data")).json()["markers"], [])

    def test_notification_filter_precedes_limit_and_rechecks_hide(self):
        good = self.notification(self.visible)
        for _ in range(31):
            self.notification(self.hidden)
        data = self.notifications().json()["notifications"]
        self.assertEqual([item["id"] for item in data], [good.pk])
        self.visible.status = "hidden"
        self.visible.save()
        self.assertEqual(self.notifications().json()["notifications"], [])
        self.visible.status = "published"
        self.visible.save()
        self.report.status = "hidden"
        self.report.save()
        self.assertEqual(self.notifications().json()["notifications"], [])

    def test_private_review_reply_reaches_only_owner_not_hidden_sightings(self):
        self.report.status = "rejected"
        self.report.review_note = "Please correct the request"
        self.report.save()
        notify_request_review(self.report)
        self.notification(self.hidden, recipient=self.owner)
        self.notification(recipient=self.reader)
        items = self.notifications(self.owner_raw).json()["notifications"]
        self.assertEqual(len(items), 1)
        self.assertIn("rechazada", items[0]["title"])
        self.assertEqual(self.notifications().json()["notifications"], [])

    def test_generation_and_push_recheck_database_not_stale_objects(self):
        note = self.notification(self.visible)
        MobilePushDevice.objects.create(user=self.reader, token="ExponentPushToken[test]", platform="android", access_token=self.session)
        with patch("lost_pets.push.urlopen") as send:
            send_expo_push([note])
            from .push import process_push_batch
            process_push_batch()
            send.assert_called_once()
            send.reset_mock()
            Sighting.objects.filter(pk=self.visible.pk).update(status="hidden")
            send_expo_push([note])
            send.assert_not_called()
        count = CommunityNotification.objects.count()
        notify_new_sighting(self.report, self.visible)
        self.assertEqual(CommunityNotification.objects.count(), count)
        LostPetReport.objects.filter(pk=self.report.pk).update(status="hidden")
        notify_new_report(self.report)
        self.assertEqual(CommunityNotification.objects.count(), count)

    def test_private_rejection_push_is_preserved(self):
        raw, session = MobileAccessToken.issue(self.owner, "owner push")
        MobilePushDevice.objects.create(user=self.owner, token="ExponentPushToken[owner]", platform="android", access_token=session)
        self.report.status = "rejected"
        self.report.save()
        with patch("lost_pets.push.urlopen") as send:
            notify_request_review(self.report)
            from .push import process_push_batch
            process_push_batch()
            send.assert_called_once()
            payload = json.loads(send.call_args.args[0].data)
            self.assertIn("rechazada", payload[0]["title"])

    def test_known_photo_urls_are_protected_after_hiding_even_with_path_alias(self):
        self.client.logout()
        response = self.client.get(self.report.photo.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        response.close()
        self.assertEqual(self.client.get(self.hidden.photo.url).status_code, 404)
        self.assertEqual(self.client.get(self.hidden.photo.url.replace("lost-pets/", "LOST-PETS/")).status_code, 404)
        self.assertEqual(self.client.get(self.hidden.photo.url.replace("lost-pets/", "lost-pets./")).status_code, 404)
        self.assertEqual(self.client.get(self.hidden.photo.url.replace("lost-pets/", "lost-pets%20/")).status_code, 404)
        self.report.status = "hidden"
        self.report.save()
        self.assertEqual(self.client.get(self.report.photo.url).status_code, 404)
        self.assertEqual(self.client.get("/media/other/../" + self.report.photo.name).status_code, 404)
        self.client.force_login(self.staff)
        response = self.client.get(self.hidden.photo.url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_owner_preview_links_are_scoped_short_lived_and_revoked_with_session(self):
        self.report.status = "hidden"
        self.report.save()
        response = self.client.get(reverse("mobile_my_search_requests"), HTTP_AUTHORIZATION=f"Bearer {self.owner_raw}")
        url = response.json()["requests"][0]["photo_url"]
        self.assertNotIn(self.owner_raw, url)
        parts = urlsplit(url)
        path = parts.path + "?" + parts.query
        self.client.logout()
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.get(self.hidden.photo.url + "?" + parts.query).status_code, 404)
        with patch("django.core.signing.time.time", return_value=time.time() + 301):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.client.post(reverse("mobile_logout"), HTTP_AUTHORIZATION=f"Bearer {self.owner_raw}")
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_resolved_reports_remain_in_mobile_history(self):
        self.report.status = "resolved"
        self.report.save()
        response = self.client.get(reverse("mobile_reports"), {"estado": "encontrados"}, HTTP_AUTHORIZATION=f"Bearer {self.raw}")
        self.assertEqual([item["id"] for item in response.json()["reports"]], [self.report.pk])

    def test_unrelated_media_and_public_sighting_photos_remain_available(self):
        path = default_storage.save("organizations/logos/control.png", ContentFile(b"logo"))
        self.client.logout()
        response = self.client.get("/media/" + path)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.visible.photo.save("public.jpg", ContentFile(b"public photo"))
        response = self.client.get(self.visible.photo.url)
        self.assertEqual(response.status_code, 200)
        response.close()
