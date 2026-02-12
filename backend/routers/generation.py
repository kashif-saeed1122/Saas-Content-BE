from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import logging

from database import get_db
from dependencies import get_current_user
import models
import schemas
from lambda_trigger import trigger_worker
from agents.title_agent import generate_titles

router = APIRouter(prefix="/generate", tags=["generation"])
titles_router = APIRouter(prefix="/titles", tags=["titles"])
logger = logging.getLogger(__name__)

async def trigger_worker_task(payload: dict):
    try:
        await trigger_worker(
            payload["article_id"], payload["query"], payload["category"],
            payload["target_length"], payload["source_count"]
        )
    except Exception as e:
        logger.error(f"❌ Background Trigger Failed: {e}")

@router.post("", response_model=schemas.ArticleResponse)
async def generate_article(
    request: schemas.ArticleCreateRequest, 
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    logger.info(f"📝 Creating new article for user: {current_user.id}")
    logger.info(f"   Query: {request.query_explanation[:50]}...")
    logger.info(f"   Category: {request.category}")
    logger.info(f"   Target Length: {request.target_length}")
    
    new_article = models.Article(
        id=uuid.uuid4(),
        user_id=current_user.id,
        raw_query=request.query_explanation,
        category=request.category,
        target_length=request.target_length,
        source_count=request.source_count,
        scheduled_at=request.scheduled_at,
        timezone=request.timezone,
        webhook_integration_id=request.webhook_integration_id,  
        status="queued",
        topic=request.query_explanation[:50] + "..."
    )
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    
    logger.info(f"✅ Article created with ID: {new_article.id}")

    payload = {
        "article_id": str(new_article.id), "query": new_article.raw_query,
        "category": new_article.category, "target_length": new_article.target_length,
        "source_count": new_article.source_count
    }
    background_tasks.add_task(trigger_worker_task, payload)
    return new_article

@router.post("/titles", response_model=List[schemas.ArticleTitle])
async def generate_article_titles(
    request: schemas.TitleGenerationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"🎯 Generating {request.count} titles for user: {current_user.id}")
    
    titles = await generate_titles(request.description, request.count)
    
    db_titles = []
    for title_text in titles:
        db_title = models.ArticleTitle(
            id=uuid.uuid4(),
            user_id=current_user.id,
            title=title_text,
            description=request.description,
            status="generated"
        )
        db.add(db_title)
        db_titles.append(db_title)
    
    db.commit()
    for t in db_titles:
        db.refresh(t)
    
    return db_titles

@router.post("/batch")
async def generate_batch_articles(
    request: schemas.BatchGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"🚀 Batch generation: {len(request.title_ids)} titles")
    
    titles = db.query(models.ArticleTitle).filter(
        models.ArticleTitle.id.in_(request.title_ids),
        models.ArticleTitle.user_id == current_user.id
    ).all()
    
    if len(titles) != len(request.title_ids):
        raise HTTPException(status_code=400, detail="Some titles not found")
    
    created_articles = []
    
    for title_obj in titles:
        new_article = models.Article(
            id=uuid.uuid4(),
            user_id=current_user.id,
            raw_query=title_obj.title,
            category=request.category,
            target_length=request.target_length,
            source_count=request.source_count,
            scheduled_at=request.scheduled_at,
            timezone=request.timezone,
            webhook_integration_id=request.webhook_integration_id,
            status="queued",
            topic=title_obj.title
        )
        db.add(new_article)
        created_articles.append(new_article)
    
    db.commit()
    
    for article in created_articles:
        db.refresh(article)
        payload = {
            "article_id": str(article.id),
            "query": article.raw_query,
            "category": article.category,
            "target_length": article.target_length,
            "source_count": article.source_count
        }
        background_tasks.add_task(trigger_worker_task, payload)
    
    logger.info(f"✅ Created {len(created_articles)} articles and queued")
    
    return {
        "success": True,
        "message": f"Created {len(created_articles)} articles",
        "article_ids": [str(a.id) for a in created_articles]
    }

@titles_router.patch("/{title_id}/verify")
async def verify_title(
    title_id: uuid.UUID,
    request: schemas.TitleVerificationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    title = db.query(models.ArticleTitle).filter(
        models.ArticleTitle.id == title_id,
        models.ArticleTitle.user_id == current_user.id
    ).first()
    
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    
    title.title = request.title
    title.status = request.status
    db.commit()
    db.refresh(title)
    
    return {"success": True, "title": title}