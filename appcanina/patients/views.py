import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import DatabaseError, transaction
from django.db.models import F, Q, Sum
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import CareReminderForm, ClinicalRecordForm, ContactForm, ExistingPatientContactForm, PatientContactForm, PatientForm
from .models import CareReminder, ClinicalRecord, Contact, Patient, PatientContact
from sales.models import Sale
from inventory.models import Product
from grooming.models import GroomingAppointment
from visits.models import HomeVisit


logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Compact desktop-first landing page for the day-to-day operation."""
    today = timezone.localdate()
    metrics = []
    attention = []
    if request.user.has_perm("patients.view_patient"):
        metrics.append({"value": Patient.objects.filter(active=True).count(), "label": "pacientes activos", "url": "patient_list", "tone": "teal"})
    if request.user.has_perm("grooming.view_groomingappointment"):
        turns_today = GroomingAppointment.objects.filter(starts_at__date=today).exclude(status=GroomingAppointment.Status.CANCELED).count()
        metrics.append({"value": turns_today, "label": "turnos de hoy", "url": "grooming_agenda", "tone": "amber"})
    if request.user.has_perm("visits.view_homevisit"):
        visits_today = HomeVisit.objects.filter(scheduled_for__date=today).exclude(status=HomeVisit.Status.CANCELED).count()
        metrics.append({"value": visits_today, "label": "visitas de hoy", "url": "home_visit_list", "tone": "blue"})
    if request.user.has_perm("patients.view_carereminder"):
        due_reminders = CareReminder.objects.filter(completed_on__isnull=True, due_on__lte=today)
        if due_reminders.exists():
            attention.append({"value": due_reminders.count(), "label": "recordatorios clínicos pendientes", "url": "care_reminder_list"})
    if request.user.has_perm("inventory.view_product"):
        low_stock = Product.objects.filter(active=True, stock__lte=F("minimum_stock")).count()
        metrics.append({"value": Product.objects.filter(active=True).count(), "label": "productos activos", "url": "inventory_list", "tone": "blue"})
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
    patients = Patient.objects.filter(active=True).prefetch_related("patientcontact_set__contact")
    if query:
        patients = patients.filter(Q(name__icontains=query) | Q(breed__icontains=query) | Q(microchip__icontains=query) | Q(contacts__full_name__icontains=query) | Q(contacts__phone__icontains=query) | Q(contacts__email__icontains=query)).distinct()
    return render(request, "patients/patient_list.html", {"patients": patients, "query": query})


@login_required
def global_search(request):
    query = request.GET.get("q", "").strip()
    patient_results, contact_results, product_results = [], [], []
    if query and request.user.has_perm("patients.view_patient"):
        patient_results = Patient.objects.filter(active=True).filter(Q(name__icontains=query) | Q(breed__icontains=query) | Q(microchip__icontains=query) | Q(contacts__full_name__icontains=query) | Q(contacts__phone__icontains=query) | Q(contacts__email__icontains=query)).prefetch_related("patientcontact_set__contact").distinct()[:12]
        contact_results = Contact.objects.filter(Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query)).prefetch_related("patients").distinct()[:12]
    if query and request.user.has_perm("inventory.view_product"):
        product_results = Product.objects.filter(active=True).filter(Q(name__icontains=query) | Q(commercial_name__icontains=query) | Q(sku__icontains=query) | Q(brand__name__icontains=query) | Q(supplier__name__icontains=query)).select_related("brand", "supplier")[:12]
    return render(request, "patients/global_search.html", {"query": query, "patient_results": patient_results, "contact_results": contact_results, "product_results": product_results})


@login_required
@permission_required(["patients.add_patient", "patients.add_contact", "patients.add_patientcontact"], raise_exception=True)
def patient_create(request):
    patient_form = PatientForm(request.POST or None, request.FILES or None, prefix="patient")
    contact_form = ContactForm(request.POST or None, prefix="contact")
    if request.method == "POST" and patient_form.is_valid() and contact_form.is_valid():
        with transaction.atomic():
            patient = patient_form.save()
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
        Patient.objects.prefetch_related("patientcontact_set__contact", "clinical_records__professional", "care_reminders"),
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
    reminders = CareReminder.objects.select_related("patient")
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
    patient = get_object_or_404(Patient, pk=patient_id, active=True)
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
    reminder = get_object_or_404(CareReminder, pk=reminder_id)
    reminder.completed_on = timezone.localdate()
    reminder.save(update_fields=["completed_on"])
    return redirect(request.POST.get("next") or "care_reminder_list")


@login_required
@permission_required(["patients.change_patient", "patients.change_contact", "patients.change_patientcontact"], raise_exception=True)
def patient_edit(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
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
    patient = get_object_or_404(Patient, pk=patient_id)
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
        PatientContact.objects.select_related("patient", "contact"),
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
    relation = get_object_or_404(PatientContact, pk=relation_id, patient_id=patient_id)
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
    patient = get_object_or_404(Patient, pk=patient_id)
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
    patient = get_object_or_404(Patient, pk=patient_id)
    patient.active = False
    patient.save(update_fields=["active"])
    return redirect("patient_list")
