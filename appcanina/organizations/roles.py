from django.contrib.auth.models import Group, Permission


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
    return user.is_authenticated and user.groups.filter(name=COMMUNITY_COLLABORATOR_GROUP).exists()
