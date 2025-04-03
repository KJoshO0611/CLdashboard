import multiprocessing

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'cldashboard'

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048

# SSL
keyfile = None
certfile = None

# Worker process settings
worker_tmp_dir = '/dev/shm'
max_requests = 1000
max_requests_jitter = 50

# Graceful timeout
graceful_timeout = 30 