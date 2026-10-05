from django.contrib.auth.models import User

from organizations.roles import COMMUNITY_COLLABORATOR_GROUP

from .models import CommunityNotification
from .push import send_expo_push


def _summary(description, fallback):
    return (description or fallback)[:280]


def notify_new_report(report):
    recipients = User.objects.filter(
        is_active=True,
        groups__name=COMMUNITY_COLLABORATOR_GROUP,
    ).exclude(pk=report.reporter_id).distinct()
    notifications = [
        CommunityNotification(
            recipient=recipient,
            report=report,
            title=f"Alerta: {report.name} está extraviado",
            body=_summary(report.description, f"Última zona informada: {report.area_label}."),
        )
        for recipient in recipients
    ]
    CommunityNotification.objects.bulk_create(notifications)
    send_expo_push(notifications)


def notify_new_sighting(report, sighting):
    community_ids = User.objects.filter(
        is_active=True,
        groups__name=COMMUNITY_COLLABORATOR_GROUP,
    ).values_list("id", flat=True)
    recipient_ids = set(community_ids)
    recipient_ids.add(report.reporter_id)
    recipient_ids.discard(sighting.reporter_id)
    recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
    notifications = [
        CommunityNotification(
            recipient=recipient,
            report=report,
            sighting=sighting,
            title=f"Nuevo avistamiento de {report.name}",
            body=_summary(sighting.description, f"Informado en {sighting.area_label}."),
        )
        for recipient in recipients
    ]
    CommunityNotification.objects.bulk_create(notifications)
    send_expo_push(notifications)
