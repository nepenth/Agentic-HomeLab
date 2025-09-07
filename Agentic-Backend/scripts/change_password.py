#!/usr/bin/env python3
"""Script to change a user's password."""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session_context
from app.db.models.user import User
from app.utils.auth import get_password_hash, get_user_by_username
import getpass


async def change_password(username: str, new_password: str):
    """Change a user's password."""
    async with get_session_context() as db:
        # Find the user
        user = await get_user_by_username(db, username)
        
        if not user:
            print(f"User '{username}' not found!")
            return False
        
        # Change password
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        await db.refresh(user)
        
        print(f"Password changed successfully for user '{username}' (ID: {user.id})")
        return True


async def main():
    """Main function to change a user's password."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/change_password.py <username> [new_password]")
        print("")
        print("Examples:")
        print("  python scripts/change_password.py nepenthe mynewpassword123")
        print("  python scripts/change_password.py nepenthe  # Will prompt for password")
        print("")
        print("Note: Run this script from the project root directory")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # Get password from command line or prompt securely
    if len(sys.argv) >= 3:
        new_password = sys.argv[2]
        print(f"Changing password for user: {username}")
    else:
        print(f"Changing password for user: {username}")
        new_password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm new password: ")
        
        if new_password != confirm_password:
            print("❌ Passwords do not match!")
            sys.exit(1)
    
    if len(new_password) < 6:
        print("❌ Password must be at least 6 characters long!")
        sys.exit(1)
    
    try:
        await change_password(username, new_password)
    except Exception as e:
        print(f"❌ Error changing password: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())