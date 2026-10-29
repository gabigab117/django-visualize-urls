"""The page of the demo shop in a real browser, with Playwright: ``pytest -m browser``.

Needs the ``browser`` dependency group and Chromium: ``uv sync --group browser``, then
``uv run playwright install chromium``.
"""

import pytest

from django_visualize_urls.collect import collect_urls
from django_visualize_urls.render import render_html

expect = pytest.importorskip("playwright.sync_api").expect

pytestmark = pytest.mark.browser


def all_routes(nodes):
    for node in nodes:
        if node["type"] == "include":
            yield from all_routes(node["children"])
        else:
            yield node


@pytest.fixture
def demo(page):
    """The page of the demo shop open in the browser, its data, and the JavaScript errors it raised."""
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    url_map = collect_urls()
    page.set_content(render_html(url_map))
    return page, url_map.to_dict(), errors


def tile(page, key):
    return page.locator(f'.tile[data-key="{key}"] .tile-value')


def test_page_loads_without_javascript_errors(demo):
    """Given the page of the demo shop,
    When it loads in the browser,
    Then it raises no JavaScript error and draws the tree."""
    page, data, errors = demo

    expect(page.locator("#tree > .node").first).to_be_visible()
    assert errors == []


def test_tiles_match_the_json(demo):
    """Given the page of the demo shop, third-party routes hidden,
    When it loads,
    Then each tile counts the project routes of the JSON that it stands for."""
    page, data, _ = demo
    routes = [route for route in all_routes(data["tree"]) if route["project"]]
    expected = {
        "all": len(routes),
        "protected": sum(route["category"] == "protected" for route in routes),
        "hint": sum(route["category"] == "hint" for route in routes),
        "none": sum(route["category"] == "none" for route in routes),
        "csrf": sum(bool(route["csrf"]) for route in routes),
        "duplicate": sum(route["duplicate"] for route in routes),
        "unnamed": sum(not route["name"] for route in routes),
        "error": sum(bool(route["error"]) for route in routes),
    }

    for key, count in expected.items():
        expect(tile(page, key)).to_have_text(str(count))


def test_search_shows_the_matching_routes(demo):
    """Given the page of the demo shop,
    When "webhook" is typed in the search field,
    Then only the payment webhook is shown, its include unfolded."""
    page, _, errors = demo

    page.fill("#q", "webhook")

    expect(page.locator("#status")).to_contain_text("1 route shown")
    expect(page.locator(".route:visible .name")).to_have_text(["orders:payment-webhook"])
    assert errors == []


def test_third_party_routes_toggle(demo):
    """Given the page of the demo shop, third-party routes hidden,
    When the third-party switch is turned on,
    Then the tiles and the status count every route of the JSON."""
    page, data, errors = demo
    routes = list(all_routes(data["tree"]))
    expect(tile(page, "all")).to_have_text(str(sum(route["project"] for route in routes)))

    page.check("#third-party")

    expect(tile(page, "all")).to_have_text(str(len(routes)))
    expect(page.locator("#status")).to_have_text(f"{len(routes)} routes shown")
    assert errors == []
