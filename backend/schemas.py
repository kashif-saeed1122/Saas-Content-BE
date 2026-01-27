from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class ArticleCreateRequest(BaseModel):
    query: str = Field(..., description="The article topic or query")
    category: str = "General"
    target_length: int = 1500
    source_count: int = 5
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"

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
    outline: Optional[Any] = None  # Flexible: accepts any JSON structure (list or object)
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

    class Config:
        from_attributes = True

# New schemas for multi-article generation
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