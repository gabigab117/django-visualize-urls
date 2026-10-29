"""Catalog views of the demo shop: class-based views and their mixins."""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from tests.demo.mixins import BreadcrumbMixin
from tests.demo.mixins import SupplierRequiredMixin


class ShopPageView(TemplateView):
    extra_context = {"shop": "Demo shop"}


class ProductListView(ShopPageView):
    template_name = "catalog/list.html"


class ProductDetailView(BreadcrumbMixin, ShopPageView):
    template_name = "catalog/detail.html"


def search(request, query=""):
    return HttpResponse(f"Results for {query}")


class ProductCreateView(LoginRequiredMixin, TemplateView):
    template_name = "catalog/create.html"

    def post(self, request):
        return HttpResponse("Product created", status=201)


class ProductDeleteView(PermissionRequiredMixin, View):
    permission_required = ("catalog.delete_product", "catalog.view_product")

    def post(self, request, slug):
        return HttpResponse(f"{slug} deleted")


class StockView(UserPassesTestMixin, TemplateView):
    template_name = "catalog/stock.html"

    def test_func(self):
        return self.request.user.groups.filter(name="warehouse").exists()


@method_decorator(login_required, name="dispatch")
class WishlistView(TemplateView):
    template_name = "catalog/wishlist.html"


class ReviewView(TemplateView):
    template_name = "catalog/reviews.html"

    @method_decorator(login_required)
    def post(self, request, slug):
        return HttpResponse("Review posted", status=201)


class SupplierView(SupplierRequiredMixin, TemplateView):
    template_name = "catalog/suppliers.html"
