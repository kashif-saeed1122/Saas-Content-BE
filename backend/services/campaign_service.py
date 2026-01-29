from sqlalchemy.orm import Session
from models import Campaign, User, Article
from datetime import datetime, date, time
import uuid
import logging
from agents.title_agent import generate_titles
from services import credit_service

logger = logging.getLogger(__name__)

def create_campaign(db: Session, user: User, campaign_data: dict) -> Campaign:
    campaign = Campaign(
        user_id=user.id,
        **campaign_data
    )
    
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    return campaign

async def generate_first_batch(db: Session, campaign: Campaign, user: User, background_tasks, trigger_func):
    today = date.today()
    articles_created = []
    
    titles = await generate_titles(campaign.topic, campaign.articles_per_day)
    
    existing_topics = db.query(Article.topic).filter(
        Article.campaign_id == campaign.id
    ).all()
    existing_topics = [t[0] for t in existing_topics if t[0]]
    
    unique_titles = [t for t in titles if t not in existing_topics][:campaign.articles_per_day]
    
    for idx, title in enumerate(unique_titles):
        if user.credits < 1:
            logger.warning(f"Insufficient credits for campaign {campaign.id}")
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
        db.refresh(article)
        background_tasks.add_task(
            trigger_func,
            str(article.id),
            article.raw_query,
            article.category,
            article.target_length,
            article.source_count
        )
    
    return articles_created

def get_user_campaigns(db: Session, user_id: uuid.UUID):
    return db.query(Campaign).filter(
        Campaign.user_id == user_id
    ).order_by(Campaign.created_at.desc()).all()

def get_campaign_by_id(db: Session, campaign_id: uuid.UUID, user_id: uuid.UUID):
    return db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == user_id
    ).first()

def update_campaign(db: Session, campaign: Campaign, update_data: dict):
    for key, value in update_data.items():
        if value is not None:
            setattr(campaign, key, value)
    
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    
    return campaign

def pause_campaign(db: Session, campaign: Campaign):
    campaign.status = 'paused'
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return campaign

def resume_campaign(db: Session, campaign: Campaign):
    campaign.status = 'active'
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return campaign

def cancel_campaign(db: Session, campaign: Campaign):
    campaign.status = 'cancelled'
    campaign.updated_at = datetime.utcnow()
    db.commit()
    return campaign

def get_active_campaigns(db: Session):
    today = date.today()
    return db.query(Campaign).filter(
        Campaign.status == 'active',
        Campaign.start_date <= today
    ).all()

def should_run_campaign_today(campaign: Campaign) -> bool:
    today = date.today()
    
    if campaign.start_date > today:
        return False
    
    if campaign.end_date and campaign.end_date < today:
        return False
    
    if campaign.total_articles and campaign.articles_generated >= campaign.total_articles:
        return False
    
    return True