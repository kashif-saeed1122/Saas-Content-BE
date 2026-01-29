from celery_app import celery_app
from database import SessionLocal
from models import Campaign, Article, User
from services import campaign_service, credit_service
from lambda_trigger import trigger_worker
from agents.title_agent import generate_titles
from datetime import datetime, date, time
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def process_daily_campaigns():
    db = SessionLocal()
    today = date.today()
    
    try:
        campaigns = campaign_service.get_active_campaigns(db)
        
        for campaign in campaigns:
            if not campaign_service.should_run_campaign_today(campaign):
                continue
            
            user = campaign.user
            
            if user.credits < campaign.articles_per_day:
                campaign.status = 'paused'
                db.commit()
                logger.warning(f"Campaign {campaign.id} paused - insufficient credits")
                continue
            
            try:
                titles = asyncio.run(generate_titles(campaign.topic, campaign.articles_per_day))
                
                existing_topics = db.query(Article.topic).filter(
                    Article.campaign_id == campaign.id
                ).all()
                existing_topics = [t[0] for t in existing_topics if t[0]]
                
                unique_titles = [t for t in titles if t not in existing_topics][:campaign.articles_per_day]
                
                articles_created = []
                
                for idx, title in enumerate(unique_titles):
                    if user.credits < 1:
                        break
                    
                    posting_time = campaign.posting_times[idx] if idx < len(campaign.posting_times) else campaign.posting_times[0]
                    hour, minute = map(int, posting_time.split(':'))
                    scheduled_at = datetime.combine(today, time(hour, minute))
                    
                    article = Article(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        campaign_id=campaign.id,
                        raw_query=title,
                        topic=title,
                        category=campaign.category,
                        target_length=campaign.target_length,
                        source_count=campaign.source_count,
                        scheduled_at=scheduled_at,
                        is_recurring=True,
                        status='queued'
                    )
                    db.add(article)
                    articles_created.append(article)
                    
                    credit_service.add_credits(
                        db, user, -1,
                        type='usage',
                        description=f"Campaign: {campaign.name} - {title[:50]}"
                    )
                    
                    campaign.articles_generated += 1
                    campaign.credits_used += 1
                
                campaign.last_run_at = datetime.utcnow()
                db.commit()
                
                for article in articles_created:
                    asyncio.run(trigger_worker(
                        str(article.id),
                        article.raw_query,
                        article.category,
                        article.target_length,
                        article.source_count
                    ))
                
                logger.info(f"Campaign {campaign.id} generated {len(articles_created)} articles")
                
            except Exception as e:
                logger.error(f"Error generating topics for campaign {campaign.id}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error in process_daily_campaigns: {e}")
    finally:
        db.close()