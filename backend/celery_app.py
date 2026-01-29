from celery import Celery
from celery.schedules import crontab

celery_app = Celery('neuralgen')

celery_app.config_from_object('celery_config')

celery_app.conf.beat_schedule = {
    'process-campaigns-daily': {
        'task': 'tasks.campaign_tasks.process_daily_campaigns',
        'schedule': crontab(hour=0, minute=0),
    },
    'post-scheduled-articles': {
        'task': 'tasks.posting_tasks.post_scheduled_articles',
        'schedule': 60.0,
    },
}

celery_app.autodiscover_tasks(['tasks'], force=True)