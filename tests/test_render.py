"""JSON and standalone HTML page of the URL map."""

import json
import re

from django_visualize_urls.collect import Route
from django_visualize_urls.collect import UrlMap
from django_visualize_urls.render import DATA_ELEMENT_ID
from django_visualize_urls.render import render_html
from django_visualize_urls.render import render_json


def page_data(html):
    """Data of the page, read back as the page script reads them."""
    match = re.search(rf'<script id="{DATA_ELEMENT_ID}" type="application/json">(.*?)</script>', html, re.DOTALL)
    return json.loads(match.group(1))


def count_routes(nodes):
    return sum(count_routes(node["children"]) if node["type"] == "include" else 1 for node in nodes)


def test_json_holds_the_whole_map(url_map):
    """Given the map of the demo shop,
    When it is rendered as JSON,
    Then the JSON is valid and holds the meta data and every route with its controls."""
    data = json.loads(render_json(url_map))
    orders = next(node for node in data["tree"] if node["type"] == "include" and node["url"] == "/orders/")
    order_list = orders["children"][0]

    assert data["meta"]["urlconf"] == "tests.demo.urls"
    assert count_routes(data["tree"]) == sum(1 for _ in url_map.routes())
    assert (order_list["type"], order_list["name"], order_list["category"]) == ("route", "orders:list", "protected")
    assert order_list["controls"][0] == {
        "kind": "access",
        "label": "login_required",
        "detail": None,
        "where": None,
        "scope": None,
    }


def test_page_embeds_the_same_data_as_the_json(url_map):
    """Given the map of the demo shop,
    When it is rendered as an HTML page,
    Then the page holds the data of the JSON in a json_script element."""
    html = render_html(url_map)

    assert html.startswith("<!doctype html>")
    assert page_data(html) == json.loads(render_json(url_map))


def test_closing_script_tag_in_the_data_does_not_break_the_page(url_map):
    """Given a route whose name holds </script> and an HTML comment opener,
    When the map is rendered as an HTML page,
    Then the data stay inside their script element and read back unchanged."""
    name = "</script><script>alert(1)</script><!--"
    evil = Route(url="/x/", prefix="/", name=name, view="shop.views.x", kind="FBV", project=True)
    url_map = UrlMap(meta=url_map.meta, tree=[evil, *url_map.tree])

    html = render_html(url_map)

    assert "<script>alert(1)" not in html
    assert page_data(html)["tree"][0]["name"] == name


def test_page_needs_no_external_resource(url_map):
    """Given the map of the demo shop,
    When it is rendered as an HTML page,
    Then the page loads nothing from the network: no external URL, stylesheet link or script source."""
    html = render_html(url_map)

    assert not re.search(r"https?://|//cdn|<link\b|<script[^>]+src=|@import|url\(", html)
