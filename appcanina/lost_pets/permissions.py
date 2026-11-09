from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def report_read_required(view):
    """Allow platform oversight or the existing lost-report read permission."""
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_active or not (
            user.is_staff or user.has_perm("lost_pets.view_lostpetreport")
        ):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
