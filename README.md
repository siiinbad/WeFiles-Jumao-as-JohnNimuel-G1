# WeFiles

WeFiles is a Django web application designed for a shared file workspace and crew collaboration. Its current version provides the account features that support that workspace.

## Account features

- **Account registration:** Create an account with a unique username and email address. Required fields, email format and password confirmation are validated, and passwords are hashed using Django authentication.
- **Login and logout:** Sign in with a username and password, receive clear feedback for invalid credentials, and sign out to end the session. Protected pages require an active login.
- **Role-based dashboards:** Admins see account totals and recent registrations. Members see their own account summary. Each role is restricted to its own dashboard.

## User roles

| Role | Dashboard and access |
| --- | --- |
| Admin | Account statistics, recent registrations |
| Member | Personal account summary |

New registrations receive the Member role. Workspace roles are managed by the system operator. Django maintenance permissions are assigned separately.

## Technology

WeFiles uses Django for the backend and frontend, with server-rendered Django templates and Supabase PostgreSQL for persistent data. The project includes Render deployment configuration with Gunicorn and WhiteNoise.

File sharing and crew chat are planned extensions; the current version implements registration, sign-in and role-based dashboards.

[Setup and deployment](docs/SETUP.md)
