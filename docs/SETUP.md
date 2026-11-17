# Setup and deployment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
touch .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set `DEBUG=True` and `ALLOWED_HOSTS=localhost,127.0.0.1` in your local `.env`. All `.env` files are ignored by Git.

Paste that generated value into `.env` as `SECRET_KEY`. Create a Supabase project, open **Connect > Session pooler**, copy its PostgreSQL URL into `DATABASE_URL`, replace the password with its URL-encoded value, then run:

Use a **new Supabase project for this app**. Do not reuse the original WeFiles database: its migration history and user schema differ.

```bash
python manage.py migrate
python manage.py runserver
```

Visit http://127.0.0.1:8000/accounts/register/. Submit missing fields, an invalid email, mismatched passwords, and finally a valid account. Duplicate username/email checks are case-insensitive and backed by database constraints.

## Environment

| Variable | Purpose |
| --- | --- |
| SECRET_KEY | Random secret, at least 50 characters |
| DEBUG | True locally, False on Render |
| ALLOWED_HOSTS | Comma-separated explicit hostnames |
| CSRF_TRUSTED_ORIGINS | Comma-separated trusted HTTPS origins |
| DATABASE_URL | Supabase PostgreSQL Session pooler URL, SSL required |
| TEST_DATABASE_URL | Optional separate disposable Supabase project for destructive tests |
| TRUST_PROXY | True only behind Render's trusted proxy |

There is no SQLite fallback. Session pooler port 5432 avoids the IPv6-only direct-host connectivity issue. If using transaction pooler port 6543, settings automatically disable persistent connections and server-side cursors.

## Tests

```bash
python manage.py test accounts.tests.test_registration accounts.tests.test_sessions accounts.tests.test_roles accounts.tests.test_profiles --settings=config.test_settings
```

Database tests need a **separate, disposable Supabase project**. Set its URL as `TEST_DATABASE_URL`; never point it at production. Tests flush that project's database. `--keepdb` reuses the database rather than requesting database-creation privileges.

```bash
python manage.py test accounts.tests.test_database --settings=config.test_settings --keepdb --parallel 1
```

## Render

Push this folder as its own repository, then create a Render Blueprint using `render.yaml`. Generate a fresh `SECRET_KEY` with the command above and enter it and `DATABASE_URL` in Render. Keep DEBUG=False and TRUST_PROXY=True. Render hostname is added automatically. Build: `bash build.sh`; start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. The build runs checks, collectstatic and migrations. Configure custom domains through ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS.

No uploads are implemented for this account-only submission, so Storage credentials are not required. Source prepared does not mean deployed: a real Supabase connection and a Render service must be configured by the operator.

Production settings enable HTTPS redirect, secure cookies and HSTS. Django's optional subdomain-HSTS and preload checks report warnings; those policies remain off until the operator can confirm control of all affected subdomains and choose preload. The build fails on deployment-check errors, not these optional warnings.

## Acceptance

- [x] Registration, validation, case-insensitive uniqueness, hashed passwords
- [x] Login / logout, CSRF-protected POST logout and protected pages
- [x] Admin / Member dashboards, server-side role checks and role-based redirects
- [x] Own profile view / edit, validated email and restricted editable fields

Use a public repository named `WeFiles-Lastname-Firstname-Section`. Never commit `.env`. Rotate any credential that has ever been committed. Commit dates should record when work was actually committed.

## Roles

New registrations are always Members. Register an account, then assign its Admin role from the operator's terminal:

```bash
python manage.py promote_workspace_admin YOUR_USERNAME
```

Admin dashboard: `/accounts/dashboard/admin/`; Member dashboard: `/accounts/dashboard/member/`. Typing the other role's URL returns 403. Django maintenance privileges (`is_staff`, `is_superuser`) are separate. For maintenance access, use `python manage.py createsuperuser` and `/maintenance/`; set its workspace role explicitly if it also needs the Admin dashboard. Workspace Admin accounts see real account counts and recent registrations; Members see their own account summary. No role fields are accepted at registration.

## Submission walkthrough

1. Register a Member; demonstrate required fields, invalid email, duplicate username/email and mismatched passwords.
2. Sign in with an incorrect password, then the correct one. Confirm redirect to the Member dashboard.
3. Sign out using the button. Open `/accounts/profile/`; confirm redirect to login.
4. Register another account, promote it through the command above, then sign in and show the Admin dashboard's real account counts and recent registrations.
5. As each role, type the other dashboard's URL. Both must return 403.
6. Open My profile; edit first name, last name and email, save, reload, sign out/in and confirm persistence. Duplicate/invalid emails must show errors.
7. A profile uses the current session user. Adding `?user_id=OTHER_ID` cannot open or update that user's profile; `/accounts/profile/OTHER_ID/` does not exist.

Account data includes username, contact email, optional name, password hash, role and session timestamps. It is stored in Supabase and processed by the Render application when deployed. Only essential session/CSRF cookies are used; no analytics is included. Emails are contact information, not verified identities. Before public use, the operator must provide a privacy contact, retention/deletion procedure and published notice that matches their configuration.

