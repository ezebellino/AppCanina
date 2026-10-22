import logging
import hashlib
from datetime import timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import DatabaseError, transaction
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import CareReminderForm, ClinicalRecordForm, ContactForm, ExistingPatientContactForm, OwnerAccountLinkForm, PatientContactForm, PatientForm, TravelAccessRequestForm
from .models import CareReminder, ClinicalHistoryAccessLog, Contact, OwnerAccountLink, Patient, PatientContact, PatientSharingConsent, TravelAccessRequest, TravelCredential
from organizations.roles import organizations_managed_by
from sales.models import CashSession, Sale
from inventory.models import Product
from grooming.models import GroomingAppointment
from visits.models import HomeVisit


logger = logging.getLogger(__name__)


def _operating_organizations(user):
    """Organizations the signed-in staff member is allowed to operate.

    Clinical permissions are deliberately global Django permissions because they
    describe a role.  The organization membership is the second, mandatory
    boundary that decides which clinical data that role may access.
    """
    return organizations_managed_by(user)


def _patients_visible_to(user):
    """Return only the clinical files visible in the current organization scope.

    ``organization=None`` is intentionally not visible to regular staff.  The
    data migration assigns historic records to the primary business profile;
    keeping unassigned data superuser-only prevents a fallback from becoming a
    cross-tenant bypass.
    """
    if user.is_superuser:
        return Patient.objects.all()
    return Patient.objects.filter(organization__in=_operating_organizations(user))


def _patient_or_404_for(user, patient_id, *, active_only=False):
    patients = _patients_visible_to(user)
    if active_only:
        patients = patients.filter(active=True)
    return get_object_or_404(patients, pk=patient_id)


def _default_operating_organization(user):
    """Choose a server-side organization for a new clinical file.

    A member may belong to several institutions.  Prefer the designated
    business profile when it is one of them; otherwise use the first owned
    organization deterministically.  The browser never submits this value.
    """
    organizations = _operating_organizations(user)
    return organizations.filter(is_business_profile=True).first() or organizations.order_by("id").first()


def _owned_patient_or_404(user, patient_id):
    contact_ids = OwnerAccountLink.objects.filter(user=user).values_list("contact_id", flat=True)
    return get_object_or_404(Patient.objects.prefetch_related("clinical_records__professional"), pk=patient_id, patientcontact__contact_id__in=contact_ids)


@login_required
def my_animals(request):
    contact_ids = OwnerAccountLink.objects.filter(user=request.user).values_list("contact_id", flat=True)
    patients = Patient.objects.filter(patientcontact__contact_id__in=contact_ids, active=True).distinct().prefetch_related("patientcontact_set__contact")
    return render(request, "patients/my_animals.html", {"patients": patients})


@login_required
def my_animal_history(request, patient_id):
    patient = _owned_patient_or_404(request.user, patient_id)
    contact_ids = OwnerAccountLink.objects.filter(user=request.user).values_list("contact_id", flat=True)
    sharing_enabled = PatientSharingConsent.objects.filter(patient=patient, contact_id__in=contact_ids, enabled=True).exists()
    return render(request, "patients/my_animal_history.html", {"patient": patient, "sharing_enabled": sharing_enabled})


@login_required
@require_POST
def my_animal_sharing(request, patient_id):
    patient = _owned_patient_or_404(request.user, patient_id)
    contact_ids = OwnerAccountLink.objects.filter(user=request.user).values_list("contact_id", flat=True)
    relation = patient.patientcontact_set.filter(contact_id__in=contact_ids).select_related("contact").first()
    consent, _ = PatientSharingConsent.objects.update_or_create(patient=patient, contact=relation.contact, defaults={"enabled": request.POST.get("enabled") == "on"})
    messages.success(request, "Preferencia de historial compartido actualizada." if consent.enabled else "El acceso compartido fue desactivado.")
    return redirect("my_animal_history", patient_id=patient.id)


@login_required
def my_animal_credential(request, patient_id):
    patient = _owned_patient_or_404(request.user, patient_id)
    contact_ids = OwnerAccountLink.objects.filter(user=request.user).values_list("contact_id", flat=True)
    relation = patient.patientcontact_set.filter(contact_id__in=contact_ids).select_related("contact").first()
    code, credential = TravelCredential.issue(patient, relation.contact, timezone.now() + timedelta(days=7))
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buffer = BytesIO(); pdf = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    pdf.setTitle(f"Credencial de viaje - {patient.name}"); pdf.setFont("Helvetica-Bold", 18); pdf.drawString(54, height - 64, "Credencial veterinaria de viaje")
    pdf.setFont("Helvetica", 11); lines = [f"Animal: {patient.name}", f"Especie: {patient.get_species_display()}", f"Raza: {patient.breed or 'No informada'}", f"Identificación: {patient.microchip or 'No informada'}", f"Responsable: {relation.contact.full_name}", f"Válida hasta: {credential.expires_at.astimezone().strftime('%d/%m/%Y %H:%M')}", f"Código temporal: {code}", "Presentala voluntariamente en una veterinaria. No habilita acceso automático por GPS."]
    y = height - 112
    for line in lines: pdf.drawString(54, y, line); y -= 24
    pdf.setFont("Helvetica-Oblique", 9); pdf.drawString(54, 58, "AppCanina - Información clínica bajo consentimiento del responsable."); pdf.save()
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf"); response["Content-Disposition"] = f'attachment; filename="credencial-{patient.name.lower()}.pdf"'; return response


@login_required
@permission_required("patients.change_patientcontact", raise_exception=True)
def patient_owner_account_link(request, patient_id):
    patient = get_object_or_404(_patients_visible_to(request.user).prefetch_related("patientcontact_set__contact"), pk=patient_id)
    form = OwnerAccountLinkForm(request.POST or None)
    relation = patient.patientcontact_set.select_related("contact").filter(role__in=[PatientContact.Role.RESPONSIBLE, PatientContact.Role.ADOPTER]).first()
    if request.method == "POST" and relation and form.is_valid():
        OwnerAccountLink.objects.get_or_create(contact=relation.contact, user=form.cleaned_data["user"])
        messages.success(request, "Cuenta vinculada. La persona ya puede consultar sus animales desde Mis animales.")
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patients/owner_account_link.html", {"patient": patient, "relation": relation, "form": form})


@login_required
@permission_required("patients.view_clinicalrecord", raise_exception=True)
def travel_access_request(request):
    form = TravelAccessRequestForm(request.POST or None)
    organizations = organizations_managed_by(request.user).filter(kind="veterinary")
    organization = organizations.first()
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["credential_code"].strip()
        credential = TravelCredential.objects.select_related("patient", "contact").filter(digest=hashlib.sha256(code.encode()).hexdigest(), revoked_at__isnull=True).first()
        locality = form.cleaned_data["locality"].strip()
        allowed = bool(credential and organization and credential.expires_at > timezone.now() and organization.locality.strip().casefold() == locality.casefold() and PatientSharingConsent.objects.filter(patient=credential.patient, contact=credential.contact, enabled=True).exists())
        request_entry = TravelAccessRequest.objects.create(patient=credential.patient if credential else Patient.objects.none().first(), credential=credential, organization=organization, requester=request.user, locality=locality, purpose=form.cleaned_data["purpose"], status=TravelAccessRequest.Status.APPROVED if allowed else TravelAccessRequest.Status.DENIED, expires_at=min(credential.expires_at, timezone.now() + timedelta(hours=24)) if allowed else None) if credential and organization else None
        if not request_entry:
            messages.error(request, "No se pudo validar la credencial o la veterinaria solicitante.")
        elif request_entry.is_active:
            return redirect("travel_access_history", request_id=request_entry.id)
        else:
            messages.error(request, "Acceso no autorizado: verificá la credencial, el consentimiento y la localidad declarada.")
    return render(request, "patients/travel_access_request.html", {"form": form, "organization": organization})


@login_required
@permission_required("patients.view_clinicalrecord", raise_exception=True)
def travel_access_history(request, request_id):
    access = get_object_or_404(TravelAccessRequest.objects.select_related("patient", "organization"), pk=request_id, requester=request.user)
    if not access.is_active:
        messages.error(request, "Esta autorización ya no está vigente.")
        return redirect("travel_access_request")
    # One audit entry per approved request keeps the record meaningful while
    # allowing the professional to revisit the page during the same consultation.
    ClinicalHistoryAccessLog.objects.get_or_create(
        patient=access.patient,
        organization=access.organization,
        user=request.user,
        travel_request=access,
    )
    return render(request, "patients/travel_access_history.html", {"access": access, "patient": access.patient})


@login_required
def dashboard(request):
    """Compact desktop-first landing page for the day-to-day operation."""
    if request.user.is_staff:
        return redirect("platform_dashboard")
    if (
        request.user.has_perm("lost_pets.view_lostpetreport")
        and not request.user.has_perm("patients.view_patient")
        and not request.user.has_perm("grooming.view_groomingappointment")
        and not request.user.has_perm("inventory.view_product")
    ):
        return redirect("lost_pet_list")
    today = timezone.localdate()
    organization = _default_operating_organization(request.user)
    visible_patients = _patients_visible_to(request.user)
    metrics = []
    attention = []
    if request.user.has_perm("patients.view_patient"):
        metrics.append({"value": visible_patients.filter(active=True).count(), "label": "pacientes activos", "url": "patient_list", "tone": "teal"})
    if request.user.has_perm("grooming.view_groomingappointment"):
        turns_today = GroomingAppointment.objects.filter(patient__in=visible_patients, starts_at__date=today).exclude(status=GroomingAppointment.Status.CANCELED).count()
        metrics.append({"value": turns_today, "label": "turnos de hoy", "url": "grooming_agenda", "tone": "amber"})
    if request.user.has_perm("visits.view_homevisit"):
        visits_today = HomeVisit.objects.filter(patient__in=visible_patients, scheduled_for__date=today).exclude(status=HomeVisit.Status.CANCELED).count()
        metrics.append({"value": visits_today, "label": "visitas de hoy", "url": "home_visit_list", "tone": "blue"})
    if request.user.has_perm("patients.view_carereminder"):
        due_reminders = CareReminder.objects.filter(patient__in=visible_patients, completed_on__isnull=True, due_on__lte=today)
        if due_reminders.exists():
            attention.append({"value": due_reminders.count(), "label": "recordatorios clínicos pendientes", "url": "care_reminder_list"})
    if request.user.has_perm("inventory.view_product"):
        products = Product.objects.filter(organization=organization, active=True) if organization else Product.objects.none()
        low_stock = products.filter(stock__lte=F("minimum_stock")).count()
        metrics.append({"value": products.count(), "label": "productos activos", "url": "inventory_list", "tone": "blue"})
        if low_stock:
            attention.append({"value": low_stock, "label": "productos con stock bajo", "url": "inventory_alerts"})
    if request.user.has_perm("sales.view_sale"):
        sales_total = Sale.objects.filter(created_at__date=today).aggregate(total=Sum("total"))["total"] or 0
        metrics.append({"value": f"${sales_total:,.0f}", "label": "ventas de hoy", "url": "daily_report", "tone": "teal"})
    return render(request, "patients/dashboard.html", {"metrics": metrics, "attention": attention})


@login_required
@permission_required("patients.view_patient", raise_exception=True)
def patient_list(request):
    query = request.GET.get("q", "").strip()
    species = request.GET.get("species", "").strip()
    patients = _patients_visible_to(request.user).filter(active=True).prefetch_related("patientcontact_set__contact")
    if query:
        patients = patients.filter(Q(name__icontains=query) | Q(breed__icontains=query) | Q(microchip__icontains=query) | Q(contacts__full_name__icontains=query) | Q(contacts__phone__icontains=query) | Q(contacts__email__icontains=query)).distinct()
    if species in dict(Patient.Species.choices):
        patients = patients.filter(species=species)
    return render(
        request,
        "patients/patient_list.html",
        {
            "patients": patients,
            "query": query,
            "species": species,
            "species_choices": Patient.Species.choices,
            "result_count": patients.count(),
        },
    )


@login_required
@permission_required("patients.view_patient", raise_exception=True)
def daily_animal_care(request):
    """Permission-aware clinical work queue for the current day."""
    today = timezone.localdate()
    visible_patients = _patients_visible_to(request.user).filter(active=True)
    reminders = CareReminder.objects.none()
    visits = HomeVisit.objects.none()
    if request.user.has_perm("patients.view_carereminder"):
        reminders = CareReminder.objects.select_related("patient").filter(
            patient__in=visible_patients, completed_on__isnull=True, due_on__lte=today
        ).order_by("due_on", "id")
    if request.user.has_perm("visits.view_homevisit"):
        visits = HomeVisit.objects.select_related("patient", "assigned_to").filter(
            patient__in=visible_patients, scheduled_for__date=today
        ).exclude(status=HomeVisit.Status.CANCELED).order_by("scheduled_for", "id")
    return render(request, "patients/daily_animal_care.html", {
        "today": today,
        "reminders": reminders,
        "visits": visits,
        "overdue_reminders": reminders.filter(due_on__lt=today).count(),
        "today_reminders": reminders.filter(due_on=today).count(),
    })


@login_required
def daily_close(request):
    """Short, permission-aware operational close for the current organization."""
    today = timezone.localdate()
    organization = _default_operating_organization(request.user)
    visible_patients = _patients_visible_to(request.user).filter(active=True)
    metrics, pending = [], []
    if request.user.has_perm("sales.view_sale") and organization:
        sales = Sale.objects.filter(organization=organization, created_at__date=today)
        metrics.append({"icon": "▣", "tone": "commerce", "value": sales.aggregate(total=Sum("total"))["total"] or 0, "label": "vendido hoy", "detail": f"{sales.count()} venta{'s' if sales.count() != 1 else ''} registrada{'s' if sales.count() != 1 else ''}", "url": "daily_report", "currency": True})
    if request.user.has_perm("sales.view_cashsession") and organization:
        cash_session = CashSession.objects.filter(organization=organization, closed_at__isnull=True).first()
        if cash_session:
            pending.append({"icon": "◷", "label": "La caja sigue abierta", "detail": "Revisá el arqueo antes de cerrar la jornada.", "url": "cash_dashboard"})
        else:
            metrics.append({"icon": "✓", "tone": "calm", "value": "Cerrada", "label": "caja diaria", "detail": "No hay una caja abierta.", "url": "cash_dashboard", "currency": False})
    if request.user.has_perm("grooming.view_groomingappointment"):
        appointments = GroomingAppointment.objects.filter(patient__in=visible_patients, starts_at__date=today)
        done = appointments.filter(status=GroomingAppointment.Status.DONE).count()
        active = appointments.exclude(status__in=[GroomingAppointment.Status.DONE, GroomingAppointment.Status.CANCELED]).count()
        metrics.append({"icon": "✂", "tone": "services", "value": done, "label": "turnos finalizados", "detail": f"{active} pendiente{'s' if active != 1 else ''} de resolver", "url": "grooming_agenda", "currency": False})
        if active:
            pending.append({"icon": "✂", "label": f"{active} turno{'s' if active != 1 else ''} aún activo{'s' if active != 1 else ''}", "detail": "Confirmá, finalizá o marcá inasistencia.", "url": "grooming_agenda"})
    if request.user.has_perm("visits.view_homevisit"):
        visits = HomeVisit.objects.filter(patient__in=visible_patients, scheduled_for__date=today).exclude(status=HomeVisit.Status.CANCELED)
        completed = visits.filter(status=HomeVisit.Status.COMPLETED).count()
        pending_visits = visits.exclude(status=HomeVisit.Status.COMPLETED).count()
        metrics.append({"icon": "⌖", "tone": "visits", "value": completed, "label": "visitas finalizadas", "detail": f"{pending_visits} pendiente{'s' if pending_visits != 1 else ''} de gestión", "url": "home_visit_list", "currency": False})
    if request.user.has_perm("patients.view_carereminder"):
        reminders = CareReminder.objects.filter(patient__in=visible_patients, completed_on__isnull=True, due_on__lte=today)
        if reminders.exists():
            pending.append({"icon": "⚕", "label": f"{reminders.count()} cuidado{'s' if reminders.count() != 1 else ''} pendiente{'s' if reminders.count() != 1 else ''}", "detail": "Incluye recordatorios vencidos y previstos para hoy.", "url": "daily_animal_care"})
    if request.user.has_perm("inventory.view_product") and organization:
        low_stock = Product.objects.filter(organization=organization, active=True, stock__lte=F("minimum_stock")).count()
        metrics.append({"icon": "▤", "tone": "stock", "value": low_stock, "label": "alertas de stock", "detail": "Productos en o bajo su mínimo.", "url": "inventory_alerts", "currency": False})
        if low_stock:
            pending.append({"icon": "▤", "label": f"{low_stock} producto{'s' if low_stock != 1 else ''} para reponer", "detail": "Revisá stock crítico antes de mañana.", "url": "inventory_alerts"})
    return render(request, "patients/daily_close.html", {"today": today, "close_metrics": metrics, "pending": pending, "organization": organization})


@login_required
def global_search(request):
    if (
        request.user.has_perm("lost_pets.view_lostpetreport")
        and not request.user.has_perm("patients.view_patient")
        and not request.user.has_perm("inventory.view_product")
    ):
        return redirect("lost_pet_list")
    query = request.GET.get("q", "").strip()
    patient_results, contact_results, product_results = [], [], []
    if query and request.user.has_perm("patients.view_patient"):
        visible_patients = _patients_visible_to(request.user).filter(active=True)
        patient_results = visible_patients.filter(Q(name__icontains=query) | Q(breed__icontains=query) | Q(microchip__icontains=query) | Q(contacts__full_name__icontains=query) | Q(contacts__phone__icontains=query) | Q(contacts__email__icontains=query)).prefetch_related("patientcontact_set__contact").distinct()[:12]
        contact_results = Contact.objects.filter(patients__in=visible_patients).filter(Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query)).prefetch_related("patients").distinct()[:12]
    if query and request.user.has_perm("inventory.view_product"):
        product_results = Product.objects.filter(active=True).filter(Q(name__icontains=query) | Q(commercial_name__icontains=query) | Q(sku__icontains=query) | Q(brand__name__icontains=query) | Q(supplier__name__icontains=query)).select_related("brand", "supplier")[:12]
    return render(request, "patients/global_search.html", {"query": query, "patient_results": patient_results, "contact_results": contact_results, "product_results": product_results})


@login_required
@permission_required(["patients.add_patient", "patients.add_contact", "patients.add_patientcontact"], raise_exception=True)
def patient_create(request):
    patient_form = PatientForm(request.POST or None, request.FILES or None, prefix="patient")
    contact_form = ContactForm(request.POST or None, prefix="contact")
    if request.method == "POST" and patient_form.is_valid() and contact_form.is_valid():
        organization = _default_operating_organization(request.user)
        if not organization:
            messages.error(request, "Tu cuenta no está vinculada a una organización para crear fichas clínicas.")
            return render(request, "patients/patient_form.html", {"patient_form": patient_form, "contact_form": contact_form})
        with transaction.atomic():
            patient = patient_form.save(commit=False)
            patient.organization = organization
            patient.save()
            contact_data = contact_form.cleaned_data
            contact = Contact.objects.filter(full_name__iexact=contact_data["full_name"].strip(), kind=contact_data["kind"], phone=contact_data["phone"], email__iexact=contact_data["email"].strip()).first()
            if not contact:
                contact = contact_form.save()
            PatientContact.objects.create(patient=patient, contact=contact, role=PatientContact.Role.RESPONSIBLE, is_primary=True)
        return redirect("patient_list")
    return render(request, "patients/patient_form.html", {"patient_form": patient_form, "contact_form": contact_form})


@login_required
@permission_required("patients.view_patient", raise_exception=True)
def patient_detail(request, patient_id):
    patient = get_object_or_404(
        _patients_visible_to(request.user).prefetch_related("patientcontact_set__contact", "clinical_records__professional", "care_reminders"),
        pk=patient_id,
    )
    commercial_context = {"patient_sales": [], "responsible_sales": [], "patient_total": 0, "responsible_total": 0, "completed_grooming_count": 0}
    if request.user.has_perm("sales.view_sale"):
        patient_sales = Sale.objects.filter(patient=patient).select_related("contact", "seller").prefetch_related("lines")
        contact_ids = patient.patientcontact_set.values_list("contact_id", flat=True)
        responsible_sales = Sale.objects.filter(contact_id__in=contact_ids).exclude(patient=patient).select_related("patient", "contact", "seller").prefetch_related("lines")
        commercial_context = {"patient_sales": patient_sales[:8], "responsible_sales": responsible_sales[:5], "patient_total": patient_sales.aggregate(total=Sum("total"))["total"] or 0, "responsible_total": responsible_sales.aggregate(total=Sum("total"))["total"] or 0, "completed_grooming_count": patient.grooming_appointments.filter(status="done").count()}
    return render(request, "patients/patient_detail.html", {"patient": patient, "today": timezone.localdate(), **commercial_context})


@login_required
@permission_required("patients.view_carereminder", raise_exception=True)
def care_reminder_list(request):
    today = timezone.localdate()
    view_mode = request.GET.get("view", "pending")
    reminders = CareReminder.objects.select_related("patient").filter(patient__in=_patients_visible_to(request.user))
    if view_mode == "done":
        reminders = reminders.filter(completed_on__isnull=False)
    elif view_mode == "all":
        pass
    else:
        view_mode = "pending"
        reminders = reminders.filter(completed_on__isnull=True)
    return render(request, "patients/care_reminder_list.html", {"reminders": reminders, "view_mode": view_mode, "today": today})


@login_required
@permission_required("patients.add_carereminder", raise_exception=True)
def care_reminder_create(request, patient_id):
    patient = _patient_or_404_for(request.user, patient_id, active_only=True)
    form = CareReminderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reminder = form.save(commit=False)
        reminder.patient = patient
        reminder.save()
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patients/care_reminder_form.html", {"patient": patient, "form": form})


@login_required
@permission_required("patients.change_carereminder", raise_exception=True)
@require_POST
def care_reminder_complete(request, reminder_id):
    reminder = get_object_or_404(CareReminder.objects.filter(patient__in=_patients_visible_to(request.user)), pk=reminder_id)
    reminder.completed_on = timezone.localdate()
    reminder.save(update_fields=["completed_on"])
    return redirect(request.POST.get("next") or "care_reminder_list")


@login_required
@permission_required(["patients.change_patient", "patients.change_contact", "patients.change_patientcontact"], raise_exception=True)
def patient_edit(request, patient_id):
    patient = _patient_or_404_for(request.user, patient_id)
    primary_relation = patient.patientcontact_set.select_related("contact").filter(is_primary=True).first()
    patient_form = PatientForm(request.POST or None, request.FILES or None, instance=patient, prefix="patient")
    contact_form = ContactForm(request.POST or None, instance=primary_relation.contact if primary_relation else None, prefix="contact")
    if request.method == "POST" and patient_form.is_valid() and contact_form.is_valid():
        try:
            with transaction.atomic():
                patient = patient_form.save()
                contact = contact_form.save()
                if primary_relation:
                    primary_relation.contact = contact
                    primary_relation.save(update_fields=["contact"])
                else:
                    PatientContact.objects.create(patient=patient, contact=contact, role=PatientContact.Role.RESPONSIBLE, is_primary=True)
        except (DatabaseError, OSError):
            logger.exception("No se pudo guardar la edición del paciente %s", patient_id)
            messages.error(request, "No se pudieron guardar los cambios. La ficha no fue modificada; intentá nuevamente.")
            return render(
                request,
                "patients/patient_form.html",
                {"patient_form": patient_form, "contact_form": contact_form, "patient": patient, "editing": True},
            )
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patients/patient_form.html", {"patient_form": patient_form, "contact_form": contact_form, "patient": patient, "editing": True})


@login_required
@permission_required(["patients.add_contact", "patients.add_patientcontact"], raise_exception=True)
def patient_contact_create(request, patient_id):
    patient = _patient_or_404_for(request.user, patient_id)
    contact_form = ContactForm(request.POST or None, prefix="contact")
    relation_form = PatientContactForm(request.POST or None, prefix="relation")
    existing_form = ExistingPatientContactForm(request.POST or None, prefix="existing")
    if request.method == "POST" and request.POST.get("action") == "existing" and existing_form.is_valid():
        with transaction.atomic():
            contact = existing_form.cleaned_data["contact"]
            relation, created = PatientContact.objects.get_or_create(patient=patient, contact=contact, role=existing_form.cleaned_data["role"], defaults={"is_primary": existing_form.cleaned_data["is_primary"]})
            if not created and existing_form.cleaned_data["is_primary"]:
                relation.is_primary = True
                relation.save(update_fields=["is_primary"])
            if existing_form.cleaned_data["is_primary"]:
                patient.patientcontact_set.filter(is_primary=True).exclude(pk=relation.pk).update(is_primary=False)
        return redirect("patient_detail", patient_id=patient.id)
    if request.method == "POST" and contact_form.is_valid() and relation_form.is_valid():
        with transaction.atomic():
            contact_data = contact_form.cleaned_data
            contact = Contact.objects.filter(full_name__iexact=contact_data["full_name"].strip(), kind=contact_data["kind"], phone=contact_data["phone"], email__iexact=contact_data["email"].strip()).first()
            if not contact:
                contact = contact_form.save()
            relation = relation_form.save(commit=False)
            relation.patient = patient
            relation.contact = contact
            if relation.is_primary:
                patient.patientcontact_set.filter(is_primary=True).update(is_primary=False)
            relation.save()
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patients/patient_contact_form.html", {"patient": patient, "contact_form": contact_form, "relation_form": relation_form, "existing_form": existing_form})


@login_required
@permission_required("patients.change_patientcontact", raise_exception=True)
def patient_contact_edit(request, patient_id, relation_id):
    relation = get_object_or_404(
        PatientContact.objects.select_related("patient", "contact").filter(patient__in=_patients_visible_to(request.user)),
        pk=relation_id,
        patient_id=patient_id,
    )
    form = PatientContactForm(request.POST or None, instance=relation)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            relation = form.save(commit=False)
            if relation.is_primary:
                PatientContact.objects.filter(patient=relation.patient, is_primary=True).exclude(pk=relation.pk).update(is_primary=False)
            relation.save()
        return redirect("patient_detail", patient_id=relation.patient_id)
    return render(request, "patients/patient_contact_edit_form.html", {"patient": relation.patient, "relation": relation, "form": form})


@login_required
@permission_required("patients.delete_patientcontact", raise_exception=True)
@require_POST
def patient_contact_remove(request, patient_id, relation_id):
    relation = get_object_or_404(PatientContact.objects.filter(patient__in=_patients_visible_to(request.user)), pk=relation_id, patient_id=patient_id)
    with transaction.atomic():
        patient_id = relation.patient_id
        was_primary = relation.is_primary
        relation.delete()
        if was_primary:
            replacement = PatientContact.objects.filter(patient_id=patient_id).order_by("id").first()
            if replacement:
                replacement.is_primary = True
                replacement.save(update_fields=["is_primary"])
    return redirect("patient_detail", patient_id=patient_id)


@login_required
@permission_required("patients.add_clinicalrecord", raise_exception=True)
def clinical_record_create(request, patient_id):
    patient = _patient_or_404_for(request.user, patient_id)
    form = ClinicalRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.patient = patient
        record.professional = request.user
        record.save()
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patients/clinical_record_form.html", {"patient": patient, "form": form})


@login_required
@permission_required("patients.delete_patient", raise_exception=True)
@require_POST
def patient_archive(request, patient_id):
    patient = _patient_or_404_for(request.user, patient_id)
    patient.active = False
    patient.save(update_fields=["active"])
    return redirect("patient_list")
