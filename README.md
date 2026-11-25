# WeFiles - Project Development 3

PD3 hardens the existing private file vault and standard account features.
It adds regression coverage and safer access, validation, and deletion handling;
it does not add new product features. Local PostgreSQL verification is complete.
GitHub is read-only for this work: local branches/commits are prepared, while
remote PRs, deployment verification, and final submission evidence remain pending.

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

## Local setup (Windows, Linux, or macOS)

Run this checkout with Python and a native PostgreSQL installation. The steps
below use the files already in this repository; no Docker, Podman, Supabase
account, or downloaded project helper scripts are required.

### Windows (Command Prompt)

1. Install **Python 3.14** from [python.org](https://www.python.org/downloads/)
   and **PostgreSQL 17** from the [Windows installer](https://www.postgresql.org/download/windows/).
   Keep PostgreSQL's default port (`5432`) and remember the `postgres` password.

2. Open **SQL Shell (psql)** from the Start menu. Press Enter to accept the
   default server, database, port, and username, then enter the `postgres`
   password. Run this once to create the app's database:

   ```sql
   CREATE ROLE wefiles LOGIN CREATEDB;
   SET password_encryption = 'scram-sha-256';
   \password wefiles
   CREATE DATABASE wefiles OWNER wefiles;
   \q
   ```

   When `\password` asks, choose a password for `wefiles`. Save it for step 4.
   `CREATEDB` lets this local development login create Django's test database;
   do not grant it to a production application login.
   Use a new database for this checkout, separate from older WeFiles projects.

3. Open **Command Prompt** in the project folder (where `manage.py` is), then run:

   ```bat
   py -3.14 -m venv .venv
   .venv\Scripts\activate.bat
   python -m pip install -r requirements.txt
   if not exist .env copy .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   notepad .env
   ```

4. In Notepad, update these values and save. Use the secret printed above and
   the `wefiles` password you chose in step 2:

   ```dotenv
   SECRET_KEY=PASTE_THE_GENERATED_SECRET_HERE
   DJANGO_DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=postgresql://wefiles:YOUR_PASSWORD@127.0.0.1:5432/wefiles
   PRIVATE_STORAGE_BACKEND=local
   ```

   URL-encode special characters in the database password, such as `@` as `%40`.
   Leave the other settings as provided in `.env.example`.

5. Back in the same Command Prompt, start the app:

   ```bat
   python manage.py migrate
   python manage.py runserver
   ```

   Open **http://127.0.0.1:8000/** and register an account. Press **Ctrl+C** to stop.
   To make a registered account an Admin, stop the server and run
   `python manage.py promote_workspace_admin USERNAME`, then start it again.

**Next time**, open Command Prompt in the project folder and run:

```bat
.venv\Scripts\activate.bat
python manage.py runserver
```

If the database connection is refused, open **Services** from the Start menu
and start the PostgreSQL service. Keep your existing `.env` and database when
restarting. After pulling updates, reinstall dependencies if they changed and
run `python manage.py migrate` before starting the app.

### Linux / macOS

#### 1. Install the prerequisites

- **Python 3.14** with pip and venv. The exact version is recorded in
  [`.python-version`](.python-version) (currently `3.14.10`). Install it through
  [Python's downloads](https://www.python.org/downloads/) or your version manager.
  On Linux, install the matching venv package if creating the virtual environment
  reports that `ensurepip` is missing.
- **Native PostgreSQL server and tools**, using the instructions below.
  The macOS example uses PostgreSQL 17; Linux can use a supported distribution
  version (14 or later). This project has no SQLite fallback.
- Open a terminal in the repository folder containing `manage.py`.

##### Ubuntu / Debian

Install the native packages and start the service:

```bash
sudo apt update
sudo apt install postgresql postgresql-client
sudo systemctl enable --now postgresql
sudo -u postgres psql -d postgres
```

Continue to step 2 inside `psql`. These commands assume a systemd-based desktop
or server. See the [PostgreSQL Ubuntu installation guide](https://www.postgresql.org/download/linux/ubuntu/)
for distribution packages and version-specific repositories.

##### Fedora

Install the native packages, initialize the database cluster **once on a new
installation**, and start the service. Skip `postgresql-setup` if a cluster
already exists; do not reinitialize an existing database installation.

```bash
sudo dnf install postgresql postgresql-server
sudo postgresql-setup --initdb --unit postgresql
sudo systemctl enable --now postgresql
sudo -u postgres psql -d postgres
```

Continue to step 2 inside `psql`. These commands use
[Fedora's distribution packages](https://developer.fedoraproject.org/tech/database/postgresql/about.html).
For other Linux distributions, use their native PostgreSQL packages and service
instructions from the [PostgreSQL Linux downloads page](https://www.postgresql.org/download/linux/).

##### macOS (Terminal)

With [Homebrew](https://brew.sh/) installed:

```bash
brew install postgresql@17
brew services start postgresql@17
export PATH="$(brew --prefix postgresql@17)/bin:$PATH"
psql -d postgres
```

Homebrew initializes a new cluster during installation; the initial database
administrator is normally your macOS user, so do not add `-U postgres` here.
Continue to step 2. See the [Homebrew PostgreSQL 17 formula](https://formulae.brew.sh/formula/postgresql@17)
for service details. Repeat the PATH command in new terminals, or add it to your
shell startup file (normally `~/.zshrc`).

#### 2. Create a dedicated local database

At the `psql` prompt opened above, run these commands **once**:

```sql
CREATE ROLE wefiles LOGIN CREATEDB;
SET password_encryption = 'scram-sha-256';
\password wefiles
CREATE DATABASE wefiles OWNER wefiles;
\q
```

`\password` asks you to enter and confirm a new password for `wefiles`. Save it
for the `.env` step. This local development login can create the separate database used by Django
tests. Do not grant `CREATEDB` to a production application login. If the role/database already
exists for this checkout, reuse it rather than creating it again. Use a separate
empty database from any older WeFiles checkout because the user schema and
migration history differ.

Check password authentication from your terminal:

```text
psql -h 127.0.0.1 -p 5432 -U wefiles -d wefiles -W -c "SELECT 1;"
```

Enter the `wefiles` password. A result of `1` confirms that Django's intended
connection works.

**Fedora / authentication troubleshooting:** If this check reports `Ident
authentication failed` or `no pg_hba.conf entry`, open the administrator `psql`
session again with `sudo -u postgres psql -d postgres` and run `SHOW hba_file;`.
Edit the reported file with administrator privileges, placing this rule **before
any existing matching `host` rules**:

```text
host    wefiles    wefiles    127.0.0.1/32    scram-sha-256
```

From the administrator `psql` session, run `SELECT pg_reload_conf();`, exit with
`\q`, and retry the password connection check. Keep the existing local socket
administrator rules. PostgreSQL uses the first matching rule; see the
[authentication configuration reference](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html).

#### 3. Create the Python environment

Run these commands from this repository's root. Copy `.env.example` only on the
first setup; keep an existing `.env` when restarting or pulling updates.

```bash
python3.14 --version
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### 4. Configure `.env`

Open `.env` in a text editor. Replace the Supabase example `DATABASE_URL` and set
these values, using the secret printed in step 3 and your database password:

```dotenv
SECRET_KEY=PASTE_THE_GENERATED_SECRET_HERE
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://wefiles:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/wefiles
PRIVATE_STORAGE_BACKEND=local
PRIVATE_MEDIA_ROOT=media
TRUST_PROXY=False
```

`SECRET_KEY` must contain at least 50 characters; use the generated value, not
the placeholder above. If the database password contains reserved URL characters
such as `@`, `:`, `/`, `#`, or `%`, URL-encode the password portion of the URL.
For example, `@` becomes `%40`. Use your actual PostgreSQL port if it differs
from `5432`.

Django automatically reads `.env` at startup. Existing environment variables in
your terminal take precedence, so remove any old exported database/debug settings
if your edits appear to be ignored. Supabase S3 settings can remain blank for
this local setup. Database records live in native PostgreSQL; uploaded files
live in the ignored `media/` directory.

#### 5. Apply migrations and start the app

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

Open **http://127.0.0.1:8000/**, register at `/accounts/register/`, and sign in.
The database health endpoint at **http://127.0.0.1:8000/health/** should return
`{"status": "ok"}`. Keep the terminal open while using the app; press **Ctrl+C**
to stop Django. This is the local development server.

To give a registered account the workspace Admin role, run the appropriate
command in another terminal (replace `USERNAME` with the account's username):

```bash
# Linux / macOS
.venv/bin/python manage.py promote_workspace_admin USERNAME
```

#### Starting again later

Open a terminal in the repository and ensure the native PostgreSQL service is
running: use `sudo systemctl start postgresql` on the Linux installations
above, or `brew services start postgresql@17` on macOS.

```bash
source .venv/bin/activate
python manage.py runserver
```

After pulling changes, install `requirements.txt` again if dependencies changed
and run `manage.py migrate` before starting the server. Do not recreate `.env`,
the database, or its role each time. Stopping Django leaves PostgreSQL and your
data intact. `.env`, `.venv/`, and `media/` are local generated files and are
ignored by Git; no credentials or accounts are bundled in the repository. Keep
private uploads outside public file serving.

## Tests

With the virtual environment activated and your local PostgreSQL service
running, run the entire suite from the project folder:

```text
python manage.py test
```

This command selects `config.test_settings` automatically. It runs the core
vault tests and the registration, login/logout, role dashboard, and profile
tests; database tests are not silently skipped. Uploads use temporary local
storage, and Django creates and drops a separate `test_<database name>` database.
Your local development database login needs `CREATEDB`:

```sql
-- Run once in an administrator psql session if the local role already exists.
ALTER ROLE wefiles CREATEDB;
```

The local setup above creates that role with `CREATEDB` already. Use this
permission only for local development/test logins, never the production login.

For a separate test login/database, put a disposable PostgreSQL connection in
`.env` as `TEST_DATABASE_URL`, then use the same test command. It must identify a
different database from `DATABASE_URL`. Remote application databases are never
used implicitly for tests. For disposable Supabase test projects, see
[SETUP](docs/SETUP.md); explicit opt-in and `--keepdb --parallel 1` are required
because that mode reuses and flushes the disposable project's tables.

To run just the checks that need no database or `.env`:

```text
python manage.py test accounts.tests.test_registration accounts.tests.test_sessions accounts.tests.test_roles accounts.tests.test_profiles vault.tests vault.tests_deployment
python manage.py check --settings=config.test_settings
```

For verbose test names use `python manage.py test --verbosity 2`. CI uses the
same full-suite command against an isolated PostgreSQL service.

## Render deployment

Follow the [numbered deployment walkthrough](docs/RENDER_DEPLOYMENT.md):
**GitHub -> Supabase -> Render -> live verification**. It includes the exact
Git push commands, PR order, private bucket setup, production variables,
Render build/start commands, automatic table creation and troubleshooting.
Deployment remains the owner's task; no cloud service was created here.

[render.yaml](render.yaml), [build.sh](build.sh), and [start.sh](start.sh) prepare
static collection, HTTPS/proxy settings, private Supabase Storage, migrations,
Gunicorn and a database health check. Automatic deployment is disabled.
Creating a Render Blueprint still causes its first deployment; do this only
when the remaining setup is ready. No Render service was created here.

See [setup and deployment](docs/SETUP.md),
[requirements status](docs/REQUIREMENTS.md),
[branch/PR workflow](docs/GITHUB_WORKFLOW.md), and [verification](VERIFICATION.md).
The [PD3 hardening report](docs/WeFiles-Lastname-Firstname-Section-PD3.pdf)
retains every section of the supplied template. Student identity fields are
blank as requested. It is an unsigned local draft: browser screenshots, hosted
acceptance, and the required GitHub PR merges remain pending. The filename
keeps identity placeholders until those fields are supplied. See
[PD3 evidence and remaining work](docs/PD3_EVIDENCE.md) and the captured
[test results](docs/pd3/test-results.txt).

The historical PD2 report and template are retained for comparison. To regenerate
the PD3 PDF, install `requirements-docs.txt` and LibreOffice, then run
`python scripts/generate_pd3_report.py`. These tools are optional and are not
needed to run the app or its tests.
