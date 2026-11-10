import posixpath
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import Http404
from django.views.decorators.cache import never_cache
from django.views.static import serve

from config.public_urls import public_url
from .models import LostPetReport, MobileAccessToken, Sighting
from .visibility import PUBLIC_REPORT_STATUSES, can_review_reports, can_review_sightings, reports_visible_to


PREVIEW_SALT = "lost-pets.private-request-photo"


def request_photo_url(request, report):
    if not report.photo:
        return None
    url = public_url(request, report.photo.url)
    if report.status not in PUBLIC_REPORT_STATUSES and report.requested_via_mobile and report.reporter_id == request.mobile_user.pk:
        # Scoped to this photo and session; never embed the reusable bearer token.
        preview = signing.dumps({"session": request.mobile_token.pk, "report": report.pk, "photo": report.photo.name}, salt=PREVIEW_SALT)
        url += "?" + urlencode({"preview": preview})
    return url


def _can_preview_request(request, report, path):
    if not report.requested_via_mobile:
        return False
    if request.user.is_authenticated and request.user.is_active and request.user.pk == report.reporter_id:
        return True
    try:
        payload = signing.loads(request.GET.get("preview", ""), salt=PREVIEW_SALT, max_age=300)
    except signing.BadSignature:
        return False
    if payload.get("report") != report.pk or payload.get("photo") != path:
        return False
    token = MobileAccessToken.objects.select_related("user").filter(pk=payload.get("session"), user_id=report.reporter_id).first()
    return bool(token and token.is_valid())


@never_cache
def protected_media_serve(request, path, document_root=None):
    # Normalize before selecting the policy, so /other/../lost-pets cannot bypass it.
    path = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
    if path == ".." or path.startswith("../"):
        raise Http404
    if any(part != part.rstrip(" .") or ":" in part for part in path.split("/")):
        raise Http404
    root = Path(document_root or settings.MEDIA_ROOT).resolve()
    try:
        # Resolve filesystem aliases and symlinks before deciding visibility.
        path = (root / path).resolve(strict=True).relative_to(root).as_posix()
    except (OSError, RuntimeError, ValueError):
        raise Http404
    if path.casefold().startswith("lost-pets/"):
        reports = LostPetReport.objects.filter(photo=path)
        sightings = Sighting.objects.filter(photo=path)
        public = reports.filter(status__in=PUBLIC_REPORT_STATUSES).exists() or sightings.filter(
            status=Sighting.Status.PUBLISHED, report__status__in=PUBLIC_REPORT_STATUSES,
        ).exists()
        allowed = public
        if not allowed and can_review_reports(request.user):
            allowed = reports.exists()
        if not allowed and can_review_sightings(request.user):
            allowed = sightings.filter(report__in=reports_visible_to(request.user)).exists()
        if not allowed:
            allowed = any(_can_preview_request(request, report, path) for report in reports)
        if not allowed:
            raise Http404
    return serve(request, path, document_root=root)
