import functools

from django.urls import path

from tests.demo.legacy import views

app_name = "legacy"

urlpatterns = [
    path("pages/<slug:slug>/", functools.partial(views.page, template="legacy"), name="page"),
    path("old-home/", views.Redirect("/"), name="old-home"),
    path("newsletter/", views.newsletter, name="newsletter"),
    path("broken/", views.BrokenView(), name="broken"),
    path("archive/<slug:slug>/", views.ArchivedPageView.as_view(), name="archived-page"),
]
