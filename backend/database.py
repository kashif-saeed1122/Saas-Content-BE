import os
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

logger = logging.getLogger(__name__)

DEFAULT_DB_URL = "postgresql://postgres:1122@localhost:5432/seo_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# Connection pooling configuration for scalability
engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=10,              # Core connections kept alive
    max_overflow=20,           # Extra connections when needed
    pool_timeout=30,           # Wait up to 30s for available connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Verify connection before using
    echo=False                 # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session dependency with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection():
    """Test database connectivity on startup"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False