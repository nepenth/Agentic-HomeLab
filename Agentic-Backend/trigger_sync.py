
import asyncio
import sys
import logging
from app.db.database import get_session_context
from app.services.email_sync_service import email_sync_service

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    account_id = "a1228fe7-c3e2-4ad1-b90c-7fb561a2ecab"
    print(f"Triggering sync for account {account_id}...")
    
    async with get_session_context() as db:
        try:
            result = await email_sync_service.sync_account(db, account_id)
            print(f"Sync Result: {result}")
        except Exception as e:
            print(f"Sync Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
