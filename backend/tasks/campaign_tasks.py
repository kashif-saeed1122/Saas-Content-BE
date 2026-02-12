from celery_app import celery_app
from database import DatabaseSession
from models import Campaign, Article, User
from services import campaign_service, credit_service
from lambda_trigger import trigger_worker
from agents.title_agent import generate_titles
from datetime import datetime, date, time
from sqlalchemy.exc import OperationalError
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task(
    name='tasks.campaign_tasks.process_daily_campaigns',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def process_daily_campaigns(self):
    """
    Process all active campaigns for the day.
    Runs daily at midnight UTC (configured in celery_app.py)
    
    Features:
    - Automatic retry on database errors
    - Connection pooling via DatabaseSession
    - Transaction management per campaign
    - Credit validation before article generation
    - Duplicate title prevention
    """
    try:
        with DatabaseSession() as db:
            today = date.today()
            
            # Get all active campaigns
            campaigns = campaign_service.get_active_campaigns(db)
            
            if not campaigns:
                logger.info("📭 No active campaigns to process")
                return {"processed": 0, "articles_created": 0}
            
            total_processed = 0
            total_articles_created = 0
            
            for campaign in campaigns:
                try:
                    # Check if campaign should run today
                    if not campaign_service.should_run_campaign_today(campaign):
                        logger.debug(f"⏭️  Campaign {campaign.id} - Not scheduled for today")
                        continue
                    
                    user = campaign.user
                    
                    # Validate credits
                    if user.credits < campaign.articles_per_day:
                        campaign.status = 'paused'
                        db.commit()
                        logger.warning(
                            f"⚠️  Campaign {campaign.id} paused - "
                            f"Insufficient credits (has: {user.credits}, needs: {campaign.articles_per_day})"
                        )
                        continue
                    
                    # Generate article titles
                    try:
                        titles = asyncio.run(
                            generate_titles(campaign.topic, campaign.articles_per_day)
                        )
                        
                        if not titles:
                            logger.warning(f"⚠️  Campaign {campaign.id} - No titles generated")
                            continue
                        
                    except Exception as title_error:
                        logger.error(f"❌ Error generating titles for campaign {campaign.id}: {title_error}")
                        continue
                    
                    # Filter out duplicate titles
                    existing_topics = db.query(Article.topic).filter(
                        Article.campaign_id == campaign.id
                    ).all()
                    existing_topics = [t[0] for t in existing_topics if t[0]]
                    
                    unique_titles = [
                        t for t in titles if t not in existing_topics
                    ][:campaign.articles_per_day]
                    
                    if not unique_titles:
                        logger.warning(f"⚠️  Campaign {campaign.id} - All titles are duplicates")
                        continue
                    
                    articles_created = []
                    
                    # Create articles
                    for idx, title in enumerate(unique_titles):
                        if user.credits < 1:
                            logger.warning(
                                f"⚠️  Campaign {campaign.id} - "
                                f"Ran out of credits after {len(articles_created)} articles"
                            )
                            break
                        
                        # Determine posting time
                        posting_time = (
                            campaign.posting_times[idx] 
                            if idx < len(campaign.posting_times) 
                            else campaign.posting_times[0]
                        )
                        hour, minute = map(int, posting_time.split(':'))
                        scheduled_at = datetime.combine(today, time(hour, minute))
                        
                        # Create article
                        article = Article(
                            id=uuid.uuid4(),
                            user_id=user.id,
                            campaign_id=campaign.id,
                            webhook_integration_id=campaign.webhook_integration_id,
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
                        
                        # Deduct credit
                        credit_service.add_credits(
                            db, user, -1,
                            type='usage',
                            description=f"Campaign: {campaign.name} - {title[:50]}"
                        )
                        
                        campaign.articles_generated += 1
                        campaign.credits_used += 1
                    
                    # Update campaign
                    campaign.last_run_at = datetime.utcnow()
                    db.commit()
                    
                    # Trigger workers for created articles
                    for article in articles_created:
                        try:
                            asyncio.run(trigger_worker(
                                str(article.id),
                                article.raw_query,
                                article.category,
                                article.target_length,
                                article.source_count
                            ))
                        except Exception as worker_error:
                            logger.error(
                                f"❌ Failed to trigger worker for article {article.id}: {worker_error}"
                            )
                            # Don't fail the entire campaign if one worker trigger fails
                            continue
                    
                    total_processed += 1
                    total_articles_created += len(articles_created)
                    
                    logger.info(
                        f"✅ Campaign {campaign.id} ({campaign.name}) - "
                        f"Created {len(articles_created)} articles"
                    )
                    
                except Exception as campaign_error:
                    logger.error(
                        f"❌ Error processing campaign {campaign.id}: {campaign_error}",
                        exc_info=True
                    )
                    db.rollback()
                    # Continue with next campaign
                    continue
            
            summary = {
                "processed": total_processed,
                "articles_created": total_articles_created,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📊 Daily campaign summary: {summary}")
            return summary
            
    except OperationalError as e:
        logger.error(f"🔌 Database connection error in process_daily_campaigns: {e}")
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=300 * (2 ** self.request.retries))
        
    except Exception as e:
        logger.error(
            f"❌ Unexpected error in process_daily_campaigns: {e}",
            exc_info=True
        )
        return {"error": str(e), "processed": 0, "articles_created": 0}