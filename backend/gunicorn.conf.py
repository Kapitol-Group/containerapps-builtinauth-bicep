import multiprocessing

max_requests = 1000
max_requests_jitter = 50

# Log to stdout for container logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

bind = "0.0.0.0:50505"

workers = (multiprocessing.cpu_count() * 2) + 1
threads = workers
timeout = 120
