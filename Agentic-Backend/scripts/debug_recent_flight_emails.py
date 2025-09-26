#!/usr/bin/env python3
"""
Debug Recent Flight Emails

This script specifically looks for recent flight-related emails to understand
why the San Diego Delta flight email from 9/2/25 isn't being found.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_session_context
from app.db.models.email import Email, EmailEmbedding
from app.services.email_embedding_service import EmailEmbeddingService
from sqlalchemy import select, and_, or_, func, text, desc
from sqlalchemy.orm import selectinload
from app.utils.logging import get_logger

logger = get_logger("recent_flight_debug")


async def find_recent_flight_emails(user_id: int, days_back: int = 60) -> List[Email]:
    """Find recent emails containing flight/travel keywords."""
    async with get_session_context() as db:
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Search for recent emails with flight-related keywords
        flight_keywords = ['delta', 'flight', 'airline', 'boarding', 'itinerary', 'san diego', 'trip']
        conditions = []

        for keyword in flight_keywords:
            conditions.extend([
                Email.subject.ilike(f'%{keyword}%'),
                Email.body_text.ilike(f'%{keyword}%'),
                Email.body_html.ilike(f'%{keyword}%')
            ])

        query = select(Email).where(
            and_(
                Email.user_id == user_id,
                Email.received_at >= cutoff_date,
                or_(*conditions)
            )
        ).order_by(desc(Email.received_at))

        result = await db.execute(query)
        return result.scalars().all()


async def check_email_embeddings(email: Email) -> Dict[str, Any]:
    """Check if an email has embeddings and their details."""
    async with get_session_context() as db:
        embeddings_query = select(EmailEmbedding).where(
            EmailEmbedding.email_id == email.id
        )
        result = await db.execute(embeddings_query)
        embeddings = result.scalars().all()

        return {
            'email_id': email.id,
            'subject': email.subject,
            'received_at': email.received_at,
            'embeddings_generated': email.embeddings_generated,
            'embeddings_count': len(embeddings),
            'embedding_types': [emb.embedding_type for emb in embeddings],
            'embedding_models': [emb.model_name for emb in embeddings],
            'body_preview': (email.body_text or '')[:500] if email.body_text else 'No body text'
        }


async def test_specific_query_similarity(user_id: int, email_id: str, query: str) -> float:
    """Test similarity score for a specific email against the query."""
    embedding_service = EmailEmbeddingService()

    async with get_session_context() as db:
        # Get the specific email
        email_query = select(Email).where(
            and_(Email.id == email_id, Email.user_id == user_id)
        )
        result = await db.execute(email_query)
        email = result.scalar_one_or_none()

        if not email:
            return 0.0

        # Run similarity search and find this specific email's score
        similarity_results = await embedding_service.search_similar_emails(
            db=db,
            query_text=query,
            user_id=user_id,
            limit=100,  # Get many results to find our target email
            similarity_threshold=0.01,  # Very low threshold
            temporal_boost=0.0,  # No temporal boost for pure similarity
            importance_boost=0.0  # No importance boost for pure similarity
        )

        # Find our specific email in the results
        for result_email, score in similarity_results:
            if result_email.id == email_id:
                return score

        return 0.0  # Email not found in similarity results


async def main():
    """Main debugging function for recent flight emails."""
    if len(sys.argv) < 2:
        print("Usage: python debug_recent_flight_emails.py <user_id>")
        sys.exit(1)

    user_id = int(sys.argv[1])
    query = "flight itinerary San Diego Delta"

    print(f"🔍 Debugging Recent Flight Emails for User {user_id}")
    print("=" * 60)

    try:
        # 1. Find recent flight-related emails
        print("\n📧 Finding recent flight-related emails...")
        recent_emails = await find_recent_flight_emails(user_id, days_back=60)
        print(f"Found {len(recent_emails)} recent flight-related emails")

        # 2. Check each email's embeddings and content
        print("\n🔍 Analyzing recent flight emails:")
        september_emails = []

        for email in recent_emails[:20]:  # Check first 20
            email_info = await check_email_embeddings(email)

            # Look for September 2025 emails specifically
            if email.received_at and email.received_at.month == 9 and email.received_at.year == 2025:
                september_emails.append(email)
                print(f"\n📅 SEPTEMBER 2025 EMAIL FOUND:")
                print(f"  ID: {email_info['email_id']}")
                print(f"  Subject: {email_info['subject']}")
                print(f"  Date: {email_info['received_at']}")
                print(f"  Has Embeddings: {email_info['embeddings_generated']}")
                print(f"  Embedding Count: {email_info['embeddings_count']}")
                print(f"  Embedding Types: {email_info['embedding_types']}")
                print(f"  Body Preview: {email_info['body_preview'][:200]}...")

                # Test similarity for this email
                similarity_score = await test_specific_query_similarity(
                    user_id, email.id, query
                )
                print(f"  Similarity Score: {similarity_score:.4f}")

        # 3. Look specifically for Delta or San Diego in September emails
        print(f"\n✈️ Found {len(september_emails)} September 2025 emails")

        delta_emails = []
        san_diego_emails = []

        for email in september_emails:
            subject_lower = (email.subject or '').lower()
            body_lower = (email.body_text or '').lower()

            if 'delta' in subject_lower or 'delta' in body_lower:
                delta_emails.append(email)
                print(f"🔺 DELTA EMAIL: {email.subject} [{email.received_at}]")

            if 'san diego' in subject_lower or 'san diego' in body_lower:
                san_diego_emails.append(email)
                print(f"🌴 SAN DIEGO EMAIL: {email.subject} [{email.received_at}]")

        # 4. Summary
        print(f"\n📊 SUMMARY:")
        print(f"  Total recent flight emails: {len(recent_emails)}")
        print(f"  September 2025 emails: {len(september_emails)}")
        print(f"  Delta-related emails: {len(delta_emails)}")
        print(f"  San Diego-related emails: {len(san_diego_emails)}")

        if not september_emails:
            print(f"\n❌ No September 2025 emails found!")
            print(f"   This suggests the email might not exist or wasn't synced")
        elif not delta_emails and not san_diego_emails:
            print(f"\n❌ No Delta or San Diego emails found in September 2025")
            print(f"   The email content might not contain these keywords")
        else:
            print(f"\n✅ Found relevant emails - similarity scoring may be the issue")

    except Exception as e:
        logger.error(f"Error during debug analysis: {e}")
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)