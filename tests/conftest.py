import pytest

from django_visualize_urls.collect import collect_urls


@pytest.fixture
def route():
    """Find the only route with a given name in the map of the demo shop.

    The map is collected at each call, so that the settings changed by a test apply.
    """

    def find(name, urlconf=None):
        routes = [route for route in collect_urls(urlconf).routes() if route.name == name]
        assert len(routes) == 1, f"{len(routes)} routes named {name!r}"
        return routes[0]

    return find


@pytest.fixture
def url_map():
    return collect_urls()
