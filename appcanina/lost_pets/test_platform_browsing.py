from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from unittest.mock import patch
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

    def test_staff_has_moderation_without_superuser_and_no_publish_shortcuts(self):
        self.client.force_login(self.staff)
        self.assertFalse(self.staff.is_superuser)
        self.assertFalse(self.staff.has_perm("lost_pets.change_lostpetreport"))
        for name in ("personal_profile", "platform_dashboard", "lost_pet_list", "my_search_requests"):
            page = self.client.get(reverse(name))
            self.assertEqual(page.status_code, 200)
            self.assertNotContains(page, 'href="' + reverse("lost_pet_create") + '"')
            self.assertContains(page, "Revisar búsquedas")
        page = self.client.get(reverse("lost_pet_list"), {"view": "requests"})
        self.assertEqual(list(page.context["reports"]), [self.hidden])
        self.assertContains(page, "Solicitudes (1)")
        self.assertContains(self.client.get(reverse("lost_pet_detail", args=[self.hidden.pk])), "Aceptar y publicar")
        action = reverse("lost_pet_change_status", args=[self.hidden.pk])
        self.assertEqual(self.client.get(action).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        self.assertEqual(csrf_client.post(action, {"status": "published"}).status_code, 403)
        with patch("lost_pets.views.notify_new_report") as published, patch("lost_pets.views.notify_request_review") as reviewed:
            self.assertEqual(self.client.post(action, {"status": "rejected"}).status_code, 302)
            self.hidden.refresh_from_db()
            self.assertEqual(self.hidden.status, "hidden")
            reviewed.assert_not_called()
            self.client.post(action, {"status": "rejected", "review_note": "Confirmar zona"})
            self.hidden.refresh_from_db()
            self.assertEqual(self.hidden.status, "rejected")
            self.assertEqual(self.hidden.review_note, "Confirmar zona")
            self.client.post(action, {"status": "published"})
            self.hidden.refresh_from_db()
            self.assertEqual(self.hidden.status, "published")
            self.assertEqual(self.hidden.review_note, "")
            published.assert_called_once()
            self.assertEqual(reviewed.call_count, 2)
        self.assertEqual(self.client.get(reverse("sighting_create", args=[self.report.pk])).status_code, 403)

    def test_collaborator_cannot_moderate_even_own_request(self):
        user = get_user_model().objects.create_user("request-owner")
        user.groups.add(ensure_base_roles()["collaborator"])
        self.hidden.reporter = user
        self.hidden.save()
        action = reverse("lost_pet_change_status", args=[self.hidden.pk])
        self.assertEqual(self.client.post(action, {"status": "published"}).status_code, 302)
        self.client.force_login(user)
        self.assertEqual(self.client.post(action, {"status": "published"}).status_code, 403)
        self.hidden.refresh_from_db()
        self.assertEqual(self.hidden.status, "hidden")

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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_approval_notification_is_visible_to_owner_on_web_and_read_is_private(self):
        from .models import CommunityNotification
        from django.core import mail
        owner = get_user_model().objects.create_user("search-owner", email="owner@example.com")
        owner.groups.add(ensure_base_roles()["collaborator"])
        self.hidden.reporter = owner
        self.hidden.save()
        self.client.force_login(self.staff)
        with patch("lost_pets.notifications.send_expo_push"):
            self.client.post(reverse("lost_pet_change_status", args=[self.hidden.pk]), {"status": "published"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("ya está publicada", mail.outbox[0].subject)
        self.assertIn(reverse("my_search_requests"), mail.outbox[0].body)
        self.client.post(reverse("lost_pet_change_status", args=[self.hidden.pk]), {"status": "published"})
        self.assertEqual(len(mail.outbox), 1)
        notification = CommunityNotification.objects.get(recipient=owner, report=self.hidden)
        self.client.force_login(owner)
        counts = reverse("adoption_update_counts")
        self.assertEqual(self.client.get(counts).json()["search_unread_count"], 1)
        page = self.client.get(reverse("my_search_requests"))
        self.assertContains(page, notification.title)
        self.assertContains(page, "Marcar como leído")
        notification.refresh_from_db()
        self.assertIsNone(notification.read_at)
        mark = reverse("search_update_read", args=[notification.pk])
        self.assertEqual(self.client.get(mark).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(owner)
        self.assertEqual(csrf_client.post(mark).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(counts).json()["search_unread_count"], 0)
        self.assertEqual(self.client.post(mark).status_code, 404)
        self.client.force_login(owner)
        newer = CommunityNotification.objects.create(recipient=owner, report=self.hidden, title="Otra novedad", body="Detalle")
        self.assertEqual(self.client.post(mark).status_code, 302)
        self.assertEqual(self.client.get(counts).json()["search_unread_count"], 1)
        newer.refresh_from_db()
        self.assertIsNone(newer.read_at)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_review_mail_failure_preserves_decision_and_private_notification(self):
        from .models import CommunityNotification
        self.staff.email = "staff@example.com"
        self.staff.save()
        self.client.force_login(self.staff)
        with patch("lost_pets.notifications.send_expo_push"), patch("lost_pets.search_email.EmailMessage.send", side_effect=OSError("private smtp error")):
            response = self.client.post(reverse("lost_pet_change_status", args=[self.hidden.pk]),
                {"status": "rejected", "review_note": "Confirmar la zona"}, follow=True)
        self.assertContains(response, "no pudimos enviar el correo")
        self.hidden.refresh_from_db()
        self.assertEqual(self.hidden.status, "rejected")
        self.assertEqual(CommunityNotification.objects.filter(recipient=self.staff, report=self.hidden).count(), 1)
