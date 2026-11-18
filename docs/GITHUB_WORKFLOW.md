# GitHub workflow - preparation only

The existing account commits are retained. The increment checkout originally had
only a local `master` branch and no remote. The reference `../WeFiles/` checkout
uses `https://github.com/siiinbad/WeFiles` and has a separate history. No push,
remote creation, visibility change, release merge or fabricated PR is performed.

Local preparation creates `main` at the existing account baseline and `develop`
from `main`, with feature branches for the private vault and Render preparation.
The Render branch depends on the vault branch and is advanced to that feature's
commit before deployment changes are committed. `main` and `develop` stay at the
baseline while this increment remains in progress. The legacy `master` reference
is retained. These local branches do not satisfy the merged-PR requirement yet.

## Required remote workflow

1. Reconcile this work with the **same existing repository**; retain its history.
   If the instructor requires a rename, use the actual name/section:
   `WeFiles-Lastname-Firstname-Section`. Verify public visibility. Do not force-push
   this independent local history over the reference repository.
2. Establish/protect `main` and `develop` on that repository. Require PRs for main;
   no direct commits. Ensure auto-deletion of merged feature branches is disabled.
3. Push `feature/private-file-vault`; open a PR into `develop`, run the PostgreSQL
   CI checks, review and merge while retaining the feature branch.
4. Push `feature/render-deployment`; after the vault PR is merged, open/rebase its
   PR into `develop` so the remaining diff covers Render/docs. Run checks, review
   and merge; retain this branch too.
5. When the increment is accepted, open **develop - main**, run checks and merge.
   This is deliberately pending while the user has asked to keep work unfinished.
6. Record the two merged feature PR URLs and the merged release PR URL in every
   Branches and Pull Requests row of the supplied report. Use actual links only.

## Suggested PR descriptions

`Add the private file vault`: Members can organize, upload, download, edit and
confirm deletion of their own files/folders. Admins can manage records across
owners. Validated destinations, folder rules, authenticated private downloads
and retryable storage cleanup enforce the flow. Include exact test results and
state that live Supabase acceptance remains pending.

`Prepare Supabase Storage and Render deployment`: Configure private durable
upload storage, build/start commands, database health checks and environment
setup. Keep deployment manual and preserve a draft of every report section.
Include exact checks and the remaining cloud setup.

## Submission evidence still needed

- Public URL with the required repository name and preserved history.
- Two merged feature PRs into develop, one merged develop-to-main PR.
- Supabase-backed browser acceptance with one real test account per role.
- Labeled flow/error screenshots and final student/section details.
- Final `docs/WeFiles-Lastname-Firstname-Section-PD2.pdf` and its commit.
