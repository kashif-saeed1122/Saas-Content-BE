from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import logging

from database import get_db
from dependencies import get_current_user
import models
import schemas
from services import campaign_service, credit_service
from lambda_trigger import trigger_worker

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
logger = logging.getLogger(__name__)

async def trigger_worker_task(article_id: str, query: str, category: str, target_length: int, source_count: int):
    try:
        await trigger_worker(article_id, query, category, target_length, source_count)
    except Exception as e:
        logger.error(f"Failed to trigger worker: {e}")

@router.post("", response_model=schemas.CampaignResponse)
async def create_campaign(
    request: schemas.CampaignCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.credits < request.articles_per_day:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient credits. Need {request.articles_per_day}, have {current_user.credits}"
        )
    
    campaign_data = request.dict()
    campaign = campaign_service.create_campaign(db, current_user, campaign_data)
    
    articles = await campaign_service.generate_first_batch(
        db, campaign, current_user, background_tasks, trigger_worker_task
    )
    
    logger.info(f"Campaign {campaign.id} created with {len(articles)} articles")
    
    return campaign

@router.get("", response_model=List[schemas.CampaignResponse])
def list_campaigns(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaigns = campaign_service.get_user_campaigns(db, current_user.id)
    return campaigns

@router.get("/{campaign_id}", response_model=schemas.CampaignResponse)
def get_campaign(
    campaign_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.patch("/{campaign_id}", response_model=schemas.CampaignUpdateRequest)
def update_campaign(
    campaign_id: uuid.UUID,
    request: schemas.CampaignUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = request.dict(exclude_unset=True)
    updated_campaign = campaign_service.update_campaign(db, campaign, update_data)
    return updated_campaign

@router.post("/{campaign_id}/pause", response_model=schemas.CampaignResponse)
def pause_campaign(
    campaign_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign_service.pause_campaign(db, campaign)

@router.post("/{campaign_id}/resume", response_model=schemas.CampaignResponse)
def resume_campaign(
    campaign_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign_service.resume_campaign(db, campaign)

@router.delete("/{campaign_id}")
def cancel_campaign(
    campaign_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_service.cancel_campaign(db, campaign)
    return {"success": True, "message": "Campaign cancelled"}

@router.get("/{campaign_id}/articles", response_model=List[schemas.ArticleResponse])
def get_campaign_articles(
    campaign_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = campaign_service.get_campaign_by_id(db, campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    articles = db.query(models.Article).filter(
        models.Article.campaign_id == campaign_id
    ).order_by(models.Article.created_at.desc()).all()
    
    return articles