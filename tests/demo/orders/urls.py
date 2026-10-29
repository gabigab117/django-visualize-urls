from django.urls import include
from django.urls import path

from tests.demo.orders import views

app_name = "orders"

returns = [
    path("", views.return_list, name="list"),
    path("new/", views.return_create, name="create"),
]

urlpatterns = [
    path("", views.order_list, name="list"),
    path("<int:pk>/refund/", views.order_refund, name="refund"),
    path("export/", views.order_export, name="export"),
    path("stats/", views.order_stats, name="stats"),
    path("purge/", views.order_purge, name="purge"),
    path("<int:pk>/cancel/", views.order_cancel, name="cancel"),
    path("payment-webhook/", views.payment_webhook, name="payment-webhook"),
    path("<int:pk>/track/", views.order_track, name="track"),
    path("<int:pk>/summary/", views.order_summary, name="summary"),
    path("partner-feed/", views.partner_feed, name="partner-feed"),
    path("receipt/<uuid:token>/", views.order_receipt, name="receipt"),
    path("help/", views.order_help, name="help"),
    path("returns/", include((returns, "returns"))),
]
