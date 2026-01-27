import os
import json
import httpx
from services.queue_service import queue_service
import logging

logger = logging.getLogger(__name__)

IS_LOCAL = os.getenv("LOCAL_DEV", "true").lower() == "true"
LOCAL_LAMBDA_URL = "http://localhost:9000/2015-03-31/functions/function/invocations"

async def trigger_worker(
    article_id: str, 
    query: str, 
    category: str, 
    target_length: int = 1500, 
    source_count: int = 5
) -> bool:
    payload = {
        "article_id": article_id,
        "query": query,
        "category": category,
        "target_length": target_length,
        "source_count": source_count
    }

    logger.info(f"🚀 Enqueueing Article Job: {article_id}")
    
    if IS_LOCAL:
        # LOCAL: Call Lambda directly with raw payload
        try:
            async with httpx.AsyncClient(timeout=900.0) as client:
                response = await client.post(LOCAL_LAMBDA_URL, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"✅ Lambda invoked: {article_id}")
                    return True
                else:
                    logger.error(f"❌ Lambda failed: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Lambda error: {e}")
            return False
    else:
        # PRODUCTION: Use SQS queue
        return queue_service.enqueue_job(article_id, payload)

async def get_queue_statistics():
    return queue_service.get_queue_stats()

async def retry_article_job(article_id: str, payload: dict) -> bool:
    return queue_service.retry_failed_job(article_id, payload)