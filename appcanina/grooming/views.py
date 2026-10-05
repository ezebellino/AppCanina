from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import GroomingAppointmentForm, GroomingServiceForm
from .models import GroomingAppointment, GroomingService

@login_required
@permission_required("grooming.view_groomingappointment", raise_exception=True)
def agenda(request):
    today = timezone.localdate()
    now = timezone.now()
    all_appointments = GroomingAppointment.objects.select_related("patient", "service", "sale", "assigned_to").prefetch_related("additional_services")
    active_appointments = all_appointments.exclude(status__in=[GroomingAppointment.Status.DONE, GroomingAppointment.Status.CANCELED])
    today_appointments = active_appointments.filter(starts_at__date=today)
    delayed_appointments = today_appointments.filter(starts_at__lt=now)
    next_appointment = active_appointments.filter(starts_at__gte=now).order_by("starts_at").first()
    view_mode = request.GET.get("view", "all")
    selected_status = request.GET.get("status", "")
    selected_employee = request.GET.get("employee", "")
    appointments = all_appointments
    if view_mode == "day":
        appointments = appointments.filter(starts_at__date=today)
    elif view_mode == "week":
        week_start = today - timedelta(days=today.weekday())
        appointments = appointments.filter(starts_at__date__range=(week_start, week_start + timedelta(days=6)))
    else:
        view_mode = "all"
    valid_statuses = {choice for choice, _ in GroomingAppointment.Status.choices}
    if selected_status in valid_statuses:
        appointments = appointments.filter(status=selected_status)
    else:
        selected_status = ""
    if selected_employee == "unassigned":
        appointments = appointments.filter(assigned_to__isnull=True)
    elif selected_employee.isdigit():
        appointments = appointments.filter(assigned_to_id=selected_employee)
    else:
        selected_employee = ""
    employees = get_user_model().objects.filter(is_active=True).order_by("username")
    return render(request, "grooming/agenda.html", {"appointments": appointments, "today_appointments": today_appointments, "delayed_appointments": delayed_appointments, "next_appointment": next_appointment, "view_mode": view_mode, "selected_status": selected_status, "selected_employee": selected_employee, "employees": employees, "status_choices": GroomingAppointment.Status.choices})

@login_required
@permission_required("grooming.add_groomingappointment", raise_exception=True)
def appointment_create(request):
    form = GroomingAppointmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("grooming_agenda")
    return render(request, "grooming/appointment_form.html", {"form": form})

@login_required
@permission_required("grooming.change_groomingappointment", raise_exception=True)
def appointment_edit(request, appointment_id):
    appointment = get_object_or_404(GroomingAppointment, pk=appointment_id)
    form = GroomingAppointmentForm(request.POST or None, instance=appointment)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("grooming_agenda")
    return render(request, "grooming/appointment_form.html", {"form": form, "appointment": appointment})

@login_required
@permission_required("grooming.change_groomingappointment", raise_exception=True)
@require_POST
def appointment_status(request, appointment_id, status):
    appointment = get_object_or_404(GroomingAppointment, pk=appointment_id)
    valid_statuses = {GroomingAppointment.Status.DONE, GroomingAppointment.Status.CANCELED, GroomingAppointment.Status.CONFIRMED}
    if status in valid_statuses:
        appointment.status = status
        appointment.save(update_fields=["status"])
    return redirect("grooming_agenda")

@login_required
@permission_required("grooming.view_groomingservice", raise_exception=True)
def service_list(request):
    return render(request, "grooming/service_list.html", {"services": GroomingService.objects.all()})

@login_required
@permission_required("grooming.add_groomingservice", raise_exception=True)
def service_create(request):
    form = GroomingServiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("grooming_service_list")
    return render(request, "grooming/service_form.html", {"form": form})

@login_required
@permission_required("grooming.change_groomingservice", raise_exception=True)
def service_edit(request, service_id):
    service = get_object_or_404(GroomingService, pk=service_id)
    form = GroomingServiceForm(request.POST or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("grooming_service_list")
    return render(request, "grooming/service_form.html", {"form": form, "service": service})

@login_required
@permission_required("grooming.delete_groomingservice", raise_exception=True)
@require_POST
def service_remove(request, service_id):
    service = get_object_or_404(GroomingService, pk=service_id)
    if service.groomingappointment_set.exists():
        service.active = False
        service.save(update_fields=["active"])
    else:
        service.delete()
    return redirect("grooming_service_list")
