"""Decorators of the demo shop."""

import functools

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import Http404

staff_required = user_passes_test(lambda user: user.is_staff)


def can_manage_returns(user):
    return user.has_perm("orders.change_return")


returns_manager_required = user_passes_test(can_manage_returns)


def ajax_only(view):
    """Answer 403 to requests that the shop's JavaScript did not send: not an access control."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def api_key_required(view):
    """Let partners in with their key; anyone else gets a 404, as if the page did not exist."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.headers.get("X-Api-Key") not in settings.PARTNER_API_KEYS:
            raise Http404
        return view(request, *args, **kwargs)

    return wrapper
