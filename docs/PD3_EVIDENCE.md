# PD3 hardening evidence

The existing private vault and the four standard account features are hardened
and verified locally. The SDD account approval follow-up is documented below.
Student identity fields remain blank by request. GitHub access is read-only: no branches were
pushed, no PRs were created or merged, and no repository settings were changed.

## Verification

The complete run on 2026-11-26 used Python 3.14.10, Django 5.2.19, and native
PostgreSQL 18.6 on Fedora. The server and disposable cluster were extracted into
`/tmp`; no container or system service was used. A temporary environment selected
the isolated native connection before executing the normal project command:

```text
python manage.py test
Ran 88 tests ... OK
```

All 88 tests passed, with no skipped tests. See the unedited
[captured output](pd3/test-results.txt). The four standard features have database
journey tests as well as validation/session/role/profile checks. The vault tests
cover valid input, invalid input, anonymous requests, cross-owner IDs, CSRF,
HTTP methods, escaping, malformed UUIDs, error pages, persistence, constraints,
query counts, stale actions, storage failure/retry, cascade cleanup, and rollback.
Django system checks reported no issues; `makemigrations --check --dry-run`
reported no changes; `pip check` reported no broken dependencies.

For a repeatable run on another machine, use the README's native PostgreSQL
setup and the same test command. Django creates a separate `test_` database;
the local development login needs `CREATEDB`. A disposable `TEST_DATABASE_URL`
can be configured in `.env` instead. Remote application databases are not used
implicitly for tests. The ignored `.env` in this checkout now selects that native database through
`TEST_DATABASE_URL`; the application database setting is unchanged. The
temporary verification database is not a permanent installation and its
credentials are not committed.

## Changes and requirement evidence

| Area | Evidence |
| --- | --- |
| Plain test command | `manage.py` selects `config.test_settings`; database suites no longer skip without `TEST_DATABASE_URL`; CI uses the plain command. |
| Login and roles inside views | Each public vault view has `login_required` and `role_required`; inactive or unknown roles are rejected. `vault/tests_requests.py` checks direct view calls as well as HTTP endpoints. |
| Ownership and forged IDs | Role-scoped selectors, owner checks in services, and owner-scoped destination form fields. Tests cover forbidden file and folder POSTs and direct service calls. |
| Validation | Existing forms/models enforce required fields, sizes, names, descriptions, folder uniqueness, cycles, same-owner locations and depth. Invalid metadata is rejected before upload bytes are written. |
| Unexpected actions | Services lock the owner then re-fetch and lock the current record. Stale edits/deletes become validation errors and cannot recreate deleted records. |
| CSRF and POST mutations | All mutation forms contain tokens; authenticated requests without tokens return 403. GET only displays forms/confirmation; PUT/PATCH/DELETE are rejected. |
| Custom errors | Malformed and missing IDs return custom 404s with `DEBUG=False`; unexpected exceptions render custom 500s without their messages. The 500 handler needs no database query. |
| Escaping | A file name resembling an HTML element and a script description are escaped in list/detail output. No user input is passed through a template `safe` filter. |
| Data integrity | PostgreSQL tests check case-insensitive folder constraints, invalid roles, self-parent folders, positive size and protected contents. Owner FKs remain CASCADE; folder references remain PROTECT. |
| Private-byte cleanup | `vault/signals.py` queues deletion in the same transaction for every file row deletion, including account cascades. Cleanup runs after commit and failures retain retry jobs. Rolled-back deletion preserves metadata and bytes. |
| Duplicate refresh | Successful mutations redirect after POST. This prevents refresh-triggered repeats; arbitrary repeated POSTs are not claimed to be idempotent. |
| List performance | `select_related` loads owner/folder relationships; a regression test verifies query counts do not grow when 15 files are added. |

## PD2 outstanding issues

All four issues from the retained PD2 draft are carried into section 1 of the
PD3 report. None is falsely marked fully resolved:

- **ISS-01:** Native database and private-storage failure/retry behavior pass
  locally. Supabase credentials and live hosted storage acceptance remain open.
- **ISS-02:** The existing repository is public and its name was confirmed using
  read-only metadata. Existing merged PD2 PRs [#1](https://github.com/siiinbad/WeFiles-Jumao-as-Jumao-as-G1/pull/1),
  [#2](https://github.com/siiinbad/WeFiles-Jumao-as-Jumao-as-G1/pull/2), and
  [#3](https://github.com/siiinbad/WeFiles-Jumao-as-Jumao-as-G1/pull/3) target
  `main`. They do not satisfy the PD3 work-PR workflow into `develop`. The hosted
  URL remains unverified.
- **ISS-03:** Real local-only demo accounts exist in the isolated evidence
  database. Student identity remains blank as requested. Hosted test accounts
  and genuine screenshots remain unverified.
- **ISS-04:** A fresh database is created through Django migrations. Reusing the
  legacy schema/data directly remains unsupported; no source data migration was
  attempted.

## Local branches and remote work remaining

Work branches were created from local `develop` and retained. Their changes are
integrated into local `develop`; local `main` is unchanged.

| Work branch | Scope |
| --- | --- |
| `fix/pd3-test-runner` | Standard test command, safe test database configuration, CI and README. Includes the previously requested README edits. |
| `hardening/pd3-vault-integrity` | View login/role checks, locking and stale actions; eight service regressions. |
| `fix/pd3-cascade-cleanup` | Account-cascade cleanup, retry and rollback regressions. |
| `test/pd3-regressions-report` | HTTP, constraint, CSRF, escaping, query-count and error-page coverage; report and evidence. |

These are local Git branches/merges, **not GitHub pull requests**. Required work
PRs into remote `develop` and the final `develop` -> `main` PR remain pending
because GitHub writes are outside the user's authorization. Do not delete the
work branches when eventually completing that workflow.

## Report and screenshot limitations

The [report](WeFiles-Lastname-Firstname-Section-PD3.pdf) is filled from the supplied
[template](PD3-Hardening-Report-Template.docx), retaining all nine sections.
Student name, section, submission date and declaration signature are blank. The
filename keeps identity placeholders until the user supplies them. The report
is unsigned and discloses that the local changes are not yet published remotely.

The browser tool reported an unavailable access host and no browser surfaces.
Genuine browser screenshots of validation errors, denied access and the custom
404 page could not be captured. Their slots remain in section 5 with precise
pending notes and corresponding test evidence. The report includes an image
rendered from the real captured test log; it is explicitly **not** presented as
a terminal screenshot. Capture the requested real screenshots before submission.

Custom 404/500 behavior was tested with `DEBUG=False`. The README's local
`DJANGO_DEBUG=True` setting is for development and can show Django debug pages.
Use `DJANGO_DEBUG=False` with the required production storage configuration for
hosted acceptance; no hosted or debug-enabled acceptance is claimed here.

The three report test accounts (`pd3admin`, `pd3member`, `pd3other`) were created
only in the temporary local evidence database, with the dedicated demo password
printed in the report. They are not accounts in the user's normal or hosted
database. To demonstrate elsewhere, register disposable accounts on that local
instance and use the existing `promote_workspace_admin` command for its Admin.


## Render startup command follow-up

During owner-operated Render deployment, startup reported that
`process_storage_deletions --limit 100` was unrecognized. `start.sh` already
passed that option, but the management command had no argument definition.
The local `fix/render-storage-cleanup-limit` branch adds the option, defaults
to 100, forwards it to the existing cleanup service, and rejects nonpositive
or nonnumeric values before processing. The Render start command stays
`bash start.sh`.

Five command tests and one real PostgreSQL batch-limit regression were added.
The complete suite now passes **94 tests, with no skips**; see the captured
[follow-up output](pd3/startup-fix-test-results.txt). The retained 88-test log
and PDF describe the earlier PD3 baseline. This follow-up also needs its own
work PR into remote `develop`, then the release into `main`, before Render can
use the fix. GitHub and the hosted service were not modified by the agent.

## Admin/Member approval follow-up

The SDD review identified missing account approval and workspace account
management (BR03–BR06). The local `fix/admin-member-approval` branch adds:

- Pending registrations that cannot sign in, with server-controlled Member
  roles. Pending, Approved, Rejected and Inactive are constrained model choices.
- An approved Admin's **Manage accounts** page at `/accounts/manage/`, with
  approval/rejection, deactivation/reactivation and Admin/Member assignment.
  Ordinary workspace Admins do not need Django staff privileges.
- Login/backend and view/service checks, POST with CSRF and explicit confirmation,
  transactions and row locks for competing Admin changes, stale-form protection,
  and session revocation on every access change. Members cannot alter access;
  Admins cannot change their own access or operator maintenance accounts.
- Deactivation retains files and folders. File ownership protections remain
  unchanged. Profile saves update only profile fields so they cannot undo an
  access change made while the form was open.
- Migration `accounts.0003_account_approval`, which preserves existing active
  users as Approved and inactive users as Inactive. New accounts default Pending.
  The authentication update requires existing users to sign in again once.
- First-Admin bootstrap via `python manage.py promote_workspace_admin USERNAME`;
  this approves and activates the registered account without granting staff
  privileges. `createsuperuser` creates an approved operator Admin. Maintenance
  account screens are read-only to keep routine access changes on the guarded form.

The complete suite passes **119 tests, with no skips**, using
`python manage.py test` against isolated native PostgreSQL. The 25 added tests
include real HTTP approval and denial paths, confirmation/CSRF checks, role
assignment, old-cookie revocation after reactivation, account preservation,
concurrent mutual Admin deactivation, and a real migration of existing accounts.
See the captured [approval test output](pd3/account-approval-test-results.txt).
Existing account and vault fixtures explicitly represent approved users.

Run `python manage.py migrate` before starting this version. Render's existing
`start.sh` already runs migrations after the user releases this branch through
`develop` into `main` and deploys it. No hosted database migration, GitHub push,
remote PR, or deployment was performed by the agent. The retained PDF describes
the earlier baseline; add this follow-up and genuine hosted approval screenshots
when finalizing the submission. Browser layout verification remains pending
because the browser tool has no available host; template responses and escaping
are covered by the automated tests.
