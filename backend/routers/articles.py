from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid

from database import get_db
from dependencies import get_current_user
import models
import schemas
from lambda_trigger import retry_article_job

router = APIRouter(prefix="/articles", tags=["articles"])

class ArticleUpdateRequest(BaseModel):
    content: Optional[str] = None
    topic: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None

@router.post("", response_model=schemas.ArticleResponse)
def create_article(
    request: schemas.ArticleCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    article = models.Article(
        user_id=current_user.id,
        raw_query=request.query_explanation,
        category=request.category,
        target_length=request.target_length,
        source_count=request.source_count,
        scheduled_at=request.scheduled_at,
        timezone=request.timezone,
        status="queued"
    )
    
    db.add(article)
    db.commit()
    db.refresh(article)
    
    return article

@router.get("", response_model=List[schemas.ArticleResponse])
def list_articles(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    articles = db.query(models.Article).filter(
        models.Article.user_id == current_user.id
    ).order_by(models.Article.created_at.desc()).offset(skip).limit(limit).all()
    
    return articles

@router.get("/stats", response_model=schemas.UserStats)
def get_user_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total = db.query(models.Article).filter(
        models.Article.user_id == current_user.id
    ).count()
    
    scheduled = db.query(models.Article).filter(
        models.Article.user_id == current_user.id,
        models.Article.status == 'queued'
    ).count()
    
    completed = db.query(models.Article).filter(
        models.Article.user_id == current_user.id,
        models.Article.status == 'completed'
    ).count()
    
    posted = db.query(models.Article).filter(
        models.Article.user_id == current_user.id,
        models.Article.status == 'posted'
    ).count()
    
    return {
        "total": total,
        "scheduled": scheduled,
        "completed": completed,
        "posted": posted
    }

@router.get("/{article_id}", response_model=schemas.ArticleResponse)
def get_article(
    article_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    article = db.query(models.Article).filter(
        models.Article.id == article_id,
        models.Article.user_id == current_user.id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article

@router.post("/{article_id}/retry", response_model=schemas.ArticleResponse)
async def retry_article(
    article_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    article = db.query(models.Article).filter(
        models.Article.id == article_id,
        models.Article.user_id == current_user.id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.status not in ["failed"]:
        raise HTTPException(status_code=400, detail=f"Can only retry failed articles")
    
    if article.retry_count >= 3:
        raise HTTPException(status_code=400, detail="Maximum retry limit reached")
    
    payload = {
        "query": article.raw_query,
        "category": article.category,
        "target_length": article.target_length,
        "source_count": article.source_count
    }
    
    success = await retry_article_job(str(article.id), payload)
    
    if success:
        article.status = "queued"
        article.error_message = None
        article.retry_count += 1
        db.commit()
        db.refresh(article)
        return article
    else:
        raise HTTPException(status_code=500, detail="Failed to queue retry")

@router.patch("/{article_id}")
def update_article(
    article_id: uuid.UUID,
    updates: ArticleUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    article = db.query(models.Article).filter(
        models.Article.id == article_id, 
        models.Article.user_id == current_user.id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if updates.content is not None:
        article.content = updates.content
    if updates.topic is not None:
        article.topic = updates.topic
    if updates.category is not None:
        article.category = updates.category
    if updates.status is not None:
        article.status = updates.status
    
    db.commit()
    db.refresh(article)
        
    return {"success": True, "message": "Article updated", "article": article}

@router.delete("/{article_id}")
def delete_article(
    article_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    article = db.query(models.Article).filter(
        models.Article.id == article_id,
        models.Article.user_id == current_user.id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    db.delete(article)
    db.commit()
    
    return {"success": True, "message": "Article deleted"}