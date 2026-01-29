from fastapi import APIRouter, Depends
from datetime import datetime

from dependencies import get_current_user
import models
from lambda_trigger import get_queue_statistics

router = APIRouter(tags=["system"])

@router.get("/health")
async def health_check():
    queue_stats = await get_queue_statistics()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "queue": queue_stats
    }

@router.get("/queue/stats")
async def get_queue_stats(current_user: models.User = Depends(get_current_user)):
    stats = await get_queue_statistics()
    return {"queue_name": "article-generation-queue", **stats}