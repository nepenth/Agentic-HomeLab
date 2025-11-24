
import asyncio
from sqlalchemy import select
from app.db.database import get_session_context
from app.db.models.email import Email
from app.db.models.embedding_task import EmbeddingTask

async def main():
    async with get_session_context() as db:
        query = select(Email).where(Email.subject == "Test Embedding Queue").limit(1)
        result = await db.execute(query)
        email = result.scalar_one_or_none()
        
        if not email:
            print("Test email not found")
            return

        print(f"Email ID: {email.id}")
        print(f"Embeddings Generated: {email.embeddings_generated}")
        
        task_query = select(EmbeddingTask).where(EmbeddingTask.email_id == email.id)
        task_result = await db.execute(task_query)
        task = task_result.scalar_one_or_none()
        
        if task:
            print(f"Task Status: {task.status}")
            print(f"Task Attempts: {task.attempts}")
            print(f"Task Error: {task.error_message}")
        else:
            print("No task found")

if __name__ == "__main__":
    asyncio.run(main())
