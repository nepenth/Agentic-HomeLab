
import asyncio
import sys
from sqlalchemy import select
from app.db.database import get_session_context
from app.db.models.email import EmailAccount, EmailSyncHistory

async def main():
    async with get_session_context() as db:
        print("--- Email Accounts ---")
        query = select(EmailAccount)
        result = await db.execute(query)
        accounts = result.scalars().all()
        for account in accounts:
            print(f"ID: {account.id}")
            print(f"Email: {account.email_address}")
            print(f"Sync Status: {account.sync_status}")
            print(f"Last Sync: {account.last_sync_at}")
            print(f"Next Sync: {account.next_sync_at}")
            print(f"Auto Sync: {account.auto_sync_enabled}")
            print(f"Last Error: {account.last_error}")
            print("------------------------")

        print("\n--- Recent Sync History (Last 5) ---")
        history_query = select(EmailSyncHistory).order_by(EmailSyncHistory.started_at.desc()).limit(5)
        result = await db.execute(history_query)
        history = result.scalars().all()
        for h in history:
            print(f"ID: {h.id}")
            print(f"Account ID: {h.account_id}")
            print(f"Status: {h.status}")
            print(f"Started: {h.started_at}")
            print(f"Completed: {h.completed_at}")
            print(f"Last Updated: {getattr(h, 'last_updated', 'N/A')}")
            print(f"Emails Processed: {h.emails_processed}")
            print(f"Error: {h.error_message}")
            print("------------------------")

if __name__ == "__main__":
    asyncio.run(main())
