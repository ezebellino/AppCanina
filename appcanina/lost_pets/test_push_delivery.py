from datetime import timedelta
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from .models import CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, PushDelivery, PushWorkerLease
from .push import send_expo_push, process_push_batch


class PushDeliveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("push-user")
        _, self.session = MobileAccessToken.issue(self.user, "Phone")
        self.device = MobilePushDevice.objects.create(user=self.user, access_token=self.session,
            token="ExpoPushToken[test]", platform="android")
        self.report = LostPetReport.objects.create(reporter=self.user, name="Animal", species="dog",
            last_seen_at=timezone.now(), area_label="Centro", status="published")
        self.note = CommunityNotification.objects.create(recipient=self.user, report=self.report, title="Test", body="Test")

    def due(self):
        PushWorkerLease.objects.update(available_at=timezone.now()-timedelta(seconds=1))
        PushDelivery.objects.update(due_at=timezone.now()-timedelta(seconds=1))

    def test_enqueue_idempotent_and_does_not_call_network(self):
        with patch("lost_pets.push.urlopen") as network:
            send_expo_push([self.note])
            send_expo_push([self.note])
        network.assert_not_called()
        self.assertEqual(PushDelivery.objects.count(), 1)

    def test_ticket_then_receipt_not_delivered_claim(self):
        send_expo_push([self.note])
        with patch("lost_pets.push._post", return_value={"data": [{"status": "ok", "id": "ticket"}]}) as post:
            self.assertEqual(process_push_batch(), 1)
            self.assertEqual(post.call_args.args[1][0]["data"]["notification_id"], self.note.pk)
        job=PushDelivery.objects.get()
        self.assertEqual(job.state, "ticket")
        self.assertGreater(job.due_at, timezone.now()+timedelta(minutes=14))
        self.due()
        with patch("lost_pets.push._post", return_value={"data": {"ticket": {"status": "ok"}}}):
            process_push_batch()
        job.refresh_from_db()
        self.assertEqual((job.state, job.outcome), ("confirmed", "provider_accepted"))

    def test_global_lease_blocks_second_sender(self):
        send_expo_push([self.note])
        with patch("lost_pets.push._post", return_value={"data": [{"status":"ok", "id":"ticket"}]}) as post:
            process_push_batch()
            self.assertEqual(process_push_batch(), 0)
            post.assert_called_once()

    def test_receipt_disables_unregistered_device(self):
        send_expo_push([self.note])
        PushDelivery.objects.update(state="ticket", ticket="ticket")
        with patch("lost_pets.push._post", return_value={"data":{"ticket":{"status":"error", "details":{"error":"DeviceNotRegistered"}}}}):
            process_push_batch()
        self.device.refresh_from_db()
        self.assertFalse(self.device.active)
        self.assertEqual(PushDelivery.objects.get().state, "failed")

    def test_changed_session_cancels_without_disabling_new_registration(self):
        send_expo_push([self.note])
        _, session=MobileAccessToken.issue(self.user, "New login")
        self.device.access_token=session
        self.device.save()
        with patch("lost_pets.push._post") as post:
            process_push_batch()
        post.assert_not_called()
        self.device.refresh_from_db()
        self.assertTrue(self.device.active)
        self.assertEqual(PushDelivery.objects.get().state, "cancelled")

    def test_hidden_content_and_revoked_session_cancel(self):
        send_expo_push([self.note])
        self.report.status="hidden"
        self.report.save()
        with patch("lost_pets.push._post") as post:
            process_push_batch()
        post.assert_not_called()
        self.assertEqual(PushDelivery.objects.get().state, "cancelled")

    def test_temporary_errors_retry_with_bound(self):
        for error in [URLError("offline"), HTTPError("url",429,"rate",{},None), HTTPError("url",503,"down",{},None)]:
            PushDelivery.objects.all().delete()
            self.due()
            send_expo_push([self.note])
            with patch("lost_pets.push._post",side_effect=error):
                process_push_batch()
            job=PushDelivery.objects.get()
            self.assertEqual(job.state,"pending")
            self.assertGreater(job.due_at,timezone.now())
            job.attempts=6
            job.save()
            self.due()
            with patch("lost_pets.push._post",side_effect=error):
                process_push_batch()
            job.refresh_from_db()
            self.assertEqual(job.state,"failed")

    def test_bad_credentials_fail_without_disabling_device(self):
        send_expo_push([self.note])
        with patch("lost_pets.push._post",return_value={"data":[{"status":"error","details":{"error":"InvalidCredentials"}}]}):
            process_push_batch()
        self.device.refresh_from_db()
        self.assertTrue(self.device.active)
        self.assertEqual(PushDelivery.objects.get().outcome,"InvalidCredentials")

    def test_missing_receipt_is_polled_without_resending(self):
        send_expo_push([self.note])
        PushDelivery.objects.update(state="ticket",ticket="ticket")
        with patch("lost_pets.push._post",return_value={"data":{}}):
            process_push_batch()
        self.assertEqual(PushDelivery.objects.get().state,"ticket")

    def test_batch_is_bounded_and_all_notifications_survive(self):
        notes=[CommunityNotification.objects.create(recipient=self.user, report=self.report,title="Test",body="Test") for _ in range(102)]
        send_expo_push(notes)
        with patch("lost_pets.push._post",return_value={"data":[{"status":"ok","id":str(i)} for i in range(100)]}) as post:
            self.assertEqual(process_push_batch(),100)
            self.assertEqual(len(post.call_args.args[1]),100)
        self.assertEqual(PushDelivery.objects.filter(state="pending").count(),2)

    def test_revoked_session_is_rechecked_by_worker(self):
        send_expo_push([self.note])
        self.session.revoked_at=timezone.now()
        self.session.save()
        with patch("lost_pets.push._post") as post:
            process_push_batch()
        post.assert_not_called()
        self.assertEqual(PushDelivery.objects.get().state,"cancelled")

    def test_retry_after_is_respected(self):
        send_expo_push([self.note])
        with patch("lost_pets.push._post",side_effect=HTTPError("url",429,"rate",{"Retry-After":"1800"},None)):
            process_push_batch()
        self.assertGreater(PushDelivery.objects.get().due_at,timezone.now()+timedelta(seconds=1790))
