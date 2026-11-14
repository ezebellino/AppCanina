"""Personal inbox organization; never changes the shared adoption state."""
from django.db.models import Exists, OuterRef
from .models import AdoptionArchive, AdoptionInterest

FINAL_STATUSES = (AdoptionInterest.Status.COMPLETED, AdoptionInterest.Status.CLOSED)


def with_archive_state(interests, user, audience):
    # A later reply or reopened request must be visible again, even if closed again.
    archives = AdoptionArchive.objects.filter(
        interest_id=OuterRef("pk"), user=user, audience=audience,
        version=OuterRef("updated_at"), interest__status__in=FINAL_STATUSES,
    )
    return interests.annotate(is_archived=Exists(archives))


def set_archive(interests, user, audience, interest_id, action, expected_version):
    interest = interests.filter(pk=interest_id).first()
    if not interest:
        return "Solicitud no encontrada o acceso retirado.", 404
    if action not in ("archive", "restore"):
        return "Acción inválida.", 400
    if not isinstance(expected_version, str) or expected_version != interest.updated_at.isoformat():
        return "La solicitud cambió. Actualizá la bandeja antes de continuar.", 409
    if action == "archive":
        if interest.status not in FINAL_STATUSES:
            return "Solo podés archivar solicitudes con adopción concretada o que no continuaron.", 409
        AdoptionArchive.objects.update_or_create(
            interest=interest, user=user, audience=audience,
            defaults={"version": interest.updated_at},
        )
        return "Solicitud archivada en tu bandeja. Podés recuperarla desde Archivadas.", 200
    AdoptionArchive.objects.filter(interest=interest, user=user, audience=audience).delete()
    return "Solicitud restaurada en tu bandeja.", 200
