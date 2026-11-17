# Verification record

Prepared on 2026-11-16. No real credentials or database were available.

- 23 database-independent Django checks passed for registration validation, password hashing, sessions, CSRF, redirect safety, role authorization and profile ownership/field restrictions. Authentication and uniqueness calls are mocked where they need PostgreSQL; this does not verify live login or persistence.
- Django system checks passed. Migration files were generated and model/migration drift checked offline; database migration history could not be validated.
- Production static collection passed. Production deployment checks reported only the two optional HSTS subdomain/preload warnings documented in README.
- Production Django HTTP checks returned 200 for home, registration, login and their hashed stylesheet, with HSTS headers. HTTP redirects to HTTPS and anonymous profile access redirects to login.
- Replayed all four patches in a disposable repository. Each feature snapshot passed its applicable offline checks (6, 11, 17 and 23 tests). The commit helper created exactly four commits using a synthetic identity only in a disposable test repository; the final committed tree matched the app source. The actual submission repository has no commits or invented identity.
- A separate integration test suite covers registration persistence, duplicate email rejection, real login/logout, role enforcement, profile persistence and attempted privilege/ownership changes. It must still run against a disposable Supabase test project, using the README command. Nothing falls back to SQLite.
- Browser access was unavailable. Responsive styles and accessible form markup are included; desktop/mobile and keyboard acceptance must still be checked in a browser.
- No deployment, remote repository creation or push was performed. Git identity is supplied by the user; four sequential feature patches are supplied separately.

Run the README submission walkthrough against real Supabase before demonstrating the app. The operator must configure a public repository and Render environment before deployment.
