from django.conf import settings


def public_url(request, path):
    """Use the configured public origin, retaining request URLs for local installs."""
    if settings.PUBLIC_BASE_URL and path.startswith("/") and not path.startswith("//"):
        return settings.PUBLIC_BASE_URL + path
    return request.build_absolute_uri(path)
