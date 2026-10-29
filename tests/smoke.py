"""Smoke test of a built distribution, run outside the project by the publish workflow:

    uv run --isolated --no-project --with dist/*.whl tests/smoke.py

It checks that the installed package holds its management command and its page template.
"""

from io import StringIO

import django
from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse
from django.urls import path


def home(request):
    return HttpResponse("Home")


urlpatterns = [path("", home, name="home")]


def main():
    settings.configure(
        INSTALLED_APPS=["django_visualize_urls"],
        ROOT_URLCONF=__name__,
        TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}],
    )
    django.setup()
    stdout = StringIO()
    call_command("visualize_urls", "--output", "-", stdout=stdout)
    page = stdout.getvalue()
    assert page.startswith("<!doctype html>"), page[:200]
    assert '"name": "home"' in page, "the route is missing from the page data"
    import django_visualize_urls

    print(f"django-visualize-urls {django_visualize_urls.__version__}: smoke test passed")


if __name__ == "__main__":
    main()
