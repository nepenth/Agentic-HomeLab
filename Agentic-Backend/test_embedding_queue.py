
import asyncio
import sys
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from app.db.database import get_session_context
from app.db.models.email import Email, EmailAccount
from app.db.models.embedding_task import EmbeddingTask, EmbeddingTaskStatus
from app.services.email_embedding_service import email_embedding_service
from app.db.models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    async with get_session_context() as db:
        # 1. Setup: Get a user and account
        account_id = "a1228fe7-c3e2-4ad1-b90c-7fb561a2ecab"
        account = await db.get(EmailAccount, account_id)
        
        if not account:
            logger.error(f"Account {account_id} not found.")
            return
            
        user = await db.get(User, account.user_id)

        logger.info(f"Using User: {user.id}, Account: {account.id}")

        # 2. Create a test email
        test_email = Email(
            user_id=user.id,
            account_id=account.id,
            message_id=f"test-queue-{datetime.now().timestamp()}@example.com",
            subject="Test Embedding Queue",
            body_text="This is a test email for the embedding queue logic.",
            sender_email="test@example.com",
            folder_path="INBOX",
            embeddings_generated=False
        )
        db.add(test_email)
        await db.commit()
        await db.refresh(test_email)
        logger.info(f"Created test email: {test_email.id}")

        # 3. Test Enqueue
        logger.info("Testing _enqueue_missing_tasks...")
        await email_embedding_service._enqueue_missing_tasks(db, user.id)
        
        # Verify task created
        task = await db.scalar(select(EmbeddingTask).where(EmbeddingTask.email_id == test_email.id))
        if task:
            logger.info(f"Task created successfully: {task.id}, Status: {task.status}")
        else:
            logger.error("Failed to create task!")
            return

        # 4. Test Processing
        logger.info("Testing process_pending_emails...")
        stats = await email_embedding_service.process_pending_emails(db, user.id)
        logger.info(f"Processing stats: {stats}")

        # Verify task completed
        await db.refresh(task)
        await db.refresh(test_email)
        
        if task.status == EmbeddingTaskStatus.COMPLETED:
            logger.info("Task completed successfully!")
        else:
            logger.error(f"Task failed! Status: {task.status}, Error: {task.error_message}")

        if test_email.embeddings_generated:
            logger.info("Email marked as embeddings_generated=True")
        else:
            logger.error("Email NOT marked as embeddings_generated=True")

        # 5. Cleanup
        logger.info("Cleaning up...")
        await db.delete(task)
        await db.delete(test_email)
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
