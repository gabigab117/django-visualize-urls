from django.urls import path
from rest_framework.routers import SimpleRouter

from tests.demo.api import views

app_name = "api"

router = SimpleRouter()
router.register("carts", views.CartViewSet, basename="cart")

urlpatterns = [
    path("stats/", views.OrderStatsAPI.as_view(), name="stats"),
    path("status/", views.StatusAPI.as_view(), name="status"),
    path("partner/orders/", views.PartnerOrderAPI.as_view(), name="partner-orders"),
    path("cache/refresh/", views.refresh_cache, name="refresh-cache"),
    *router.urls,
]
