import json
from functools import wraps
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from PIL import UnidentifiedImageError

from .forms import photo_without_location_metadata
from .models import AdoptionPost, CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, Sighting
from .notifications import notify_new_sighting
from organizations.forms import CommunityCollaboratorForm
from organizations.roles import ensure_base_roles


def token_required(permission):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return JsonResponse({"detail": "Token requerido."}, status=401)
            token = MobileAccessToken.from_raw_token(header[7:])
            if not token or not token.user.has_perm(permission):
                return JsonResponse({"detail": "Token inválido o sin permiso."}, status=403)
            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at"])
            request.mobile_user = token.user
            request.mobile_token = token
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


@csrf_exempt
@require_POST
def mobile_login(request):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"mobile-login:{ip}"
    if cache.get(cache_key, 0) >= 5:
        return JsonResponse({"detail": "Demasiados intentos. Probá nuevamente en unos minutos."}, status=429)
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    user = authenticate(request, username=payload.get("username", ""), password=payload.get("password", ""))
    if not user or not user.has_perm("lost_pets.view_lostpetreport"):
        cache.set(cache_key, cache.get(cache_key, 0) + 1, 900)
        return JsonResponse({"detail": "Credenciales inválidas."}, status=401)
    cache.delete(cache_key)
    raw_token, _ = MobileAccessToken.issue(user, payload.get("device_name", "Dispositivo móvil"))
    return JsonResponse({"token": raw_token, "token_type": "Bearer", "user": {"username": user.username}})


@csrf_exempt
@require_POST
def mobile_register(request):
    """Create a strictly limited community account from the mobile app."""
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"mobile-register:{ip}"
    if cache.get(cache_key, 0) >= 3:
        return JsonResponse({"detail": "Demasiadas cuentas creadas desde esta conexión. Probá nuevamente más tarde."}, status=429)
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "JSON inválido."}, status=400)

    form = CommunityCollaboratorForm({
        "username": (payload.get("username") or "").strip(),
        "first_name": (payload.get("first_name") or "").strip(),
        "email": (payload.get("email") or "").strip(),
        "password1": payload.get("password") or "",
        "password2": payload.get("password_confirmation") or "",
    })
    if not form.is_valid():
        messages = [message for errors in form.errors.values() for message in errors]
        return JsonResponse({"detail": messages[0] if messages else "No se pudo crear la cuenta."}, status=400)

    collaborator = form.save()
    collaborator.groups.add(ensure_base_roles()["collaborator"])
    cache.set(cache_key, cache.get(cache_key, 0) + 1, 3600)
    raw_token, _ = MobileAccessToken.issue(collaborator, payload.get("device_name", "Dispositivo móvil"))
    return JsonResponse({"token": raw_token, "token_type": "Bearer", "user": {"username": collaborator.username}}, status=201)


def _mobile_report_data(request, report):
    return {
        "id": report.id,
        "name": report.name,
        "species": report.get_species_display(),
        "breed": report.breed,
        "description": report.description,
        "area": report.area_label,
        "last_seen_at": report.last_seen_at.isoformat(),
        "status": report.status,
        "status_label": report.get_status_display(),
        "photo_url": request.build_absolute_uri(report.photo.url) if report.photo else None,
    }


def _mobile_request_data(request, report):
    data = _mobile_report_data(request, report)
    data.update({
        "review_note": report.review_note,
        "editable": report.status in {LostPetReport.Status.HIDDEN, LostPetReport.Status.REJECTED},
    })
    return data


def _mobile_adoption_data(request, post):
    return {
        "id": post.id, "name": post.name, "species": post.get_species_display(), "breed": post.breed,
        "age": post.age_label, "description": post.description, "area": post.area_label,
        "status": post.status, "status_label": post.get_status_display(), "review_note": post.review_note,
        "photo_url": request.build_absolute_uri(post.photo.url) if post.photo else None,
        "editable": post.status in {AdoptionPost.Status.PENDING, AdoptionPost.Status.REJECTED},
    }


def _mobile_payload(request):
    if request.content_type and request.content_type.startswith("application/json"):
        try:
            return json.loads(request.body)
        except (TypeError, ValueError):
            return None
    return request.POST


def _mobile_coordinates(payload):
    latitude, longitude = (payload.get("latitude") or "").strip(), (payload.get("longitude") or "").strip()
    if not latitude and not longitude:
        return None, None, None
    if not latitude or not longitude:
        return None, None, "La ubicación debe incluir latitud y longitud juntas."
    try:
        latitude_value, longitude_value = Decimal(latitude), Decimal(longitude)
    except (InvalidOperation, TypeError):
        return None, None, "La ubicación no tiene un formato válido."
    if not Decimal("-90") <= latitude_value <= Decimal("90") or not Decimal("-180") <= longitude_value <= Decimal("180"):
        return None, None, "La ubicación está fuera del rango permitido."
    return latitude_value, longitude_value, None


def _mobile_photo(request):
    uploaded = request.FILES.get("photo")
    if not uploaded:
        return None
    try:
        return photo_without_location_metadata(uploaded)
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValueError("La imagen no pudo procesarse. Probá con una foto JPG o PNG.")


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_reports(request):
    state = request.GET.get("estado", "activos")
    reports = LostPetReport.objects.filter(status=LostPetReport.Status.RESOLVED if state == "encontrados" else LostPetReport.Status.PUBLISHED)
    query = request.GET.get("q", "").strip()
    if query:
        reports = reports.filter(Q(name__icontains=query) | Q(species__icontains=query) | Q(area_label__icontains=query))
    return JsonResponse({"reports": [_mobile_report_data(request, report) for report in reports[:60]]})


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_adoptions(request):
    posts = AdoptionPost.objects.filter(status=AdoptionPost.Status.PUBLISHED)
    query = request.GET.get("q", "").strip()
    if query:
        posts = posts.filter(Q(name__icontains=query) | Q(species__icontains=query) | Q(area_label__icontains=query))
    return JsonResponse({"adoptions": [_mobile_adoption_data(request, post) for post in posts[:60]]})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_adoption_request(request):
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    species_map = {"perro": "dog", "perros": "dog", "dog": "dog", "gato": "cat", "gatos": "cat", "cat": "cat", "otro": "other", "other": "other"}
    name, area = (payload.get("name") or "").strip(), (payload.get("area") or "").strip()
    species = species_map.get((payload.get("species") or "").strip().lower())
    if not name or not species or not area:
        return JsonResponse({"detail": "Indicá nombre, especie y zona aproximada."}, status=400)
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    post = AdoptionPost.objects.create(publisher=request.mobile_user, name=name[:100], species=species, breed=(payload.get("breed") or "").strip()[:100], age_label=(payload.get("age") or "").strip()[:80], description=(payload.get("description") or "").strip(), area_label=area[:120], photo=photo)
    return JsonResponse({"id": post.id, "detail": "Recibimos la publicación. La veterinaria o refugio responsable la revisará antes de mostrarla."}, status=201)


@csrf_exempt
@require_POST
@token_required("lost_pets.add_sighting")
def mobile_sighting_create(request, report_id):
    report = LostPetReport.objects.filter(pk=report_id, status=LostPetReport.Status.PUBLISHED).first()
    if not report:
        return JsonResponse({"detail": "El aviso ya no está disponible para recibir avistamientos."}, status=404)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    area = (payload.get("area") or "").strip()
    if not area:
        return JsonResponse({"detail": "Indicá una zona aproximada para el avistamiento."}, status=400)
    latitude, longitude, coordinate_error = _mobile_coordinates(payload)
    if coordinate_error:
        return JsonResponse({"detail": coordinate_error}, status=400)
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    sighting = Sighting.objects.create(
        report=report,
        reporter=request.mobile_user,
        area_label=area[:120],
        description=(payload.get("description") or "").strip(),
        latitude=latitude,
        longitude=longitude,
        photo=photo,
        status=Sighting.Status.PUBLISHED,
    )
    notify_new_sighting(report, sighting)
    return JsonResponse({"id": sighting.id, "detail": "Avistamiento compartido. El mapa mostrará solo una zona aproximada."}, status=201)


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_search_request(request):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    cache_key = f"mobile-search-request:{ip}"
    if cache.get(cache_key, 0) >= 3:
        return JsonResponse({"detail": "Ya enviaste varias solicitudes desde esta conexión. Probá nuevamente más tarde."}, status=429)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "JSON inválido."}, status=400)

    species_map = {"perro": "dog", "perros": "dog", "dog": "dog", "gato": "cat", "gatos": "cat", "cat": "cat", "otro": "other", "other": "other"}
    species = species_map.get((payload.get("species") or "").strip().lower())
    name = (payload.get("name") or "").strip()
    area = (payload.get("area") or "").strip()
    if not name or not species or not area:
        return JsonResponse({"detail": "Indicá nombre del animal, especie (perro, gato u otro) y zona aproximada."}, status=400)
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    report = LostPetReport.objects.create(
        reporter=request.mobile_user,
        name=name[:100],
        species=species,
        breed=(payload.get("breed") or "").strip()[:100],
        description=(payload.get("description") or "").strip(),
        area_label=area[:120],
        last_seen_at=timezone.now(),
        status=LostPetReport.Status.HIDDEN,
        requested_via_mobile=True,
        photo=photo,
    )
    cache.set(cache_key, cache.get(cache_key, 0) + 1, 3600)
    return JsonResponse({"id": report.id, "detail": "Recibimos tu solicitud. El equipo la revisará antes de publicarla."}, status=201)


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_my_search_requests(request):
    requests = LostPetReport.objects.filter(reporter=request.mobile_user, requested_via_mobile=True).order_by("-updated_at", "-id")
    return JsonResponse({"requests": [_mobile_request_data(request, report) for report in requests[:30]]})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_search_request_edit(request, report_id):
    report = LostPetReport.objects.filter(
        pk=report_id,
        reporter=request.mobile_user,
        requested_via_mobile=True,
    ).first()
    if not report:
        return JsonResponse({"detail": "Solicitud no encontrada."}, status=404)
    if report.status not in {LostPetReport.Status.HIDDEN, LostPetReport.Status.REJECTED}:
        return JsonResponse({"detail": "Esta solicitud ya fue publicada o cerrada y no se puede editar desde el teléfono."}, status=409)
    payload = _mobile_payload(request)
    if payload is None:
        return JsonResponse({"detail": "Datos inválidos."}, status=400)
    species_map = {"perro": "dog", "perros": "dog", "dog": "dog", "gato": "cat", "gatos": "cat", "cat": "cat", "otro": "other", "other": "other"}
    species = species_map.get((payload.get("species") or "").strip().lower())
    name = (payload.get("name") or "").strip()
    area = (payload.get("area") or "").strip()
    if not name or not species or not area:
        return JsonResponse({"detail": "Indicá nombre del animal, especie (perro, gato u otro) y zona aproximada."}, status=400)
    report.name = name[:100]
    report.species = species
    report.breed = (payload.get("breed") or "").strip()[:100]
    report.description = (payload.get("description") or "").strip()
    report.area_label = area[:120]
    try:
        photo = _mobile_photo(request)
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    if photo:
        report.photo = photo
    report.status = LostPetReport.Status.HIDDEN
    report.review_note = ""
    report.save()
    return JsonResponse({"request": _mobile_request_data(request, report), "detail": "Solicitud actualizada. El equipo la revisará nuevamente."})


@csrf_exempt
@require_GET
@token_required("lost_pets.view_lostpetreport")
def mobile_notifications(request):
    items = CommunityNotification.objects.filter(recipient=request.mobile_user, read_at__isnull=True).select_related("report", "sighting")[:30]
    notifications = []
    for item in items:
        photo = item.sighting.photo if item.sighting and item.sighting.photo else item.report.photo
        description = item.sighting.description if item.sighting and item.sighting.description else item.report.description
        area = item.sighting.area_label if item.sighting else item.report.area_label
        notifications.append({
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "report_id": item.report_id,
            "animal_name": item.report.name,
            "species": item.report.get_species_display(),
            "description": description,
            "area": area,
            "photo_url": request.build_absolute_uri(photo.url) if photo else None,
            "created_at": item.created_at.isoformat(),
        })
    return JsonResponse({"notifications": notifications})


@csrf_exempt
@require_POST
@token_required("lost_pets.view_lostpetreport")
def mobile_push_device_register(request):
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    push_token = (payload.get("push_token") or "").strip()
    platform = (payload.get("platform") or "").lower()
    if not push_token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
        return JsonResponse({"detail": "Token de notificación inválido."}, status=400)
    if platform not in {MobilePushDevice.Platform.ANDROID, MobilePushDevice.Platform.IOS}:
        return JsonResponse({"detail": "Plataforma de dispositivo inválida."}, status=400)
    device, created = MobilePushDevice.objects.update_or_create(
        token=push_token,
        defaults={"user": request.mobile_user, "platform": platform, "active": True},
    )
    return JsonResponse({"id": device.id, "registered": created})
