from celery_app import celery_app
from database import SessionLocal
from models import Article
from services import posting_service
from datetime import datetime

@celery_app.task
def post_scheduled_articles():
    db = SessionLocal()
    now = datetime.utcnow()
    
    try:
        articles = db.query(Article).filter(
            Article.status == 'completed',
            Article.scheduled_at <= now,
            Article.posting_attempt_count < 3
        ).all()
        
        for article in articles:
            user = article.user
            
            webhook_url = None
            webhook_secret = None
            
            if article.campaign_id and article.campaign:
                webhook_url = article.campaign.webhook_url
                webhook_secret = article.campaign.webhook_secret
            elif user.integrations and len(user.integrations) > 0:
                integration = user.integrations[0]
                webhook_url = integration.webhook_url
                webhook_secret = integration.webhook_secret
            
            if not webhook_url:
                article.status = 'completed'
                db.commit()
                continue
            
            success, error_message = posting_service.post_article_to_webhook(
                article, user, webhook_url, webhook_secret
            )
            
            if success:
                article.status = 'posted'
                article.posted_at = datetime.utcnow()
                
                if article.campaign_id and article.campaign:
                    article.campaign.articles_posted += 1
            else:
                article.posting_attempt_count += 1
                article.last_posting_error = error_message
            
            db.commit()
        
    except Exception as e:
        print(f"Error in post_scheduled_articles: {e}")
    finally:
        db.close()
