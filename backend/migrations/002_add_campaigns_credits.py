from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1122@localhost:5432/seo_db")

def run_migration():
    engine = create_engine(DATABASE_URL)
    
    migrations = [
        """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 10,
        ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free',
        ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50);
        """,
        
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            key_hash VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(100),
            prefix VARCHAR(20),
            last_used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            revoked_at TIMESTAMP
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
        """,
        
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            topic TEXT NOT NULL,
            category VARCHAR(100) DEFAULT 'General',
            articles_per_day INTEGER DEFAULT 1,
            posting_times JSON DEFAULT '["09:00", "17:00"]',
            start_date DATE NOT NULL,
            end_date DATE,
            total_articles INTEGER,
            target_length INTEGER DEFAULT 1500,
            source_count INTEGER DEFAULT 5,
            status VARCHAR(20) DEFAULT 'active',
            articles_generated INTEGER DEFAULT 0,
            articles_posted INTEGER DEFAULT 0,
            credits_used INTEGER DEFAULT 0,
            webhook_url TEXT,
            webhook_secret VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            last_run_at TIMESTAMP,
            next_run_at TIMESTAMP
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id);
        CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
        CREATE INDEX IF NOT EXISTS idx_campaigns_next_run ON campaigns(next_run_at);
        """,
        
        """
        ALTER TABLE articles 
        ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS posting_attempt_count INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS last_posting_error TEXT,
        ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0;
        """,
        
        """
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            type VARCHAR(50),
            reference_type VARCHAR(50),
            reference_id UUID,
            description TEXT,
            tokens_consumed INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_credit_txn_user ON credit_transactions(user_id);
        """,
        
        """
        CREATE TABLE IF NOT EXISTS webhook_integrations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255),
            webhook_url TEXT NOT NULL,
            webhook_secret VARCHAR(255),
            platform_type VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            last_test_at TIMESTAMP,
            last_test_status VARCHAR(20),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
    ]
    
    try:
        with engine.connect() as conn:
            for i, migration in enumerate(migrations, 1):
                print(f"Running migration {i}/{len(migrations)}...")
                conn.execute(text(migration))
                conn.commit()
            
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
