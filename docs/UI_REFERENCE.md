# WeFiles UI reference

The increment uses the existing ../WeFiles/ project as its visual reference.
The original project is unchanged. Implementation is on feature/wefiles-ui,
which depends on feature/vault-search and the prepared vault/deployment work.
The former feature/reference-ui branch is retained as a checkpoint.

## Reused assets

- static/brand/logo.svg and static/icons.svg: original brand and icon sprite.
- static/css/tokens.css: original light/dark colors and spacing variables.
- static/css/app.css and nojs.css: original responsive shell and component styles.
- static/js/theme.js and app.js: original theme preference, mobile menu, keyboard
  handling and form busy states.
- static/vendor/bootstrap/bootstrap.min.css with its original LICENSE.

The shared template tag helpers are adapted from core/templatetags/ui.py in the
reference project. Increment-specific styles live in static/css/vault.css.

## Adapted screens

- Dark sidebar, top bar, profile shortcut, active navigation and original logo.
- Member/Admin dashboards with scoped file/folder/storage statistics and recent
  files; the admin dashboard also shows recent accounts.
- Folder cards, compact file tables, full breadcrumbs, file details and forms.
- Centered registration/login cards, validation feedback and account settings.
- Mobile navigation, light/dark/system themes and a no-JavaScript navigation path.

All navigation points to implemented increment features. Profile initials use the
existing account fields. Search finds accessible filenames/descriptions and
folders; the workspace search includes nested folders, while folder search stays
within the open folder. All read paths keep the existing ownership/Admin rules.

## Verification

56 Django tests pass on disposable local PostgreSQL, including regression checks
for scoped search and dashboard summaries. Chrome browser acceptance covers
registration validation, login/logout, folder/file CRUD, downloaded contents,
profile changes, search, role isolation, desktop/mobile layout, theme persistence,
Escape-key menu behavior and navigation with JavaScript disabled. Local preview
screenshots are in the ignored .test-artifacts/ folder.

Supabase, hosted Render acceptance and final submission evidence remain pending.
