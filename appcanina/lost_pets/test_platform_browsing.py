from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organizations.roles import ensure_base_roles
from .models import LostPetReport


class PlatformLostReportBrowsingTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user("platform-only", is_staff=True)
        self.report = LostPetReport.objects.create(
            reporter=self.staff, name="Visible", species="dog",
            last_seen_at=timezone.now(), area_label="Centro",
            latitude="-34.603722", longitude="-58.381592",
        )
        self.hidden = LostPetReport.objects.create(
            reporter=self.staff, name="Pendiente", species="cat",
            last_seen_at=timezone.now(), area_label="Norte",
            status="hidden", requested_via_mobile=True,
        )
        self.urls = [
            reverse("lost_pet_list"), reverse("lost_pet_detail", args=[self.report.pk]),
            reverse("lost_pet_map"), reverse("lost_pet_map_data"),
        ]

    def test_staff_without_groups_can_follow_list_detail_and_map(self):
        self.client.force_login(self.staff)
        for url in self.urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(reverse("lost_pet_map_data"))
        markers = response.json()["markers"]
        self.assertEqual([m["id"] for m in markers], [self.report.pk])
        self.assertNotEqual(markers[0]["public_latitude"], float(self.report.latitude))
        self.assertNotEqual(markers[0]["public_longitude"], float(self.report.longitude))
        for mode in ("active", "resolved", "all", "requests"):
            self.assertEqual(self.client.get(reverse("lost_pet_list"), {"view": mode}).status_code, 200)
        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[self.hidden.pk])).status_code, 200)

    def test_staff_read_access_does_not_grant_writes(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("lost_pet_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("sighting_create", args=[self.report.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("lost_pet_change_status", args=[self.report.pk]), {"status": "resolved"}).status_code, 403)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "published")

    def test_anonymous_and_unprivileged_users_remain_denied(self):
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        other = get_user_model().objects.create_user("no-permission")
        self.client.force_login(other)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_collaborator_still_cannot_read_hidden_reports(self):
        user = get_user_model().objects.create_user("community-reader")
        user.groups.add(ensure_base_roles()["collaborator"])
        self.client.force_login(user)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[self.hidden.pk])).status_code, 404)
        response = self.client.get(reverse("lost_pet_list"), {"view": "all"})
        self.assertEqual(list(response.context["reports"]), [self.report])
