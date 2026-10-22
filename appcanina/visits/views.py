from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from organizations.roles import organizations_managed_by
from patients.models import Patient
from .forms import HomeVisitForm
from .models import HomeVisit


def _visible_patients(user):
    if user.is_superuser:
        return Patient.objects.all()
    return Patient.objects.filter(organization__in=organizations_managed_by(user))


def _default_organization(user):
    organizations = organizations_managed_by(user)
    return organizations.filter(is_business_profile=True).first() or organizations.order_by("id").first()


def _visit_or_404_for(user, visit_id):
    return get_object_or_404(
        HomeVisit.objects.select_related("patient", "assigned_to").filter(patient__in=_visible_patients(user)),
        pk=visit_id,
    )


@login_required
@permission_required("visits.view_homevisit", raise_exception=True)
def home_visit_list(request):
    today = timezone.localdate()
    visits = HomeVisit.objects.select_related("patient", "assigned_to").filter(patient__in=_visible_patients(request.user))
    view_mode = request.GET.get("view", "upcoming")
    if view_mode == "today":
        visits = visits.filter(scheduled_for__date=today)
    elif view_mode == "all":
        pass
    else:
        view_mode = "upcoming"
        visits = visits.filter(scheduled_for__gte=timezone.now()).exclude(status=HomeVisit.Status.CANCELED)
    today_count = visits.filter(scheduled_for__date=today).exclude(status=HomeVisit.Status.CANCELED).count()
    active_count = visits.exclude(status__in=[HomeVisit.Status.COMPLETED, HomeVisit.Status.CANCELED]).count()
    return render(request, "visits/home_visit_list.html", {"visits": visits, "view_mode": view_mode, "today_count": today_count, "active_count": active_count})


@login_required
@permission_required("visits.add_homevisit", raise_exception=True)
def home_visit_create(request):
    initial = {"patient": request.GET.get("patient"), "scheduled_for": timezone.localtime().replace(minute=0, second=0, microsecond=0)}
    organization = _default_organization(request.user)
    if not organization:
        raise PermissionDenied("Tu cuenta no tiene una organización veterinaria asignada.")
    form = HomeVisitForm(request.POST or None, initial=initial, patient_queryset=_visible_patients(request.user).filter(active=True))
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            visit = form.save(commit=False)
            visit.patient = form.create_patient_if_needed(organization)
            visit.save()
        return redirect("home_visit_list")
    return render(request, "visits/home_visit_form.html", {"form": form})


@login_required
@permission_required("visits.change_homevisit", raise_exception=True)
def home_visit_edit(request, visit_id):
    visit = _visit_or_404_for(request.user, visit_id)
    form = HomeVisitForm(request.POST or None, instance=visit, patient_queryset=_visible_patients(request.user).filter(active=True))
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("home_visit_list")
    return render(request, "visits/home_visit_form.html", {"form": form, "visit": visit})
