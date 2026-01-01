"""Create database tables directly"""
import asyncio
import asyncpg

DATABASE_URL = 'postgresql://neondb_owner:npg_2EA9gjUvaZry@ep-small-silence-a4op8mv6-pooler.us-east-1.aws.neon.tech/neondb?ssl=require'

async def create_tables():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Drop existing tables and types if they exist
    print("Dropping existing objects...")
    await conn.execute("DROP TABLE IF EXISTS api_usage CASCADE")
    await conn.execute("DROP TABLE IF EXISTS subscriptions CASCADE")
    await conn.execute("DROP TABLE IF EXISTS scans CASCADE")
    await conn.execute("DROP TABLE IF EXISTS users CASCADE")
    await conn.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    await conn.execute("DROP TYPE IF EXISTS user_tier CASCADE")
    await conn.execute("DROP TYPE IF EXISTS scan_mode CASCADE")
    await conn.execute("DROP TYPE IF EXISTS scan_status CASCADE")
    await conn.execute("DROP TYPE IF EXISTS subscription_tier CASCADE")
    await conn.execute("DROP TYPE IF EXISTS subscription_status CASCADE")
    
    print("Creating types...")
    await conn.execute("CREATE TYPE user_tier AS ENUM ('free', 'premium', 'enterprise')")
    await conn.execute("CREATE TYPE scan_mode AS ENUM ('common', 'fast', 'full')")
    await conn.execute("CREATE TYPE scan_status AS ENUM ('queued', 'running', 'completed', 'failed')")
    await conn.execute("CREATE TYPE subscription_tier AS ENUM ('premium', 'enterprise')")
    await conn.execute("CREATE TYPE subscription_status AS ENUM ('active', 'canceled', 'past_due')")
    
    print("Creating users table...")
    await conn.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            tier VARCHAR(20) NOT NULL DEFAULT 'free',
            api_key_hash VARCHAR(64) UNIQUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_login TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            email_verified BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    await conn.execute("CREATE INDEX ix_users_email ON users(email)")
    await conn.execute("CREATE INDEX ix_users_tier ON users(tier)")
    
    print("Creating scans table...")
    await conn.execute("""
        CREATE TABLE scans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            target VARCHAR(500) NOT NULL,
            scan_mode scan_mode NOT NULL DEFAULT 'common',
            status scan_status NOT NULL DEFAULT 'queued',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            duration_seconds INTEGER,
            vulnerabilities_found INTEGER NOT NULL DEFAULT 0,
            critical_count INTEGER NOT NULL DEFAULT 0,
            high_count INTEGER NOT NULL DEFAULT 0,
            medium_count INTEGER NOT NULL DEFAULT 0,
            low_count INTEGER NOT NULL DEFAULT 0,
            platform_detected VARCHAR(100),
            confidence NUMERIC(3,2),
            report_json JSONB,
            report_text TEXT,
            error_message TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("CREATE INDEX ix_scans_user_id ON scans(user_id)")
    await conn.execute("CREATE INDEX ix_scans_status ON scans(status)")
    await conn.execute("CREATE INDEX ix_scans_created_at ON scans(created_at)")
    
    print("Creating subscriptions table...")
    await conn.execute("""
        CREATE TABLE subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            stripe_subscription_id VARCHAR(255) NOT NULL UNIQUE,
            stripe_customer_id VARCHAR(255) NOT NULL,
            tier subscription_tier NOT NULL,
            status subscription_status NOT NULL DEFAULT 'active',
            current_period_start TIMESTAMP NOT NULL,
            current_period_end TIMESTAMP NOT NULL,
            cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("CREATE INDEX ix_subscriptions_user_id ON subscriptions(user_id)")
    await conn.execute("CREATE INDEX ix_subscriptions_status ON subscriptions(status)")
    
    print("Creating api_usage table...")
    await conn.execute("""
        CREATE TABLE api_usage (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            endpoint VARCHAR(255) NOT NULL,
            method VARCHAR(10) NOT NULL,
            status_code INTEGER NOT NULL,
            response_time_ms INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("CREATE INDEX ix_api_usage_user_id ON api_usage(user_id)")
    await conn.execute("CREATE INDEX ix_api_usage_created_at ON api_usage(created_at)")
    
    # Verify tables
    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    print("\nTables created:", [t['table_name'] for t in tables])
    
    await conn.close()
    print("\nDatabase setup complete!")

if __name__ == "__main__":
    asyncio.run(create_tables())
