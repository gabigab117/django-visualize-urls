"""Walk the URL resolver loaded in memory and build the tree of includes and routes."""

from __future__ import annotations

import inspect
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from importlib import import_module
from pathlib import Path
from urllib.parse import quote

import django
from django.conf import settings
from django.contrib.admindocs.views import simplify_regex
from django.urls import URLResolver
from django.urls import get_resolver
from django.utils.module_loading import import_string

from django_visualize_urls import __version__
from django_visualize_urls.conf import get_config
from django_visualize_urls.controls import NONE
from django_visualize_urls.controls import Control
from django_visualize_urls.controls import Inspector
from django_visualize_urls.controls import inherits

LOGIN_REQUIRED_MIDDLEWARE = "django.contrib.auth.middleware.LoginRequiredMiddleware"


@dataclass
class Route:
    type: str = field(default="route", init=False)
    url: str
    prefix: str
    name: str | None  # with its namespaces, as reverse() takes it
    view: str
    kind: str  # FBV, CBV, DRF, admin, callable, or ? when the view could not be read
    project: bool  # declared in a URLconf of the project, or served by a view of the project
    src: str | None = None
    line: int | None = None
    local: bool = False  # the view itself is project code
    editor_url: str | None = None
    controls: list[Control] = field(default_factory=list)
    methods: list[str] | None = None
    csrf: str | None = None
    category: str = NONE
    duplicate: bool = False
    error: str | None = None


@dataclass
class Include:
    type: str = field(default="include", init=False)
    url: str
    prefix: str
    namespace: str | None
    app_name: str | None
    module: str | None  # None for a list of patterns (admin.site.urls, include([...]))
    src: str | None
    project: bool
    children: list[Include | Route]


@dataclass
class UrlMap:
    meta: dict
    tree: list[Include | Route]

    def routes(self):
        return iter_routes(self.tree)

    def to_dict(self):
        return {"meta": self.meta, "tree": [asdict(node) for node in self.tree]}


def iter_routes(nodes):
    for node in nodes:
        if isinstance(node, Include):
            yield from iter_routes(node.children)
        else:
            yield node


class Sources:
    """Tells project code from installed packages, and shows paths from their root."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def display(self, filename):
        """(path to show, whether the file belongs to the project)."""
        path = Path(filename).resolve()
        for folder in ("site-packages", "dist-packages"):
            if folder in path.parts:
                return "/".join(path.parts[path.parts.index(folder) + 1 :]), False
        if path.is_relative_to(self.root):
            return path.relative_to(self.root).as_posix(), True
        return path.as_posix(), False

    def locate(self, obj):
        """(path, line, in the project) of a function, class or code object; (None, None, False) if unknown."""
        code = getattr(obj, "__code__", obj)
        try:
            filename = inspect.getsourcefile(code)
        except TypeError:  # built-in
            filename = None
        if filename is None:
            return None, None, False
        path, local = self.display(filename)
        if inspect.iscode(code):
            return path, code.co_firstlineno, local
        try:
            return path, inspect.getsourcelines(obj)[1], local
        except OSError:  # a class made by type()
            return path, None, local

    def where(self, obj):
        """ "path:line" of project code, None for the code of an installed package."""
        path, line, local = self.locate(obj)
        if not local:
            return None
        return f"{path}:{line}" if line else path

    def is_project(self, obj):
        return self.locate(obj)[2]


def project_root():
    """settings.BASE_DIR, or else the folder that holds the package of ROOT_URLCONF."""
    base_dir = getattr(settings, "BASE_DIR", None)
    if base_dir:
        return Path(base_dir)
    module = import_module(settings.ROOT_URLCONF)
    path = Path(module.__file__).resolve()
    return path.parents[module.__name__.count(".") + (path.name == "__init__.py")]


def uses_login_middleware():
    """Whether settings.MIDDLEWARE holds LoginRequiredMiddleware or a subclass of it."""
    for dotted_path in settings.MIDDLEWARE:
        try:
            middleware = import_string(dotted_path)
        except ImportError:
            continue
        if inherits(middleware, LOGIN_REQUIRED_MIDDLEWARE):
            return True
    return False


def drf_default_permissions():
    classes = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_PERMISSION_CLASSES")
    return [dotted_path.rsplit(".", 1)[-1] for dotted_path in classes] if classes else None


class _Walker:
    def __init__(self, sources, inspector, editor_link):
        self.sources = sources
        self.inspector = inspector
        self.editor_link = editor_link

    def walk(self, patterns, raw_prefix, namespaces, declared):
        """Nodes of ``patterns``; ``declared``: they are declared in a URLconf module of the project."""
        nodes = []
        for pattern in patterns:
            raw = raw_prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                nodes.append(self._include(pattern, raw, raw_prefix, namespaces))
            else:
                nodes.append(self._route(pattern, raw, raw_prefix, namespaces, declared))
        return nodes

    def _include(self, resolver, raw, raw_prefix, namespaces):
        module = resolver.urlconf_module
        filename = getattr(module, "__file__", None)
        src, local = self.sources.display(filename) if filename else (None, False)
        if resolver.namespace:
            namespaces = (*namespaces, resolver.namespace)
        # A list of patterns has no module: its routes are the project's only when their view is.
        children = self.walk(resolver.url_patterns, raw, namespaces, local)
        return Include(
            url=simplify_regex(raw),
            prefix=simplify_regex(raw_prefix),
            namespace=resolver.namespace,
            app_name=resolver.app_name,
            module=getattr(module, "__name__", None),
            src=src if local else None,
            project=local or any(route.project for route in iter_routes(children)),
            children=children,
        )

    def _route(self, pattern, raw, raw_prefix, namespaces, declared):
        route = Route(
            url=simplify_regex(raw),
            prefix=simplify_regex(raw_prefix),
            name=":".join((*namespaces, pattern.name)) if pattern.name else None,
            view=pattern.lookup_str,
            kind="?",
            project=declared,
        )
        try:
            analysis = self.inspector.analyze(pattern.callback)
        except Exception as error:  # an unexpected view shape must not stop the whole map
            route.error = repr(error)
            return route
        route.src, route.line, route.local = self.sources.locate(analysis.target)
        route.view = f"{analysis.target.__module__}.{analysis.target.__qualname__}"
        route.kind = analysis.kind
        # A TemplateView declared in a URLconf of the project is a route of the project.
        route.project = declared or route.local
        route.editor_url = self.editor_link(route.src, route.line) if route.local else None
        route.controls = analysis.controls
        route.methods = analysis.methods
        route.csrf = analysis.csrf
        route.category = analysis.category
        return route


def editor_link_maker(template, root):
    """Builds editor links from EDITOR_URL; ``root`` replaces the project root (``--editor-root``)."""
    base = root.replace("\\", "/").rstrip("/")

    def editor_link(src, line):
        if not template:
            return None
        return template.format(path=quote(f"{base}/{src}".lstrip("/"), safe="/:"), line=line or 1)

    return editor_link


def collect_urls(urlconf=None, *, editor_root=None):
    """Map of the URLs of ``urlconf`` (ROOT_URLCONF by default), read from the loaded resolver.

    Nothing is written and the database is not touched. ``editor_root`` replaces the project root in editor
    links, for a project that runs in a container while the editor runs on the host.
    """
    config = get_config()
    urlconf = urlconf or settings.ROOT_URLCONF
    module = import_module(urlconf)
    sources = Sources(project_root())
    login_middleware = uses_login_middleware()
    walker = _Walker(
        sources,
        Inspector(sources, config, login_middleware),
        editor_link_maker(config["EDITOR_URL"], editor_root or sources.root.as_posix()),
    )
    tree = walker.walk(get_resolver(urlconf).url_patterns, "", (), sources.display(module.__file__)[1])
    routes = list(iter_routes(tree))
    names = Counter(route.name for route in routes if route.name)
    for route in routes:
        route.duplicate = bool(route.name) and names[route.name] > 1
    meta = {
        "urlconf": urlconf,
        "django": django.get_version(),
        "version": __version__,
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "login_middleware": login_middleware,
        "drf_default_permissions": drf_default_permissions(),
    }
    return UrlMap(meta=meta, tree=tree)
