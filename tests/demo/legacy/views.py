"""Views kept from the first version of the shop, in shapes the map has to survive."""

import functools

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView


@login_required
def page(request, slug, template):
    """Served through functools.partial."""
    return HttpResponse(f"{template}: {slug}")


class Redirect:
    """A callable object used as a view."""

    def __init__(self, to):
        self.to = to

    @method_decorator(never_cache)
    def __call__(self, request):
        return HttpResponseRedirect(self.to)


class logged:  # a class-based decorator, named like a function
    def __init__(self, view):
        functools.update_wrapper(self, view)

    def __call__(self, request, *args, **kwargs):
        return self.__wrapped__(request, *args, **kwargs)


@logged
def newsletter(request):
    return HttpResponse("Newsletter")


class BrokenView:
    """Stands for a lazy proxy whose target fails to load: reading the view raises."""

    def __call__(self, request):
        return HttpResponse("Never served")

    @property
    def __wrapped__(self):
        raise RuntimeError("the legacy view could not be loaded")


# A class made by type(): its file is known, its source is not.
ArchivedPageView = type("ArchivedPageView", (TemplateView,), {"template_name": "legacy/archived.html"})
