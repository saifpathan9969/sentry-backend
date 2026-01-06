"""Create SQLite database tables for local development"""
import asyncio
import aiosqlite
from pathlib import Path

DATABASE_PATH = "pentest_brain.db"

async def create_tables():
    """Create all necessary tables for the application"""
    
    # Try to remove existing database
    db_path = Path(DATABASE_PATH)
    if db_path.exists():
        try:
            db_path.unlink()
            print(f"Removed existing database: {DATABASE_PATH}")
        except PermissionError:
            print(f"Database {DATABASE_PATH} is in use, will recreate tables...")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Drop existing tables if they exist
        print("Dropping existing tables if they exist...")
        await db.execute("DROP TABLE IF EXISTS api_usage")
        await db.execute("DROP TABLE IF EXISTS subscriptions")
        await db.execute("DROP TABLE IF EXISTS scans")
        await db.execute("DROP TABLE IF EXISTS users")
        await db.execute("DROP TABLE IF EXISTS alembic_version")
        
        print("Creating users table...")
        await db.execute("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                tier VARCHAR(20) NOT NULL DEFAULT 'free',
                api_key_hash VARCHAR(64) UNIQUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                email_verified BOOLEAN NOT NULL DEFAULT 0
            )
        """)
        await db.execute("CREATE INDEX ix_users_email ON users(email)")
        await db.execute("CREATE INDEX ix_users_tier ON users(tier)")
        
        print("Creating scans table...")
        await db.execute("""
            CREATE TABLE scans (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                target VARCHAR(500) NOT NULL,
                scan_mode VARCHAR(20) NOT NULL DEFAULT 'common',
                status VARCHAR(20) NOT NULL DEFAULT 'queued',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds INTEGER,
                vulnerabilities_found INTEGER NOT NULL DEFAULT 0,
                critical_count INTEGER NOT NULL DEFAULT 0,
                high_count INTEGER NOT NULL DEFAULT 0,
                medium_count INTEGER NOT NULL DEFAULT 0,
                low_count INTEGER NOT NULL DEFAULT 0,
                platform_detected VARCHAR(100),
                confidence REAL,
                report_json TEXT,
                report_text TEXT,
                error_message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX ix_scans_user_id ON scans(user_id)")
        await db.execute("CREATE INDEX ix_scans_status ON scans(status)")
        await db.execute("CREATE INDEX ix_scans_created_at ON scans(created_at)")
        
        print("Creating subscriptions table...")
        await db.execute("""
            CREATE TABLE subscriptions (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                stripe_subscription_id VARCHAR(255) NOT NULL UNIQUE,
                stripe_customer_id VARCHAR(255) NOT NULL,
                tier VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                current_period_start TIMESTAMP NOT NULL,
                current_period_end TIMESTAMP NOT NULL,
                cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX ix_subscriptions_user_id ON subscriptions(user_id)")
        await db.execute("CREATE INDEX ix_subscriptions_status ON subscriptions(status)")
        
        print("Creating api_usage table...")
        await db.execute("""
            CREATE TABLE api_usage (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                endpoint VARCHAR(255) NOT NULL,
                method VARCHAR(10) NOT NULL,
                status_code INTEGER NOT NULL,
                response_time_ms INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX ix_api_usage_user_id ON api_usage(user_id)")
        await db.execute("CREATE INDEX ix_api_usage_created_at ON api_usage(created_at)")
        
        # Create alembic version table to mark as migrated
        print("Creating alembic_version table...")
        await db.execute("""
            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            )
        """)
        await db.execute("INSERT INTO alembic_version (version_num) VALUES ('001')")
        
        await db.commit()
        
        # Verify tables
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = await cursor.fetchall()
        print("\nTables created:", [t[0] for t in tables])
        
    print(f"\nSQLite database setup complete: {DATABASE_PATH}")

if __name__ == "__main__":
    asyncio.run(create_tables())