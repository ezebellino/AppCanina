from .models import Organization


def business_profile(request):
    """Expose the institution relevant to the current session in the app shell."""
    profile = None
    user = getattr(request, "user", None)
    if user and user.is_authenticated and user.is_staff:
        return {"organization_profile": None}
    if user and user.is_authenticated:
        managed_profile = Organization.objects.filter(memberships__user=user).order_by("id").first()
        if managed_profile:
            profile = managed_profile
    return {"organization_profile": profile}
