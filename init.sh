#! /bin/bash

if [ $ENV_EVALIA == "PROD" ]; then
  
 # pour avoir une page web (flower pour gérer les tasks celery)
  celery -A tasks.celery_app flower --port=5555 &&
  celery -A tasks.celery_app worker --log-level=nfo &&
  python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp &&
    gunicorn -w 5 -b '0.0.0.0:8000' 'app:app'   \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --log-file - \
    --capture-output \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
    --enable-stdio-inheritance &
  wait
else
  celery -A tasks.celery_app flower --port=5555 &&
  celery -A tasks.celery_app worker --log-level=nfo &&
    python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp &&
    python3 app.py
  wait
fi
