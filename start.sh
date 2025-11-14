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

# Debug: Show what we're setting up (output to both stdout and file)
echo "=== Cron setup debug ==="
echo "=== Cron setup debug ===" >> /var/log/cron.log
echo "Date: $(date)"
echo "Date: $(date)" >> /var/log/cron.log
echo "Cron job file exists: $(test -f /etc/cron.d/mycron && echo 'YES' || echo 'NO')"
echo "Cron job file exists: $(test -f /etc/cron.d/mycron && echo 'YES' || echo 'NO')" >> /var/log/cron.log
if [ -f /etc/cron.d/mycron ]; then
    echo "Cron job file content:"
    cat /etc/cron.d/mycron
    echo "Cron job file content:" >> /var/log/cron.log
    cat /etc/cron.d/mycron >> /var/log/cron.log
fi
echo "Environment variables for cron:"
cat /etc/environment
echo "Environment variables for cron:" >> /var/log/cron.log
cat /etc/environment >> /var/log/cron.log
echo "=== Starting cron ==="
echo "=== Starting cron ===" >> /var/log/cron.log

# Start cron in the background with debug logging
cron -L 15
echo "Cron started with PID: $(pgrep cron)"
echo "Cron started with PID: $(pgrep cron)" >> /var/log/cron.log

# Start gunicorn as the main process
exec gunicorn -c gunicorn.conf.py app:app
