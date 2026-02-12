import os

broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')


task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True


task_track_started = True
task_time_limit = 30 * 60  # 30 minutes hard limit
task_soft_time_limit = 25 * 60  # 25 minutes soft limit
task_acks_late = True  # Acknowledge after task completion
worker_prefetch_multiplier = 1  # Fetch one task at a time


task_autoretry_for = (Exception,)  # Auto-retry on any exception
task_retry_kwargs = {'max_retries': 3}
task_default_retry_delay = 60  # Wait 60 seconds before retry
task_retry_backoff = True  # Use exponential backoff
task_retry_backoff_max = 600  # Max 10 minutes between retries
task_retry_jitter = True  # Add randomness to prevent thundering herd

broker_connection_retry = True
broker_connection_retry_on_startup = True
broker_connection_max_retries = 10


result_expires = 3600  # Results expire after 1 hour
result_persistent = True  # Persist results
result_compression = 'gzip'  # Compress results


worker_max_tasks_per_child = 1000  
worker_disable_rate_limits = False
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'


beat_schedule_filename = 'celerybeat-schedule.db'


worker_send_task_events = True
task_send_sent_event = True

# ============================================
# SECURITY (for production)
# ============================================
# Uncomment these in production with proper certificates
# broker_use_ssl = True
# redis_backend_use_ssl = True