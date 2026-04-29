#!/bin/sh

set -e

attempt=0
until python manage.py migrate --noinput; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 10 ]; then
    echo "Database migrations failed after multiple attempts."
    exit 1
  fi
  echo "Database not ready yet. Retrying in 3 seconds..."
  sleep 3
done

python manage.py collectstatic --noinput

exec "$@"
