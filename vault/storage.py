"""Private Supabase S3 objects are accessed only through authorized Django views."""
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from storages.backends.s3 import S3Storage


class PrivateSupabaseStorage(S3Storage):
    def __init__(self, **kwargs):
        kwargs.setdefault("client_config", Config(
            signature_version="s3v4", connect_timeout=10, read_timeout=30,
            retries={"max_attempts": 2}, s3={"addressing_style": "path"},
        ))
        super().__init__(**kwargs)

    def url(self, name, **kwargs):
        raise NotImplementedError("Use the authenticated vault download route.")

    def _open(self, name, mode="rb"):
        try:
            file = super()._open(name, mode)
            # Materialize the remote object before FileResponse starts streaming.
            file.seek(0)
            return file
        except (BotoCoreError, ClientError):
            raise OSError("Private storage is unavailable.") from None

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except (BotoCoreError, ClientError):
            raise OSError("Private storage is unavailable.") from None

    def delete(self, name):
        try:
            return super().delete(name)
        except (BotoCoreError, ClientError):
            raise OSError("Private storage is unavailable.") from None
