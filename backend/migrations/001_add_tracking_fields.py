"""
Database Migration: Add error tracking and updated_at fields
Run this once to update your existing database schema.
"""

from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1122@localhost:5432/seo_db")

def run_migration():
    engine = create_engine(DATABASE_URL)
    
    migrations = [
        # Add error_message column (nullable - won't break existing data)
        """
        ALTER TABLE articles 
        ADD COLUMN IF NOT EXISTS error_message TEXT;
        """,
        
        # Add retry_count column with default 0
        """
        ALTER TABLE articles 
        ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
        """,
        
        # Add updated_at column with current timestamp as default
        """
        ALTER TABLE articles 
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """,
        
        # Add index on status for faster queries
        """
        CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
        """,
        
        # Update existing NULL updated_at values
        """
        UPDATE articles 
        SET updated_at = created_at 
        WHERE updated_at IS NULL;
        """
    ]
    
    try:
        with engine.connect() as conn:
            for i, migration in enumerate(migrations, 1):
                print(f"Running migration {i}/{len(migrations)}...")
                conn.execute(text(migration))
                conn.commit()
            
        print("✅ Migration completed successfully!")
        print("   - Added: error_message (TEXT)")
        print("   - Added: retry_count (INTEGER)")
        print("   - Added: updated_at (TIMESTAMP)")
        print("   - Created: index on status")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()