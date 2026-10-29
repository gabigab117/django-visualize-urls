"""Tree of the URL map: includes, full URLs, names, project and third-party routes, sources."""

import inspect
from datetime import datetime
from pathlib import Path

import django
import pytest
from django.conf import settings
from django.contrib.admindocs.views import simplify_regex
from django.core.exceptions import ImproperlyConfigured

from django_visualize_urls import __version__
from django_visualize_urls.collect import Include
from django_visualize_urls.collect import Sources
from django_visualize_urls.collect import collect_urls
from tests.demo.orders import views as order_views


def nodes(tree):
    for node in tree:
        yield node
        if isinstance(node, Include):
            yield from nodes(node.children)


def include_at(url_map, url):
    return next(node for node in nodes(url_map.tree) if isinstance(node, Include) and node.url == url)


def route_at(url_map, url):
    return next(route for route in url_map.routes() if route.url == url)


def test_nested_include_gives_full_url_and_prefix(route):
    """Given a route two includes deep (orders/, then returns/),
    When the map is collected,
    Then its URL is the full path and its prefix is the path of the include that holds it."""
    create = route("orders:returns:create")

    assert (create.url, create.prefix) == ("/orders/returns/new/", "/orders/returns/")


def test_include_of_a_project_module(url_map):
    """Given include("tests.demo.orders.urls"), whose module sets app_name,
    When the map is collected,
    Then the include node names the module, its file and its namespace."""
    orders = include_at(url_map, "/orders/")

    assert (orders.namespace, orders.app_name, orders.module) == ("orders", "orders", "tests.demo.orders.urls")
    assert (orders.src, orders.project) == ("demo/orders/urls.py", True)


def test_include_of_a_pattern_list_with_an_app_name(url_map):
    """Given include((patterns, "returns")) inside the orders URLconf,
    When the map is collected,
    Then the node has the namespace but no module, and its routes combine both namespaces."""
    returns = include_at(url_map, "/orders/returns/")

    assert (returns.namespace, returns.app_name, returns.module, returns.src) == ("returns", "returns", None, None)
    assert [route.name for route in returns.children] == ["orders:returns:list", "orders:returns:create"]


def test_admin_site_urls(url_map):
    """Given admin.site.urls mounted on admin/,
    When the map is collected,
    Then it is a list of patterns in the admin namespace, out of the project."""
    admin = include_at(url_map, "/admin/")

    assert (admin.namespace, admin.app_name, admin.module, admin.project) == ("admin", "admin", None, False)


def test_re_path_is_shown_like_a_path(route):
    """Given a route declared with re_path() and a named group,
    When the map is collected,
    Then its URL reads like a path."""
    assert route("archive").url == "/archive/<year>/"


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (r"^archive/(?P<year>[0-9]{4})/$", "/archive/<year>/"),
        (r"^files/(.+)\.pdf$", r"/files/<var>\.pdf"),
        (r"^(?:page-(?P<number>\d+)/)?$", "/"),
        ("orders/<int:pk>/", "/orders/<int:pk>/"),
        ("", "/"),
    ],
)
def test_simplify_regex_of_admindocs(pattern, expected):
    """Given simplify_regex() of django.contrib.admindocs, an undocumented function the map relies on,
    When it reads regular expressions and path() routes,
    Then it gives the forms shown on the page: a change in Django shows here first."""
    assert simplify_regex(pattern) == expected


def test_route_without_a_name(url_map):
    """Given robots.txt declared without a name,
    When the map is collected,
    Then the route has no name."""
    assert route_at(url_map, "/robots.txt").name is None


def test_duplicate_names_are_flagged(url_map, route):
    """Given two catalog routes named search, with and without a query,
    When the map is collected,
    Then both are flagged as duplicates, and a route with a name of its own is not."""
    search = [route for route in url_map.routes() if route.name == "catalog:search"]

    assert [route.duplicate for route in search] == [True, True]
    assert route("catalog:list").duplicate is False


def test_project_and_third_party_routes(url_map, route):
    """Given project views, a TemplateView declared in the project URLconf, the auth URLs and the admin,
    When the map is collected,
    Then the routes declared or served by the project are the project's, and those of packages are not."""
    orders = route("orders:list")
    robots = route_at(url_map, "/robots.txt")

    assert (orders.project, orders.local) == (True, True)
    assert (robots.project, robots.local, robots.view) == (True, False, "django.views.generic.base.TemplateView")
    assert route("login").project is False
    assert route("admin:index").project is False


def test_route_source_and_editor_link(route):
    """Given a view of the project,
    When the map is collected,
    Then the route gives its file from the project root, its line and a VS Code link to it."""
    orders = route("orders:list")
    path = (Path(settings.BASE_DIR) / "demo/orders/views.py").as_posix()

    assert (orders.src, orders.line) == ("demo/orders/views.py", inspect.getsourcelines(order_views.order_list)[1])
    assert orders.editor_url == f"vscode://file/{path.lstrip('/')}:{orders.line}"


def test_editor_root_replaces_the_project_root():
    """Given a project that runs in a container while the editor runs on the host,
    When the map is collected with editor_root,
    Then the editor links point at the folder of the host."""
    orders = next(
        route for route in collect_urls(editor_root="/Users/me/shop/").routes() if route.name == "orders:list"
    )

    assert orders.editor_url == f"vscode://file/Users/me/shop/demo/orders/views.py:{orders.line}"


def test_editor_url_setting(settings, route):
    """Given EDITOR_URL set for another editor,
    When the map is collected,
    Then the links follow it."""
    settings.VISUALIZE_URLS = {"EDITOR_URL": "pycharm://open?file=/{path}&line={line}"}

    assert route("orders:list").editor_url.startswith("pycharm://open?file=/")


def test_editor_links_can_be_disabled(settings, route):
    """Given EDITOR_URL set to None,
    When the map is collected,
    Then no route has an editor link."""
    settings.VISUALIZE_URLS = {"EDITOR_URL": None}

    assert route("orders:list").editor_url is None


def test_project_root_without_base_dir(settings, route):
    """Given settings without BASE_DIR,
    When the map is collected,
    Then the project root is the folder that holds the package of ROOT_URLCONF."""
    del settings.BASE_DIR

    assert route("orders:list").src == "tests/demo/orders/views.py"


def test_unknown_setting_is_refused(settings):
    """Given a misspelled key in VISUALIZE_URLS,
    When the map is collected,
    Then the error names the key and the valid ones."""
    settings.VISUALIZE_URLS = {"HINT": ["check_key("]}

    with pytest.raises(ImproperlyConfigured, match=r"Unknown VISUALIZE_URLS keys: HINT\. Valid keys: HINTS, "):
        collect_urls()


def test_package_file_is_shown_from_site_packages():
    """Given a file installed in the site-packages of a virtualenv inside the project,
    When it is displayed,
    Then its path starts after site-packages and it is not project code."""
    sources = Sources("/srv/shop")

    path = sources.display("/srv/shop/.venv/lib/python3.14/site-packages/django/views/generic/base.py")

    assert path == ("django/views/generic/base.py", False)


def test_file_outside_the_project_and_the_packages(tmp_path):
    """Given a file neither under the project root nor in site-packages,
    When it is displayed,
    Then its absolute path is shown and it is not project code."""
    sources = Sources(tmp_path / "shop")

    assert sources.display(tmp_path / "views.py") == ((tmp_path / "views.py").resolve().as_posix(), False)


def test_code_without_a_source_file():
    """Given a function compiled from a string,
    When it is located,
    Then it has no file, no line, and it is not project code."""
    namespace = {}
    exec(compile("def generated(request): pass", "<generated>", "exec"), namespace)

    assert Sources(settings.BASE_DIR).locate(namespace["generated"]) == (None, None, False)


def test_meta_describes_the_project(url_map):
    """Given the demo shop,
    When the map is collected,
    Then its meta data name the URLconf, the versions and the time, without LoginRequiredMiddleware."""
    meta = url_map.meta

    assert (meta["urlconf"], meta["django"], meta["version"]) == ("tests.demo.urls", django.get_version(), __version__)
    assert (meta["login_middleware"], meta["drf_default_permissions"]) == (False, None)
    assert datetime.fromisoformat(meta["generated"]).tzinfo is not None


def test_meta_lists_the_default_drf_permissions(settings):
    """Given DEFAULT_PERMISSION_CLASSES in the REST_FRAMEWORK settings,
    When the map is collected,
    Then the meta data list their class names."""
    settings.REST_FRAMEWORK = {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}

    assert collect_urls().meta["drf_default_permissions"] == ["IsAuthenticated"]


def test_other_urlconf():
    """Given the dotted path of another URLconf,
    When the map is collected from it,
    Then the map holds the routes of that module only, without its namespace."""
    url_map = collect_urls("tests.demo.catalog.urls")

    assert url_map.meta["urlconf"] == "tests.demo.catalog.urls"
    assert [route.name for route in url_map.routes()][:3] == ["list", "search", "search"]
