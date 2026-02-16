import multiprocessing

max_requests = 1000
max_requests_jitter = 50

# Log to stdout for container logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

bind = "0.0.0.0:50505"

# Use a SINGLE worker with multiple threads so that in-memory job dicts
# (bulk_upload_jobs, chunked_uploads, sharepoint_import_jobs) are shared
# across all request-handling threads.  Horizontal scaling is handled by
# Container Apps replicas, not by gunicorn workers.
worker_class = "gthread"
workers = 1
threads = (multiprocessing.cpu_count() * 2) + 1
timeout = 300
