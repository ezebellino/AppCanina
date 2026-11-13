"""Persistent Expo outbox. A worker sends bounded batches and checks receipts."""
import json
import logging
import random
from datetime import timedelta
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from .models import MobilePushDevice, PushDelivery, PushWorkerLease
from .visibility import deliverable_notifications

logger = logging.getLogger(__name__)
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"
TERMINAL = {"DeviceNotRegistered", "MessageTooBig", "InvalidCredentials", "MismatchSenderId"}


def send_expo_push(notifications):
    # No network in HTTP requests; unique pairs make enqueue idempotent.
    current = deliverable_notifications().filter(pk__in=[n.pk for n in notifications])
    for notification in current.iterator():
        for device in MobilePushDevice.objects.filter(user_id=notification.recipient_id, active=True).select_related("access_token__user"):
            if device.access_token and device.access_token.user_id == device.user_id and device.access_token.is_valid():
                PushDelivery.objects.get_or_create(notification=notification, device=device,
                    defaults={"session": device.access_token})


def _post(url, payload):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.EXPO_PUSH_ACCESS_TOKEN:
        headers["Authorization"] = "Bearer " + settings.EXPO_PUSH_ACCESS_TOKEN
    with urlopen(Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST"), timeout=10) as response:
        return json.loads(response.read(1024 * 1024))


def _eligible(job):
    device = job.device
    return (device.active and device.access_token_id == job.session_id
        and device.user_id == job.notification.recipient_id
        and job.session.user_id == device.user_id and job.session.is_valid()
        and deliverable_notifications().filter(pk=job.notification_id).exists())


def _finish(job, state, outcome):
    job.state, job.outcome = state, outcome
    job.save(update_fields=["state", "outcome"])
    logger.info("expo_push_%s", outcome)


def _retry(job, outcome, receipt=False, delay=0):
    if job.attempts >= 6 or timezone.now() - job.created_at > timedelta(hours=24):
        _finish(job, "failed", "retry_exhausted")
        return
    job.state = "ticket" if receipt else "pending"
    job.outcome = outcome
    job.due_at = timezone.now() + timedelta(seconds=max(delay, min(3600, 30 * 2 ** job.attempts) + random.randint(0, 15)))
    job.save(update_fields=["state", "outcome", "due_at"])


def _result(job, result, receipt=False):
    if not isinstance(result, dict):
        _retry(job, "malformed_response", receipt)
        return
    if result.get("status") == "ok":
        if receipt:
            _finish(job, "confirmed", "provider_accepted")
        elif isinstance(result.get("id"), str) and 0 < len(result["id"]) <= 100:
            job.ticket, job.state, job.attempts = result["id"], "ticket", 0
            job.due_at = timezone.now() + timedelta(minutes=15)
            job.save(update_fields=["ticket", "state", "attempts", "due_at"])
        else:
            _retry(job, "malformed_response")
        return
    details = result.get("details") or {}
    error = details.get("error") if isinstance(details, dict) else None
    if error == "DeviceNotRegistered":
        # An old receipt must never disable a newly registered session.
        MobilePushDevice.objects.filter(pk=job.device_id, access_token_id=job.session_id).update(active=False)
    if error in TERMINAL:
        _finish(job, "failed", error)
    elif error == "MessageRateExceeded":
        # Explicit provider rejection: a new send, not another receipt query.
        _retry(job, "rate_exceeded")
    else:
        _retry(job, "provider_error", receipt)


def process_push_batch():
    lease, _ = PushWorkerLease.objects.get_or_create(name="expo")
    now = timezone.now()
    until = now + timedelta(seconds=120)
    if not PushWorkerLease.objects.filter(pk=lease.pk, available_at__lte=now).update(available_at=until):
        return 0
    try:
        # One request per turn, globally: <=100 messages per 2 seconds.
        jobs = list(PushDelivery.objects.filter(state__in=["pending", "ticket"], due_at__lte=now)
            .select_related("device", "notification", "session__user").order_by("due_at", "id")[:100])
        eligible = []
        for job in jobs:
            if not _eligible(job):
                _finish(job, "cancelled", "no_longer_eligible")
            elif now - job.created_at > timedelta(hours=24):
                _finish(job, "failed", "expired")
            else:
                eligible.append(job)
        if not eligible:
            return 0
        receipt = eligible[0].state == "ticket"
        jobs = [j for j in eligible if (j.state == "ticket") == receipt]
        for job in jobs:
            job.attempts += 1
            job.due_at = until  # Retry after worker crash; delivery is at-least-once.
            job.save(update_fields=["attempts", "due_at"])
        payload = {"ids": [j.ticket for j in jobs]} if receipt else [{
            "to": j.device.token, "title": j.notification.title, "body": j.notification.body,
            "sound": "default", "priority": "high", "channelId": "animales-extraviados",
            "ttl": 3600, "data": {"notification_id": j.notification_id, "report_id": j.notification.report_id},
        } for j in jobs]
        try:
            response = _post(EXPO_RECEIPTS_URL if receipt else EXPO_PUSH_URL, payload)
            data = response.get("data") if isinstance(response, dict) else None
            if receipt:
                if not isinstance(data, dict):
                    raise ValueError("invalid receipts")
                for job in jobs:
                    if job.ticket in data:
                        _result(job, data[job.ticket], True)
                    else:
                        _retry(job, "receipt_pending", True, 300)
            else:
                if not isinstance(data, list) or len(data) != len(jobs):
                    raise ValueError("invalid tickets")
                for job, result in zip(jobs, data):
                    _result(job, result)
        except HTTPError as error:
            temporary = error.code == 429 or error.code >= 500
            delay = 60
            retry_after = error.headers.get("Retry-After", "") if error.headers else ""
            try:
                delay = max(delay, int(retry_after))
            except (ValueError, TypeError):
                try:
                    delay = max(delay, (parsedate_to_datetime(retry_after) - timezone.now()).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
            for job in jobs:
                if temporary:
                    _retry(job, "http_temporary", receipt, delay)
                else:
                    _finish(job, "failed", "http_rejected")
        except (URLError, TimeoutError, OSError, ValueError, TypeError):
            for job in jobs:
                _retry(job, "transport_error", receipt)
        return len(jobs)
    finally:
        PushWorkerLease.objects.filter(pk=lease.pk, available_at=until).update(available_at=timezone.now() + timedelta(seconds=2))
