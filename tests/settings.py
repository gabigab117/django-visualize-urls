"""Settings of the demo shop used by the tests: no database, no network."""

from importlib.util import find_spec
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "django-visualize-urls-tests"  # not a secret: the demo serves no request
DEBUG = False
USE_TZ = True
DATABASES = {}
ROOT_URLCONF = "tests.demo.urls"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    *(["rest_framework"] if find_spec("rest_framework") else []),
    "django_visualize_urls",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}]
