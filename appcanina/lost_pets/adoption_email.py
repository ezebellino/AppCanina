"""Private visit alerts; mail failures never roll back a saved visit."""
import logging

from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.urls import reverse

logger = logging.getLogger(__name__)


def notify_visit(interest, request):
    requested = interest.visit_status == interest.VisitStatus.REQUESTED
    if requested:
        addresses = interest.post.organization.memberships.filter(
            role="manager", user__is_active=True,
        ).values_list("user__email", flat=True)
        title = "Nueva solicitud de visita"
        detail = "Una persona quiere coordinar una visita. Ingresá para responder."
        route = "adoption_interest_list"
    else:
        addresses = [interest.applicant.email] if interest.applicant.is_active else []
        accepted = interest.visit_status == interest.VisitStatus.ACCEPTED
        title = "Visita aceptada" if accepted else "Respuesta a tu solicitud de visita"
        detail = ("El refugio aceptó tu visita. Consultá la ubicación y las indicaciones en tu cuenta."
                  if accepted else "El refugio no pudo aceptar esta visita. Consultá la respuesta en tu cuenta.")
        route = "my_adoption_interests"
    recipients = set()
    for address in addresses:
        address = (address or "").strip()
        try:
            validate_email(address)
        except ValidationError:
            continue
        recipients.add(address.lower())
    if not recipients:
        logger.warning("adoption_email_missing_recipient")
        return False
    # Keep personal text out of headers, and location/instructions out of email.
    body = (f"{interest.post.name} — {interest.post.organization.name}\n\n{detail}\n\n"
            f"{request.build_absolute_uri(reverse(route))}\n\n"
            "Iniciá sesión con la cuenta correspondiente para ver la solicitud.")
    try:
        sent = EmailMessage(
            subject=f"AppCanina: {title}", body=body, bcc=sorted(recipients),
        ).send(fail_silently=False)
    except Exception:
        # SMTP responses and exception strings may contain private data.
        logger.warning("adoption_email_failed")
        return False
    logger.info("adoption_email_smtp_accepted" if sent else "adoption_email_not_sent")
    return bool(sent)
