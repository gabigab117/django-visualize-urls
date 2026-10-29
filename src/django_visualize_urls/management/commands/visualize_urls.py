from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_visualize_urls.collect import collect_urls
from django_visualize_urls.render import render_html
from django_visualize_urls.render import render_json


class Command(BaseCommand):
    help = "Write the map of the project URLs, with the access control of each route, as HTML or JSON."
    # The map only reads the URL resolver: the system checks would not make it more right.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=["html", "json"], default="html", dest="output_format")
        parser.add_argument(
            "--output", "-o", help="File to write, or - for the standard output. Default: url-map.html or url-map.json."
        )
        parser.add_argument("--urlconf", help="Dotted path of the URLconf to map. Default: settings.ROOT_URLCONF.")
        parser.add_argument(
            "--editor-root",
            help="Project root for editor links, when the project runs in a container and the editor on the host.",
        )

    def handle(self, *args, output_format, output, urlconf, editor_root, **options):
        urlconf = urlconf or settings.ROOT_URLCONF
        try:
            url_map = collect_urls(urlconf, editor_root=editor_root)
        except ImportError as error:
            raise CommandError(f"Cannot import the URLconf {urlconf!r}: {error}") from error
        except ImproperlyConfigured as error:  # a URLconf without urlpatterns, an unknown VISUALIZE_URLS key
            raise CommandError(str(error)) from error
        content = render_html(url_map) if output_format == "html" else render_json(url_map)
        if output == "-":
            self.stdout.write(content)
            return
        path = Path(output or f"url-map.{output_format}")
        path.write_text(content, encoding="utf-8")
        routes = sum(1 for _ in url_map.routes())
        self.stdout.write(f"Wrote {path} ({routes} routes, {len(content.encode()) // 1024} KB).")
