"""In-app activity only; independent of push transport."""
from .adoption_archives import with_archive_state
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from .api import token_required, _mobile_interest_data, _mobile_request_data, _mobile_managed_shelter_ids, _mobile_payload
from .adoption_updates import unread_interests
from .models import AdoptionInterest, AdoptionReadReceipt
from .visibility import deliverable_notifications
from .mobile_inbox import _item


def response(data, status=200):
    result = JsonResponse(data, status=status)
    result["Cache-Control"] = "no-store"
    return result


def sources(user):
    return {
        "community": deliverable_notifications().filter(recipient=user).select_related("report", "sighting"),
        "applicant": AdoptionInterest.objects.filter(applicant=user, applicant_activity_at__isnull=False).select_related("post__organization"),
        "institution": AdoptionInterest.objects.filter(post__organization_id__in=_mobile_managed_shelter_ids(user), institution_activity_at__isnull=False).select_related("post__organization", "applicant"),
    }


def pending(query, kind, user):
    return query.filter(read_at__isnull=True) if kind == "community" else unread_interests(query, user, kind)


def activity(item, kind):
    return item.created_at if kind == "community" else getattr(item, f"{kind}_activity_at")


def serialize(item, kind, unread):
    return {"key": f"{kind}-{item.pk}", "unread": unread, "activity_at": activity(item, kind).isoformat(),
            "title": item.title if kind == "community" else ("Solicitud recibida" if kind == "institution" else "Novedades de tu adopción") + f": {item.post.name}",
            "body": item.body if kind == "community" else f"{item.get_status_display()} · {item.get_visit_status_display()}",
            "category": "Búsquedas" if kind == "community" else "Adopciones"}


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def feed(request):
    try:
        page = int(request.GET.get("page", "1"))
        if not 1 <= page <= 1000:
            raise ValueError
    except (ValueError, TypeError):
        return response({"detail": "Página inválida."}, 400)
    unread_only = request.GET.get("filter", "all") == "unread"
    queries = sources(request.mobile_user)
    unread_count = sum(pending(query, kind, request.mobile_user).count() for kind, query in queries.items())
    if request.GET.get("count_only") == "1":
        return response({"unread_count": unread_count})
    items = []
    for kind, query in queries.items():
        if kind != "community":
            query = with_archive_state(query, request.mobile_user, kind).filter(is_archived=False)
        query = pending(query, kind, request.mobile_user) if unread_only else query
        field = "created_at" if kind == "community" else f"{kind}_activity_at"
        batch = list(query.order_by(f"-{field}", "-id")[:page * 20 + 1])
        unread_ids = set(pending(queries[kind].filter(pk__in=[item.pk for item in batch]), kind, request.mobile_user).values_list("pk", flat=True))
        items.extend(serialize(item, kind, item.pk in unread_ids) for item in batch)
    items.sort(key=lambda item: (item["activity_at"], item["key"].split("-")[0], int(item["key"].split("-")[1])), reverse=True)
    offset = (page - 1) * 20
    return response({"notifications": items[offset:offset + 20], "has_next": len(items) > offset + 20,
                     "page": page, "unread_count": unread_count})


def find(user, key):
    try:
        kind, raw_id = key.split("-", 1)
        query = sources(user)[kind]
        if kind != "community":
            query = with_archive_state(query, user, kind)
        return kind, query.filter(pk=int(raw_id)).first()
    except (KeyError, ValueError):
        return None, None


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def detail(request, key):
    kind, item = find(request.mobile_user, key)
    if not item:
        return response({"detail": "Esta novedad ya no está disponible para tu cuenta."}, 404)
    data = {"key": key, "activity_at": activity(item, kind).isoformat(),
            "unread": pending(sources(request.mobile_user)[kind].filter(pk=item.pk), kind, request.mobile_user).exists()}
    if kind == "community":
        own_request = not item.sighting_id and item.report.requested_via_mobile and item.report.reporter_id == request.mobile_user.pk
        if own_request:
            data.update(target="search_request", request=_mobile_request_data(request, item.report))
        else:
            data.update(target="report", report_id=item.report_id)
    elif kind == "applicant":
        data.update(target="adoption", interest=_mobile_interest_data(item))
    else:
        data.update(target="institution", interest=_item(item), status_choices=[{"value": value, "label": label} for value, label in AdoptionInterest.Status.choices])
    return response(data)


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mark_read(request, key):
    kind, item = find(request.mobile_user, key)
    if not item:
        return response({"detail": "Novedad no encontrada."}, 404)
    payload = _mobile_payload(request)
    try:
        seen = parse_datetime(payload.get("activity_at", "")) if isinstance(payload, dict) else None
    except (TypeError, ValueError):
        seen = None
    if seen is None or timezone.is_naive(seen) or seen > activity(item, kind):
        return response({"detail": "Fecha de lectura inválida."}, 400)
    if kind == "community":
        if seen != item.created_at:
            return response({"detail": "La novedad cambió. Volvé a abrirla."}, 409)
        sources(request.mobile_user)[kind].filter(pk=item.pk, read_at__isnull=True).update(read_at=timezone.now())
    else:
        # Only acknowledge the version actually displayed, never a later update.
        with transaction.atomic():
            receipt, _ = AdoptionReadReceipt.objects.get_or_create(interest=item, user=request.mobile_user, audience=kind, defaults={"seen_at": seen})
            AdoptionReadReceipt.objects.filter(pk=receipt.pk, seen_at__lt=seen).update(seen_at=seen)
    return response({"detail": "Lectura registrada."})
