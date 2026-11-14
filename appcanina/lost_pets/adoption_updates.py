from .adoption_archives import with_archive_state
from django.db.models import Exists, OuterRef
from django.utils import timezone

from organizations.roles import organizations_managed_by, verified_shelters_managed_by
from .models import AdoptionInterest, AdoptionReadReceipt
from .visibility import deliverable_notifications


def search_updates(user):
    return deliverable_notifications().filter(recipient=user, report__reporter=user)


def managed_interest_organizations(user):
    shelters = verified_shelters_managed_by(user).distinct()
    if user.has_perm("lost_pets.change_adoptioninterest"):
        return (shelters | organizations_managed_by(user).distinct()).distinct()
    return shelters


def unread_interests(interests, user, audience):
    interests = with_archive_state(interests, user, audience).filter(is_archived=False)
    activity = f"{audience}_activity_at"
    receipts = AdoptionReadReceipt.objects.filter(
        interest_id=OuterRef("pk"), user=user, audience=audience,
        seen_at__gte=OuterRef(activity),
    )
    return interests.filter(**{f"{activity}__isnull": False}).annotate(
        already_read=Exists(receipts),
    ).filter(already_read=False)


def unread_counts(user):
    institutions = managed_interest_organizations(user)
    return {
        "search_unread_count": search_updates(user).filter(read_at__isnull=True).count(),
        "applicant_unread_count": unread_interests(AdoptionInterest.objects.filter(applicant=user), user, "applicant").count(),
        "institution_unread_count": unread_interests(AdoptionInterest.objects.filter(post__organization__in=institutions), user, "institution").count(),
        "can_receive_adoption_requests": institutions.exists(),
    }


def read_inbox(interests, user, audience):
    # Capture before fetching: an update arriving later must remain unread.
    seen_at = timezone.now()
    unread_ids = set(unread_interests(interests, user, audience).values_list("pk", flat=True))
    items = list(interests)
    for item in items:
        item.has_new_activity = item.pk in unread_ids
        AdoptionReadReceipt.objects.update_or_create(
            interest=item, user=user, audience=audience, defaults={"seen_at": seen_at},
        )
    return items
