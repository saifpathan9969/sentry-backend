import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        'postgresql://neondb_owner:npg_2EA9gjUvaZry@ep-small-silence-a4op8mv6-pooler.us-east-1.aws.neon.tech/neondb?ssl=require'
    )
    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    print("Tables in database:", [t['table_name'] for t in tables])
    await conn.close()

asyncio.run(check())
