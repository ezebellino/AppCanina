from .models import Organization


def business_profile(request):
    """Expose the institution relevant to the current session in the app shell."""
    profile = Organization.objects.filter(is_business_profile=True).first()
    user = getattr(request, "user", None)
    if user and user.is_authenticated and not user.is_superuser:
        managed_profile = Organization.objects.filter(memberships__user=user).order_by("id").first()
        if managed_profile:
            profile = managed_profile
    return {"organization_profile": profile}
