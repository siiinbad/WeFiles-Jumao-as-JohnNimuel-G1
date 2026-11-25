# Deploy WeFiles to Render

This guide is for the owner to perform the deployment. The local PD3 work has
88 passing tests; no Render service, Supabase project, remote branch, or pull
request was created by the agent. GitHub remains read-only for this task.

Use **Render for the Django web service** and **Supabase for PostgreSQL and a
private file-storage bucket**. This matches the current application. There is
no container setup and no frontend build step.

## 1. Publish the tested code through your required PR workflow

The new hardening changes currently exist locally, not on remote `main`.
Deploying the current GitHub `main` immediately would deploy the older PD2 code.

When you are ready to make GitHub changes yourself:

1. Use the same public repository. If remote `develop` does not exist, create it
   from the current stable remote `main`.
2. Publish these retained work branches and merge their PRs into remote
   `develop`, in this order:

   | Work branch | Contents |
   | --- | --- |
   | `fix/pd3-test-runner` | Plain test command, test isolation, README and CI. |
   | `hardening/pd3-vault-integrity` | Login/role checks, stale records and locks. |
   | `fix/pd3-cascade-cleanup` | Private-byte cleanup on account deletion and rollback. |
   | `test/pd3-regressions-report` | HTTP/constraint regressions, report and this guide. |

3. Review CI results, then merge a `develop` -> `main` PR. Keep the work branches.

Local `develop` already includes local integration merges. **Do not publish
that integrated branch as remote `develop` before the work PRs**: doing so would
put their changes in the target already and can leave the PRs with no changes.
Publish the work branches first against the remote integration branch above.
Do not commit `.env`, `.venv/`, local databases, or private uploads.

## 2. Prepare PostgreSQL and private storage in Supabase

Create a new Supabase project for this Django schema, or use a compatible
project dedicated to this checkout. Keep it separate from the older WeFiles
schema and from disposable test databases. Django's migrations create the
application tables; do not apply the legacy React/Supabase SQL.

From the project's **Connect** dialog, copy the **Session pooler** PostgreSQL
connection string on port `5432`. Replace its password placeholder with the
URL-encoded database password. This becomes `DATABASE_URL` in Render. It must
be a hosted database address, not `localhost` or the laptop's test connection.
See [Supabase's connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres).

Django owns registration and sessions; this app does not use Supabase Auth.
Disable the Supabase Data API if unused, or keep the Django tables out of its
exposed schemas with appropriate grants, as described in [SETUP](SETUP.md).

In **Storage**:

1. Create a **private** bucket named `wefiles-private`.
2. Set its upload size limit to at least `52,428,800` bytes (50 MiB), matching
   the app's maximum. Keep public access disabled.
3. In the Storage S3 settings, generate an **S3 access key ID and secret**.
   Copy the displayed S3 endpoint and region too. Use these S3 credentials,
   rather than an anon/publishable key or database password.

These S3 credentials belong only in the Django server's environment. They can
bypass bucket RLS and must not be placed in browser code. The current backend
checks ownership before streaming a private attachment.
[Supabase S3 authentication](https://supabase.com/docs/guides/storage/s3/authentication).

## 3. Create a native Python web service in Render

Use **New -> Web Service**, connect the same GitHub repository, and select the
released `main` branch. The manual dashboard route lets you review the instance
plan and all secrets before the first deployment.

| Render field | Value |
| --- | --- |
| Language/runtime | Python 3, native environment |
| Branch | `main`, after the PD3 release PR is merged |
| Root directory | Leave blank when `manage.py` is at the repository root |
| Build command | `bash build.sh` |
| Start command | `bash start.sh` |
| Health check path | `/health/` |
| Instances | Start with one |
| Auto-deploy | Off initially; deploy manually after review |
| Instance plan | Choose explicitly; Free can be used for a limited demo |

The tracked `.python-version` selects Python `3.14.10`. If you set
`PYTHON_VERSION` in Render, use the same full version because that variable
has precedence. See [Render's Python version settings](https://render.com/docs/python-version).

The repository also contains a `render.yaml` Blueprint with the same commands.
You can use it instead, but review its plan before applying: the file does not
select Free explicitly. **Creating a Blueprint starts an initial deployment**,
even though `autoDeployTrigger: off` disables later automatic code deploys.
If you want fully manual Blueprint updates, disable its Auto Sync separately.
See [Render Blueprints](https://render.com/docs/infrastructure-as-code) and the
[Blueprint field reference](https://render.com/docs/blueprint-spec).

## 4. Enter the production environment variables

Add these in Render before creating/deploying the service:

| Variable | Production value |
| --- | --- |
| `SECRET_KEY` | A newly generated random secret of at least 50 characters; keep it stable across deploys |
| `DATABASE_URL` | The hosted PostgreSQL session-pooler URL from step 2 |
| `DJANGO_DEBUG` | `False` |
| `TRUST_PROXY` | `True` |
| `PRIVATE_STORAGE_BACKEND` | `supabase` |
| `SUPABASE_S3_ENDPOINT_URL` | The copied HTTPS S3 endpoint, usually `https://PROJECT_REF.storage.supabase.co/storage/v1/s3` |
| `SUPABASE_S3_REGION` | The region copied from Supabase Storage |
| `SUPABASE_S3_ACCESS_KEY_ID` | The generated S3 access key ID |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | The generated S3 secret |
| `SUPABASE_STORAGE_BUCKET` | `wefiles-private` |

Generate a production secret on your machine, using your virtual environment:

```text
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Render's `*.onrender.com` hostname is added automatically to `ALLOWED_HOSTS`
and `CSRF_TRUSTED_ORIGINS` by this app. For a custom domain, also set explicit
`ALLOWED_HOSTS=files.example.com` and
`CSRF_TRUSTED_ORIGINS=https://files.example.com`, using your real hostname.

Copy only these production settings into Render. The local `.env` contains
local/test database addresses, so do not import it wholesale. Leave
`TEST_DATABASE_URL` unset on the hosted service, and do not select
`config.test_settings` or the temporary local-preview settings there.
[Render environment-variable guide](https://render.com/docs/configure-environment-variables).

## 5. Start the deployment and inspect the logs

After checking the plan and variables, create the service or manually deploy
the latest released commit. Render will run:

1. `build.sh`: install `requirements.txt`, run production configuration checks,
   and collect static assets.
2. `start.sh`: apply Django migrations, retry queued private-object deletions,
   and start Gunicorn on Render's provided port.
3. `/health/`: query PostgreSQL to confirm the database is reachable.

Keep one service instance initially: the current startup script applies
migrations. Move schema changes to a coordinated deployment step before scaling
to multiple instances. A failed build/start log should be fixed before treating
the service as ready.

No persistent Render disk is needed for this configuration: PostgreSQL holds
records and Supabase holds uploaded bytes. Render's local filesystem is
**ephemeral**, so do not switch hosted uploads to `local`. The app rejects
local storage when `DJANGO_DEBUG=False`.
[Render filesystem and free-service behavior](https://render.com/docs/free).

## 6. Verify the deployed app

Use the actual HTTPS Render URL and disposable demo accounts:

- Open `/health/`: expect `{"status":"ok"}`. This checks the database, not S3.
- Check the home page and CSS, register two Members and an Admin candidate,
  sign in/out, and edit each user's own profile.
- Promote the Admin candidate with the existing command:

  ```text
  python manage.py promote_workspace_admin YOUR_REGISTERED_USERNAME
  ```

  Run it in Render Shell if your plan provides one. Otherwise, run it on your
  machine with a temporary terminal environment pointing `DATABASE_URL` to the
  same hosted application database. Keep local/test settings separate. Do not
  run the automated suite against the production database.

- As Member A: create nested folders, upload a small file, download and compare
  its bytes, rename/move it, and confirm deletion. Also verify a larger file
  within the 50 MiB limit; do not claim that limit is verified from a tiny file.
- Try blank names, an empty upload, duplicate folders, invalid destinations,
  deleting a nonempty folder, and deletion without confirmation. Expect clear
  errors and unchanged records.
- As Member B: try Member A's file/folder URLs and POST actions; expect denial
  without seeing or changing A's content. A Member's Admin dashboard URL should
  return 403.
- Visit an invalid URL: expect the custom 404 page with no debug traceback.
  The custom 500 handler has local regression coverage; do not deliberately
  break the live service to collect a screenshot.
- Restart/redeploy once, then confirm accounts, metadata, and uploaded bytes
  still exist. After deleting a file, check private-byte cleanup or its retry
  job. If needed, run `python manage.py process_storage_deletions --limit 100`.
- Capture the report's real validation-error, denied-access, custom-404 and
  console test-output screenshots. Update the report's hosted URL, remaining
  issue statuses and deployed demo accounts only after these checks pass.

The report's current three accounts are local evidence accounts only. They
are not automatically created in the hosted database; create dedicated hosted
accounts and use test passwords for the submitted account table.

## 7. Common deployment problems

| Symptom | Check |
| --- | --- |
| `Set SECRET_KEY` | Set a generated secret of at least 50 characters. |
| Invalid `DATABASE_URL` or connection refused | Use the hosted session-pooler URL, URL-encode the password, confirm the database is active and accessible. |
| Missing private-storage settings | Enter all five S3 settings and keep `PRIVATE_STORAGE_BACKEND=supabase`. |
| `AccessDenied` / storage unavailable | Check bucket name, endpoint, region, generated S3 keys and bucket limits. `/health/` alone does not establish storage access. |
| 400 / disallowed host | Check the actual service hostname or custom `ALLOWED_HOSTS`; do not use `*`. |
| 403 on a normal form | Use the HTTPS hostname, check the custom trusted origin, and reload the form for a fresh CSRF token. |
| Static CSS missing | Check build logs for `collectstatic` and keep the provided WhiteNoise configuration. |
| First request is slow on Free | Free web services spin down after 15 minutes idle and take time to wake. |
| Deployed app lacks PD3 changes | Check that the selected branch/commit includes the local hardening work after your release PR. |

Review current [Render plan details](https://render.com/docs/free) before your
class demonstration. A Free service can sleep; choose a plan deliberately for
the availability you need. This guide makes no claim that cloud deployment or
hosted acceptance has already passed.
