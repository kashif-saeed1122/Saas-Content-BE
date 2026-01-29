import uuid
import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    
    hashed_password = Column(String(255), nullable=True) 
    google_id = Column(String(255), unique=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    credits = Column(Integer, default=10)
    plan = Column(String(20), default='free')
    stripe_customer_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    articles = relationship("Article", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    integrations = relationship("WebhookIntegration", back_populates="user")

class Article(Base):
    __tablename__ = "articles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    
    raw_query = Column(Text, nullable=False) 
    topic = Column(String(255))              
    category = Column(String(100))
    target_length = Column(Integer, default=1500)
    source_count = Column(Integer, default=5)
    
    status = Column(String(20), default="queued", index=True)
    scheduled_at = Column(DateTime, nullable=True) 
    timezone = Column(String(50), default="UTC")
    
    is_recurring = Column(Boolean, default=False)
    posted_at = Column(DateTime, nullable=True)
    posting_attempt_count = Column(Integer, default=0)
    last_posting_error = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="articles")
    campaign = relationship("Campaign", back_populates="articles")
    sources = relationship("SourceContent", back_populates="article", cascade="all, delete-orphan")
    brief = relationship("SEOBrief", back_populates="article", uselist=False, cascade="all, delete-orphan")

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    topic = Column(Text, nullable=False)
    category = Column(String(100), default='General')
    
    articles_per_day = Column(Integer, default=1)
    posting_times = Column(JSON, default=["09:00", "17:00"])
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    total_articles = Column(Integer, nullable=True)
    
    target_length = Column(Integer, default=1500)
    source_count = Column(Integer, default=5)
    
    status = Column(String(20), default='active', index=True)
    articles_generated = Column(Integer, default=0)
    articles_posted = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    
    webhook_url = Column(Text, nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="campaigns")
    articles = relationship("Article", back_populates="campaign")

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    prefix = Column(String(20))
    
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="api_keys")

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    type = Column(String(50))
    reference_type = Column(String(50))
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(Text)
    tokens_consumed = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="credit_transactions")

class WebhookIntegration(Base):
    __tablename__ = "webhook_integrations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(255))
    webhook_url = Column(Text, nullable=False)
    webhook_secret = Column(String(255), nullable=True)
    platform_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="integrations")

class SourceContent(Base):
    __tablename__ = "source_contents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    
    url = Column(Text, nullable=False)
    title = Column(String(500))
    full_content = Column(Text)
    source_origin = Column(String(100))
    
    article = relationship("Article", back_populates="sources")

class SEOBrief(Base):
    __tablename__ = "seo_briefs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    
    keywords = Column(JSON)      
    outline = Column(JSON)       
    strategy = Column(Text)
    analysis_meta = Column(JSON) 
    
    article = relationship("Article", back_populates="brief")

class ArticleTitle(Base):
    __tablename__ = "article_titles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="generated")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User")
