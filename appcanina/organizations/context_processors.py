from .models import Organization


def business_profile(request):
    """Makes the single business identity available to the app and sign-in screen."""
    return {"organization_profile": Organization.objects.filter(is_business_profile=True).first()}
