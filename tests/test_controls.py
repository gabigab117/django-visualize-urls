"""Access control of each route of the demo shop: one test for each way of protecting a view."""

import inspect

import pytest

from django_visualize_urls.collect import collect_urls
from tests.demo import decorators
from tests.demo.catalog import views as catalog_views

LOGIN_REQUIRED_MIDDLEWARE = "django.contrib.auth.middleware.LoginRequiredMiddleware"


@pytest.fixture
def drf():
    return pytest.importorskip("rest_framework")


def kinds_and_labels(route):
    return [(control.kind, control.label) for control in route.controls]


# Function views


def test_login_required(route):
    """Given a view decorated with login_required (and never_cache),
    When the map is collected,
    Then the route is protected by login_required, and never_cache is listed as another decorator."""
    orders = route("orders:list")

    assert orders.category == "protected"
    assert kinds_and_labels(orders) == [("access", "login_required"), ("other", "never_cache")]


def test_permission_required_with_its_permissions(route):
    """Given a view decorated with permission_required and two permissions,
    When the map is collected,
    Then the route is protected by permission_required, which lists both permissions."""
    refund = route("orders:refund")

    assert refund.category == "protected"
    assert [(control.label, control.detail) for control in refund.controls] == [
        ("permission_required", "orders.change_order, orders.refund_order")
    ]


def test_staff_member_required(route):
    """Given a view decorated with staff_member_required of the admin,
    When the map is collected,
    Then the route is protected by staff_member_required."""
    export = route("orders:export")

    assert (export.category, kinds_and_labels(export)) == ("protected", [("access", "staff_member_required")])


def test_project_decorator_is_named_after_its_variable(route):
    """Given staff_required = user_passes_test(lambda user: user.is_staff) in the project,
    When the map is collected,
    Then the route is protected by staff_required, with the line of the lambda and its place."""
    control = route("orders:stats").controls[0]
    test_func = inspect.getclosurevars(decorators.staff_required).nonlocals["test_func"]

    assert (control.kind, control.label) == ("access", "staff_required")
    assert control.detail == "staff_required = user_passes_test(lambda user: user.is_staff)"
    assert control.where == f"demo/decorators.py:{test_func.__code__.co_firstlineno}"


def test_project_decorator_with_a_named_test(route):
    """Given returns_manager_required = user_passes_test(can_manage_returns) in the project,
    When the map is collected,
    Then the route is protected by returns_manager_required, whose detail names the test."""
    control = route("orders:returns:create").controls[0]

    assert (control.kind, control.label, control.detail) == ("access", "returns_manager_required", "can_manage_returns")


def test_inline_user_passes_test(route):
    """Given a view decorated with user_passes_test and a lambda written in place,
    When the map is collected,
    Then the route is protected by user_passes_test, whose detail is the line of the lambda."""
    control = route("orders:purge").controls[0]

    assert (control.kind, control.label) == ("access", "user_passes_test")
    assert control.detail == "@user_passes_test(lambda user: user.is_superuser)"


def test_login_required_on_top_of_require_post(route):
    """Given a view decorated with login_required then require_POST,
    When the map is collected,
    Then the route is protected and only answers POST."""
    cancel = route("orders:cancel")

    assert (cancel.category, cancel.methods, kinds_and_labels(cancel)) == (
        "protected",
        ["POST"],
        [("access", "login_required")],
    )


def test_csrf_exempt(route):
    """Given a webhook decorated with csrf_exempt,
    When the map is collected,
    Then the route is flagged csrf exempt, and csrf_exempt is not counted as a control."""
    webhook = route("orders:payment-webhook")

    assert (webhook.csrf, webhook.category, webhook.controls) == ("exempt", "none", [])


def test_decorator_made_from_a_middleware(route):
    """Given a public view decorated with cache_page, built by decorator_from_middleware(),
    When the map is collected,
    Then cache_page is named after its middleware, and the route has no access control."""
    help_page = route("orders:help")

    assert (help_page.category, kinds_and_labels(help_page)) == ("none", [("other", "cache_page")])


# Class-based views


def test_login_required_mixin_and_methods_read_from_the_handlers(route):
    """Given a TemplateView with LoginRequiredMixin and a post() handler,
    When the map is collected,
    Then the route is protected by LoginRequiredMixin and answers GET and POST."""
    create = route("catalog:create")

    assert (create.kind, create.category, create.methods) == ("CBV", "protected", ["GET", "POST"])
    assert kinds_and_labels(create) == [("access", "LoginRequiredMixin")]


def test_permission_required_mixin(route):
    """Given a view with PermissionRequiredMixin and two permissions,
    When the map is collected,
    Then the route is protected by PermissionRequiredMixin, which lists the permissions."""
    delete = route("catalog:delete")

    assert (delete.category, delete.methods) == ("protected", ["POST"])
    assert [(control.label, control.detail) for control in delete.controls] == [
        ("PermissionRequiredMixin", "catalog.delete_product, catalog.view_product")
    ]


def test_user_passes_test_mixin(route):
    """Given a view with UserPassesTestMixin,
    When the map is collected,
    Then the route is protected by UserPassesTestMixin, which points at its test_func()."""
    control = route("catalog:stock").controls[0]
    line = inspect.getsourcelines(catalog_views.StockView.test_func)[1]

    assert (control.label, control.detail) == ("UserPassesTestMixin", "StockView.test_func")
    assert control.where == f"demo/catalog/views.py:{line}"


def test_method_decorator_on_dispatch(route):
    """Given a class decorated with method_decorator(login_required, name="dispatch"),
    When the map is collected,
    Then the route is protected by login_required."""
    wishlist = route("catalog:wishlist")

    assert (wishlist.category, kinds_and_labels(wishlist)) == ("protected", [("access", "login_required")])


def test_method_decorator_on_one_handler_only(route):
    """Given a view whose post() alone is decorated with method_decorator(login_required),
    When the map is collected,
    Then login_required is scoped to POST and the route is a hint to read, as GET stays public."""
    reviews = route("catalog:reviews")

    assert reviews.category == "hint"
    assert [(control.label, control.scope) for control in reviews.controls] == [("login_required", "POST")]


def test_project_mixin_with_a_hint(route):
    """Given a project mixin whose dispatch() raises PermissionDenied,
    When the map is collected,
    Then the route has a hint named after the mixin, with the words found."""
    suppliers = route("catalog:suppliers")

    assert suppliers.category == "hint"
    assert [(control.kind, control.label, control.detail) for control in suppliers.controls] == [
        ("hint", "SupplierRequiredMixin", "PermissionDenied, has_perm")
    ]


def test_project_mixin_without_a_hint(route):
    """Given a project mixin that only adds context, and a project base view,
    When the map is collected,
    Then the mixin is listed as another control, the base view is not, and the route has no access control."""
    detail = route("catalog:detail")

    assert (detail.category, kinds_and_labels(detail)) == ("none", [("other", "BreadcrumbMixin")])


# Django REST framework


def test_drf_is_authenticated(drf, route):
    """Given an APIView with IsAuthenticated,
    When the map is collected,
    Then the route is protected by IsAuthenticated, with the authentication classes and the methods of the handlers."""
    stats = route("api:stats")

    assert (stats.kind, stats.category, stats.methods) == ("DRF", "protected", ["GET"])
    assert [(control.label, control.detail) for control in stats.controls] == [
        ("IsAuthenticated", "authentication: SessionAuthentication, BasicAuthentication")
    ]


def test_drf_allow_any(drf, route):
    """Given an APIView with AllowAny,
    When the map is collected,
    Then the route has no access control."""
    status = route("api:status")

    assert (status.category, status.controls) == ("none", [])


def test_drf_routed_viewset(drf, route):
    """Given a ViewSet registered on a router, with composed permissions,
    When the map is collected,
    Then each route answers the methods of its actions, and the composition is spelled out."""
    carts = route("api:cart-list")
    cart = route("api:cart-detail")

    assert (carts.methods, cart.methods, cart.url) == (["GET", "POST"], ["GET", "DELETE"], "/api/carts/<pk>/")
    assert [control.label for control in cart.controls] == ["IsAuthenticated & ~IsAdminUser"]


def test_drf_csrf_exemption_of_as_view(drf, route):
    """Given DRF views, which APIView.as_view() exempts from CsrfViewMiddleware,
    When the map is collected,
    Then they are flagged, and told apart when SessionAuthentication checks the CSRF token again."""
    assert route("api:stats").csrf == "drf-session"
    assert route("api:partner-orders").csrf == "drf"


def test_drf_api_view_function(drf, route):
    """Given a function decorated with @api_view(["POST"]) and @permission_classes,
    When the map is collected,
    Then the route points at the function, answers POST and is protected."""
    refresh = route("api:refresh-cache")

    assert (refresh.view, refresh.src, refresh.methods) == (
        "tests.demo.api.views.refresh_cache",
        "demo/api/views.py",
        ["POST"],
    )
    assert kinds_and_labels(refresh) == [("access", "IsAdminUser")]


# Admin


def test_admin_views_are_protected_by_the_site(route):
    """Given admin.site.urls, and the password view that UserAdmin wraps itself with admin_view(),
    When the map is collected,
    Then both routes are protected by the admin site."""
    index = route("admin:index")
    password = route("admin:auth_user_password_change")

    assert (index.kind, index.category, kinds_and_labels(index)) == ("admin", "protected", [("admin", "admin_view")])
    assert (password.kind, password.category, password.controls[0].label) == ("admin", "protected", "admin_view")


def test_admin_login_page_is_public(route):
    """Given the login page of the admin site,
    When the map is collected,
    Then the route is an admin view without access control."""
    login = route("admin:login")

    assert (login.kind, login.category) == ("admin", "none")


# LoginRequiredMiddleware


def test_login_required_middleware(settings, route):
    """Given LoginRequiredMiddleware in MIDDLEWARE,
    When the map is collected,
    Then the routes require login, except the views marked login_not_required."""
    settings.MIDDLEWARE = [*settings.MIDDLEWARE, LOGIN_REQUIRED_MIDDLEWARE]

    help_page = route("orders:help")
    receipt = route("orders:receipt")

    assert (help_page.category, kinds_and_labels(help_page)[0]) == ("protected", ("access", "LoginRequiredMiddleware"))
    assert (receipt.category, receipt.controls) == ("none", [])
    assert route("admin:login").category == "none"


def test_login_required_middleware_skips_drf_views(drf, settings, route):
    """Given LoginRequiredMiddleware in MIDDLEWARE,
    When the map is collected,
    Then DRF views, which APIView.as_view() marks login_not_required, are not covered by it."""
    settings.MIDDLEWARE = [*settings.MIDDLEWARE, LOGIN_REQUIRED_MIDDLEWARE]

    assert route("api:status").controls == []


def test_subclass_of_login_required_middleware(settings):
    """Given a project middleware that subclasses LoginRequiredMiddleware,
    When the map is collected,
    Then the middleware is found."""
    settings.MIDDLEWARE = [*settings.MIDDLEWARE, "tests.demo.middleware.ShopLoginRequiredMiddleware"]

    assert collect_urls().meta["login_middleware"] is True


def test_middleware_that_cannot_be_imported_is_skipped(settings):
    """Given a middleware path that cannot be imported,
    When the map is collected,
    Then it is skipped instead of failing the map."""
    settings.MIDDLEWARE = ["tests.demo.missing.Middleware", *settings.MIDDLEWARE]

    assert collect_urls().meta["login_middleware"] is False


# Hints


def test_hint_in_a_project_decorator(route):
    """Given ajax_only, a project decorator that raises PermissionDenied for another reason than access,
    When the map is collected,
    Then the route has a hint named after the decorator, with the word found and its place."""
    summary = route("orders:summary")
    control = summary.controls[0]

    assert (summary.category, control.kind, control.label, control.detail) == (
        "hint",
        "hint",
        "ajax_only",
        "PermissionDenied",
    )
    assert control.where.startswith("demo/decorators.py:")


def test_hint_in_the_view_body(route):
    """Given a view that checks is_authenticated in its body,
    When the map is collected,
    Then the route has a hint on the view code, with the words found."""
    track = route("orders:track")

    assert track.category == "hint"
    assert [(control.label, control.detail) for control in track.controls] == [
        ("view code", "is_authenticated, redirect_to_login")
    ]


def test_hints_setting(settings, route):
    """Given a webhook whose signature is checked in a function it calls, with no hint in the view itself,
    When verify_signature( is added to HINTS,
    Then the route has a hint."""
    assert route("orders:payment-webhook").category == "none"

    settings.VISUALIZE_URLS = {"HINTS": ["verify_signature("]}

    webhook = route("orders:payment-webhook")
    assert (webhook.category, [(control.label, control.detail) for control in webhook.controls]) == (
        "hint",
        [("view code", "verify_signature")],
    )


def test_neutral_decorators_setting(settings, route):
    """Given ajax_only listed in NEUTRAL_DECORATORS,
    When the map is collected,
    Then its code is not searched and the route has no hint."""
    settings.VISUALIZE_URLS = {"NEUTRAL_DECORATORS": ["ajax_only"]}

    summary = route("orders:summary")

    assert (summary.category, kinds_and_labels(summary)) == ("none", [("other", "ajax_only")])


def test_access_decorators_setting(settings, route):
    """Given api_key_required, a project decorator that answers 404 without the partner key: no hint word,
    When its dotted path is listed in ACCESS_DECORATORS,
    Then the route is protected by it."""
    assert route("orders:partner-feed").category == "none"

    settings.VISUALIZE_URLS = {"ACCESS_DECORATORS": ["tests.demo.decorators.api_key_required"]}

    feed = route("orders:partner-feed")
    assert (feed.category, [(control.kind, control.label, control.detail) for control in feed.controls]) == (
        "protected",
        [("access", "api_key_required", "listed in ACCESS_DECORATORS")],
    )


# Unexpected view shapes


def test_view_served_through_functools_partial(route):
    """Given a view served through functools.partial,
    When the map is collected,
    Then the decorators of the wrapped function are read."""
    page = route("legacy:page")

    assert (page.kind, page.category, page.view) == ("FBV", "protected", "tests.demo.legacy.views.page")


def test_callable_object_as_a_view(route):
    """Given an object used as a view, whose __call__() is decorated with method_decorator(never_cache),
    When the map is collected,
    Then the route points at its class and reads the decorators of __call__()."""
    old_home = route("legacy:old-home")

    assert (old_home.kind, old_home.view, old_home.src, old_home.category) == (
        "callable",
        "tests.demo.legacy.views.Redirect",
        "demo/legacy/views.py",
        "none",
    )
    assert kinds_and_labels(old_home) == [("other", "never_cache")]


def test_class_based_decorator(route):
    """Given a view decorated by a class whose instances wrap it,
    When the map is collected,
    Then the decorator is named after its class."""
    newsletter = route("legacy:newsletter")

    assert (newsletter.kind, kinds_and_labels(newsletter)) == ("FBV", [("other", "logged")])


def test_view_class_made_by_type(route):
    """Given a view class made by type(), whose source cannot be read,
    When the map is collected,
    Then the route gives its file without a line."""
    archived = route("legacy:archived-page")

    assert (archived.kind, archived.src, archived.line, archived.category) == (
        "CBV",
        "demo/legacy/views.py",
        None,
        "none",
    )


def test_view_that_cannot_be_read_carries_the_error(url_map):
    """Given a view whose introspection raises,
    When the map is collected,
    Then the map is complete and the route carries the error."""
    names = [route.name for route in url_map.routes()]
    broken = next(route for route in url_map.routes() if route.name == "legacy:broken")

    assert (broken.kind, broken.error) == ("?", "RuntimeError('the legacy view could not be loaded')")
    assert names.index("legacy:archived-page") == names.index("legacy:broken") + 1
