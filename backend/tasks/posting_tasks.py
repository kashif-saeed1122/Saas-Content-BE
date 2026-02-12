from celery_app import celery_app
from database import DatabaseSession
from models import Article, WebhookIntegration
from services import posting_service
from datetime import datetime
from sqlalchemy.exc import OperationalError
import logging
from sqlalchemy import or_


logger = logging.getLogger(__name__)

@celery_app.task(
    name='tasks.posting_tasks.trigger_webhook_post',
    bind=True,
    max_retries=3
)
def trigger_webhook_post(self, article_id: str):
    try:
        with DatabaseSession() as db:
            article = db.query(Article).filter(Article.id == article_id).first()
            
            if not article or not article.webhook_integration_id:
                return
            
            integration = db.query(WebhookIntegration).filter(
                WebhookIntegration.id == article.webhook_integration_id,
                WebhookIntegration.is_active == True
            ).first()
            
            if not integration:
                return
            
            user = article.user
            success, message = posting_service.post_article_to_webhook(
                article, user, integration.webhook_url, integration.webhook_secret
            )
            
            if success:
                article.status = 'posted'
                article.posted_at = datetime.utcnow()
                integration.last_test_at = datetime.utcnow()
                integration.last_test_status = 'success'
                
                if article.campaign_id and article.campaign:
                    article.campaign.articles_posted += 1
            else:
                article.posting_attempt_count += 1
                article.last_posting_error = message
                integration.last_test_status = 'failure'
                
                if article.posting_attempt_count < 3:
                    raise self.retry(countdown=300)
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Error posting article {article_id}: {e}")
        raise

@celery_app.task(
    name='tasks.posting_tasks.post_scheduled_articles',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def post_scheduled_articles(self):
    try:
        with DatabaseSession() as db:
            now = datetime.utcnow()
            
            articles = db.query(Article).filter(
                Article.status == 'completed',
                Article.webhook_integration_id.isnot(None),
                Article.posted_at.is_(None),
                or_(Article.scheduled_at.is_(None), Article.scheduled_at <= now)
            ).limit(50).all()
            
            if not articles:
                logger.debug("No articles to post")
                return {"posted": 0}
            
            for article in articles:
                trigger_webhook_post.delay(str(article.id))
            
            return {"queued": len(articles)}
            
    except OperationalError as e:
        logger.error(f"Database error: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"error": str(e), "posted": 0}