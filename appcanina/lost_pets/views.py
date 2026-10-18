from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from patients.models import Patient

from .forms import AdoptionPostForm, LostPetReportForm, SightingForm
from .models import AdoptionInterest, AdoptionPost, LostPetReport, Sighting
from .notifications import notify_new_report, notify_new_sighting, notify_request_review
from organizations.roles import can_manage_organization, is_community_collaborator, organizations_managed_by, verified_shelters_managed_by


def _adoption_manager_organizations(user):
    if user.has_perm("lost_pets.change_adoptionpost"):
        return organizations_managed_by(user)
    return verified_shelters_managed_by(user)


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
def report_list(request):
    view_mode = request.GET.get("view", "active")
    reports = LostPetReport.objects.select_related("patient", "reporter").prefetch_related("sightings")
    if is_community_collaborator(request.user):
        view_mode = "active"
        reports = reports.filter(status=LostPetReport.Status.PUBLISHED)
    elif view_mode == "all":
        pass
    elif view_mode == "resolved":
        reports = reports.filter(status=LostPetReport.Status.RESOLVED)
    elif view_mode == "requests":
        reports = reports.filter(requested_via_mobile=True, status=LostPetReport.Status.HIDDEN)
    else:
        view_mode = "active"
        reports = reports.filter(status=LostPetReport.Status.PUBLISHED)
    active_count = LostPetReport.objects.filter(status=LostPetReport.Status.PUBLISHED).count()
    pending_request_count = LostPetReport.objects.filter(requested_via_mobile=True, status=LostPetReport.Status.HIDDEN).count()
    latest_sighting = Sighting.objects.filter(status=Sighting.Status.PUBLISHED).order_by("-seen_at").first()
    return render(request, "lost_pets/report_list.html", {"reports": reports, "view_mode": view_mode, "active_count": active_count, "pending_request_count": pending_request_count, "latest_sighting": latest_sighting})


@login_required
def adoption_list(request):
    view_mode = request.GET.get("view", "published")
    posts = AdoptionPost.objects.select_related("publisher", "organization")
    managed_organizations = _adoption_manager_organizations(request.user)
    can_manage_adoptions = managed_organizations.exists()
    if not (request.user.has_perm("lost_pets.view_adoptionpost") or can_manage_adoptions):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    if view_mode == "review" and can_manage_adoptions:
        posts = posts.filter(status=AdoptionPost.Status.PENDING, organization__in=managed_organizations)
    elif view_mode == "all" and can_manage_adoptions:
        posts = posts.filter(organization__in=managed_organizations)
    else:
        view_mode = "published"
        posts = posts.filter(status=AdoptionPost.Status.PUBLISHED)
    pending_count = AdoptionPost.objects.filter(status=AdoptionPost.Status.PENDING, organization__in=managed_organizations).count()
    return render(request, "lost_pets/adoption_list.html", {"posts": posts, "view_mode": view_mode, "pending_count": pending_count, "can_manage_adoptions": can_manage_adoptions, "managed_organization_ids": list(managed_organizations.values_list("id", flat=True))})


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
def adoption_create(request):
    shelter = verified_shelters_managed_by(request.user).first()
    if not shelter:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    form = AdoptionPostForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.publisher = request.user
        post.organization = shelter
        post.status = AdoptionPost.Status.PUBLISHED
        post.save()
        messages.success(request, f"{post.name} ya está publicado para adopción.")
        return redirect("adoption_list")
    return render(request, "lost_pets/adoption_form.html", {"form": form, "shelter": shelter})


@login_required
@login_required
@require_POST
def adoption_change_status(request, post_id):
    post = get_object_or_404(AdoptionPost, pk=post_id)
    managed_organizations = _adoption_manager_organizations(request.user)
    if post.organization and not managed_organizations.filter(pk=post.organization_id).exists():
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    status = request.POST.get("status")
    allowed = {AdoptionPost.Status.PUBLISHED, AdoptionPost.Status.REJECTED, AdoptionPost.Status.ADOPTED, AdoptionPost.Status.ARCHIVED}
    if status not in allowed:
        messages.error(request, "El estado indicado no es válido.")
    elif status == AdoptionPost.Status.REJECTED and not request.POST.get("review_note", "").strip():
        messages.error(request, "Indicá un motivo breve para rechazar la publicación.")
    else:
        post.status = status
        post.review_note = request.POST.get("review_note", "").strip()[:280] if status == AdoptionPost.Status.REJECTED else ""
        post.save(update_fields=["status", "review_note", "updated_at"])
        messages.success(request, f"Publicación marcada como {post.get_status_display().lower()}.")
    return redirect("adoption_list")


@login_required
@permission_required("lost_pets.change_adoptioninterest", raise_exception=True)
def adoption_interest_list(request):
    interests = AdoptionInterest.objects.select_related("post", "post__organization", "applicant").filter(post__organization__in=organizations_managed_by(request.user))
    return render(request, "lost_pets/adoption_interest_list.html", {"interests": interests, "status_choices": AdoptionInterest.Status.choices})


@login_required
@permission_required("lost_pets.change_adoptioninterest", raise_exception=True)
@require_POST
def adoption_interest_change_status(request, interest_id):
    interest = get_object_or_404(AdoptionInterest, pk=interest_id)
    if interest.post.organization and not can_manage_organization(request.user, interest.post.organization):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    status = request.POST.get("status")
    if status not in AdoptionInterest.Status.values:
        messages.error(request, "El estado indicado no es válido.")
    else:
        interest.status = status
        interest.staff_note = request.POST.get("staff_note", "").strip()[:280]
        interest.save(update_fields=["status", "staff_note", "updated_at"])
        messages.success(request, "Estado del interés actualizado.")
    return redirect("adoption_interest_list")


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
def map_view(request):
    return render(request, "lost_pets/map.html")


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
@require_GET
def map_data(request):
    reports = LostPetReport.objects.filter(status=LostPetReport.Status.PUBLISHED).prefetch_related("sightings")
    markers = []
    for report in reports:
        latest_sighting = next((sighting for sighting in report.sightings.all() if sighting.status == Sighting.Status.PUBLISHED), None)
        location = latest_sighting or report
        coordinates = location.public_coordinates
        markers.append({
            "id": report.id,
            "name": report.name,
            "species": report.get_species_display(),
            "area": location.area_label,
            "seen_at": location.seen_at.isoformat() if latest_sighting else report.last_seen_at.isoformat(),
            "has_approximate_location": coordinates is not None,
            "public_latitude": coordinates[0] if coordinates else None,
            "public_longitude": coordinates[1] if coordinates else None,
            "detail_url": request.build_absolute_uri(f"/extraviados/{report.id}/"),
            "photo_url": request.build_absolute_uri(report.photo.url) if report.photo else None,
        })
    return JsonResponse({"markers": markers})


@login_required
@permission_required("lost_pets.add_lostpetreport", raise_exception=True)
def report_create(request):
    patient_id = request.GET.get("patient")
    initial = {"patient": patient_id, "last_seen_at": timezone.localtime().replace(second=0, microsecond=0)}
    if patient_id:
        patient = get_object_or_404(Patient, pk=patient_id, active=True)
        initial.update({"name": patient.name, "species": patient.species, "breed": patient.breed})
    form = LostPetReportForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        report.reporter = request.user
        report.status = LostPetReport.Status.PUBLISHED
        report.save()
        notify_new_report(report)
        messages.success(request, "El aviso fue publicado y ya puede recibir avistamientos.")
        return redirect("lost_pet_detail", report_id=report.id)
    return render(request, "lost_pets/report_form.html", {"form": form})


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
def report_detail(request, report_id):
    reports = LostPetReport.objects.select_related("patient", "reporter").prefetch_related("sightings__reporter")
    if is_community_collaborator(request.user):
        reports = reports.filter(status=LostPetReport.Status.PUBLISHED)
    report = get_object_or_404(reports, pk=report_id)
    return render(request, "lost_pets/report_detail.html", {"report": report, "sightings": report.sightings.all()})


@login_required
@permission_required("lost_pets.add_sighting", raise_exception=True)
def sighting_create(request, report_id):
    report = get_object_or_404(LostPetReport, pk=report_id, status=LostPetReport.Status.PUBLISHED)
    form = SightingForm(request.POST or None, request.FILES or None, initial={"seen_at": timezone.localtime().replace(second=0, microsecond=0)})
    if request.method == "POST" and form.is_valid():
        sighting = form.save(commit=False)
        sighting.report = report
        sighting.reporter = request.user
        sighting.status = Sighting.Status.PUBLISHED
        sighting.save()
        notify_new_sighting(report, sighting)
        messages.success(request, "El avistamiento fue publicado de inmediato.")
        return redirect("lost_pet_detail", report_id=report.id)
    return render(request, "lost_pets/sighting_form.html", {"form": form, "report": report})


@login_required
@permission_required("lost_pets.change_lostpetreport", raise_exception=True)
@require_POST
def report_change_status(request, report_id):
    report = get_object_or_404(LostPetReport, pk=report_id)
    allowed_statuses = {LostPetReport.Status.PUBLISHED, LostPetReport.Status.HIDDEN, LostPetReport.Status.REJECTED, LostPetReport.Status.RESOLVED, LostPetReport.Status.ARCHIVED}
    status = request.POST.get("status")
    if status not in allowed_statuses:
        messages.error(request, "El estado indicado no es válido.")
    elif status == LostPetReport.Status.REJECTED and not request.POST.get("review_note", "").strip():
        messages.error(request, "Indicá un motivo breve para rechazar la solicitud.")
    else:
        was_published = report.status == LostPetReport.Status.PUBLISHED
        report.status = status
        report.review_note = request.POST.get("review_note", "").strip()[:280] if status == LostPetReport.Status.REJECTED else ""
        report.save(update_fields=["status", "review_note", "updated_at"])
        if status == LostPetReport.Status.PUBLISHED and not was_published:
            notify_new_report(report)
        if report.requested_via_mobile and status in {LostPetReport.Status.PUBLISHED, LostPetReport.Status.REJECTED}:
            notify_request_review(report)
        messages.success(request, f"Aviso marcado como {report.get_status_display().lower()}.")
    return redirect("lost_pet_detail", report_id=report.id)
