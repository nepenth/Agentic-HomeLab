#!/usr/bin/env python3
"""Script to set up the database tables."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import create_tables, engine
from app.db.models import *  # Import all models to ensure they're registered


async def setup_database():
    """Create all database tables."""
    print("Setting up database tables...")
    
    try:
        await create_tables()
        print("✅ Database tables created successfully!")
        
        # Test connection
        from sqlalchemy import text
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ Connected to PostgreSQL: {version[0]}")
            
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False
    
    return True


async def main():
    """Main function."""
    print("Database Setup Script")
    print("=" * 50)
    
    success = await setup_database()
    
    if success:
        print("\n✅ Database setup complete!")
        print("You can now run: python scripts/create_user.py ...")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())