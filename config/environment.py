"""Validate connection and private storage configuration without leaking secrets."""
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


def database_config(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError
        if not all((parsed.hostname, parsed.username, parsed.password, parsed.path.strip("/"))):
            raise ValueError
        remote = parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        config = dj_database_url.parse(url, conn_max_age=60, ssl_require=remote)
        config.setdefault("OPTIONS", {})["connect_timeout"] = 10
        if remote:
            config["OPTIONS"]["sslmode"] = "require"
        if parsed.port == 6543:
            config["CONN_MAX_AGE"] = 0
            config["DISABLE_SERVER_SIDE_CURSORS"] = True
        return config
    except (ValueError, KeyError, TypeError):
        raise ImproperlyConfigured(
            "DATABASE_URL must be a valid PostgreSQL URL (including Supabase PostgreSQL)."
        ) from None


def project_ref(url):
    parsed = urlsplit(url)
    if (parsed.hostname or "").endswith(".pooler.supabase.com"):
        return (parsed.username or "").split(".")[-1]
    if (parsed.hostname or "").endswith(".supabase.co"):
        return parsed.hostname.removeprefix("db.").removesuffix(".supabase.co")
    return f"{parsed.hostname}:{parsed.port or 5432}/{parsed.path.strip('/')}"


def private_storage_config(environ, *, debug):
    backend = environ.get("PRIVATE_STORAGE_BACKEND", "local" if debug else "supabase")
    if backend == "local":
        if not debug:
            raise ImproperlyConfigured("Use private Supabase Storage when DEBUG=False.")
        return {"BACKEND": "django.core.files.storage.FileSystemStorage"}
    if backend != "supabase":
        raise ImproperlyConfigured("PRIVATE_STORAGE_BACKEND must be local or supabase.")
    required = ("SUPABASE_S3_ENDPOINT_URL", "SUPABASE_S3_REGION", "SUPABASE_S3_ACCESS_KEY_ID",
                "SUPABASE_S3_SECRET_ACCESS_KEY", "SUPABASE_STORAGE_BUCKET")
    if missing := [key for key in required if not environ.get(key, "").strip()]:
        raise ImproperlyConfigured("Set private storage environment variables: " + ", ".join(missing))
    endpoint = urlsplit(environ["SUPABASE_S3_ENDPOINT_URL"])
    if (endpoint.scheme != "https" or not (endpoint.hostname or "").endswith((".supabase.co", ".supabase.in"))
            or endpoint.path.rstrip("/") != "/storage/v1/s3" or endpoint.query or endpoint.fragment
            or endpoint.username or endpoint.password):
        raise ImproperlyConfigured("Use the HTTPS S3 endpoint from Supabase Storage settings.")
    return {
        "BACKEND": "vault.storage.PrivateSupabaseStorage",
        "OPTIONS": {
            "endpoint_url": environ["SUPABASE_S3_ENDPOINT_URL"],
            "region_name": environ["SUPABASE_S3_REGION"],
            "access_key": environ["SUPABASE_S3_ACCESS_KEY_ID"],
            "secret_key": environ["SUPABASE_S3_SECRET_ACCESS_KEY"],
            "bucket_name": environ["SUPABASE_STORAGE_BUCKET"],
            "addressing_style": "path", "signature_version": "s3v4",
            "default_acl": None, "file_overwrite": True, "custom_domain": None,
            "querystring_auth": True, "max_memory_size": 1024 * 1024,
            "object_parameters": {"CacheControl": "private, no-store"},
        },
    }
