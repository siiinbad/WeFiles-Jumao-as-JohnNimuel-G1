#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# A single Render instance runs additive migrations before accepting requests.
# Move migrations to a pre-deploy job before scaling beyond one instance.
python manage.py migrate --noinput
python manage.py process_storage_deletions --limit 100
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120 --access-logfile - --access-logformat '%(m)s %(s)s %(L)s'
