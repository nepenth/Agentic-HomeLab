#!/usr/bin/env python3
"""
Database initialization script.
Creates tables and runs initial setup.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.db.database import engine, Base
from app.db.models import *  # Import all models
from app.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("init_db")


async def create_database():
    """Create database tables."""
    try:
        logger.info("Creating database tables...")
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def setup_initial_data():
    """Set up initial data if needed."""
    try:
        logger.info("Setting up initial data...")
        
        # Future: Add initial agents, configurations, etc.
        
        logger.info("Initial data setup completed!")
        
    except Exception as e:
        logger.error(f"Failed to setup initial data: {e}")
        raise


async def main():
    """Main initialization function."""
    logger.info(f"Initializing database for {settings.app_name}")
    logger.info(f"Database URL: {settings.database_url}")
    
    try:
        await create_database()
        await setup_initial_data()
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())