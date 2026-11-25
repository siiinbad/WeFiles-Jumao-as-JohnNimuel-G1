# WeFiles deployment walkthrough

Follow this order: **GitHub -> Supabase -> Render -> verification**.
Supabase provides the database and private file storage. Render runs Django.
Supabase must be ready before Render's first build because the app validates
its database and storage settings during startup.

You perform the GitHub and cloud actions below. The agent has not pushed code,
created services, or deployed the app. The baseline hardening run had 88 passing tests; the startup-command fix now
has a full passing run of 94 tests. Account approval verification is recorded in
[follow-up evidence](PD3_EVIDENCE.md#adminmember-approval-follow-up).
If you already completed a step, check its expected result and continue.

## 1. Push the local work branches to GitHub

Open a terminal in the project folder and run:

```text
git fetch origin
git ls-remote --heads origin refs/heads/develop
```

If the second command prints a commit and `refs/heads/develop`, the remote
branch exists. If it prints nothing, create remote `develop` from remote `main`:

```text
git push origin origin/main:refs/heads/develop
```

Then publish the existing work branches:

```text
git push -u origin fix/pd3-test-runner
git push -u origin hardening/pd3-vault-integrity
git push -u origin fix/pd3-cascade-cleanup
git push -u origin test/pd3-regressions-report
git push -u origin fix/render-storage-cleanup-limit
git push -u origin fix/admin-member-approval
```

**Expected result:** all six branches appear in the same public
[GitHub repository](https://github.com/siiinbad/WeFiles-Jumao-as-Jumao-as-G1).

Local `develop` already includes the changes through local integration merges.
Keep that integrated branch unpushed until the work PRs are merged; publishing
it first can leave those PRs with no changes. Keep `.env` ignored and private.

## 2. Merge the work PRs into develop, then release to main

On GitHub, open **Pull requests -> New pull request**. Select **base: develop**
and the work branch as **compare**. Create and merge one PR at a time in this
order, waiting for CI to pass each time:

| Order | Compare branch | Base branch |
| --- | --- | --- |
| 1 | `fix/pd3-test-runner` | `develop` |
| 2 | `hardening/pd3-vault-integrity` | `develop` |
| 3 | `fix/pd3-cascade-cleanup` | `develop` |
| 4 | `test/pd3-regressions-report` | `develop` |
| 5 | `fix/render-storage-cleanup-limit` | `develop` |
| 6 | `fix/admin-member-approval` | `develop` |

Use **Create a merge commit** so the later work branches recognize the earlier
commits. Keep all merged branches. Then create the release PR with
**base: main**, **compare: develop**, check CI, and merge it.

**Expected result:** GitHub `main` includes the PD3 code, report, and this guide.
The repository stays Public. This meets the minimum three work PRs into
`develop` plus one release PR into `main`; this checkout provides six work PRs.
Local Git merges alone do not count as GitHub PRs.

## 3. Create your Supabase project

1. Sign in at [Supabase](https://supabase.com/dashboard).
2. Click **New project**, choose your organization, and enter a project name.
3. Choose and save the project's **database password**. This is separate from
   your Supabase account login password.
4. Choose a region near your intended Render region and create the project.
5. Wait until the project's database is ready.
6. Because this app accesses PostgreSQL through Django rather than the public
   Data API, open the **Data API integration overview** and switch
   **Enable Data API** off before creating the Django tables.

Use a fresh project dedicated to this Django schema. Existing legacy WeFiles
SQL/data is not interchangeable with these migrations. See
[Supabase's Data API guidance](https://supabase.com/docs/guides/api/securing-your-api).

**Expected result:** a ready Supabase project with its database password saved.
No Django tables are expected yet.

## 4. Copy the Supabase database connection

1. In the Supabase project, click **Connect**.
2. Select the PostgreSQL URI connection string and choose **Session pooler**.
3. Copy the complete URL. Use port **5432** and keep the exact hostname shown.
4. Replace the password placeholder with your URL-encoded database password.
   For example, `@` becomes `%40`, `#` becomes `%23`, and `%` becomes `%25`.
   Encode only the password, not the entire URL.

The URL has this shape; copy the real values from your dashboard:

```text
postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres
```

Save it privately as the value for `DATABASE_URL`. Do not use a localhost URL,
a project API URL, an anon key, or your local test database connection.
[Supabase connection instructions](https://supabase.com/docs/guides/database/connecting-to-postgres).

**Expected result:** you have the hosted PostgreSQL connection URL for Render.

## 5. Create the private upload bucket

In Supabase, open **Storage -> New bucket**:

| Setting | Value |
| --- | --- |
| Bucket name | `wefiles-private` |
| Public bucket | Off |
| File size limit | Support the app's maximum: `52,428,800` bytes (50 MiB) |
| Allowed file types | Leave unrestricted for the current general-purpose vault |

Create the bucket. Its limit cannot exceed your project's global/plan upload
limit; confirm the displayed global and bucket limits allow the file sizes you
intend to demonstrate. Keep the bucket private.
[Bucket creation](https://supabase.com/docs/guides/storage/buckets/creating-buckets),
[upload limits](https://supabase.com/docs/guides/storage/uploads/file-limits).

**Expected result:** `wefiles-private` appears in Storage as a private bucket.

## 6. Copy the Supabase S3 storage settings

Open the project's **Storage S3 settings**. Enable S3 access if prompted and
generate an S3 access-key pair. Save the following privately:

| Supabase value | Render environment-variable name |
| --- | --- |
| S3 endpoint | `SUPABASE_S3_ENDPOINT_URL` |
| Region | `SUPABASE_S3_REGION` |
| Access Key ID | `SUPABASE_S3_ACCESS_KEY_ID` |
| Secret Access Key | `SUPABASE_S3_SECRET_ACCESS_KEY` |
| Your bucket name | `SUPABASE_STORAGE_BUCKET` |

The endpoint usually looks like:

```text
https://PROJECT_REF.storage.supabase.co/storage/v1/s3
```

Copy the actual endpoint and region. S3 keys are server credentials with
privileged storage access; place them only in Render's server environment.
They are different from the database password and Supabase anon/publishable keys.
[Supabase S3 authentication](https://supabase.com/docs/guides/storage/s3/authentication).

**Expected result:** you have the database URL and all five storage values.

## 7. Configure the Render web service

1. Sign in at [Render](https://dashboard.render.com/).
2. Click **New -> Web Service** and connect the existing GitHub repository.
3. Use the following settings. Stay on the creation form until step 8 is done.

| Render setting | Value |
| --- | --- |
| Name | `wefiles` or another available service name |
| Language/runtime | Python 3, native environment |
| Branch | `main`, after step 2's release PR |
| Root directory | Leave blank; `manage.py` is at this repository's root |
| Build command | `bash build.sh` |
| Start command | `bash start.sh` |
| Health check path | `/health/` |
| Auto-deploy | Off initially |
| Instance count | Free runs one automatically; no instance-count input is needed |
| Instance plan | Choose explicitly; Free is suitable for a limited class demo |

Python `3.14.10` is selected by the tracked `.python-version`. If you also set
`PYTHON_VERSION` in Render, keep it equal to that version. Free web services
sleep after 15 idle minutes, so open the site before demonstrating it.
[Render Django setup](https://render.com/docs/deploy-django),
[Python version](https://render.com/docs/python-version),
[Free-service behavior](https://render.com/docs/free).

Use the manual Web Service route for this walkthrough. The repository's
`render.yaml` is an alternative Blueprint; creating a Blueprint immediately
starts its first deployment, and its instance plan must be reviewed separately.

**Expected result:** Render has the correct repository and commands selected,
but you have not started the initial deployment yet.

## 8. Add production environment variables in Render

Generate a new secret on your machine, in the Python environment you used for
local setup:

```text
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

On the Render creation form, add every variable below. Paste values into
Render's environment-variable fields, not into a committed file.

| Key | Value |
| --- | --- |
| `SECRET_KEY` | The generated secret; keep it stable across later deployments |
| `DATABASE_URL` | The complete Supabase Session pooler URL from step 4 |
| `DJANGO_DEBUG` | `False` |
| `TRUST_PROXY` | `True` |
| `PRIVATE_STORAGE_BACKEND` | `supabase` |
| `SUPABASE_S3_ENDPOINT_URL` | The S3 endpoint from step 6 |
| `SUPABASE_S3_REGION` | The Storage region from step 6 |
| `SUPABASE_S3_ACCESS_KEY_ID` | The S3 Access Key ID from step 6 |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | The S3 Secret Access Key from step 6 |
| `SUPABASE_STORAGE_BUCKET` | `wefiles-private` |

The app automatically trusts the Render-provided `*.onrender.com` hostname.
Leave `TEST_DATABASE_URL` unset on the hosted service and use the normal
`config.settings`, not `config.test_settings`. Your existing local `.env`
contains local/test connections, so copy only the production values above.
For a custom domain, add its real hostname to `ALLOWED_HOSTS` and its HTTPS
origin to `CSRF_TRUSTED_ORIGINS`.
[Render environment-variable guide](https://render.com/docs/configure-environment-variables).

**Expected result:** all ten required production variables have real values.

## 9. Deploy and let Django create the Supabase tables

Click **Deploy Web Service** (or the equivalent create/deploy button). Watch
Render's build and startup logs:

1. `build.sh` installs dependencies, checks production configuration and
   collects static assets.
2. `start.sh` runs `python manage.py migrate --noinput` against Supabase,
   retries queued storage deletions, then starts Gunicorn on Render's port.
3. Render checks `/health/` before considering the service healthy.

**You do not need to paste table-creation SQL into Supabase's SQL Editor.** The
tracked files in `accounts/migrations/` and `vault/migrations/` create the schema
in Supabase. If migrating manually from a correctly configured environment,
the equivalent command is `python manage.py migrate`.

After startup, Supabase's Table Editor should show tables such as:

```text
accounts_user
vault_folder
vault_vaultfile
vault_storagedeletionjob
django_session
django_migrations
```

**Expected result:** Render reports the service Live, provides an HTTPS URL,
and the Django tables exist in Supabase. A new database has no app accounts;
registration happens in your deployed Django app, not Supabase Auth.

## 10. Check the live app and finish your report

Use the actual HTTPS URL provided by Render:

1. Open `/health/`. Expect `{"status":"ok"}`. This checks PostgreSQL only.
2. Open `/accounts/register/`. Register two Members and an Admin candidate.
3. Confirm new accounts cannot sign in while Pending. Bootstrap your first
   Admin using the command below, sign in and open **Manage accounts**. Approve
   both Members, reject a disposable registration, and verify rejected sign-in
   is blocked. Check the approved Member dashboard and profile, then sign out/in.
4. Create a folder, upload a small file, download it and compare its contents.
   This verifies S3 as well as the database. Verify a larger allowed file too.
5. Rename/move the file, confirm deletion, and try deleting a nonempty folder.
6. As the second Member, try the first Member's file/folder URLs. Expect 404;
   the Admin dashboard and `/accounts/manage/` should return 403 to a Member.
   As an Admin, deactivate a Member and verify their session/sign-in is blocked.
   Reactivate by selecting Approved; require a new sign-in and verify their files
   remain available. Test role changes on a disposable account with confirmation.
7. Open an invalid URL. Expect the custom 404 page with no Django traceback.
8. Restart/redeploy once. Confirm accounts, records and uploaded bytes persist.
9. Capture the required genuine screenshots and update the PD3 report with the
   hosted URL, actual results and disposable hosted test accounts.

To approve and activate the registered Admin candidate, run this command against
the hosted application database:

```text
python manage.py promote_workspace_admin YOUR_REGISTERED_USERNAME
```

Use Render Shell if available on your plan. Otherwise run the command from your
machine with a temporary terminal environment using the hosted application's
`DATABASE_URL`. The command approves, activates and promotes a workspace Admin; Django staff privileges
remain separate. Keep local/test settings separate and never run the automated
suite against the production database.

The report's existing `pd3admin`, `pd3member`, and `pd3other` accounts belong only
to the temporary local evidence database. They are not created automatically on
Supabase. Create fresh hosted test accounts for the final report.

## If a step fails

| Problem | What to check |
| --- | --- |
| GitHub work PR has no changes | Check its base/compare branches and whether those changes are already merged. Follow the ordered work PRs instead of publishing integrated local `develop` first. |
| Database connection error | Use the exact Session pooler host on port 5432, the correct project database password and its URL-encoded form. Confirm the project is ready. |
| Missing secret/storage setting | Enter all ten variables from step 8. Keep `DJANGO_DEBUG=False`. |
| `process_storage_deletions` rejects `--limit 100` | Publish and merge the `fix/render-storage-cleanup-limit` branch through `develop` into `main`, then manually deploy the latest released commit. Keep `bash start.sh`. |
| Tables are missing | Read Render's startup migration logs. Check that `DATABASE_URL` points to the intended Supabase project. |
| `/health/` passes but uploads fail | Recheck the private bucket, S3 endpoint, region, key pair and upload limits. Health does not test storage. |
| CSS is missing | Check `collectstatic` in the build logs and keep the supplied WhiteNoise configuration. |
| Form submission returns 403 | Use the HTTPS service URL, check custom trusted origins if applicable and reload the form. |
| First request is slow on Free | Allow the service to wake from idle before your demonstration. |
| Files disappear after redeploy | Confirm storage is `supabase`, not Render's temporary local filesystem. |

The deployment is complete only after your live checks pass. Until then,
hosted acceptance, screenshots and remote PR evidence remain pending in the
report. Keep one service instance initially because migrations run at startup;
coordinate migrations separately before scaling to multiple instances.
