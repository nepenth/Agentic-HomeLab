#!/usr/bin/env python3
"""
Batch Email Embedding Generation Script

This script generates embeddings for all emails that don't have them yet.
It directly uses the semantic processing service and email embedding service
to process emails in batches, avoiding the worker event loop issues.
"""

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_session_context
from app.db.models.email import Email, EmailEmbedding
from app.services.semantic_processing_service import semantic_processing_service
from app.utils.logging import get_logger
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

logger = get_logger("email_embedding_generator")


class BatchEmbeddingGenerator:
    """Generates embeddings for emails in batches."""

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.processed_count = 0
        self.error_count = 0

    async def initialize_services(self) -> bool:
        """Initialize the semantic processing service."""
        try:
            await semantic_processing_service.initialize()
            logger.info(f"Semantic processing service initialized with model: {semantic_processing_service.embedding_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize semantic processing service: {e}")
            return False

    async def get_emails_without_embeddings(self, user_id: int, limit: int = None) -> List[Email]:
        """Get emails that don't have embeddings generated."""
        async with get_session_context() as db:
            # Subquery to get emails that already have embeddings
            existing_embeddings_subq = select(EmailEmbedding.email_id).subquery()

            # Query for emails without embeddings
            query = select(Email).where(
                and_(
                    Email.user_id == user_id,
                    Email.embeddings_generated == False,
                    Email.id.notin_(select(existing_embeddings_subq.c.email_id))
                )
            ).options(selectinload(Email.embeddings))

            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            emails = result.scalars().all()
            logger.info(f"Found {len(emails)} emails without embeddings")
            return list(emails)

    async def generate_embedding_for_email(self, email: Email) -> bool:
        """Generate embedding for a single email."""
        try:
            # Prepare text content for embedding
            content_parts = []
            if email.subject:
                content_parts.append(f"Subject: {email.subject}")
            if email.sender_name:
                content_parts.append(f"From: {email.sender_name}")
            if email.body_text:
                content_parts.append(f"Body: {email.body_text[:1000]}")  # Limit body length

            email_content = "\n".join(content_parts)

            if not email_content.strip():
                logger.warning(f"Email {email.id} has no content for embedding")
                return False

            # Generate embedding using semantic processing service
            embedding_vector = await semantic_processing_service.generate_embedding(
                email_content,
                model_name=semantic_processing_service.embedding_model
            )

            if not embedding_vector or len(embedding_vector) == 0:
                logger.error(f"Failed to generate embedding for email {email.id}")
                return False

            # Store embedding in database
            async with get_session_context() as db:
                email_embedding = EmailEmbedding(
                    email_id=email.id,
                    embedding_type="combined",  # Combined subject, sender, and body content
                    embedding_vector=embedding_vector,
                    model_name=semantic_processing_service.embedding_model,
                    content_hash=str(hash(email_content))
                )

                db.add(email_embedding)

                # Update email embeddings_generated flag
                email_obj = await db.get(Email, email.id)
                if email_obj:
                    email_obj.embeddings_generated = True

                await db.commit()
                logger.debug(f"Generated embedding for email {email.id} (subject: {email.subject[:50]}...)")
                return True

        except Exception as e:
            logger.error(f"Error generating embedding for email {email.id}: {e}")
            return False

    async def process_batch(self, emails: List[Email]) -> Dict[str, int]:
        """Process a batch of emails for embedding generation."""
        results = {"success": 0, "failed": 0}

        for email in emails:
            success = await self.generate_embedding_for_email(email)
            if success:
                results["success"] += 1
                self.processed_count += 1
            else:
                results["failed"] += 1
                self.error_count += 1

        return results

    async def generate_all_embeddings(self, user_id: int) -> Dict[str, Any]:
        """Generate embeddings for all emails without them."""
        logger.info("Starting batch embedding generation...")

        # Initialize services
        if not await self.initialize_services():
            return {"error": "Failed to initialize services"}

        start_time = datetime.now()
        total_processed = 0

        # Process emails in batches
        while True:
            emails = await self.get_emails_without_embeddings(user_id, self.batch_size)

            if not emails:
                logger.info("No more emails to process")
                break

            logger.info(f"Processing batch of {len(emails)} emails...")
            batch_results = await self.process_batch(emails)

            total_processed += len(emails)
            logger.info(f"Batch complete: {batch_results['success']} success, {batch_results['failed']} failed")
            logger.info(f"Total progress: {total_processed} emails processed, {self.processed_count} embeddings generated")

            # Add small delay to prevent overwhelming the system
            await asyncio.sleep(1)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "total_processed": total_processed,
            "embeddings_generated": self.processed_count,
            "errors": self.error_count,
            "duration_seconds": duration,
            "average_per_second": self.processed_count / duration if duration > 0 else 0
        }


async def main():
    """Main function to run the embedding generation."""
    if len(sys.argv) < 2:
        print("Usage: python generate_email_embeddings.py <user_id> [batch_size]")
        sys.exit(1)

    user_id = int(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    generator = BatchEmbeddingGenerator(batch_size=batch_size)

    try:
        results = await generator.generate_all_embeddings(user_id)

        if "error" in results:
            logger.error(f"Embedding generation failed: {results['error']}")
            sys.exit(1)
        else:
            logger.info("Embedding generation completed!")
            logger.info(f"Summary: {results}")
            print(f"""
Embedding Generation Complete!
===============================
Total Processed: {results['total_processed']} emails
Embeddings Generated: {results['embeddings_generated']}
Errors: {results['errors']}
Duration: {results['duration_seconds']:.2f} seconds
Average Rate: {results['average_per_second']:.2f} embeddings/sec
            """)

    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())