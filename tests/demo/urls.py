"""Root URLconf of the demo shop: one route for each way of protecting a view."""

from importlib.util import find_spec

from django.contrib import admin
from django.urls import include
from django.urls import path
from django.urls import re_path
from django.views.generic import TemplateView

from tests.demo import views

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    re_path(r"^archive/(?P<year>[0-9]{4})/$", views.archive, name="archive"),
    path("orders/", include("tests.demo.orders.urls")),
    path("catalog/", include("tests.demo.catalog.urls")),
    path("legacy/", include("tests.demo.legacy.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
]

if find_spec("rest_framework"):
    urlpatterns.append(path("api/", include("tests.demo.api.urls")))
