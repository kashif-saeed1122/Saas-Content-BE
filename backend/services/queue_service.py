import os
import json
import boto3
import logging
from typing import Dict, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class QueueService:
    """
    AWS SQS Queue Service for article generation jobs.
    Handles local and AWS environments seamlessly.
    """
    
    def __init__(self):
        self.is_local = os.getenv("LOCAL_DEV", "true").lower() == "true"
        self.queue_url = os.getenv("SQS_QUEUE_URL")
        self.dlq_url = os.getenv("SQS_DLQ_URL")
        
        if self.is_local:
            # LocalStack configuration for local development
            self.sqs_client = boto3.client(
                'sqs',
                endpoint_url=os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key_id='test',
                aws_secret_access_key='test'
            )
            logger.info("🔧 Queue Service: LOCAL mode (LocalStack)")
        else:
            # Production AWS SQS
            self.sqs_client = boto3.client(
                'sqs',
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            logger.info("☁️  Queue Service: AWS mode")
    
    def enqueue_job(self, article_id: str, payload: Dict) -> bool:
        """
        Add a job to the processing queue.
        
        Args:
            article_id: Unique article identifier
            payload: Job data (query, category, target_length, etc.)
        
        Returns:
            bool: True if enqueued successfully
        """
        try:
            message_body = json.dumps({
                "article_id": article_id,
                **payload
            })
            
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    'ArticleId': {
                        'StringValue': article_id,
                        'DataType': 'String'
                    },
                    'JobType': {
                        'StringValue': 'article_generation',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"✅ Job queued: {article_id} (MessageId: {response['MessageId']})")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Failed to enqueue job {article_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error enqueueing {article_id}: {e}")
            return False
    
    def get_queue_stats(self) -> Dict:
        """
        Get current queue statistics.
        
        Returns:
            Dict with queue metrics
        """
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=[
                    'ApproximateNumberOfMessages',
                    'ApproximateNumberOfMessagesNotVisible',
                    'ApproximateNumberOfMessagesDelayed'
                ]
            )
            
            attributes = response.get('Attributes', {})
            return {
                "queued": int(attributes.get('ApproximateNumberOfMessages', 0)),
                "in_progress": int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                "delayed": int(attributes.get('ApproximateNumberOfMessagesDelayed', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"queued": 0, "in_progress": 0, "delayed": 0}
    
    def retry_failed_job(self, article_id: str, payload: Dict) -> bool:
        """
        Retry a failed job by re-enqueueing it.
        
        Args:
            article_id: Article ID to retry
            payload: Original job payload
        
        Returns:
            bool: True if retry queued successfully
        """
        logger.info(f"🔄 Retrying job: {article_id}")
        return self.enqueue_job(article_id, payload)
    
    def purge_queue(self) -> bool:
        """
        Emergency: Clear all messages from queue.
        Use with caution - only for maintenance.
        """
        try:
            self.sqs_client.purge_queue(QueueUrl=self.queue_url)
            logger.warning(f"⚠️ Queue purged: {self.queue_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge queue: {e}")
            return False

# Global queue service instance
queue_service = QueueService()