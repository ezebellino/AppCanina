import json
from functools import wraps

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import CommunityNotification, MobileAccessToken


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
