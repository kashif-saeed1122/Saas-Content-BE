from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import logging

from database import get_db
import models
from tasks.posting_tasks import trigger_webhook_post

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)

INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "change-me-in-production")

class ArticleCompleteRequest(BaseModel):
    article_id: str
    tokens_used: int

@router.post("/article-complete")
def article_complete_callback(
    request: ArticleCompleteRequest,
    x_internal_secret: str = Header(None),
    db: Session = Depends(get_db)
):
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    article = db.query(models.Article).filter(
        models.Article.id == request.article_id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.tokens_used = request.tokens_used
    db.commit()
    
    from datetime import datetime
    if article.webhook_integration_id:
        if article.scheduled_at is None or article.scheduled_at <= datetime.utcnow():
            trigger_webhook_post.delay(str(article.id))
    
    return {"success": True}