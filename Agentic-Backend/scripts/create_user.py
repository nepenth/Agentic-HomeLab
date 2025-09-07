#!/usr/bin/env python3
"""Script to create a user in the database."""

import asyncio
import sys
import os
from pathlib import Path
import socket

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.models.user import User
from app.utils.auth import get_password_hash
from app.config import settings


def get_database_url():
    """Get database URL, with fallback for Docker hostnames."""
    original_url = settings.database_url

    # If running inside Docker container, use the original URL
    # If running on host, replace db:5432 with localhost:5432
    if 'db:5432' in original_url:
        # Check if we're running inside Docker by checking for /.dockerenv file
        if os.path.exists('/.dockerenv'):
            print(f"Running inside Docker container, using original URL: {original_url}")
            return original_url
        else:
            fallback_url = original_url.replace('db:5432', 'localhost:5432')
            print(f"Running on host, using localhost fallback: {fallback_url}")
            return fallback_url

    return original_url


async def create_user(username: str, email: str, password: str, is_superuser: bool = False):
    """Create a new user."""
    database_url = get_database_url()
    
    # Create our own engine and session for this script
    engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_factory() as db:
        try:
            # Check if user already exists
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.username == username))
            existing_user = result.scalars().first()
            
            if existing_user:
                print(f"User '{username}' already exists!")
                return False
            
            # Create new user
            hashed_password = get_password_hash(password)
            new_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_superuser=is_superuser,
                is_active=True
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            print(f"User '{username}' created successfully with ID: {new_user.id}")
            return True
        finally:
            await engine.dispose()


async def main():
    """Main function to create a user."""
    if len(sys.argv) < 4:
        print("Usage: python scripts/create_user.py <username> <email> <password> [--superuser]")
        print("")
        print("Examples:")
        print("  python scripts/create_user.py john john@example.com mypassword123")
        print("  python scripts/create_user.py admin admin@example.com adminpass123 --superuser")
        print("")
        print("Note: Run this script from the project root directory")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    is_superuser = "--superuser" in sys.argv
    
    print(f"Creating {'superuser' if is_superuser else 'user'}: {username} ({email})")
    
    try:
        await create_user(username, email, password, is_superuser)
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this script from the project root directory")
        print("and that all dependencies are installed (pip install -r requirements.txt)")
        sys.exit(1)
    except socket.gaierror as e:
        print(f"Database connection error: {e}")
        print("This usually means the database hostname cannot be resolved.")
        print("")
        print("Solutions:")
        print("1. If using Docker, make sure PostgreSQL is running:")
        print("   docker-compose up -d db")
        print("")
        print("2. Or update your .env file to use localhost:")
        print("   DATABASE_URL=postgresql+asyncpg://postgres:secret@localhost:5432/ai_db")
        print("")
        print("3. Or run this script inside the Docker container:")
        print("   docker-compose exec app python scripts/create_user.py ...")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())