"""Confirmation after a committed family invitation, without sensitive logs."""
import logging

from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email

logger = logging.getLogger(__name__)


def notify_family_accepted(invite, user, manage_url, animals_url):
    notices = (
        (invite.invited_by, "Acceso familiar aceptado",
         f"{user.get_full_name() or user.username} aceptó tu invitación para cuidar a {invite.patient.name}.\n"
         "Ya puede consultar su ficha e historial. Podés revisar los responsables y quitar el acceso desde tu cuenta.", manage_url),
        (user, "Tu animal ya está en Mis animales",
         f"{invite.patient.name} ya aparece en tu cuenta de AppCanina.\n"
         "Compartís su ficha e historial como responsable familiar. No hace falta registrar el animal nuevamente.", animals_url),
    )
    for recipient, title, detail, url in notices:
        address = (recipient.email or "").strip()
        try:
            validate_email(address)
        except ValidationError:
            logger.warning("family_email_missing_recipient")
            continue
        if not recipient.is_active:
            logger.warning("family_email_inactive_recipient")
            continue
        try:
            sent = EmailMessage(subject=f"AppCanina: {title}",
                                body=f"{detail}\n\n{url}\n\nIngresá con tu cuenta para consultar los datos.",
                                to=[address]).send(fail_silently=False)
        except Exception:
            logger.warning("family_email_failed")
        else:
            logger.info("family_email_smtp_accepted" if sent else "family_email_not_sent")
