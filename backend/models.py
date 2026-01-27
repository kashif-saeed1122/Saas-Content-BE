import uuid
import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    
    # SECURITY FIELDS
    hashed_password = Column(String(255), nullable=True) 
    google_id = Column(String(255), unique=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    articles = relationship("Article", back_populates="user")

class Article(Base):
    __tablename__ = "articles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Inputs
    raw_query = Column(Text, nullable=False) 
    topic = Column(String(255))              
    category = Column(String(100))
    target_length = Column(Integer, default=1500)
    source_count = Column(Integer, default=5)
    
    # Scheduling
    # Enhanced status values (backwards compatible):
    # - queued: Job added to SQS queue
    # - researching: Lambda started, gathering sources
    # - scraping: Content extraction in progress
    # - writing: AI generating article
    # - processing: Legacy status (kept for compatibility)
    # - scheduled: Awaiting scheduled publish time
    # - completed: Article ready
    # - failed: Job failed (check error_message)
    # - posted: Published to platform
    status = Column(String(20), default="queued", index=True)
    
    scheduled_at = Column(DateTime, nullable=True) 
    timezone = Column(String(50), default="UTC")
    
    # Error tracking (new field - nullable for existing records)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Final Output
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="articles")
    sources = relationship("SourceContent", back_populates="article", cascade="all, delete-orphan")
    brief = relationship("SEOBrief", back_populates="article", uselist=False, cascade="all, delete-orphan")

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
    status = Column(String(20), default="generated")  # generated, approved, rejected
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User")