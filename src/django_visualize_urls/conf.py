"""Per-project settings, read from ``settings.VISUALIZE_URLS``."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DEFAULTS = {
    # Extra strings that reveal a hand-written access check in project code, e.g. "check_api_key(".
    "HINTS": [],
    # Decorators that never control access: their code is not searched for hints.
    "NEUTRAL_DECORATORS": [],
    # Decorators that control access although nothing in their code says so: their routes count as protected.
    "ACCESS_DECORATORS": [],
    # Link that opens a view in an editor. {path} is the absolute path without its leading slash. None disables links.
    "EDITOR_URL": "vscode://file/{path}:{line}",
}


def get_config():
    config = getattr(settings, "VISUALIZE_URLS", {})
    unknown = sorted(set(config) - set(DEFAULTS))
    if unknown:
        raise ImproperlyConfigured(
            f"Unknown VISUALIZE_URLS keys: {', '.join(unknown)}. Valid keys: {', '.join(DEFAULTS)}."
        )
    return {**DEFAULTS, **config}
