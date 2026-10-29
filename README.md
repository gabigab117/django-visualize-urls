# django-visualize-urls

Map every URL of a Django project with the access control of each route, as a standalone HTML page.

`show_urls` of django-extensions lists the routes of a project. This map arranges them as a tree of includes and
tells, for each route, what protects it: `login_required`, a permission, a mixin, DRF permission classes, the admin
site, `LoginRequiredMiddleware`... or nothing. The page has filter tiles, a search field and a meter on each
include, and it needs no network access.

## Installation

```bash
pip install django-visualize-urls
```

Add the app to the settings of your development environment:

```python
INSTALLED_APPS = [
    # ...
    "django_visualize_urls",
]
```

## Usage

```bash
python manage.py visualize_urls
```

writes `url-map.html` in the current folder. Open it in a browser.

| Option | Effect |
| --- | --- |
| `--format html\|json` | Standalone page (default), or the same data as JSON for scripts. |
| `--output PATH`, `-o PATH` | File to write (default `url-map.html` or `url-map.json`); `-` writes to the standard output. |
| `--urlconf DOTTED.PATH` | URLconf to map instead of `ROOT_URLCONF`. |
| `--editor-root PATH` | Project root to put in the editor links, when the project runs in a container and the editor on the host. |

For a project that runs in a container, the host shell expands `$PWD` before the command enters the container:

```bash
docker compose exec web python manage.py visualize_urls --editor-root "$PWD"
```

The map reads the URL resolver loaded in memory: it serves no request and sends no query to the database. The
page lists the internals of the project (routes, views, file paths): keep it out of public places.

## What the map recognizes

Each route falls in one of three categories.

- **Protected**: an access control the map recognizes covers every method of the route.
- **Hint in code**: no recognized control, but the code of the view, or of a decorator or mixin of the project,
  holds words such as `is_authenticated` or `PermissionDenied`. A control that covers some handlers only
  (`method_decorator(login_required)` on `post()`) is a hint too. A hint is to be read, not a proof.
- **No hint**: neither. A public page, or a control done elsewhere (a middleware, a template, a function that
  the view calls).

Recognized controls:

- `login_required`, `permission_required` (with its permissions), `staff_member_required`, `user_passes_test`, and
  the decorators of the project built on it, named after their variable: `staff_required = user_passes_test(lambda
  u: u.is_staff)` shows as `staff_required`.
- `method_decorator()` on `dispatch()`, or on a single handler.
- `LoginRequiredMixin`, `PermissionRequiredMixin` (with its permissions), `UserPassesTestMixin`.
- Django REST framework: `permission_classes` other than `AllowAny`, compositions such as
  `IsAuthenticated & ~IsAdminUser`, `@api_view` functions, the methods of routed ViewSet actions.
- The admin site: the views it serves require an active staff account, custom views wrapped with `admin_view()`
  included; its login page is public.
- `LoginRequiredMiddleware`, or a subclass of it: every route except the views marked `login_not_required` (DRF
  marks its views so).

The map also shows the methods a route answers (`require_POST`, `require_http_methods`, the handlers of a
class-based view), the routes exempt from CSRF checks (`csrf_exempt`, and DRF views, which `APIView.as_view()`
exempts), the names shared by several routes, the routes without a name, and the other decorators (`never_cache`,
`cache_page`...).

A decorator is named after the code of the wrapper it leaves in the `__wrapped__` chain: `functools.wraps` copies
the name of the view onto the wrapper, but not its `__code__`. Its arguments, such as the test of
`user_passes_test`, are read from the closure of the wrapper.

## Settings

All keys are optional:

```python
VISUALIZE_URLS = {
    "HINTS": ["check_api_key("],
    "NEUTRAL_DECORATORS": ["require_htmx"],
    "ACCESS_DECORATORS": ["shop.decorators.partner_required"],
    "EDITOR_URL": "vscode://file/{path}:{line}",
}
```

| Key | Default | Meaning |
| --- | --- | --- |
| `HINTS` | `[]` | Strings that reveal a hand-written check in project code, added to the built-in words. For a check done in a function the view calls (a webhook signature), list that function: `"verify_signature("`. |
| `NEUTRAL_DECORATORS` | `[]` | Decorators that do not control access: their code is not searched for hints. For a decorator that answers 403 for another reason, such as a request that HTMX did not send. |
| `ACCESS_DECORATORS` | `[]` | Decorators that control access although nothing in their code says so: their routes count as protected. |
| `EDITOR_URL` | `"vscode://file/{path}:{line}"` | Link that opens a project view in an editor. `{path}` is the absolute path of the file without its leading slash, `{line}` its line. `None` removes the links. |

Decorators are listed by name (`"require_htmx"`) or by dotted path (`"shop.decorators.require_htmx"`). Other
editors: `"cursor://file/{path}:{line}"`, `"zed://file/{path}:{line}"`, `"pycharm://open?file=/{path}&line={line}"`.

## Project and third-party routes

A route is the project's when it is declared in a URLconf module of the project (a `TemplateView` declared in
`urls.py` counts) or served by a view of the project. Project code lives under `settings.BASE_DIR` (or, without
it, the folder that holds the package of `ROOT_URLCONF`) and outside `site-packages`. A list of patterns has no
module (`admin.site.urls`, `include([...])`): its routes are the project's when their view is. The page hides the
third-party routes until you turn on the switch.

## Limits

The map reads code, it does not run it. It does not see checks done in a middleware other than
`LoginRequiredMiddleware`, in a template, in an override of `get_permissions()` or `has_permission()`, or in a
function the view calls; the hints and the settings cover part of it. A view that cannot be read stays on the map,
flagged with the error.

## Requirements

Python 3.11 or later, Django 5.2, 6.0 or 6.1. Django REST framework is optional.

## Development

```bash
uv sync
uv run coverage run -m pytest -m "not browser"
uv run coverage report
uv run ruff format
uv run ruff check
```

The tests run on a demo shop (`tests/demo`) with one route for each way of protecting a view, without database or
network. Its map:

```bash
uv run django-admin visualize_urls --settings tests.settings --pythonpath .
```

The test of the page in a browser needs Playwright and Chromium, a large download:

```bash
uv sync --group browser
uv run playwright install chromium
uv run pytest -m browser
```

## License

MIT
