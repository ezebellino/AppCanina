from django.db.models import F, Q

from organizations.roles import is_community_collaborator
from .models import CommunityNotification, LostPetReport, Sighting


PUBLIC_REPORT_STATUSES = (LostPetReport.Status.PUBLISHED, LostPetReport.Status.RESOLVED)


def can_review_reports(user):
    return user.is_authenticated and user.is_active and (
        user.is_staff or user.has_perm("lost_pets.change_lostpetreport")
    )


def can_review_sightings(user):
    return user.is_authenticated and user.is_active and (
        user.is_staff or user.has_perm("lost_pets.change_sighting")
    )


def reports_visible_to(user):
    reports = LostPetReport.objects.all()
    if can_review_reports(user):
        return reports
    statuses = (LostPetReport.Status.PUBLISHED,) if is_community_collaborator(user) else PUBLIC_REPORT_STATUSES
    return reports.filter(status__in=statuses)


def sightings_visible_to(user):
    sightings = Sighting.objects.filter(report__in=reports_visible_to(user))
    return sightings if can_review_sightings(user) else sightings.filter(status=Sighting.Status.PUBLISHED)


def deliverable_notifications():
    """Current publication state, including the requester's private review reply."""
    public_report = Q(report__status__in=PUBLIC_REPORT_STATUSES)
    public_sighting = Q(sighting__status=Sighting.Status.PUBLISHED, sighting__report_id=F("report_id"))
    own_request = Q(report__requested_via_mobile=True, report__reporter_id=F("recipient_id"))
    return CommunityNotification.objects.filter(
        (public_report & public_sighting)
        | (Q(sighting__isnull=True) & (public_report | own_request))
    )
