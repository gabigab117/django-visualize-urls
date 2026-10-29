"""Access controls of a view, read by introspection of the loaded code.

``functools.wraps`` copies the name and module of a view onto each wrapper a decorator leaves in the
``__wrapped__`` chain, but not its ``__code__``: the code tells which function made the wrapper, and its
closure holds the decorator arguments (the test of ``user_passes_test``, the methods of
``require_http_methods``...). A project decorator built on Django's is thus recognized without any setting.
"""

from __future__ import annotations

import functools
import inspect
import re
from dataclasses import dataclass
from dataclasses import field
from types import FunctionType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django_visualize_urls.collect import Sources

# Kinds of controls.
ACCESS = "access"  # recognized access control
ADMIN = "admin"  # view served by an admin site, which requires an active staff account
HINT = "hint"  # project code that looks like a hand-written check
OTHER = "other"  # decorator or mixin without a recognized access control
KIND_ORDER = (ACCESS, ADMIN, HINT, OTHER)

# Route categories.
PROTECTED = "protected"
HINTED = "hint"
NONE = "none"

# Words that reveal a hand-written check in project code: view body, decorator or mixin.
BUILTIN_HINTS = (
    r"is_authenticated|is_anonymous|is_staff|is_superuser|has_perms?\(|PermissionDenied|HttpResponseForbidden"
    r"|status=40[13]|HTTP_40[13]_\w+|HTTPStatus\.(?:UNAUTHORIZED|FORBIDDEN)|NotAuthenticated|redirect_to_login"
    r"|compare_digest|hmac\.|construct_event|verify_header"
)

# Functions that make the wrappers, as (module, function) pairs.
USER_PASSES_TEST = ("django.contrib.auth.decorators", "user_passes_test")
LOGIN_REQUIRED = ("django.contrib.auth.decorators", "login_required")
PERMISSION_REQUIRED = ("django.contrib.auth.decorators", "permission_required")
STAFF_MEMBER_REQUIRED = ("django.contrib.admin.views.decorators", "staff_member_required")
REQUIRE_HTTP_METHODS = ("django.views.decorators.http", "require_http_methods")
CSRF_EXEMPT = ("django.views.decorators.csrf", "csrf_exempt")
METHOD_DECORATOR = ("django.utils.decorators", "_multi_decorate")
MIDDLEWARE_DECORATOR = ("django.utils.decorators", "make_middleware_decorator")
ADMIN_WRAPPERS = {
    ("django.contrib.admin.sites", "AdminSite.admin_view"),
    ("django.contrib.admin.sites", "AdminSite.get_urls"),
    ("django.contrib.admin.options", "ModelAdmin.get_urls"),
}
API_VIEW = ("rest_framework.decorators", "api_view")

# Decorators made by decorator_from_middleware(), named after their middleware.
MIDDLEWARE_DECORATORS = {
    "CacheMiddleware": "cache_page",
    "ConditionalGetMiddleware": "conditional_page",
    "CsrfViewMiddleware": "csrf_protect",
    "GZipMiddleware": "gzip_page",
    "_EnsureCsrfCookie": "ensure_csrf_cookie",
    "_EnsureCsrfToken": "requires_csrf_token",
}

# Classes are compared by dotted name: importing django.contrib.auth.mixins needs the auth app installed.
ACCESS_MIXINS = {
    "django.contrib.auth.mixins.LoginRequiredMixin",
    "django.contrib.auth.mixins.PermissionRequiredMixin",
    "django.contrib.auth.mixins.UserPassesTestMixin",
}
ADMIN_CLASSES = ("django.contrib.admin.sites.AdminSite", "django.contrib.admin.options.BaseModelAdmin")
API_VIEW_CLASS = "rest_framework.views.APIView"
SESSION_AUTHENTICATION = "rest_framework.authentication.SessionAuthentication"

# Order of View.http_method_names, without the implicit HEAD and OPTIONS.
METHOD_ORDER = ("get", "post", "put", "patch", "delete", "trace")


@dataclass
class Control:
    kind: str
    label: str
    detail: str | None = None
    where: str | None = None  # "path:line" of the project code that holds the control
    scope: str | None = None  # HTTP method of the only handler it covers (method_decorator on post()...)


@dataclass
class Analysis:
    kind: str  # FBV, CBV, DRF, admin or callable
    target: object  # function or class that locates the view
    controls: list[Control]
    methods: list[str] | None  # None: every method
    csrf: str | None  # "exempt", "drf" (exempted by APIView.as_view()) or "drf-session" (checked by DRF)
    category: str


@dataclass
class _Findings:
    controls: list[Control] = field(default_factory=list)
    methods: list[list[str]] = field(default_factory=list)  # one list per require_http_methods()


def origin(func):
    """(module, function) that made ``func``: the outer function of its code, without ``<locals>``."""
    func = getattr(func, "__func__", func)  # bound method
    if not inspect.isfunction(func):
        return None
    return func.__globals__.get("__name__"), func.__code__.co_qualname.split(".<locals>")[0]


def closure(func):
    return inspect.getclosurevars(func).nonlocals


def unwrap(func):
    """Wrappers of the ``__wrapped__`` chain, outermost first, and the object they wrap.

    The chain stops at the function made by ``as_view()``, which copies ``__wrapped__`` from ``dispatch()``.
    """
    layers = []

    def stop(wrapper):
        code = getattr(wrapper, "__code__", None)
        if code is not None and code.co_qualname.endswith("as_view.<locals>.view"):
            return True
        layers.append(wrapper)
        return False

    return layers, inspect.unwrap(func, stop=stop)


def hidden_layers(wrapper, free):
    """Wrappers that a later ``update_wrapper()`` took out of the ``__wrapped__`` chain.

    ``AdminSite.admin_view()`` wraps the view with its permission check, ``never_cache`` and ``csrf_protect``, then
    points ``__wrapped__`` of the outermost wrapper at the view: the others stay reachable through the
    ``view_func`` closure that Django's decorators keep.
    """
    end = getattr(wrapper, "__wrapped__", None)
    func = free.get("view_func")
    layers = []
    while inspect.isfunction(func) and func is not end and len(layers) < 50:
        layers.append(func)
        func = getattr(func, "__wrapped__", None)
    return layers


def dotted(cls):
    return f"{cls.__module__}.{cls.__qualname__}"


def inherits(obj, name):
    cls = obj if isinstance(obj, type) else type(obj)
    return any(dotted(base) == name for base in cls.__mro__)


def ordered_methods(names):
    order = {method: index for index, method in enumerate(METHOD_ORDER)}
    return sorted((name.upper() for name in names), key=lambda name: (order.get(name.lower(), len(order)), name))


def handler_methods(cls):
    """Methods a class-based view answers, read from its handlers."""
    names = [name for name in cls.http_method_names if name not in ("head", "options") and hasattr(cls, name)]
    return ordered_methods(names) or None


def permission_name(permission, nested=False):
    """Name of a DRF permission class, or of a composition such as ``IsAuthenticated & ~IsAdminUser``."""
    if hasattr(permission, "op2_class"):
        symbol = {"AND": "&", "OR": "|"}[permission.operator_class.__name__]
        text = f"{permission_name(permission.op1_class, True)} {symbol} {permission_name(permission.op2_class, True)}"
        return f"({text})" if nested else text
    if hasattr(permission, "op1_class"):
        return f"~{permission_name(permission.op1_class, True)}"
    return permission.__name__


def api_view_function(cls):
    """Function decorated by DRF's ``@api_view``, which builds a ``WrappedAPIView`` class around it."""
    for value in vars(cls).values():
        if type(value) is FunctionType and origin(value) == API_VIEW:
            return closure(value)["func"]
    return None


def decorator_variable(test):
    """Name of the module variable holding ``user_passes_test(test)``, as in ``staff_required = ...``."""
    for name, value in tuple(getattr(test, "__globals__", {}).items()):
        # type() and not isinstance(): isinstance() reads __class__, which evaluates a SimpleLazyObject.
        if (
            type(value) is FunctionType
            and origin(value) == USER_PASSES_TEST
            and value.__code__.co_name == "decorator"
            and closure(value).get("test_func") is test
        ):
            return name
    return None


def first_line(obj):
    return inspect.getsource(obj).strip().splitlines()[0][:160]


def dummy_view():
    """Stand-in view that method_decorator() decorators are applied to, as Django itself does."""
    return lambda request, *args, **kwargs: None


class Inspector:
    """Reads the access controls of views, with the project settings."""

    def __init__(self, sources: Sources, config, login_middleware):
        self.sources = sources
        extra = "".join(f"|{re.escape(hint)}" for hint in config["HINTS"])
        self.hints = re.compile(BUILTIN_HINTS + extra)
        self.neutral = set(config["NEUTRAL_DECORATORS"])
        self.access = set(config["ACCESS_DECORATORS"])
        self.login_middleware = login_middleware

    def analyze(self, callback):
        # Django calls a functools.partial as it is: its func holds the decorators, the partial itself the
        # attributes that the middleware read (csrf_exempt, login_required).
        view = callback.func if isinstance(callback, functools.partial) else callback
        layers, inner = unwrap(view)
        found = _Findings()
        for layer in layers:
            self._layer(layer, found)
        methods = None
        csrf = "exempt" if getattr(callback, "csrf_exempt", False) else None
        drf_class = getattr(view, "cls", None)
        if drf_class is not None and inherits(drf_class, API_VIEW_CLASS):
            kind, target = "DRF", api_view_function(drf_class) or drf_class
            self._view_class(drf_class, found)
            csrf, methods = self._drf(view, drf_class, found)
        elif hasattr(view, "view_class"):
            kind, target = "CBV", view.view_class
            self._view_class(target, found)
            methods = handler_methods(target)
        elif not inspect.isroutine(inner):  # an object with a __call__() method
            kind, target = "callable", type(inner)
            for layer in unwrap(target.__call__)[0]:
                self._layer(layer, found)
        else:
            kind, target = "FBV", inner
            owner = getattr(view, "__self__", None)
            admin_owner = owner is not None and any(inherits(owner, name) for name in ADMIN_CLASSES)
            if admin_owner or any(control.kind == ADMIN for control in found.controls):
                kind = "admin"
        for allowed in found.methods:
            methods = [method for method in (allowed if methods is None else methods) if method in allowed]
        if self.login_middleware and getattr(callback, "login_required", True):
            found.controls.append(Control(ACCESS, "LoginRequiredMiddleware"))
        controls = list({(control.kind, control.label, control.scope): control for control in found.controls}.values())
        category = self._category(controls, target)
        controls.sort(key=lambda control: KIND_ORDER.index(control.kind))
        return Analysis(kind, target, controls, methods, csrf, category)

    def _category(self, controls, target):
        if any(control.kind in (ACCESS, ADMIN) and control.scope is None for control in controls):
            return PROTECTED
        if any(control.kind in (ACCESS, ADMIN, HINT) for control in controls):  # a hint, or some handlers only
            return HINTED
        hints = self._hints(target) if self.sources.is_project(target) else None
        if hints:
            controls.append(Control(HINT, "view code", hints, self.sources.where(target)))
            return HINTED
        return NONE

    def _hints(self, obj):
        try:
            source = inspect.getsource(obj)
        except OSError:  # a class made by type(): its file is known, its source is not
            return None
        found = {match.rstrip("(.") for match in self.hints.findall(source)}
        return ", ".join(sorted(found)) or None

    def _layer(self, func, found, scope=None):
        """Record the control left by a wrapper of the ``__wrapped__`` chain."""
        made_by = origin(func)
        if made_by is None:  # an object left by a class-based decorator
            cls = type(func)
            found.controls.append(self._unknown(cls, (cls.__module__, cls.__qualname__), scope))
            return
        free = closure(func)
        for layer in hidden_layers(func, free):
            self._layer(layer, found, scope)
        if made_by == USER_PASSES_TEST:
            found.controls.append(self._test(free["test_func"], scope))
        elif made_by == REQUIRE_HTTP_METHODS:
            found.methods.append(list(free["request_method_list"]))
        elif made_by == METHOD_DECORATOR:
            for decorator in free["decorators"]:
                for layer in unwrap(decorator(dummy_view()))[0]:
                    self._layer(layer, found, scope)
        elif made_by == MIDDLEWARE_DECORATOR:
            middleware = type(closure(free["_pre_process_request"])["middleware"]).__name__
            found.controls.append(Control(OTHER, MIDDLEWARE_DECORATORS.get(middleware, middleware), scope=scope))
        elif made_by in ADMIN_WRAPPERS:
            site = free["self"]
            site = getattr(site, "admin_site", site)  # ModelAdmin.get_urls() goes through its admin site
            detail = f"{type(site).__name__}.has_permission(): active staff account by default"
            found.controls.append(Control(ADMIN, "admin_view", detail, scope=scope))
        elif made_by != CSRF_EXEMPT:  # read from the callback, as CsrfViewMiddleware does
            found.controls.append(self._unknown(func.__code__, made_by, scope))

    def _test(self, test, scope):
        """Control of a user_passes_test() wrapper, named after the decorator that holds its test."""
        made_by = origin(test)
        if made_by == PERMISSION_REQUIRED:
            return Control(ACCESS, "permission_required", ", ".join(closure(test)["perms"]), scope=scope)
        if made_by in (LOGIN_REQUIRED, STAFF_MEMBER_REQUIRED):
            return Control(ACCESS, made_by[1], scope=scope)
        name = getattr(test, "__name__", None)
        detail = first_line(test) if name == "<lambda>" else name or repr(test)
        label = decorator_variable(test) or "user_passes_test"
        return Control(ACCESS, label, detail, self.sources.where(test), scope)

    def _unknown(self, source, made_by, scope):
        """Control of a decorator the map does not know: the settings first, then the hints in its code.

        ``source`` is the code of the wrapper, or the class of a class-based decorator.
        """
        module, name = made_by
        where = self.sources.where(source)
        if name in self.access or f"{module}.{name}" in self.access:
            return Control(ACCESS, name, "listed in ACCESS_DECORATORS", where, scope)
        if where is None or name in self.neutral or f"{module}.{name}" in self.neutral:
            return Control(OTHER, name, None, where, scope)
        hints = self._hints(source)
        return Control(HINT if hints else OTHER, name, hints, where, scope)

    def _view_class(self, cls, found):
        """Controls of a class-based view: access mixins, project mixins, method_decorator() on its handlers."""
        for base in cls.__mro__[1:]:
            if dotted(base) in ACCESS_MIXINS:
                found.controls.append(self._mixin(cls, base))
            elif self.sources.is_project(base):
                hints = self._hints(base)
                if hints or base.__name__.endswith("Mixin"):
                    where = self.sources.where(base)
                    found.controls.append(Control(HINT if hints else OTHER, base.__name__, hints, where))
        for layer in unwrap(cls.dispatch)[0]:
            self._layer(layer, found)
        for name in cls.http_method_names:
            handler = _Findings()
            for layer in unwrap(getattr(cls, name, None))[0]:
                self._layer(layer, handler, name.upper())
            found.controls += handler.controls  # a require_http_methods() on a handler only restates its method

    def _mixin(self, cls, mixin):
        if mixin.__name__ == "PermissionRequiredMixin":
            perms = cls.permission_required
            return Control(
                ACCESS, mixin.__name__, (perms if isinstance(perms, str) else ", ".join(perms or ())) or None
            )
        if mixin.__name__ == "UserPassesTestMixin":
            return Control(ACCESS, mixin.__name__, cls.test_func.__qualname__, self.sources.where(cls.test_func))
        return Control(ACCESS, mixin.__name__)

    def _drf(self, view, cls, found):
        """CSRF and methods of a DRF view; its permission classes are recorded unless they all allow any."""
        permissions = [permission_name(permission) for permission in cls.permission_classes]
        authentication = [authenticator.__name__ for authenticator in cls.authentication_classes]
        if set(permissions) - {"AllowAny"}:
            detail = f"authentication: {', '.join(authentication) or 'none'}"
            found.controls.append(Control(ACCESS, " + ".join(permissions), detail))
        session = any(inherits(authenticator, SESSION_AUTHENTICATION) for authenticator in cls.authentication_classes)
        actions = getattr(view, "actions", None)  # routed ViewSet: {"get": "list", "post": "create"}
        return "drf-session" if session else "drf", ordered_methods(actions) if actions else handler_methods(cls)
