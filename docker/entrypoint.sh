#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Opt-in and idempotent: used only to load the public presentation DEMO on a
# fresh Railway volume.  Keep it disabled after the first deployment so a
# future restart never modifies demo state unexpectedly.
if [ "${SEED_COMMUNITY_DEMO_ON_START:-0}" = "1" ]; then
    python manage.py seed_community_demo
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --access-logfile - --error-logfile -
