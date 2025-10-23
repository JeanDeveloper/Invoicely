#!/bin/bash

NAME="invoicely"
DJANGO_DIR=$(dirname $(dirname $(cd `dirname $0` && pwd)))
SOCKFILE=/tmp/gunicorn-invoicely.sock
LOG_DIR=${DJANGO_DIR}/logs/gunicorn.log
USER=ubuntu
GROUP=ubuntu
NUM_WORKERS=5
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_WSGI_MODULE=config.wsgi
TIMEOUT=600000

if [ -e "$SOCKFILE" ]; then
    echo "Eliminando socket antiguo..."
    rm -f "$SOCKFILE"
fi

echo $DJANGO_DIR
cd $DJANGO_DIR
echo "Iniciando la aplicación $NAME con el usuario `whoami`"

export PYTHONPATH=$DJANGO_DIR:$PYTHONPATH

exec ${DJANGO_DIR}/venv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --timeout $TIMEOUT \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=$LOG_DIR
