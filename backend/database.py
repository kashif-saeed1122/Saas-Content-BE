import os
import time
from sqlalchemy import create_engine, pool, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging

logger = logging.getLogger(__name__)


ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
DEFAULT_DB_URL = "postgresql://postgres:1122@localhost:5432/seo_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

logger.info(f"🌍 Environment: {ENVIRONMENT}")
logger.info(f"🔌 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")


if IS_PRODUCTION:
    POOL_SIZE = 20
    MAX_OVERFLOW = 40
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 1800  # 30 minutes for cloud databases
else:
    POOL_SIZE = 10
    MAX_OVERFLOW = 20
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600  # 1 hour for local

def create_engine_with_retry(max_retries=5, retry_delay=2):
    """Create database engine with automatic retry logic"""
    from sqlalchemy import text  # Add this import
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                DATABASE_URL,
                poolclass=pool.QueuePool,
                pool_size=POOL_SIZE,
                max_overflow=MAX_OVERFLOW,
                pool_timeout=POOL_TIMEOUT,
                pool_recycle=POOL_RECYCLE,
                pool_pre_ping=True,
                echo=False,
                connect_args={
                    "connect_timeout": 10,
                    "options": "-c statement_timeout=30000"
                }
            )
            
            # Test connection - FIX HERE
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))  # Changed this line
            
            logger.info(f"✅ Database connected successfully (attempt {attempt + 1})")
            return engine
            
        except OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"⚠️  Database connection failed (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ Database connection failed after {max_retries} attempts: {e}")
                raise

engine = create_engine_with_retry()


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log new database connections"""
    logger.debug("🔌 New database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Handle connection checkout from pool"""
    pass

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Handle connection return to pool"""
    pass


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)
Base = declarative_base()

def get_db():
    """
    Database session dependency with automatic cleanup and error handling.
    Use with FastAPI Depends() or in context managers.
    """
    db = SessionLocal()
    try:
        yield db
    except DisconnectionError:
        logger.error("🔌 Database disconnection detected, attempting to reconnect...")
        db.rollback()
        # Connection will be refreshed on next request due to pool_pre_ping
        raise
    except Exception as e:
        logger.error(f"❌ Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_connection_pool_status():
    """Get current connection pool statistics"""
    pool_status = {
        "size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "total_connections": engine.pool.size() + engine.pool.overflow()
    }
    return pool_status

def close_all_connections():
    """Close all database connections - useful for graceful shutdown"""
    try:
        engine.dispose()
        logger.info("🔒 All database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing connections: {e}")

class DatabaseSession:
    """
    Context manager for database sessions in Celery tasks.
    Automatically handles connection lifecycle and errors.
    
    Usage:
        with DatabaseSession() as db:
            # Your database operations
            pass
    """
    def __enter__(self):
        self.db = SessionLocal()
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.db.rollback()
                logger.error(f"Transaction rolled back due to: {exc_val}")
            else:
                self.db.commit()
        except Exception as e:
            logger.error(f"Error in session cleanup: {e}")
            self.db.rollback()
        finally:
            self.db.close()
        
        # Don't suppress exceptions
        return False
