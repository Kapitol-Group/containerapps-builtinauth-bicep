#!/bin/bash
# Create log directory if it doesn't exist
mkdir -p /var/log
touch /var/log/cron.log

# Start cron in the background
cron

# Start gunicorn as the main process
exec gunicorn -c gunicorn.conf.py app:app
