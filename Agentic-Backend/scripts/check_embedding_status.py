#!/usr/bin/env python3
"""
Check Email Embedding Generation Status

This script provides detailed status on embedding generation progress.
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_session_context
from app.db.models.email import Email, EmailEmbedding
from sqlalchemy import select, func, and_
from app.utils.logging import get_logger

logger = get_logger("embedding_status_checker")


async def get_embedding_status(user_id: int) -> Dict[str, Any]:
    """Get comprehensive embedding generation status."""
    async with get_session_context() as db:
        # Count total emails
        total_emails_result = await db.execute(
            select(func.count(Email.id)).where(Email.user_id == user_id)
        )
        total_emails = total_emails_result.scalar()

        # Count emails with embeddings_generated = True
        emails_with_flag_result = await db.execute(
            select(func.count(Email.id)).where(
                and_(Email.user_id == user_id, Email.embeddings_generated == True)
            )
        )
        emails_with_flag = emails_with_flag_result.scalar()

        # Count actual embedding records
        actual_embeddings_result = await db.execute(
            select(func.count(EmailEmbedding.id))
            .select_from(EmailEmbedding)
            .join(Email, EmailEmbedding.email_id == Email.id)
            .where(Email.user_id == user_id)
        )
        actual_embeddings = actual_embeddings_result.scalar()

        # Count emails without embeddings
        emails_without_embeddings_result = await db.execute(
            select(func.count(Email.id)).where(
                and_(
                    Email.user_id == user_id,
                    Email.embeddings_generated == False
                )
            )
        )
        emails_without_embeddings = emails_without_embeddings_result.scalar()

        # Get latest embedding info
        latest_embedding_result = await db.execute(
            select(EmailEmbedding.created_at, EmailEmbedding.model_name)
            .select_from(EmailEmbedding)
            .join(Email, EmailEmbedding.email_id == Email.id)
            .where(Email.user_id == user_id)
            .order_by(EmailEmbedding.created_at.desc())
            .limit(1)
        )
        latest_embedding = latest_embedding_result.first()

        return {
            "total_emails": total_emails,
            "emails_with_embeddings_flag": emails_with_flag,
            "actual_embedding_records": actual_embeddings,
            "emails_without_embeddings": emails_without_embeddings,
            "completion_percentage": (actual_embeddings / total_emails * 100) if total_emails > 0 else 0,
            "latest_embedding_created": latest_embedding.created_at if latest_embedding else None,
            "embedding_model": latest_embedding.model_name if latest_embedding else None,
            "generation_complete": emails_without_embeddings == 0
        }


async def main():
    """Main function to check embedding status."""
    if len(sys.argv) < 2:
        print("Usage: python check_embedding_status.py <user_id>")
        sys.exit(1)

    user_id = int(sys.argv[1])

    try:
        status = await get_embedding_status(user_id)

        print(f"""
Email Embedding Generation Status
=================================
User ID: {user_id}

📊 Overview:
  Total Emails: {status['total_emails']:,}
  Embedding Records: {status['actual_embedding_records']:,}
  Completion: {status['completion_percentage']:.1f}%

📈 Progress:
  Emails with embeddings: {status['emails_with_embeddings_flag']:,}
  Emails without embeddings: {status['emails_without_embeddings']:,}

🤖 Model Info:
  Embedding Model: {status['embedding_model'] or 'N/A'}
  Latest Embedding: {status['latest_embedding_created'] or 'None'}

✅ Status: {'COMPLETE' if status['generation_complete'] else 'IN PROGRESS'}
        """)

        if not status['generation_complete']:
            remaining = status['emails_without_embeddings']
            print(f"⏳ {remaining:,} emails still need embeddings")

        return 0 if status['generation_complete'] else 1

    except Exception as e:
        logger.error(f"Error checking embedding status: {e}")
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)