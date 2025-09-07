#!/usr/bin/env python3
"""Script to check users in the database."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import get_async_session
from sqlalchemy import text


async def check_users():
    """Check what users exist in the database."""
    async for session in get_async_session():
        try:
            result = await session.execute(
                text("SELECT id, username, email, is_active, is_superuser, created_at FROM users ORDER BY created_at DESC")
            )
            users = result.fetchall()

            if users:
                print(f"Found {len(users)} user(s) in the database:")
                print("-" * 80)
                print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Active':<8} {'Superuser':<10} {'Created At'}")
                print("-" * 80)
                for user in users:
                    print(f"{user[0]:<5} {user[1]:<20} {user[2]:<30} {user[3]:<8} {user[4]:<10} {user[5]}")
            else:
                print("No users found in the database.")

        except Exception as e:
            print(f"Error querying users: {e}")
        finally:
            await session.close()
            break


if __name__ == "__main__":
    asyncio.run(check_users())