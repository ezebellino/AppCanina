import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

from .models import MobilePushDevice


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_expo_push(notifications):
    """Best-effort push delivery. Notifications remain available in-app on failure."""
    if not notifications:
        return
    notification_by_user = {notification.recipient_id: notification for notification in notifications}
    devices = MobilePushDevice.objects.filter(user_id__in=notification_by_user, active=True)
    messages = []
    for device in devices:
        notification = notification_by_user[device.user_id]
        messages.append({
            "to": device.token,
            "title": notification.title,
            "body": notification.body,
            "sound": "default",
            "priority": "high",
            "channelId": "animales-extraviados",
            "data": {"report_id": notification.report_id},
        })
    for start in range(0, len(messages), 100):
        request = Request(
            EXPO_PUSH_URL,
            data=json.dumps(messages[start:start + 100]).encode(),
            headers={"Accept": "application/json", "Accept-encoding": "gzip, deflate", "Content-Type": "application/json"},
            method="POST",
        )
        if settings.EXPO_PUSH_ACCESS_TOKEN:
            request.add_header("Authorization", f"Bearer {settings.EXPO_PUSH_ACCESS_TOKEN}")
        try:
            with urlopen(request, timeout=5):
                pass
        except (URLError, TimeoutError):
            continue
