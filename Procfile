web: python -m alembic upgrade head && gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 60
