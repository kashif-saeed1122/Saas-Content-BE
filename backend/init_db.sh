#!/bin/bash
set -e

echo "🚀 Initializing NeuralGen Database..."

# Create database if it doesn't exist (already created by POSTGRES_DB env var)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Ensure database is created
    SELECT 'Database seo_db initialized successfully!' as message;
    
    -- Create extensions if needed
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON DATABASE seo_db TO postgres;
EOSQL

echo "✅ Database initialization complete!"