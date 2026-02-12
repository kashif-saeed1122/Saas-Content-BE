from celery import Celery
from celery.schedules import crontab

celery_app = Celery('neuralgen')

celery_app.config_from_object('celery_config')

celery_app.conf.beat_schedule = {
    'process-campaigns-hourly': {
        'task': 'tasks.campaign_tasks.process_daily_campaigns',
        'schedule': crontab(minute=0),
    },
    'post-scheduled-articles': {
        'task': 'tasks.posting_tasks.post_scheduled_articles',
        'schedule': 60.0,
    },
}

from tasks import campaign_tasks
from tasks import posting_tasks