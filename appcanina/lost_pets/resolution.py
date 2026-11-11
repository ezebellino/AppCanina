"""Permissions and idempotent closure of active searches."""
from django.db.models import Q
from django.utils import timezone
from organizations.models import OrganizationMembership
from .models import LostPetReport
from .visibility import can_review_reports


def manageable_searches(user):
    if not user.is_authenticated or not user.is_active:
        return LostPetReport.objects.none()
    reports = LostPetReport.objects.all()
    if can_review_reports(user):
        return reports
    shelters = OrganizationMembership.objects.filter(
        user=user, role="manager", organization__kind="shelter", organization__is_verified=True,
    ).values_list("organization_id", flat=True)
    return reports.filter(Q(reporter=user) | Q(patient__organization_id__in=shelters))


def finish_search(user, report_id):
    return manageable_searches(user).filter(pk=report_id, status=LostPetReport.Status.PUBLISHED).update(
        status=LostPetReport.Status.RESOLVED, updated_at=timezone.now(),
    )
