import multiprocessing
import os

bind = "0.0.0.0:8000"
backlog = 2048

workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

accesslog = "/app/logs/gunicorn_access.log"
errorlog = "/app/logs/gunicorn_error.log"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = "dealership_gunicorn"

daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
umask = 0
tmp_upload_dir = None

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

