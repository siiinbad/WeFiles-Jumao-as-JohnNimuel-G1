# WeFiles - Project Development 2 (in progress)

Increment 2 in `wefiles-increment/` builds on this checkout's existing Django
account feature and uses `../WeFiles/` as the reference for folders, uploads,
private downloads, validation and storage cleanup. The original `WeFiles/`
application is preserved. This increment is being prepared; Supabase and Render
are not configured and the submission is not final.

## Core feature: private file vault

A member signs in, opens **My files**, creates nested folders, uploads one file
(up to 50 MiB), browses and downloads it, edits its name/description/location,
and confirms deletion. Empty folders can be renamed, moved and deleted.
Administrators use **All files** to manage records across accounts; uploads and
new folders always belong to the signed-in creator. Success/error messages and
server-side form validation cover every mutation.

Every file and folder has an owner ForeignKey to `accounts.User`. Members can
only access their own records, including direct detail/download/edit/delete
URLs and destination selectors. Administrators retain the original owner's
identity when managing records. Folder parents and file destinations must
belong to that owner. Folder names are unique within the same parent and owner,
case-insensitively; cycles, excessive nesting and deletion of nonempty folders
are rejected. Downloads are authenticated attachments with private cache headers.

All account, session, folder, file metadata and deletion-job records use
PostgreSQL (Supabase PostgreSQL is supported; there is no SQLite fallback).
Uploaded bytes use a private Supabase Storage bucket in production, accessed
through its S3 interface. Local filesystem storage is allowed only in debug
mode. Production startup refuses local upload storage or missing cloud settings.

Registration, login/POST logout, Admin/Member dashboards and own profile editing
remain included. New registrations cannot select privileges. Workspace Admin
roles are separate from Django maintenance staff permissions.

The interface uses the original WeFiles logo, sidebar, design tokens, responsive
file tables, account cards and theme controls. See [UI reference](docs/UI_REFERENCE.md)
for the source assets and adapted screens. Workspace search and dashboard
statistics respect the same owner/Admin access rules.

## Run this prepared checkout (PowerShell)

This checkout already has a virtual environment and local PostgreSQL under
`.venv/` and `.tools/`. Use the commands below to run before Supabase is
configured. These ignored local tools are not included in a fresh Git clone;
for a new checkout, follow the setup section below.

Open PowerShell and run:

```powershell
cd C:\Users\L13X16W25\production\wefiles-increment

# Start PostgreSQL; skip this command if it is already running.
& .\.tools\postgres-bin\package\native\bin\pg_ctl.exe -D .\.tools\pgdata -l .\.tools\postgres.log -o "-h 127.0.0.1 -p 55439" -w start

# Configure this terminal session.
$env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
$env:DJANGO_DEBUG = "True"
$env:PRIVATE_STORAGE_BACKEND = "local"
$env:DATABASE_URL = "postgresql://wefiles_test:local-disposable-only@127.0.0.1:55439/wefiles_acceptance"

# Apply migrations and start Django.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open **http://127.0.0.1:8000/**, create an account, and sign in. Keep the terminal
open while using the app. These environment settings apply only to that terminal
session; repeat them when opening a new terminal. No virtual environment
activation or `.env` copy is needed for this prepared-checkout flow.

Press **Ctrl+C** to stop Django. To stop PostgreSQL afterward:

```powershell
& .\.tools\postgres-bin\package\native\bin\pg_ctl.exe -D .\.tools\pgdata -w stop
```

The database login above is for this local development instance only. Supabase
and Render remain unconfigured.

## Local setup for a fresh checkout

Use the Python version in `.python-version`. In PowerShell, inside this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

1. Put the generated value in `.env` as `SECRET_KEY`.
2. Set `DJANGO_DEBUG=True`, `PRIVATE_STORAGE_BACKEND=local`, and explicit local
   `ALLOWED_HOSTS`. `DJANGO_DEBUG` avoids collisions with the host's `DEBUG` variable.
3. Set `DATABASE_URL` to a new Supabase project's session pooler connection
   string, or a local PostgreSQL database. URL-encode special password characters.
   Do not reuse `WeFiles`'s existing database; the user schema/migrations differ.
4. Run `python manage.py migrate` and `python manage.py runserver`.
5. Register and sign in at `/accounts/register/`. For an administrator, register
   another account then run `python manage.py promote_workspace_admin USERNAME`.

No production credentials or real accounts are bundled. `.env`, private uploads, test tools
and virtual environments are ignored. Do not serve `media/` through public URLs.

## Tests

Database-independent checks need no `.env` or Supabase project:

```powershell
python manage.py test accounts.tests.test_registration accounts.tests.test_sessions accounts.tests.test_roles accounts.tests.test_profiles vault.tests vault.tests_deployment --settings=config.test_settings
python manage.py check --settings=config.test_settings
```

For the complete journey suite, set `TEST_DATABASE_URL` to a separate disposable
PostgreSQL database. Local PostgreSQL tests create/drop a `test_` database, so
its login needs `CREATEDB`. Never use production credentials for tests.

```powershell
$env:TEST_DATABASE_URL = 'postgresql://test_user:TEST_PASSWORD@127.0.0.1:5432/wefiles_test'
python manage.py test --settings=config.test_settings --parallel 1
```

For a disposable Supabase test project, see [SETUP](docs/SETUP.md): its test
runner reuses and flushes that project's tables and requires explicit opt-in.
GitHub Actions is prepared with an isolated PostgreSQL service.

## Render preparation

[render.yaml](render.yaml), [build.sh](build.sh), and [start.sh](start.sh) prepare
static collection, HTTPS/proxy settings, private Supabase Storage, migrations,
Gunicorn and a database health check. Automatic deployment is disabled.
Creating a Render Blueprint still causes its first deployment; do this only
when the remaining setup is ready. No Render service was created here.

See [setup and deployment](docs/SETUP.md),
[requirements status](docs/REQUIREMENTS.md),
[branch/PR workflow](docs/GITHUB_WORKFLOW.md), and [verification](VERIFICATION.md).
The supplied report template is retained in `docs/`; the filled report stays a
**draft**, with final identity, screenshots, test accounts, PR links and hosted
verification pending. Its final required filename is
`WeFiles-Lastname-Firstname-Section-PD2.pdf`.
