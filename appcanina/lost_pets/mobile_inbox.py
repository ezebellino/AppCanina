"""Private adoption inbox for managers of verified shelters."""
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .api import token_required, _mobile_payload, _mobile_interest_data, _mobile_managed_shelter_ids, _mobile_visit_available
from .adoption_email import notify_visit
from .models import AdoptionInterest


def _response(data, status=200):
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _scope(user):
    return AdoptionInterest.objects.filter(
        post__organization_id__in=_mobile_managed_shelter_ids(user),
    ).select_related("post__organization", "applicant")


def _item(interest):
    data = _mobile_interest_data(interest)
    data.pop("can_request_visit")
    data.update({
        "applicant_name": interest.applicant.get_full_name() or interest.applicant.username,
        "can_accept_visit": interest.visit_status == "requested" and _mobile_visit_available(interest),
        "can_decline_visit": interest.visit_status == "requested",
    })
    return data


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def inbox(request):
    if not _mobile_managed_shelter_ids(request.mobile_user).exists():
        return _response({"detail": "Esta bandeja está disponible para responsables de refugios verificados."}, 403)
    interests = _scope(request.mobile_user)
    counts = {"all": interests.count(), "received": interests.filter(status="received").count(),
              "visits": interests.filter(visit_status="requested").count()}
    view = request.GET.get("view", "all")
    if view not in counts:
        return _response({"detail": "Filtro inválido."}, 400)
    try:
        page = int(request.GET.get("page", "1"))
        if page < 1 or page > 100000:
            raise ValueError
    except (ValueError, TypeError):
        return _response({"detail": "Página inválida."}, 400)
    if view == "received":
        interests = interests.filter(status="received")
    elif view == "visits":
        interests = interests.filter(visit_status="requested")
    offset = (page - 1) * 20
    items = list(interests.order_by("-updated_at", "-id")[offset:offset + 21])
    return _response({"interests": [_item(item) for item in items[:20]], "counts": counts,
                      "page": page, "has_next": len(items) > 20,
                      "status_choices": [{"value": value, "label": label} for value, label in AdoptionInterest.Status.choices]})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def update(request, interest_id):
    interest = _scope(request.mobile_user).filter(pk=interest_id).first()
    if not interest:
        return _response({"detail": "Solicitud no encontrada o acceso retirado."}, 404)
    payload = _mobile_payload(request)
    if not isinstance(payload, dict):
        return _response({"detail": "Datos inválidos."}, 400)
    if not isinstance(payload.get("expected_updated_at"), str) or not payload["expected_updated_at"]:
        return _response({"detail": "Falta la versión de la solicitud. Actualizá la bandeja."}, 400)
    if payload.get("expected_updated_at") != interest.updated_at.isoformat():
        return _response({"detail": "La solicitud cambió. Actualizá la bandeja antes de guardar."}, 409)
    action = payload.get("action")
    now = timezone.now()
    updates = {"updated_at": now, "applicant_activity_at": now}
    query = _scope(request.mobile_user).filter(pk=interest.pk, updated_at=interest.updated_at)
    if action == "status":
        status, note = payload.get("status"), payload.get("staff_note", "")
        if not isinstance(status, str) or status not in AdoptionInterest.Status.values or not isinstance(note, str) or len(note.strip()) > 280:
            return _response({"detail": "Elegí un estado válido y un mensaje de hasta 280 caracteres."}, 400)
        if status == interest.status and note.strip() == interest.staff_note:
            return _response({"interest": _item(interest), "detail": "No hay cambios para guardar."})
        updates.update(status=status, staff_note=note.strip())
    elif action in ("accept", "decline"):
        address, instructions = payload.get("visit_address", ""), payload.get("visit_instructions", "")
        if not isinstance(address, str) or not isinstance(instructions, str) or len(address.strip()) > 300 or len(instructions.strip()) > 280:
            return _response({"detail": "Revisá la dirección (hasta 300 caracteres) y las indicaciones (hasta 280)."}, 400)
        if interest.visit_status != "requested":
            return _response({"detail": "La visita ya fue respondida o todavía no fue solicitada."}, 409)
        if action == "accept" and (not address.strip() or not _mobile_visit_available(interest)):
            return _response({"detail": "Indicá la dirección y verificá que la adopción siga disponible."}, 400)
        query = query.filter(visit_status="requested")
        updates.update(visit_status="accepted" if action == "accept" else "declined",
                       visit_address=address.strip() if action == "accept" else "",
                       visit_instructions=instructions.strip(), visit_answered_at=now)
    else:
        return _response({"detail": "Acción inválida."}, 400)
    if not query.update(**updates):
        return _response({"detail": "La solicitud cambió o perdiste el acceso. Actualizá la bandeja."}, 409)
    interest.refresh_from_db()
    detail = "Cambios guardados. La persona puede verlos en su solicitud."
    if action in ("accept", "decline") and not notify_visit(interest, request):
        detail = "Respuesta guardada, pero no pudimos enviar el correo. La persona puede verla en su solicitud."
    return _response({"interest": _item(interest), "detail": detail})
