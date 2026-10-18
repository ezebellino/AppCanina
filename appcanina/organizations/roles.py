from django.contrib.auth.models import Group, Permission

from .models import Organization


COMMUNITY_COLLABORATOR_GROUP = "Colaborador comunitario"


def ensure_base_roles():
    """Create the roles used by the application without granting extra access."""
    app_permissions = Permission.objects.filter(
        content_type__app_label__in=["patients", "grooming", "inventory", "sales", "lost_pets"]
    )

    admin, _ = Group.objects.get_or_create(name="Administrador")
    admin.permissions.set(
        app_permissions | Permission.objects.filter(
            content_type__app_label="auth", codename__in=["add_user", "change_user", "view_user"]
        )
    )

    employee, _ = Group.objects.get_or_create(name="Empleado")
    employee.permissions.set(
        app_permissions.filter(
            codename__in=[
                "view_patient", "view_contact", "view_patientcontact", "view_clinicalrecord",
                "view_groomingappointment", "view_product", "view_brand", "view_supplier",
                "view_sale", "add_sale", "view_lostpetreport", "add_lostpetreport", "add_sighting",
            ]
        )
    )

    collaborator, _ = Group.objects.get_or_create(name=COMMUNITY_COLLABORATOR_GROUP)
    collaborator.permissions.set(
        Permission.objects.filter(
            content_type__app_label="lost_pets",
            codename__in=["view_lostpetreport", "add_sighting"],
        )
    )
    return {"admin": admin, "employee": employee, "collaborator": collaborator}


def is_community_collaborator(user):
    """True only for community-only accounts, never for an administrator who also collaborates."""
    return (
        user.is_authenticated
        and user.groups.filter(name=COMMUNITY_COLLABORATOR_GROUP).exists()
        and not user.is_staff
        and not user.is_superuser
        and not user.groups.filter(name="Administrador").exists()
    )


def organizations_managed_by(user):
    """Organizations whose adoption workflow the user can operate.

    Existing administrator accounts keep access to the main business profile
    until they are explicitly linked to a refuge. Superusers can oversee all
    organizations.
    """
    if not user.is_authenticated:
        return Organization.objects.none()
    if user.is_superuser:
        return Organization.objects.all()
    organizations = Organization.objects.filter(memberships__user=user).distinct()
    if organizations.exists() or not user.has_perm("lost_pets.change_adoptionpost"):
        return organizations
    return Organization.objects.filter(is_business_profile=True)


def can_manage_organization(user, organization):
    return organizations_managed_by(user).filter(pk=organization.pk).exists()


def verified_shelters_managed_by(user):
    """Refuges whose responsible person may publish and manage adoptions."""
    if not user.is_authenticated:
        return Organization.objects.none()
    if user.is_superuser:
        return Organization.objects.filter(kind=Organization.Kind.SHELTER, is_verified=True)
    return Organization.objects.filter(
        kind=Organization.Kind.SHELTER,
        is_verified=True,
        memberships__user=user,
        memberships__role="manager",
    ).distinct()
