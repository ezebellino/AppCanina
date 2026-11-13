"""Review email; failures preserve the decision and the in-app notification."""
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.urls import reverse
from config.public_urls import public_url

logger = logging.getLogger(__name__)


def notify_search_review(report, request):
    address = (report.reporter.email or "").strip()
    if not report.reporter.is_active:
        return False
    try:
        validate_email(address)
    except ValidationError:
        logger.warning("search_review_email_missing_recipient")
        return False
    accepted = report.status == report.Status.PUBLISHED
    title = "Tu búsqueda ya está publicada" if accepted else "Respuesta a tu búsqueda"
    detail = ("Tu búsqueda fue aprobada y ya está visible para la comunidad." if accepted else
              "El equipo revisó tu búsqueda. Consultá el motivo del rechazo y corregí el aviso desde Mis búsquedas.")
    body = (f"{report.name}\n\n{detail}\n\n"
            f"{public_url(request, reverse('my_search_requests'))}\n\n"
            "Iniciá sesión con la cuenta que creó la búsqueda.")
    try:
        sent = EmailMessage(subject=f"{settings.APP_NAME}: {title}", body=body, to=[address]).send(fail_silently=False)
    except Exception:
        logger.warning("search_review_email_failed")
        return False
    logger.info("search_review_email_smtp_accepted" if sent else "search_review_email_not_sent")
    return bool(sent)
