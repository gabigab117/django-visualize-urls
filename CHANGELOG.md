# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `visualize_urls` management command: writes the URL map of a project as a standalone HTML page or as JSON
  (`--format`, `--output`, `--urlconf`, `--editor-root`).
- Tree of includes and routes: full URLs, combined namespaces, `re_path` shown like paths, duplicate names,
  unnamed routes, project and third-party routes.
- Access controls: auth decorators and the project decorators built on `user_passes_test`, `method_decorator`,
  access mixins, Django REST framework permissions, the admin site, `LoginRequiredMiddleware`, and hints in
  project code.
- `VISUALIZE_URLS` setting: `HINTS`, `NEUTRAL_DECORATORS`, `ACCESS_DECORATORS`, `EDITOR_URL`.
