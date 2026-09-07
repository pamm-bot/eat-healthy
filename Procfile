release: python manage.py migrate && (python manage.py seed_demo || true)
web: gunicorn config.wsgi --log-file -
