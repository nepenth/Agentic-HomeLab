#!/usr/bin/env python3
"""Script to check database tables."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import get_async_session
from sqlalchemy import text


async def check_tables():
    """Check what tables exist in the database."""
    async for session in get_async_session():
        try:
            result = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = result.fetchall()

            print("Database tables:")
            for table in tables:
                print(f"  - {table[0]}")

            # Also check if alembic_version table exists
            result = await session.execute(
                text("SELECT version_num FROM alembic_version")
            )
            version = result.fetchone()
            if version:
                print(f"\nAlembic version: {version[0]}")
            else:
                print("\nNo alembic version found")

        finally:
            await session.close()
            break


if __name__ == "__main__":
    asyncio.run(check_tables())