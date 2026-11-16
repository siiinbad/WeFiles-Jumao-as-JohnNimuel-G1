"""Validate environment values without including credentials in errors."""
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


def database_config(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError
        host = parsed.hostname or ""
        if not host.endswith((".pooler.supabase.com", ".supabase.co")):
            raise ValueError
        if not all((parsed.username, parsed.password, parsed.path.strip("/"))):
            raise ValueError
        config = dj_database_url.parse(url, conn_max_age=60, ssl_require=True)
        config["OPTIONS"].update(sslmode="require", connect_timeout=10)
        if parsed.port == 6543:
            config["CONN_MAX_AGE"] = 0
            config["DISABLE_SERVER_SIDE_CURSORS"] = True
        return config
    except (ValueError, KeyError, TypeError) as exc:
        raise ImproperlyConfigured(
            "DATABASE_URL must be a valid Supabase PostgreSQL pooler URL."
        ) from None


def project_ref(url):
    parsed = urlsplit(url)
    if (parsed.hostname or "").endswith(".pooler.supabase.com"):
        return (parsed.username or "").split(".")[-1]
    return (parsed.hostname or "").removeprefix("db.").removesuffix(".supabase.co")
