import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import asyncpg
from ..config import Config
from ..utils.database_migration import run_migrations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.config = Config()

    async def connect(self) -> None:
        """Establish database connection"""
        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.config.DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection established successfully")
            
            # Run migrations on connection
            await self.run_migrations()
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def close(self) -> None:
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    async def run_migrations(self) -> None:
        """Run database migrations"""
        try:
            await run_migrations(self.pool)
            logger.info("Database migrations completed successfully")
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise

    async def execute(self, query: str, *args) -> Any:
        """Execute a database query"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        return await self.pool.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """Fetch results from a database query"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        return await self.pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row from a database query"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        return await self.pool.fetchrow(query, *args)

# Create a global database instance
db = Database()

# Initialize database connection
async def init_db():
    await db.connect()

# Close database connection
async def close_db():
    await db.close() 