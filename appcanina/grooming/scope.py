from django.contrib.auth import get_user_model
from django.db.models import Q

from organizations.roles import organizations_managed_by
from organizations.models import OrganizationMembership
from patients.models import Patient
from .models import GroomingAppointment


def visible_patients(user):
    if user.is_superuser:
        return Patient.objects.all()
    return Patient.objects.filter(organization__in=organizations_managed_by(user))


def visible_appointments(user):
    return GroomingAppointment.objects.filter(patient__in=visible_patients(user))


def visible_employees(user):
    users = get_user_model().objects.filter(is_active=True)
    if not user.is_superuser:
        member_ids = OrganizationMembership.objects.filter(
            organization__in=organizations_managed_by(user),
        ).values('user_id')
        users = users.filter(Q(pk__in=member_ids) | Q(pk=user.pk))
    return users.order_by('username')
