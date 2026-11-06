from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


MANAGER_ROLES = {"owner", "admin"}
REVIEWER_ROLES = MANAGER_ROLES | {"reviewer"}


def can_manage(membership) -> bool:
    return bool(membership and membership.is_active and membership.role in MANAGER_ROLES)


def can_review(membership) -> bool:
    return bool(membership and membership.is_active and membership.role in REVIEWER_ROLES)


def workspace_member_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.membership or not request.workspace:
            raise PermissionDenied("Ваш обліковий запис не має активного робочого простору.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def manager_required(view_func):
    @workspace_member_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not can_manage(request.membership):
            raise PermissionDenied("Ця дія доступна лише адміністраторам робочого простору.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def reviewer_required(view_func):
    @workspace_member_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not can_review(request.membership):
            raise PermissionDenied("Недостатньо прав для перевірки результатів.")
        return view_func(request, *args, **kwargs)

    return _wrapped
