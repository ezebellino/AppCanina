from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import HomeVisitForm
from .models import HomeVisit


@login_required
@permission_required("visits.view_homevisit", raise_exception=True)
def home_visit_list(request):
    today = timezone.localdate()
    visits = HomeVisit.objects.select_related("patient", "assigned_to")
    view_mode = request.GET.get("view", "upcoming")
    if view_mode == "today":
        visits = visits.filter(scheduled_for__date=today)
    elif view_mode == "all":
        pass
    else:
        view_mode = "upcoming"
        visits = visits.filter(scheduled_for__gte=timezone.now()).exclude(status=HomeVisit.Status.CANCELED)
    today_count = HomeVisit.objects.filter(scheduled_for__date=today).exclude(status=HomeVisit.Status.CANCELED).count()
    active_count = HomeVisit.objects.exclude(status__in=[HomeVisit.Status.COMPLETED, HomeVisit.Status.CANCELED]).count()
    return render(request, "visits/home_visit_list.html", {"visits": visits, "view_mode": view_mode, "today_count": today_count, "active_count": active_count})


@login_required
@permission_required("visits.add_homevisit", raise_exception=True)
def home_visit_create(request):
    initial = {"patient": request.GET.get("patient"), "scheduled_for": timezone.localtime().replace(minute=0, second=0, microsecond=0)}
    form = HomeVisitForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            visit = form.save(commit=False)
            visit.patient = form.create_patient_if_needed()
            visit.save()
        return redirect("home_visit_list")
    return render(request, "visits/home_visit_form.html", {"form": form})


@login_required
@permission_required("visits.change_homevisit", raise_exception=True)
def home_visit_edit(request, visit_id):
    visit = get_object_or_404(HomeVisit, pk=visit_id)
    form = HomeVisitForm(request.POST or None, instance=visit)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("home_visit_list")
    return render(request, "visits/home_visit_form.html", {"form": form, "visit": visit})
