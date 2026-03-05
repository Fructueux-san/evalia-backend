#! /bin/bash

# ──────────────────────────────────────────────────────────────
#  Attendre que la base PostgreSQL soit prête
# ──────────────────────────────────────────────────────────────
echo " En attente de la base de données PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0
until python3 -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(
        host=os.environ.get('DATABASE_HOST'),
        port=os.environ.get('DATABASE_PORT'),
        user=os.environ.get('DATABASE_USER'),
        password=os.environ.get('DATABASE_PASSWORD'),
        dbname=os.environ.get('DATABASE_NAME')
    )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo " Impossible de se connecter à la DB après $MAX_RETRIES tentatives."
    exit 1
  fi
  echo "  ↻ Tentative $RETRY_COUNT/$MAX_RETRIES — nouvelle tentative dans 2s..."
  sleep 2
done
echo " Base de données prête !"

# ──────────────────────────────────────────────────────────────
#  Appliquer les migrations
# ──────────────────────────────────────────────────────────────
echo " Application des migrations..."
flask db upgrade
if [ $? -ne 0 ]; then
  echo " Échec de l'application des migrations. Arrêt."
  exit 1
fi
echo " Migrations appliquées !"

# ──────────────────────────────────────────────────────────────
#  Peupler la base de données (seeds)
# ──────────────────────────────────────────────────────────────
echo " Exécution des seeds..."
python3 seeds.py
if [ $? -ne 0 ]; then
  echo " Échec des seeds (non bloquant)"
fi

# ──────────────────────────────────────────────────────────────
#  Lancement des services
# ──────────────────────────────────────────────────────────────
if [ "$ENV_EVALIA" == "PROD" ]; then

  celery -A tasks.celery_app flower --port=5555 &
  celery -A tasks.celery_app worker --loglevel=INFO &
  python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp &&
  gunicorn -w 1 -k gevent -b '0.0.0.0:9001' sse:app --timeout 0 --graceful-timeout 0 &
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
  celery -A tasks.celery_app flower --port=5555 &
  celery -A tasks.celery_app worker --loglevel=INFO &
    python3 -m pytest -v tests/APITesting.py -o cache_dir=/tmp &&
    gunicorn -w 1 -k gevent -b '0.0.0.0:8001' sse:app --timeout 0 --graceful-timeout 0 &
    python3 app.py
  wait
fi
