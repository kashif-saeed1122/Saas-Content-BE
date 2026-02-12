import json
import logging
from typing import Dict, Any
import httpx
import asyncio


from graph import generate_article_workflow
from db_sync import save_research_data, finalize_article_in_db
from sqlalchemy import create_engine, text
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_article_status(article_id: str, status: str, error_message: str = None):
    """Update article status in database"""
    engine = create_engine(Config.DB_URL)
    try:
        with engine.connect() as conn:
            if error_message:
                conn.execute(text("""
                    UPDATE articles 
                    SET status = :status, 
                        error_message = :error,
                        updated_at = NOW()
                    WHERE id = :id
                """), {"status": status, "error": error_message, "id": article_id})
            else:
                conn.execute(text("""
                    UPDATE articles 
                    SET status = :status,
                        updated_at = NOW()
                    WHERE id = :id
                """), {"status": status, "id": article_id})
            conn.commit()
            logger.info(f"✅ Status updated: {article_id} -> {status}")
    except Exception as e:
        logger.error(f"Failed to update status: {e}")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for processing SQS events.
    Each event can contain multiple records (batched by SQS).
    
    Args:
        event: SQS event with Records array
        context: Lambda context object
    
    Returns:
        Response with processing results
    """
    logger.info(f"📥 Received {len(event.get('Records', []))} messages")
    
    successful = []
    failed = []
    
    for record in event.get('Records', []):
        try:
            # Parse message body
            body = json.loads(record['body'])
            article_id = body['article_id']
            query = body['query']
            category = body.get('category', 'General')
            target_length = body.get('target_length', 1500)
            source_count = body.get('source_count', 5)
            
            logger.info(f"🚀 Processing Article: {article_id}")
            logger.info(f"   Query: {query}")
            
            # Update status to 'researching'
            update_article_status(article_id, "researching")
            
            # Run the article generation workflow
            result = generate_article_workflow(
                article_id=article_id,
                query=query,
                category=category,
                target_length=target_length,
                source_count=source_count
            )
            
            if result.get('status') == 'success':
                logger.info(f"✅ Article generated successfully: {article_id}")
                
                # Update status to 'scraping'
                update_article_status(article_id, "scraping")
                save_research_data(article_id, result.get('sources', []))
                
                # Update status to 'writing'
                update_article_status(article_id, "writing")
                
                # Finalize article
                finalize_article_in_db(
                    article_id=article_id,
                    content=result.get('content', ''),
                    seo_brief=result.get('seo_brief', {})
                )

                tokens = result.get('tokens_used', 0)
                asyncio.run(notify_api_completion(article_id, tokens))
                successful.append(article_id)
                
            else:
                error_msg = result.get('error', 'Unknown error during generation')
                logger.error(f"❌ Generation failed: {article_id} - {error_msg}")
                update_article_status(article_id, "failed", error_msg)
                failed.append(article_id)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            failed.append("unknown")
            
        except KeyError as e:
            logger.error(f"Missing required field: {e}")
            failed.append("unknown")
            
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            
            # Try to extract article_id for status update
            try:
                body = json.loads(record['body'])
                article_id = body['article_id']
                update_article_status(article_id, "failed", str(e))
                failed.append(article_id)
            except:
                failed.append("unknown")
    
    # Return processing summary
    response = {
        "statusCode": 200,
        "body": json.dumps({
            "processed": len(event.get('Records', [])),
            "successful": len(successful),
            "failed": len(failed),
            "successful_ids": successful,
            "failed_ids": failed
        })
    }
    
    logger.info(f"📊 Batch Summary: {len(successful)} success, {len(failed)} failed")
    
    return response

async def notify_api_completion(article_id: str, tokens_used: int):
    api_url = os.getenv("API_URL", "http://localhost:8000")
    internal_secret = os.getenv("INTERNAL_SECRET", "change-me-in-production")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{api_url}/internal/article-complete",
                json={"article_id": article_id, "tokens_used": tokens_used},
                headers={"X-Internal-Secret": internal_secret}
            )
    except Exception as e:
        logger.error(f"Failed to notify API: {e}")
