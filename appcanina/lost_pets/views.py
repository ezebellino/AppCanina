from config.public_urls import public_url
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db.models import Prefetch, Q
from django.core.cache import cache
from patients.ownership import owner_relations
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from patients.models import Patient

from .forms import AdoptionPostForm, LostPetReportForm, SightingForm
from .models import AdoptionInterest, AdoptionPost, LostPetReport, Sighting
from .notifications import notify_new_report, notify_new_sighting, notify_request_review
from .adoption_email import notify_visit
from .resolution import manageable_searches, finish_search
from .permissions import report_read_required
from .visibility import reports_visible_to, sightings_visible_to, can_review_reports
from .adoption_updates import managed_interest_organizations, read_inbox, unread_counts
from organizations.roles import can_manage_organization, is_community_collaborator, organizations_managed_by, verified_shelters_managed_by


def _adoption_manager_organizations(user):
    if user.has_perm("lost_pets.change_adoptionpost"):
        return organizations_managed_by(user)
    return verified_shelters_managed_by(user)


@report_read_required
def report_list(request):
    view_mode = request.GET.get("view", "active")
    visible_reports = reports_visible_to(request.user)
    reports = visible_reports.select_related("patient", "reporter").prefetch_related(
        Prefetch("sightings", queryset=sightings_visible_to(request.user))
    )
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
    pending_request_count = visible_reports.filter(requested_via_mobile=True, status=LostPetReport.Status.HIDDEN).count() if can_review_reports(request.user) else 0
    latest_sighting = sightings_visible_to(request.user).filter(status=Sighting.Status.PUBLISHED).select_related("report").order_by("-seen_at").first()
    closable_ids = set(manageable_searches(request.user).filter(status=LostPetReport.Status.PUBLISHED).values_list("id", flat=True))
    for report in reports:
        report.can_finish_search = report.id in closable_ids
    return render(request, "lost_pets/report_list.html", {"reports": reports, "view_mode": view_mode, "active_count": active_count, "pending_request_count": pending_request_count, "latest_sighting": latest_sighting})


@login_required
def adoption_list(request):
    view_mode = request.GET.get("view", "published")
    posts = AdoptionPost.objects.select_related("publisher", "organization")
    managed_organizations = _adoption_manager_organizations(request.user)
    can_manage_adoptions = managed_organizations.exists()
    if not (request.user.is_staff or request.user.has_perm("lost_pets.view_lostpetreport")
            or request.user.has_perm("lost_pets.view_adoptionpost") or can_manage_adoptions):
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
    can_manage_post = (
        managed_organizations.filter(pk=post.organization_id).exists()
        if post.organization_id else request.user.has_perm("lost_pets.change_adoptionpost")
    )
    if not can_manage_post:
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
@permission_required("lost_pets.view_lostpetreport", raise_exception=True)
@require_http_methods(["GET", "POST"])
def adoption_interest_create(request, post_id):
    post = get_object_or_404(AdoptionPost.objects.select_related("organization", "publisher"), pk=post_id, status=AdoptionPost.Status.PUBLISHED)
    interest = AdoptionInterest.objects.filter(post=post, applicant=request.user).first()
    message = ""
    error = ""
    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        if interest:
            messages.info(request, "Ya enviaste tu interés por este animal.")
            return redirect("adoption_interest_create", post_id=post.id)
        if not 10 <= len(message) <= 700:
            error = "Contanos por qué te interesa adoptar, entre 10 y 700 caracteres."
        else:
            interest, created = AdoptionInterest.objects.get_or_create(
                post=post, applicant=request.user, defaults={"message": message},
            )
            messages.success(request, "Tu interés quedó registrado de forma privada." if created else "Ya enviaste tu interés por este animal.")
            return redirect("adoption_interest_create", post_id=post.id)
    return render(request, "lost_pets/adoption_interest_form.html", {"post": post, "interest": interest, "message": message, "error": error})


@login_required
@require_GET
def my_adoption_interests(request):
    interests = AdoptionInterest.objects.filter(applicant=request.user).select_related(
        "post", "post__organization"
    ).order_by("-updated_at", "-id")
    return render(request, "lost_pets/my_adoption_interests.html", {"interests": read_inbox(interests, request.user, "applicant")})


@login_required
@require_GET
def adoption_update_counts(request):
    response = JsonResponse(unread_counts(request.user))
    response["Cache-Control"] = "no-store"
    return response


def _interest_manager_organizations(user):
    return managed_interest_organizations(user)


@login_required
@require_POST
def adoption_visit_request(request, interest_id):
    interest = get_object_or_404(AdoptionInterest.objects.select_related("post__organization"), pk=interest_id, applicant=request.user)
    organization = interest.post.organization
    if (interest.post.status != AdoptionPost.Status.PUBLISHED or not organization
            or organization.kind != "shelter" or not organization.is_verified
            or interest.status in (AdoptionInterest.Status.CLOSED, AdoptionInterest.Status.COMPLETED)):
        messages.error(request, "Esta solicitud no está disponible para coordinar una visita.")
    else:
        changed = AdoptionInterest.objects.filter(pk=interest.pk, visit_status=AdoptionInterest.VisitStatus.NONE).update(
            visit_status=AdoptionInterest.VisitStatus.REQUESTED, visit_requested_at=timezone.now(), updated_at=timezone.now(), institution_activity_at=timezone.now(),
        )
        messages.info(request, "Solicitud de visita enviada al refugio." if changed else "La visita ya tiene una solicitud registrada.")
        if changed:
            interest.refresh_from_db()
            if not notify_visit(interest, request):
                messages.warning(request, "La visita quedó solicitada, pero no pudimos enviar el aviso por correo. El refugio puede verla en su bandeja de solicitudes.")
    return redirect("my_adoption_interests")


@login_required
@require_POST
def adoption_visit_respond(request, interest_id):
    interest = get_object_or_404(
        AdoptionInterest.objects.select_related("post__organization"), pk=interest_id,
        post__organization__in=_interest_manager_organizations(request.user),
        post__organization__kind="shelter", post__organization__is_verified=True,
    )
    action = request.POST.get("action")
    address = (request.POST.get("visit_address") or "").strip()
    instructions = (request.POST.get("visit_instructions") or "").strip()
    if action not in ("accept", "decline") or len(instructions) > 280:
        messages.error(request, "Revisá la respuesta y las indicaciones (hasta 280 caracteres).")
    elif action == "accept" and (not address or len(address) > 300 or interest.post.status != AdoptionPost.Status.PUBLISHED
            or interest.status in (AdoptionInterest.Status.CLOSED, AdoptionInterest.Status.COMPLETED)):
        messages.error(request, "Para aceptar, indicá una dirección (hasta 300 caracteres) y verificá que la adopción siga disponible.")
    else:
        changed = AdoptionInterest.objects.filter(pk=interest.pk, visit_status=AdoptionInterest.VisitStatus.REQUESTED).update(
            visit_status=AdoptionInterest.VisitStatus.ACCEPTED if action == "accept" else AdoptionInterest.VisitStatus.DECLINED,
            visit_address=address if action == "accept" else "", visit_instructions=instructions,
            visit_answered_at=timezone.now(), updated_at=timezone.now(), applicant_activity_at=timezone.now(),
        )
        messages.success(request, "Respuesta guardada. La persona la verá en Mis solicitudes." if changed else "Esta visita ya fue respondida o no fue solicitada.")
        if changed:
            interest.refresh_from_db()
            if not notify_visit(interest, request):
                messages.warning(request, "La respuesta quedó guardada, pero no pudimos enviar el aviso por correo. La persona puede verla en Mis solicitudes.")
    return redirect("adoption_interest_list")


@login_required
def adoption_interest_list(request):
    if not _interest_manager_organizations(request.user).exists() and not request.user.has_perm("lost_pets.change_adoptioninterest"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    interests = AdoptionInterest.objects.select_related("post", "post__organization", "applicant").filter(post__organization__in=_interest_manager_organizations(request.user))
    counts = {"total": interests.count(), "received": interests.filter(status=AdoptionInterest.Status.RECEIVED).count(), "visits": interests.filter(visit_status=AdoptionInterest.VisitStatus.REQUESTED).count()}
    view_mode = request.GET.get("view", "all")
    if view_mode == "received":
        interests = interests.filter(status=AdoptionInterest.Status.RECEIVED)
    elif view_mode == "visits":
        interests = interests.filter(visit_status=AdoptionInterest.VisitStatus.REQUESTED)
    else:
        view_mode = "all"
    return render(request, "lost_pets/adoption_interest_list.html", {"interests": read_inbox(interests.order_by("-created_at"), request.user, "institution"), "status_choices": AdoptionInterest.Status.choices, "counts": counts, "view_mode": view_mode})


@login_required
@require_POST
def adoption_interest_change_status(request, interest_id):
    interest = get_object_or_404(AdoptionInterest, pk=interest_id, post__organization__in=_interest_manager_organizations(request.user))
    if interest.post.organization and not can_manage_organization(request.user, interest.post.organization):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    status = request.POST.get("status")
    if status not in AdoptionInterest.Status.values:
        messages.error(request, "El estado indicado no es válido.")
    else:
        note = request.POST.get("staff_note", "").strip()[:280]
        if interest.status != status or interest.staff_note != note:
            interest.applicant_activity_at = timezone.now()
        interest.status = status
        interest.staff_note = note
        interest.save(update_fields=["status", "staff_note", "updated_at", "applicant_activity_at"])
        messages.success(request, "Estado del interés actualizado.")
    return redirect("adoption_interest_list")


@report_read_required
def map_view(request):
    return render(request, "lost_pets/map.html")


@report_read_required
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
            "detail_url": public_url(request, f"/extraviados/{report.id}/"),
            "photo_url": public_url(request, report.photo.url) if report.photo else None,
        })
    return JsonResponse({"markers": markers})


@report_read_required
@require_http_methods(["GET", "POST"])
def report_create(request, report_id=None):
    editing = None
    if report_id is not None:
        editing = get_object_or_404(LostPetReport, pk=report_id, reporter=request.user,
                                    requested_via_mobile=True, status__in=["hidden", "rejected"])
    direct = request.user.has_perm("lost_pets.add_lostpetreport") and editing is None
    patient_id = request.GET.get("patient")
    initial = {"patient": patient_id, "last_seen_at": timezone.localtime().replace(second=0, microsecond=0)} if not editing else {}
    own_ids = owner_relations(request.user).values("patient_id")
    if direct:
        managed = organizations_managed_by(request.user)
    else:
        managed = verified_shelters_managed_by(request.user)
    visible_patients = Patient.objects.filter(active=True).filter(Q(pk__in=own_ids) | Q(organization__in=managed))
    if request.user.is_superuser:
        visible_patients = Patient.objects.filter(active=True)
    if patient_id:
        patient = get_object_or_404(visible_patients, pk=patient_id)
        initial.update({"name": patient.name, "species": patient.species, "breed": patient.breed})
    form = LostPetReportForm(request.POST or None, request.FILES or None, initial=initial,
                            instance=editing, patient_queryset=visible_patients)
    form.fields["patient"].label = "Vincular con uno de mis animales (opcional)"
    if request.method == "POST" and form.is_valid():
        key = f"mobile-search-request:{request.META.get('REMOTE_ADDR', 'unknown')}"
        if not direct and not editing and cache.get(key, 0) >= 3:
            form.add_error(None, "Ya enviaste varias búsquedas. Probá nuevamente más tarde.")
        else:
            report = form.save(commit=False)
            report.reporter = request.user
            report.status = LostPetReport.Status.PUBLISHED if direct else LostPetReport.Status.HIDDEN
            report.requested_via_mobile = not direct  # Existing community moderation/preview workflow, shared with web.
            report.review_note = ""
            report.save()
            if direct:
                notify_new_report(report)
                messages.success(request, "El aviso fue publicado y ya puede recibir avistamientos.")
                return redirect("lost_pet_detail", report_id=report.id)
            if not editing:
                cache.set(key, cache.get(key, 0) + 1, 3600)
            messages.success(request, "Recibimos tu búsqueda. El equipo la revisará antes de publicarla.")
            return redirect("my_search_requests")
    animal_data = {str(patient.pk): {
        "name": patient.name, "species": patient.species, "breed": patient.breed,
        "photo": patient.photo.url if patient.photo else "",
    } for patient in form.fields["patient"].queryset}
    response = render(request, "lost_pets/report_form.html", {
        "form": form, "direct_publish": direct, "editing_request": editing, "animal_data": animal_data,
    })
    response["Cache-Control"] = "no-store"
    return response


@report_read_required
@require_GET
def my_search_requests(request):
    reports = LostPetReport.objects.filter(reporter=request.user).order_by("-updated_at", "-id")
    from django.core.paginator import Paginator
    page = Paginator(reports, 20).get_page(request.GET.get("page"))
    response = render(request, "lost_pets/my_search_requests.html", {"page_obj": page})
    response["Cache-Control"] = "no-store"
    return response


@report_read_required
def report_detail(request, report_id):
    reports = reports_visible_to(request.user).select_related("patient", "reporter")
    report = get_object_or_404(reports, pk=report_id)
    can_finish_search = report.status == LostPetReport.Status.PUBLISHED and manageable_searches(request.user).filter(pk=report.pk).exists()
    return render(request, "lost_pets/report_detail.html", {"report": report, "can_finish_search": can_finish_search, "sightings": sightings_visible_to(request.user).filter(report=report).select_related("reporter")})


@report_read_required
@require_http_methods(["GET", "POST"])
def report_found(request, report_id):
    report = get_object_or_404(manageable_searches(request.user), pk=report_id, status__in=["published", "resolved"])
    if request.method == "POST":
        changed = finish_search(request.user, report.pk)
        messages.success(request, f"¡{report.name} fue encontrado! La búsqueda quedó finalizada." if changed else "La búsqueda ya no está activa.")
        return redirect("lost_pet_list")
    return render(request, "lost_pets/report_found.html", {"report": report})


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
