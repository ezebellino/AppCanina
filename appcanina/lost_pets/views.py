from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from patients.models import Patient

from .forms import LostPetReportForm, SightingForm
from .models import CommunityNotification, LostPetReport, Sighting


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
def report_list(request):
    view_mode = request.GET.get("view", "active")
    reports = LostPetReport.objects.select_related("patient", "reporter").prefetch_related("sightings")
    if view_mode == "all":
        pass
    elif view_mode == "resolved":
        reports = reports.filter(status=LostPetReport.Status.RESOLVED)
    else:
        view_mode = "active"
        reports = reports.filter(status=LostPetReport.Status.PUBLISHED)
    active_count = LostPetReport.objects.filter(status=LostPetReport.Status.PUBLISHED).count()
    latest_sighting = Sighting.objects.filter(status=Sighting.Status.PUBLISHED).order_by("-seen_at").first()
    return render(request, "lost_pets/report_list.html", {"reports": reports, "view_mode": view_mode, "active_count": active_count, "latest_sighting": latest_sighting})


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
        messages.success(request, "El aviso fue publicado y ya puede recibir avistamientos.")
        return redirect("lost_pet_detail", report_id=report.id)
    return render(request, "lost_pets/report_form.html", {"form": form})


@login_required
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
def report_detail(request, report_id):
    report = get_object_or_404(LostPetReport.objects.select_related("patient", "reporter").prefetch_related("sightings__reporter"), pk=report_id)
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
        if report.reporter_id != request.user.id:
            CommunityNotification.objects.create(recipient=report.reporter, report=report, sighting=sighting, title=f"Nuevo avistamiento de {report.name}", body=f"{sighting.area_label} · {sighting.seen_at:%d/%m %H:%M}")
        messages.success(request, "El avistamiento fue publicado de inmediato.")
        return redirect("lost_pet_detail", report_id=report.id)
    return render(request, "lost_pets/sighting_form.html", {"form": form, "report": report})


@login_required
@permission_required("lost_pets.change_lostpetreport", raise_exception=True)
@require_POST
def report_change_status(request, report_id):
    report = get_object_or_404(LostPetReport, pk=report_id)
    allowed_statuses = {LostPetReport.Status.PUBLISHED, LostPetReport.Status.HIDDEN, LostPetReport.Status.RESOLVED, LostPetReport.Status.ARCHIVED}
    status = request.POST.get("status")
    if status not in allowed_statuses:
        messages.error(request, "El estado indicado no es válido.")
    else:
        report.status = status
        report.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Aviso marcado como {report.get_status_display().lower()}.")
    return redirect("lost_pet_detail", report_id=report.id)
