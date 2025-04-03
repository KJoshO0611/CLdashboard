import logging
from typing import Optional
import asyncpg
from pathlib import Path

logger = logging.getLogger(__name__)

async def run_migrations(pool: Optional[asyncpg.Pool] = None) -> None:
    """Run database migrations"""
    if not pool:
        raise RuntimeError("Database pool not provided")
    
    try:
        # Create migrations table if it doesn't exist
        await pool.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Get list of applied migrations
        applied = await pool.fetch('SELECT name FROM migrations')
        applied_names = {row['name'] for row in applied}
        
        # Get list of migration files
        migrations_dir = Path(__file__).parent.parent / 'migrations'
        migration_files = sorted(migrations_dir.glob('*.sql'))
        
        # Apply each migration
        for migration_file in migration_files:
            if migration_file.name not in applied_names:
                logger.info(f"Applying migration: {migration_file.name}")
                
                # Read and execute migration SQL
                sql = migration_file.read_text()
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(sql)
                        await conn.execute(
                            'INSERT INTO migrations (name) VALUES ($1)',
                            migration_file.name
                        )
                
                logger.info(f"Successfully applied migration: {migration_file.name}")
        
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise 