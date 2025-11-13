#!/bin/bash
# Create log directory if it doesn't exist
mkdir -p /var/log
touch /var/log/cron.log

# Export environment variables for cron jobs
# Properly escape values for shell sourcing by:
# 1. Using double quotes around the value
# 2. Escaping backslashes, double quotes, dollar signs, and backticks
{
    printenv | grep -E '^AZURE_' | while IFS='=' read -r name value; do
        # Escape special characters that need escaping inside double quotes
        escaped_value=$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\$/\\$/g; s/`/\\`/g')
        printf 'export %s="%s"\n' "$name" "$escaped_value"
    done
} > /etc/environment

# Start cron in the background
cron

# Start gunicorn as the main process
exec gunicorn -c gunicorn.conf.py app:app
