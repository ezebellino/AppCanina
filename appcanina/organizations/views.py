from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import CommunityCollaboratorForm
from .models import Organization
from .roles import ensure_base_roles
from .setup_forms import InitialSetupForm


def initial_setup(request):
    """Public exactly once: creates the first owner and business identity."""
    if User.objects.exists():
        messages.info(request, "La cuenta inicial ya fue configurada. Ingresá con tu usuario.")
        return redirect("login")
    form = InitialSetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ensure_base_roles()
            user = User.objects.create_superuser(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
            )
            Organization.objects.create(
                name=form.cleaned_data["business_name"],
                kind=form.cleaned_data["business_kind"],
                is_business_profile=True,
            )
        login(request, user)
        return redirect("dashboard")
    return render(request, "organizations/initial_setup.html", {"form": form})


@login_required
@permission_required("auth.add_user", raise_exception=True)
def community_collaborators(request):
    roles = ensure_base_roles()
    collaborators = User.objects.filter(groups=roles["collaborator"]).order_by("username")
    form = CommunityCollaboratorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        collaborator = form.save()
        collaborator.groups.add(roles["collaborator"])
        messages.success(request, f"{collaborator.username} ya puede colaborar desde la app móvil.")
        return redirect("community_collaborators")
    return render(
        request,
        "organizations/community_collaborators.html",
        {"form": form, "collaborators": collaborators},
    )
