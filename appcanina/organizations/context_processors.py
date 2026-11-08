from .models import Organization
from .roles import verified_shelters_managed_by


def application_version(request):
    from django.conf import settings

    return {"app_version": settings.APP_VERSION, "app_name": settings.APP_NAME}


def business_profile(request):
    """Expose the institution relevant to the current session in the app shell."""
    profile = None
    updates = {"applicant_unread_count": 0, "institution_unread_count": 0, "can_receive_adoption_requests": False}
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        from lost_pets.adoption_updates import unread_counts
        updates = unread_counts(user)
        managed_profile = Organization.objects.filter(memberships__user=user).order_by("id").first() if not user.is_staff else None
        if managed_profile:
            profile = managed_profile
    return {"organization_profile": profile, "is_shelter_manager": bool(user and user.is_authenticated and verified_shelters_managed_by(user).exists()), **updates}
