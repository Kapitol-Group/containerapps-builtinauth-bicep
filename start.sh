#!/bin/bash
# Start crond in the background
crond
# Start gunicorn as the main process
exec gunicorn -c gunicorn.conf.py app:app
