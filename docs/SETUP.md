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
python manage.py test accounts.tests.test_registration accounts.tests.test_sessions --settings=config.test_settings
```

Database tests need a **separate, disposable Supabase project**. Set its URL as `TEST_DATABASE_URL`; never point it at production. Tests flush that project's database. `--keepdb` reuses the database rather than requesting database-creation privileges.

```bash
python manage.py test accounts.tests.test_database --settings=config.test_settings --keepdb --parallel 1
```

## Render

Push this folder as its own repository, then create a Render Blueprint using `render.yaml`. Generate a fresh `SECRET_KEY` with the command above and enter it and `DATABASE_URL` in Render. Keep DEBUG=False and TRUST_PROXY=True. Render hostname is added automatically. Build: `bash build.sh`; start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. The build runs checks, collectstatic and migrations. Configure custom domains through ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS.

No uploads are implemented for this account-only submission, so Storage credentials are not required. Source prepared does not mean deployed: a real Supabase connection and a Render service must be configured by the operator.

## Acceptance

- [x] Registration, validation, case-insensitive uniqueness, hashed passwords
- [x] Login / logout, CSRF-protected POST logout and protected pages
- [ ] Role dashboards
- [ ] Own profile view / edit

Use a public repository named `WeFiles-Lastname-Firstname-Section`. Never commit `.env`. Rotate any credential that has ever been committed. Commit dates should record when work was actually committed.
