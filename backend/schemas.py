from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid

class ArticleCreateRequest(BaseModel):
    query_explanation: str = Field(..., alias="query")
    category: str = "General"
    target_length: int = 1500
    source_count: int = 5
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"
    webhook_integration_id: Optional[str] = None

    class Config:
        populate_by_name = True

class UserStats(BaseModel):
    total: int
    scheduled: int
    completed: int
    posted: int

class SourceResponse(BaseModel):
    id: uuid.UUID
    url: str
    title: Optional[str]
    source_origin: Optional[str]
    
    class Config:
        from_attributes = True

class SEOBriefResponse(BaseModel):
    keywords: Optional[List[str]] = None
    outline: Optional[Any] = None
    strategy: Optional[str] = None
    
    class Config:
        from_attributes = True

class ArticleResponse(BaseModel):
    id: uuid.UUID
    topic: Optional[str] = None
    raw_query: Optional[str] = None
    status: str
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    created_at: datetime
    category: Optional[str] = None
    target_length: Optional[int] = None
    source_count: Optional[int] = None
    content: Optional[str] = None
    sources: Optional[List[SourceResponse]] = []
    brief: Optional[SEOBriefResponse] = None
    campaign_id: Optional[uuid.UUID] = None
    is_recurring: Optional[bool] = False
    tokens_used: Optional[int] = 0

    class Config:
        from_attributes = True

class TitleGenerationRequest(BaseModel):
    description: str = Field(..., description="The topic description")
    count: int = Field(default=1, ge=1, le=5, description="Number of titles to generate (1-5)")

class ArticleTitle(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TitleVerificationRequest(BaseModel):
    title: str
    status: str = Field(..., pattern="^(approved|rejected)$")

class BatchGenerationRequest(BaseModel):
    title_ids: List[uuid.UUID] = Field(..., description="List of approved title IDs")
    category: str = "General"
    target_length: int = 1500
    source_count: int = 5
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"
    webhook_integration_id: Optional[str] = None

class CampaignCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    topic: str
    category: str = "General"
    articles_per_day: int = Field(default=1, ge=1, le=10)
    posting_times: List[str] = ["09:00", "17:00"]
    start_date: date
    end_date: Optional[date] = None
    total_articles: Optional[int] = None
    target_length: int = 1500
    source_count: int = 5
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_integration_id: Optional[str] = None

class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    articles_per_day: Optional[int] = None
    posting_times: Optional[List[str]] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    webhook_url: Optional[str] = None

class CampaignResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str]
    topic: str
    category: str
    articles_per_day: int
    posting_times: List[str]
    start_date: date
    end_date: Optional[date]
    total_articles: Optional[int]
    target_length: int
    source_count: int
    status: str
    articles_generated: int
    articles_posted: int
    credits_used: int
    webhook_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class APIKeyCreateRequest(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: Optional[str]
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class APIKeyCreateResponse(BaseModel):
    id: uuid.UUID
    name: Optional[str]
    key: str
    prefix: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class CreditBalanceResponse(BaseModel):
    credits: int
    plan: str
    
class CreditTransactionResponse(BaseModel):
    id: uuid.UUID
    amount: int
    balance_after: int
    type: str
    reference_type: Optional[str]
    reference_id: Optional[uuid.UUID]
    description: Optional[str]
    tokens_consumed: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class WebhookIntegrationRequest(BaseModel):
    name: str
    webhook_url: str
    webhook_secret: Optional[str] = None
    platform_type: str = "custom"

class WebhookIntegrationResponse(BaseModel):
    id: uuid.UUID
    name: Optional[str]
    webhook_url: str
    platform_type: Optional[str]
    is_active: bool
    last_test_at: Optional[datetime]
    last_test_status: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class WebhookTestRequest(BaseModel):
    webhook_url: str
    webhook_secret: Optional[str] = None
