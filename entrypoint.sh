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

# Create or update a bootstrap admin when env vars are provided.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = '${DJANGO_SUPERUSER_EMAIL}'
password = '${DJANGO_SUPERUSER_PASSWORD}'
username = '${DJANGO_SUPERUSER_USERNAME:-admin}'
user, _ = User.objects.get_or_create(email=email, defaults={'username': username})
user.username = username
user.role = 'ADMIN'
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print('Bootstrap admin is ready:', email)
"
fi

python manage.py collectstatic --noinput

exec "$@"
