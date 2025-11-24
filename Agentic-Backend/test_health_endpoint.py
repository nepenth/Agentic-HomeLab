
import asyncio
import logging
from app.db.database import get_session_context
from app.db.models.email import EmailAccount
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

        logger.info("Testing get_sync_health...")
        health = await email_sync_service.get_sync_health(db, account.user_id)
        
        logger.info(f"System Status: {health['system_status']}")
        for acc in health['accounts']:
            logger.info(f"Account {acc['email_address']}: {acc['status']}")
            logger.info(f"  Consecutive Failures: {acc['consecutive_failures']}")
            logger.info(f"  Circuit Breaker Open: {acc['circuit_breaker_open']}")
            logger.info(f"  Is Locked: {acc['is_locked']}")
            logger.info(f"  Lock Stale: {acc['lock_stale']}")

        if health['system_status'] in ["healthy", "unhealthy", "degraded"]:
            logger.info("PASS: Health check returned valid status")
        else:
            logger.error("FAIL: Invalid system status")

if __name__ == "__main__":
    asyncio.run(main())
