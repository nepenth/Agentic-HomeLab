
import asyncio
import sys
from sqlalchemy import select, func, or_
from app.db.database import get_session_context
from app.db.models.email import Email

async def main():
    async with get_session_context() as db:
        query = select(func.count(Email.id)).where(
            or_(
                Email.embeddings_generated == False,
                Email.embeddings_generated.is_(None)
            )
        )
        result = await db.execute(query)
        count = result.scalar()
        print(f"Pending embeddings: {count}")

if __name__ == "__main__":
    asyncio.run(main())
