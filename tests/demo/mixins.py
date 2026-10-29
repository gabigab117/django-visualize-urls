"""Mixins of the demo shop."""

from django.core.exceptions import PermissionDenied


class BreadcrumbMixin:
    """Add the breadcrumb of the page to its context."""

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "breadcrumb": ["Catalog"]}


class SupplierRequiredMixin:
    """Let in the members of the supplier group only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("catalog.supply"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
