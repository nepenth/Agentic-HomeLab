
import asyncio
import sys
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, delete
from app.db.database import get_session_context
from app.db.models.email import EmailAccount, EmailSyncHistory
from app.services.email_sync_service import email_sync_service
from app.db.models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    async with get_session_context() as db:
        # 1. Setup
        account_id = "a1228fe7-c3e2-4ad1-b90c-7fb561a2ecab"
        account = await db.get(EmailAccount, account_id)
        if not account:
            logger.error("Account not found")
            return

        logger.info("=== Testing Locking ===")
        # Simulate running sync
        account.sync_status = "running"
        # Create a "running" history record
        history = EmailSyncHistory(
            account_id=account.id,
            sync_type="manual",
            status="running",
            started_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        db.add(history)
        await db.commit()

        # Try sync - should fail
        logger.info("Attempting sync with active lock...")
        result = await email_sync_service.sync_account(db, account.id)
        if not result.success and "Sync already in progress" in str(result.error_message):
            logger.info("PASS: Lock prevented sync")
        else:
            logger.error(f"FAIL: Lock did not prevent sync. Result: {result}")

        # Simulate stale lock
        logger.info("Simulating stale lock...")
        history.last_updated = datetime.now(timezone.utc) - timedelta(hours=2)
        await db.commit()

        # Try sync - should succeed (or at least pass lock check)
        # Note: It might fail later due to connection issues, but we check error message
        logger.info("Attempting sync with stale lock...")
        result = await email_sync_service.sync_account(db, account.id)
        if result.success or "Sync already in progress" not in str(result.error_message):
            logger.info("PASS: Stale lock broken")
        else:
            logger.error(f"FAIL: Stale lock not broken. Result: {result}")

        # Cleanup lock test
        account.sync_status = "pending"
        await db.execute(delete(EmailSyncHistory).where(EmailSyncHistory.account_id == account.id))
        await db.commit()

        logger.info("=== Testing Circuit Breaker ===")
        # Insert 5 failed records
        for i in range(5):
            fail_hist = EmailSyncHistory(
                account_id=account.id,
                sync_type="manual",
                status="failed",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=i*5),
                completed_at=datetime.now(timezone.utc),
                error_message="Simulated failure"
            )
            db.add(fail_hist)
        await db.commit()

        # Try sync - should fail
        logger.info("Attempting sync with 5 recent failures...")
        result = await email_sync_service.sync_account(db, account.id)
        if not result.success and "Circuit breaker open" in str(result.error_message):
            logger.info("PASS: Circuit breaker prevented sync")
        else:
            logger.error(f"FAIL: Circuit breaker did not prevent sync. Result: {result}")

        # Cleanup CB test
        # Delete the simulated failures
        await db.execute(delete(EmailSyncHistory).where(EmailSyncHistory.error_message == "Simulated failure"))
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
