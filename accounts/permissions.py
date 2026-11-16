from functools import wraps
from django.core.exceptions import PermissionDenied


def role_required(role):
    """Apply inside login_required; do not trust a role supplied by a request."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate
