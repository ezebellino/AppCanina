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


def notify_request_review(report):
    if not report.requested_via_mobile or not report.reporter.is_active:
        return
    accepted = report.status == report.Status.PUBLISHED
    notification = CommunityNotification.objects.create(
        recipient=report.reporter,
        report=report,
        title=f"Tu solicitud para {report.name} fue {'publicada' if accepted else 'rechazada'}",
        body=_summary(report.review_note, "Ya está visible para la comunidad." if accepted else "Revisá la nota del equipo y podés corregirla desde Mis solicitudes."),
    )
    send_expo_push([notification])
