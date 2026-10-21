#!/bin/sh
set -eu

# A client installation should not ship a shared predictable secret.  Docker
# persists a locally generated key in its data volume; managed deployments can
# (and should) provide DJANGO_SECRET_KEY as an environment secret instead.
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    secret_file="${DJANGO_SECRET_FILE:-/data/.django_secret_key}"
    if [ -f "$secret_file" ]; then
        DJANGO_SECRET_KEY="$(cat "$secret_file")"
    else
        umask 077
        DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
        printf '%s' "$DJANGO_SECRET_KEY" > "$secret_file"
    fi
    export DJANGO_SECRET_KEY
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Opt-in and idempotent: used only to load the public presentation DEMO on a
# fresh Railway volume.  Keep it disabled after the first deployment so a
# future restart never modifies demo state unexpectedly.
if [ "${SEED_COMMUNITY_DEMO_ON_START:-0}" = "1" ]; then
    python manage.py seed_community_demo
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --access-logfile - --error-logfile -
