"""Render a URL map as JSON, or as a standalone HTML page that needs no network access."""

import json

from django.template.loader import render_to_string
from django.utils.html import json_script

DATA_ELEMENT_ID = "url-map-data"


def render_json(url_map, indent=2):
    return json.dumps(url_map.to_dict(), indent=indent, ensure_ascii=False)


def render_html(url_map):
    # json_script() escapes <, > and & so that no value can close the <script> element that holds the data.
    return render_to_string(
        "django_visualize_urls/map.html",
        {"urlconf": url_map.meta["urlconf"], "data": json_script(url_map.to_dict(), DATA_ELEMENT_ID)},
    )
