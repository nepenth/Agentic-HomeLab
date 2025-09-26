#!/usr/bin/env python3
"""
Debug San Diego Flight Search Issue

This script tests the specific search query for San Diego flight emails
to understand why they're not being found.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_session_context
from app.db.models.email import Email, EmailEmbedding
from app.services.email_embedding_service import EmailEmbeddingService
from app.services.enhanced_email_chat_service import EnhancedEmailChatService
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from app.utils.logging import get_logger

logger = get_logger("san_diego_search_debug")


async def search_emails_by_keywords(user_id: int, keywords: List[str]) -> List[Email]:
    """Search emails by keywords in subject and body."""
    async with get_session_context() as db:
        # Build keyword search conditions
        keyword_conditions = []
        for keyword in keywords:
            keyword_conditions.append(
                or_(
                    Email.subject.ilike(f'%{keyword}%'),
                    Email.body_text.ilike(f'%{keyword}%'),
                    Email.body_html.ilike(f'%{keyword}%')
                )
            )

        # Combine all keyword conditions with OR
        where_condition = and_(
            Email.user_id == user_id,
            or_(*keyword_conditions)
        )

        query = select(Email).where(where_condition).order_by(Email.sent_at.desc())
        result = await db.execute(query)
        return result.scalars().all()


async def test_semantic_search(user_id: int, query: str) -> List[tuple]:
    """Test semantic search for the query."""
    embedding_service = EmailEmbeddingService()

    async with get_session_context() as db:
        results = await embedding_service.search_similar_emails(
            db=db,
            query_text=query,
            user_id=user_id,
            limit=20,
            similarity_threshold=0.05,  # Very low threshold for debugging
            temporal_boost=0.2,
            importance_boost=0.3
        )
        return results


async def test_enhanced_chat_search(user_id: int, query: str) -> Dict[str, Any]:
    """Test the enhanced chat service search."""
    chat_service = EnhancedEmailChatService()

    async with get_session_context() as db:
        response = await chat_service.chat_with_email_context(
            db=db,
            user_id=user_id,
            message=query + " (fresh test)",  # Add suffix to avoid cache
            include_email_search=True,
            max_days_back=1095  # Look back 3 years
        )
        return response


async def analyze_embeddings_status(user_id: int) -> Dict[str, Any]:
    """Analyze embedding generation status."""
    async with get_session_context() as db:
        # Count total emails
        total_result = await db.execute(
            select(func.count(Email.id)).where(Email.user_id == user_id)
        )
        total_emails = total_result.scalar()

        # Count emails with embeddings
        with_embeddings_result = await db.execute(
            select(func.count(Email.id)).where(
                and_(
                    Email.user_id == user_id,
                    Email.embeddings_generated == True
                )
            )
        )
        with_embeddings = with_embeddings_result.scalar()

        # Count actual embedding records
        embedding_records_result = await db.execute(
            select(func.count(EmailEmbedding.id))
            .join(Email, EmailEmbedding.email_id == Email.id)
            .where(Email.user_id == user_id)
        )
        embedding_records = embedding_records_result.scalar()

        # Get sample of emails to check content
        sample_emails_result = await db.execute(
            select(Email.id, Email.subject, Email.sent_at, Email.embeddings_generated)
            .where(Email.user_id == user_id)
            .order_by(Email.sent_at.desc())
            .limit(10)
        )
        sample_emails = sample_emails_result.all()

        return {
            "total_emails": total_emails,
            "emails_with_embeddings": with_embeddings,
            "actual_embedding_records": embedding_records,
            "sample_recent_emails": sample_emails
        }


async def main():
    """Main debugging function."""
    if len(sys.argv) < 2:
        print("Usage: python debug_san_diego_search.py <user_id>")
        sys.exit(1)

    user_id = int(sys.argv[1])
    search_query = "Please help me find an email with my flight itinerary for a trip to San Diego and back"

    print(f"🔍 Debugging San Diego Flight Search for User {user_id}")
    print("=" * 60)

    try:
        # 1. Check embeddings status
        print("\n📊 Checking embeddings status...")
        embedding_status = await analyze_embeddings_status(user_id)
        print(f"Total emails: {embedding_status['total_emails']}")
        print(f"Emails with embeddings: {embedding_status['emails_with_embeddings']}")
        print(f"Actual embedding records: {embedding_status['actual_embedding_records']}")

        # Show sample recent emails
        print("\n📧 Recent emails sample:")
        for email_id, subject, sent_at, has_embeddings in embedding_status['sample_recent_emails']:
            print(f"  {email_id}: {subject[:50]}... [{sent_at}] Embeddings: {has_embeddings}")

        # 2. Test keyword search
        print("\n🔤 Testing keyword search...")
        keywords = ["San Diego", "flight", "itinerary", "Delta", "airline", "trip"]
        keyword_results = await search_emails_by_keywords(user_id, keywords)
        print(f"Found {len(keyword_results)} emails with keywords")

        for email in keyword_results[:5]:  # Show first 5
            print(f"  ✉️  {email.subject} [{email.sent_at}]")
            if hasattr(email, 'body_text') and email.body_text:
                preview = email.body_text[:200].replace('\n', ' ')
                print(f"     Preview: {preview}...")

        # 3. Test semantic search directly
        print("\n🧠 Testing semantic search...")
        semantic_results = await test_semantic_search(user_id, search_query)
        print(f"Found {len(semantic_results)} semantically similar emails")

        for email, score in semantic_results[:5]:  # Show first 5
            print(f"  ✉️  {email.subject} [Score: {score:.3f}] [{email.sent_at}]")

        # 4. Test enhanced chat service
        print("\n💬 Testing enhanced chat service...")
        chat_response = await test_enhanced_chat_search(user_id, search_query)

        print(f"Chat response length: {len(chat_response.get('response', ''))}")
        print(f"Email references: {len(chat_response.get('email_references', []))}")
        print(f"Emails searched: {chat_response.get('metadata', {}).get('emails_searched', 0)}")

        if chat_response.get('email_references'):
            print("Referenced emails:")
            for ref in chat_response['email_references'][:3]:
                print(f"  ✉️  {ref.get('subject', 'No subject')}")

        # 5. Manual check for specific flight terms
        print("\n🔍 Manual search for flight-related terms...")
        flight_keywords = ["flight", "airline", "boarding", "departure", "arrival", "terminal", "gate"]
        flight_results = await search_emails_by_keywords(user_id, flight_keywords)
        print(f"Found {len(flight_results)} emails with flight-related terms")

        print("\n✅ Debug analysis complete!")

        if not keyword_results and not semantic_results:
            print("\n❌ ISSUE: No emails found with San Diego or flight keywords")
            print("   This suggests either:")
            print("   1. No such emails exist in the database")
            print("   2. Content is not being indexed properly")
            print("   3. Search terms don't match email content")
        elif keyword_results and not semantic_results:
            print("\n⚠️  ISSUE: Keyword search works but semantic search doesn't")
            print("   This suggests embedding generation or similarity search issues")
        else:
            print("\n✅ Both searches found results - may need to check similarity thresholds")

    except Exception as e:
        logger.error(f"Error during debug analysis: {e}")
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)