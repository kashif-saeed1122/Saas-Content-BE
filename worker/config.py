import os
import logging
from dotenv import load_dotenv

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    load_dotenv()
    
    # Database with connection pooling for Lambda
    # Lambda containers are reused, so pooling helps reuse connections
    DEFAULT_DB_URL = "postgresql://postgres:1122@host.docker.internal:5432/seo_db"
    DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    
    # Connection pool settings for Lambda
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    # Google API (Custom Search)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    
    # API Usage Limits
    DAILY_API_LIMIT = 95
    
    # SQS Configuration (for local Lambda testing)
    SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
    SQS_DLQ_URL = os.getenv("SQS_DLQ_URL")