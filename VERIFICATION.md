# Verification record - Increment 2, in progress

Verified on 2026-11-18. Supabase and Render remain unconfigured.

## Passed in this workspace

- **53 Django tests passed against a temporary local PostgreSQL 17 database**,
  with no skips. All migrations were applied to a fresh test database and the
  test database was destroyed afterward. The isolated loopback PostgreSQL server
  was stopped. App credentials or the reference WeFiles database were not used.
- The suite includes existing registration persistence/uniqueness, real session
  login/logout, role dashboards, profile persistence and attempted privilege
  changes. Vault journeys cover member file/folder CRUD, nested folders, download
  contents, folder moves, owner isolation, admin cross-owner access, validation,
  delete confirmation, storage failure handling and deletion retries.
- Database-independent checks verify CSRF, authentication redirects, private
  caching, storage configuration, safe provider errors, no storage URL generation,
  health-check responses and read-only maintenance behavior.
- Django system checks passed. `makemigrations --check --dry-run` reported no
  model/migration drift; the earlier offline run could not inspect a database's
  history, and the full PostgreSQL run then applied all migrations successfully.
- Production deployment checks passed at ERROR level with placeholder cloud
  settings. Only optional HSTS subdomain/preload warnings W005/W021 remain;
  these domain-wide policies are intentionally not enabled automatically.
- Production WhiteNoise collection copied 129 static files and post-processed
  assets. HTTPS page checks passed for home/registration/login and hashed vault
  CSS; HTTP redirects to HTTPS, HSTS is present, and anonymous vault access
  redirects to login with private/no-store cache headers.
- `bash -n build.sh start.sh` passed. `pip check` found no broken dependencies.
- The supplied DOCX report template was retrieved and retained. Generated draft
  DOCX/PDF keep all six numbered sections, all subsections and eleven tables.
  Automated assertions check required section headings and unfilled placeholders.

## Limits and remaining acceptance

- File bytes in automated journey tests use temporary local storage. S3
  configuration/error behavior is tested with mocks. **No live Supabase
  PostgreSQL connection or private bucket upload/download/delete was verified.**
- PostgreSQL tests use Django's HTTP client and templates, not an interactive
  browser. Desktop/mobile layout, keyboard interaction, screenshots and a
  complete browser demonstration remain pending.
- Render startup/Gunicorn were not executed on a Linux Render host. No Blueprint
  or service was created, no deployment was triggered, and no hosted URL exists.
- GitHub Actions is prepared but has not run remotely. No remote was configured
  for this independent increment history, no push or PR was made, and no merge
  into main/develop was performed. Local feature commits are preparation only.
- The report remains an unsigned draft. Confirm student name/section, populate
  real demo accounts and screenshots, record actual merged PR links, and export
  the required final filename before submission.

See README.md for repeatable tests and docs/SETUP.md for the separate disposable
Supabase test-project safety requirements and manual acceptance steps.
