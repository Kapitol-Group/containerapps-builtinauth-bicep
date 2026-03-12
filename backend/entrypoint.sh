#!/bin/sh
set -eu

APP_ROLE="${APP_ROLE:-api}"

if [ "$APP_ROLE" = "worker" ]; then
  exec python worker.py
fi

exec gunicorn -c gunicorn.conf.py app:app

