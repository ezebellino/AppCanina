from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommunityCollaboratorForm, OrganizationMembershipForm, ShelterProfileForm
from .models import Organization, OrganizationMembership
from .roles import can_manage_organization, ensure_base_roles
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


@login_required
def organization_verification_list(request):
    """Platform-only review queue for veterinary and shelter profiles."""
    if not request.user.is_staff:
        raise PermissionDenied

    pending_organizations = Organization.objects.filter(
        kind__in=[Organization.Kind.VETERINARY, Organization.Kind.SHELTER],
        verification_status=Organization.VerificationStatus.PENDING,
    ).prefetch_related("memberships__user").order_by("id")
    recent_reviews = Organization.objects.filter(
        kind__in=[Organization.Kind.VETERINARY, Organization.Kind.SHELTER],
    ).exclude(
        verification_status=Organization.VerificationStatus.PENDING,
    ).select_related("reviewed_by").order_by("-reviewed_at", "-id")[:12]
    return render(
        request,
        "organizations/verification_list.html",
        {"pending_organizations": pending_organizations, "recent_reviews": recent_reviews},
    )


@login_required
def organization_verification_update(request, organization_id):
    """Approve or reject an institutional profile; community accounts never enter this flow."""
    if not request.user.is_staff:
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied

    organization = get_object_or_404(
        Organization,
        pk=organization_id,
        kind__in=[Organization.Kind.VETERINARY, Organization.Kind.SHELTER],
    )
    action = request.POST.get("action")
    note = request.POST.get("verification_note", "").strip()
    if action not in {"approve", "reject"}:
        messages.error(request, "Acción de validación inválida.")
        return redirect("organization_verification_list")
    if action == "reject" and not note:
        messages.error(request, "Indicá un motivo para rechazar la solicitud.")
        return redirect("organization_verification_list")

    organization.reviewed_at = timezone.now()
    organization.reviewed_by = request.user
    organization.verification_note = note
    if action == "approve":
        organization.verification_status = Organization.VerificationStatus.APPROVED
        organization.is_verified = True
        roles = ensure_base_roles()
        managers = organization.memberships.filter(role=OrganizationMembership.Role.MANAGER).select_related("user")
        for membership in managers:
            membership.user.groups.add(roles["admin"])
        messages.success(request, f"{organization.name} fue validada y su responsable ya puede operar el perfil.")
    else:
        organization.verification_status = Organization.VerificationStatus.REJECTED
        organization.is_verified = False
        messages.success(request, f"La solicitud de {organization.name} fue rechazada. El perfil quedó inactivo.")
    organization.save()
    return redirect("organization_verification_list")


@login_required
@permission_required("organizations.add_organization", raise_exception=True)
def shelter_list(request):
    shelters = Organization.objects.filter(kind=Organization.Kind.SHELTER).prefetch_related("memberships__user")
    return render(request, "organizations/shelter_list.html", {"shelters": shelters})


@login_required
@permission_required("organizations.add_organization", raise_exception=True)
def shelter_create(request):
    form = ShelterProfileForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        shelter = form.save(commit=False)
        shelter.kind = Organization.Kind.SHELTER
        shelter.save()
        OrganizationMembership.objects.create(organization=shelter, user=request.user, role=OrganizationMembership.Role.MANAGER)
        messages.success(request, "El perfil del refugio ya está listo para publicar animales en adopción.")
        return redirect("shelter_detail", shelter_id=shelter.id)
    return render(request, "organizations/shelter_form.html", {"form": form, "title": "Crear perfil de refugio"})


@login_required
@permission_required("organizations.add_organization", raise_exception=True)
def shelter_detail(request, shelter_id):
    shelter = get_object_or_404(Organization, pk=shelter_id, kind=Organization.Kind.SHELTER)
    if not can_manage_organization(request.user, shelter):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    profile_form = ShelterProfileForm(request.POST or None, request.FILES or None, instance=shelter, prefix="profile")
    member_form = OrganizationMembershipForm(request.POST or None, prefix="member")
    if request.method == "POST":
        if request.POST.get("action") == "member" and member_form.is_valid():
            membership = member_form.save(commit=False)
            membership.organization = shelter
            try:
                membership.save()
            except Exception:
                member_form.add_error("user", "Esta persona ya forma parte del refugio.")
            else:
                messages.success(request, "Integrante vinculado al refugio.")
                return redirect("shelter_detail", shelter_id=shelter.id)
        elif request.POST.get("action") == "profile" and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Perfil del refugio actualizado.")
            return redirect("shelter_detail", shelter_id=shelter.id)
    members = shelter.memberships.select_related("user").order_by("role", "user__username")
    return render(request, "organizations/shelter_detail.html", {"shelter": shelter, "profile_form": profile_form, "member_form": member_form, "members": members})
