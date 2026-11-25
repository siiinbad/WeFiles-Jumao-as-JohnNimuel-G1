from functools import wraps
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Apply inside login_required; do not trust a role supplied by a request."""
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_active or request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate
