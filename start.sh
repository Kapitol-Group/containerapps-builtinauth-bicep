#!/bin/bash
set -euo pipefail

# Start script for Container Apps: supervise cron and gunicorn, forward signals,
# and keep an ordered shutdown sequence so the managed environment can stop the
# container cleanly.

# Create log directory and cron log file
mkdir -p /var/log
touch /var/log/cron.log
chmod 0666 /var/log/cron.log || true

# Export selected environment variables for cron jobs into /etc/environment so
# the cron job can source them. We only export AZURE_* variables to avoid
# leaking secrets here. Values are safely quoted.
{
    printenv | grep -E '^AZURE_' | while IFS='=' read -r name value; do
        # Escape backslashes and double quotes for safe double-quoted export
        escaped_value=$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\$/\\$/g; s/`/\\`/g')
        printf 'export %s="%s"\n' "$name" "$escaped_value"
    done
} > /etc/environment

echo "=== Cron start wrapper ==="
echo "Date: $(date)" >> /var/log/cron.log
echo "Cron job file exists: $(test -f /etc/cron.d/mycron && echo 'YES' || echo 'NO')" >> /var/log/cron.log
if [ -f /etc/cron.d/mycron ]; then
    echo "Contents of /etc/cron.d/mycron:" >> /var/log/cron.log
    sed -n '1,200p' /etc/cron.d/mycron >> /var/log/cron.log || true
fi

# Start cron in foreground so we can manage it as a child process. Stream
# cron output to both the cron log file and the container stdout (via tee)
# so the Container Apps platform (which captures container stdout/stderr) will
# include cron logs in the app logs.
cron -f 2>&1 | tee -a /var/log/cron.log &
CRON_PID=$!
echo "cron pid=${CRON_PID}" >> /var/log/cron.log

# Start gunicorn as the web process
gunicorn -c gunicorn.conf.py app:app &
GUNICORN_PID=$!
echo "gunicorn pid=${GUNICORN_PID}" >> /var/log/cron.log

# Define cleanup function to forward termination signals to child processes
finish() {
    echo "Received termination signal, shutting down..." >> /var/log/cron.log
    for pid in "${GUNICORN_PID}" "${CRON_PID}"; do
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            echo "Killing pid ${pid}" >> /var/log/cron.log
            kill -TERM "${pid}" || true
        fi
    done
    # wait for children to exit
    wait || true
    echo "Shutdown complete" >> /var/log/cron.log
}

trap finish SIGTERM SIGINT

# Wait for the gunicorn process; if it exits, return its status (and stop cron)
wait ${GUNICORN_PID}
EXIT_STATUS=$?

# If gunicorn exited, bring down cron as well
finish || true

exit ${EXIT_STATUS}
