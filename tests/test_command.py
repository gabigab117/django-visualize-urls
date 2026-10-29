"""The visualize_urls management command."""

import json
from io import StringIO

import pytest
from django.core.management import CommandError
from django.core.management import call_command


def run(*args):
    stdout = StringIO()
    call_command("visualize_urls", *args, stdout=stdout)
    return stdout.getvalue()


def test_writes_an_html_page_by_default(tmp_path, monkeypatch):
    """Given no option,
    When the command runs,
    Then it writes url-map.html in the current folder and says how many routes it holds."""
    monkeypatch.chdir(tmp_path)

    output = run()

    assert (tmp_path / "url-map.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    assert output.startswith("Wrote url-map.html (")
    assert " routes, " in output


def test_json_on_the_standard_output():
    """Given --format json --output -,
    When the command runs,
    Then the JSON map is written on the standard output only."""
    data = json.loads(run("--format", "json", "--output", "-"))

    assert data["meta"]["urlconf"] == "tests.demo.urls"


def test_output_to_a_file(tmp_path):
    """Given --output with a path,
    When the command runs,
    Then the map is written there."""
    run("--format", "json", "--output", str(tmp_path / "map.json"))

    assert json.loads((tmp_path / "map.json").read_text(encoding="utf-8"))["tree"]


def test_urlconf_option():
    """Given --urlconf with the dotted path of another URLconf,
    When the command runs,
    Then the map is the one of that URLconf."""
    data = json.loads(run("--format", "json", "--output", "-", "--urlconf", "tests.demo.catalog.urls"))

    assert data["meta"]["urlconf"] == "tests.demo.catalog.urls"
    assert data["tree"][0]["name"] == "list"


def test_editor_root_option():
    """Given --editor-root,
    When the command runs,
    Then the editor links start with that folder."""
    data = json.loads(run("--format", "json", "--output", "-", "--editor-root", "/Users/me/shop"))
    root_route = next(node for node in data["tree"] if node["type"] == "route" and node["local"])

    assert root_route["editor_url"].startswith("vscode://file/Users/me/shop/demo/")


def test_unknown_urlconf_module_gives_a_clear_error():
    """Given --urlconf with a module that does not exist,
    When the command runs,
    Then it fails with an error that names the module."""
    with pytest.raises(CommandError, match=r"Cannot import the URLconf 'shop\.missing': No module named 'shop'"):
        run("--urlconf", "shop.missing")


def test_module_without_urlpatterns_gives_a_clear_error():
    """Given --urlconf with a module that has no urlpatterns,
    When the command runs,
    Then it fails with the error of Django's resolver."""
    with pytest.raises(CommandError, match="does not appear to have any patterns in it"):
        run("--urlconf", "tests.demo.views")
