"""
Email Semantic Search Service for intelligent email search and retrieval.

This service provides advanced semantic search capabilities for emails including:
- Natural language search across email content
- Semantic similarity matching
- Email thread-aware search
- Multi-modal search (text + metadata)
- Search result ranking and filtering
- Query expansion and refinement
"""

import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import UUID

from app.services.semantic_processing_service import semantic_processing_service
from app.services.email_analysis_service import EmailAnalysis
from app.db.models.content import ContentItem, ContentEmbedding
from app.db.models.task import Task
from app.utils.logging import get_logger

logger = get_logger("email_semantic_search")


@dataclass
class EmailSearchQuery:
    """Represents a semantic search query for emails."""
    query_text: str
    user_id: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 20
    offset: int = 0
    include_threads: bool = True
    search_type: str = "semantic"  # semantic, keyword, hybrid

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query_text": self.query_text,
            "user_id": self.user_id,
            "filters": self.filters,
            "limit": self.limit,
            "offset": self.offset,
            "include_threads": self.include_threads,
            "search_type": self.search_type
        }


@dataclass
class EmailSearchResult:
    """Represents a single email search result."""
    content_item_id: str
    email_id: str
    subject: str
    sender: str
    content_preview: str
    relevance_score: float
    importance_score: Optional[float]
    categories: List[str]
    sent_date: datetime
    has_attachments: bool
    thread_id: Optional[str]
    matched_terms: List[str]
    search_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "content_item_id": self.content_item_id,
            "email_id": self.email_id,
            "subject": self.subject,
            "sender": self.sender,
            "content_preview": self.content_preview,
            "relevance_score": self.relevance_score,
            "importance_score": self.importance_score,
            "categories": self.categories,
            "sent_date": self.sent_date.isoformat(),
            "has_attachments": self.has_attachments,
            "thread_id": self.thread_id,
            "matched_terms": self.matched_terms,
            "search_metadata": self.search_metadata
        }


@dataclass
class EmailSearchResponse:
    """Complete search response with results and metadata."""
    query: EmailSearchQuery
    results: List[EmailSearchResult]
    total_count: int
    search_time_ms: float
    facets: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "query": self.query.to_dict(),
            "results": [result.to_dict() for result in self.results],
            "total_count": self.total_count,
            "search_time_ms": self.search_time_ms,
            "facets": self.facets,
            "suggestions": self.suggestions
        }


@dataclass
class EmailThreadResult:
    """Represents an email thread with related messages."""
    thread_id: str
    subject: str
    participants: List[str]
    message_count: int
    latest_message_date: datetime
    importance_score: float
    emails: List[EmailSearchResult]
    thread_summary: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "thread_id": self.thread_id,
            "subject": self.subject,
            "participants": self.participants,
            "message_count": self.message_count,
            "latest_message_date": self.latest_message_date.isoformat(),
            "importance_score": self.importance_score,
            "emails": [email.to_dict() for email in self.emails],
            "thread_summary": self.thread_summary
        }


class EmailSemanticSearch:
    """Service for semantic search across email content."""

    def __init__(self):
        self.logger = get_logger("email_semantic_search")
        self.semantic_service = semantic_processing_service

        # Search configuration
        self.max_results = 100
        self.min_relevance_threshold = 0.1
        self.thread_similarity_threshold = 0.8
        self.query_expansion_enabled = True

        # Caching for performance
        self.query_cache = {}
        self.cache_ttl_seconds = 300  # 5 minutes

    async def search_emails(
        self,
        query: EmailSearchQuery,
        db_session: Any = None
    ) -> EmailSearchResponse:
        """
        Perform semantic search across emails.

        Args:
            query: Search query with filters and parameters
            db_session: Database session for queries

        Returns:
            EmailSearchResponse with results and metadata
        """
        start_time = datetime.now()

        try:
            # Expand query if enabled
            expanded_queries = await self._expand_query(query.query_text) if self.query_expansion_enabled else [query.query_text]

            # Perform search based on type
            if query.search_type == "semantic":
                results = await self._semantic_search(expanded_queries, query, db_session)
            elif query.search_type == "keyword":
                results = await self._keyword_search(expanded_queries, query, db_session)
            else:  # hybrid
                semantic_results = await self._semantic_search(expanded_queries, query, db_session)
                keyword_results = await self._keyword_search(expanded_queries, query, db_session)
                results = self._merge_hybrid_results(semantic_results, keyword_results)

            # Apply filters
            filtered_results = self._apply_filters(results, query.filters)

            # Sort by relevance
            filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)

            # Apply pagination
            paginated_results = filtered_results[query.offset:query.offset + query.limit]

            # Generate facets and suggestions
            facets = await self._generate_facets(filtered_results, db_session)
            suggestions = await self._generate_suggestions(query.query_text, filtered_results)

            # Include thread information if requested
            if query.include_threads:
                paginated_results = await self._enrich_with_threads(paginated_results, db_session)

            search_time = (datetime.now() - start_time).total_seconds() * 1000

            response = EmailSearchResponse(
                query=query,
                results=paginated_results,
                total_count=len(filtered_results),
                search_time_ms=search_time,
                facets=facets,
                suggestions=suggestions
            )

            self.logger.info(f"Email search completed: {len(paginated_results)} results in {search_time:.2f}ms")
            return response

        except Exception as e:
            self.logger.error(f"Email search failed: {e}")
            search_time = (datetime.now() - start_time).total_seconds() * 1000

            return EmailSearchResponse(
                query=query,
                results=[],
                total_count=0,
                search_time_ms=search_time,
                facets={},
                suggestions=[]
            )

    async def _semantic_search(
        self,
        queries: List[str],
        query: EmailSearchQuery,
        db_session: Any = None
    ) -> List[EmailSearchResult]:
        """Perform semantic search using vector similarity."""
        try:
            # Generate embedding for the main query
            main_embedding = await self.semantic_service.generate_embedding(queries[0])

            # Search for similar content using semantic search
            search_results = await self.semantic_service.semantic_search(
                query=queries[0],
                top_k=self.max_results * 2,  # Get more for filtering
                threshold=self.min_relevance_threshold
            )

            results = []
            for search_result in search_results:
                # Get email details from database
                email_result = await self._get_email_details(
                    search_result.content_id,
                    search_result.similarity_score,
                    queries,
                    db_session
                )
                if email_result:
                    results.append(email_result)

            return results

        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return []

    async def _keyword_search(
        self,
        queries: List[str],
        query: EmailSearchQuery,
        db_session: Any = None
    ) -> List[EmailSearchResult]:
        """Perform keyword-based search."""
        try:
            # Build search terms from queries
            search_terms = []
            for q in queries:
                # Extract keywords and phrases
                terms = re.findall(r'\b\w+\b', q.lower())
                search_terms.extend(terms)

            # Remove duplicates and common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            search_terms = list(set(term for term in search_terms if term not in stop_words and len(term) > 2))

            if not search_terms:
                return []

            # Search database for emails containing these terms
            # This would be implemented with actual database queries
            results = await self._database_keyword_search(search_terms, query, db_session)

            return results

        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []

    async def _database_keyword_search(
        self,
        search_terms: List[str],
        query: EmailSearchQuery,
        db_session: Any = None
    ) -> List[EmailSearchResult]:
        """Search emails in database using keywords."""
        # This is a placeholder - actual implementation would query the database
        # for emails containing the search terms in subject, content, etc.
        return []

    def _merge_hybrid_results(
        self,
        semantic_results: List[EmailSearchResult],
        keyword_results: List[EmailSearchResult]
    ) -> List[EmailSearchResult]:
        """Merge semantic and keyword search results."""
        # Combine results, boosting scores for items that appear in both
        result_map = {}

        # Add semantic results
        for result in semantic_results:
            result_map[result.content_item_id] = result

        # Add/merge keyword results
        for result in keyword_results:
            if result.content_item_id in result_map:
                # Boost score for items that match both searches
                existing = result_map[result.content_item_id]
                existing.relevance_score = min(1.0, existing.relevance_score + result.relevance_score * 0.3)
                existing.matched_terms.extend(result.matched_terms)
                existing.matched_terms = list(set(existing.matched_terms))
            else:
                result_map[result.content_item_id] = result

        return list(result_map.values())

    def _apply_filters(
        self,
        results: List[EmailSearchResult],
        filters: Dict[str, Any]
    ) -> List[EmailSearchResult]:
        """Apply search filters to results."""
        filtered_results = results

        # Date range filter
        if "date_from" in filters:
            date_from = datetime.fromisoformat(filters["date_from"].replace('Z', '+00:00'))
            filtered_results = [r for r in filtered_results if r.sent_date >= date_from]

        if "date_to" in filters:
            date_to = datetime.fromisoformat(filters["date_to"].replace('Z', '+00:00'))
            filtered_results = [r for r in filtered_results if r.sent_date <= date_to]

        # Sender filter
        if "sender" in filters:
            sender_filter = filters["sender"].lower()
            filtered_results = [r for r in filtered_results if sender_filter in r.sender.lower()]

        # Category filter
        if "categories" in filters:
            category_filters = [c.lower() for c in filters["categories"]]
            filtered_results = [
                r for r in filtered_results
                if any(cat.lower() in category_filters for cat in r.categories)
            ]

        # Importance filter
        if "min_importance" in filters:
            min_importance = float(filters["min_importance"])
            filtered_results = [
                r for r in filtered_results
                if r.importance_score and r.importance_score >= min_importance
            ]

        # Attachment filter
        if "has_attachments" in filters:
            has_attachments = filters["has_attachments"]
            filtered_results = [r for r in filtered_results if r.has_attachments == has_attachments]

        return filtered_results

    async def _expand_query(self, query_text: str) -> List[str]:
        """Expand query with synonyms and related terms."""
        try:
            # Simple query expansion using basic NLP techniques
            # Split query into terms and create variations
            terms = query_text.lower().split()

            expanded_queries = [query_text]

            # Add common variations
            if len(terms) > 1:
                # Add queries with individual terms
                for term in terms:
                    if len(term) > 3:  # Only expand meaningful terms
                        expanded_queries.append(term)

                # Add query with first two terms
                if len(terms) >= 2:
                    expanded_queries.append(f"{terms[0]} {terms[1]}")

            # Limit to avoid too many queries
            return expanded_queries[:4]

        except Exception as e:
            self.logger.warning(f"Query expansion failed: {e}")
            return [query_text]

    async def _get_email_details(
        self,
        content_item_id: str,
        relevance_score: float,
        search_terms: List[str],
        db_session: Any = None
    ) -> Optional[EmailSearchResult]:
        """Get detailed email information from database."""
        # This is a placeholder - actual implementation would query the database
        # for ContentItem and related email metadata
        return None

    async def _generate_facets(
        self,
        results: List[EmailSearchResult],
        db_session: Any = None
    ) -> Dict[str, Any]:
        """Generate search facets from results."""
        facets = {
            "categories": {},
            "senders": {},
            "date_ranges": {},
            "importance_levels": {}
        }

        for result in results:
            # Category facets
            for category in result.categories:
                facets["categories"][category] = facets["categories"].get(category, 0) + 1

            # Sender facets
            sender_domain = result.sender.split('@')[-1] if '@' in result.sender else result.sender
            facets["senders"][sender_domain] = facets["senders"].get(sender_domain, 0) + 1

            # Date range facets
            date_range = self._get_date_range(result.sent_date)
            facets["date_ranges"][date_range] = facets["date_ranges"].get(date_range, 0) + 1

            # Importance facets
            if result.importance_score:
                importance_level = self._get_importance_level(result.importance_score)
                facets["importance_levels"][importance_level] = facets["importance_levels"].get(importance_level, 0) + 1

        return facets

    async def _generate_suggestions(
        self,
        original_query: str,
        results: List[EmailSearchResult]
    ) -> List[str]:
        """Generate search suggestions based on results."""
        suggestions = []

        if len(results) == 0:
            # Suggest broader queries
            suggestions.extend([
                f"broader search for {original_query}",
                f"related terms to {original_query}",
                f"recent emails about {original_query}"
            ])
        elif len(results) > 50:
            # Suggest more specific queries
            suggestions.extend([
                f"specific {original_query}",
                f"recent {original_query}",
                f"important {original_query}"
            ])

        # Add category-based suggestions
        categories = set()
        for result in results[:10]:  # Check top results
            categories.update(result.categories)

        for category in list(categories)[:3]:
            suggestions.append(f"{original_query} in {category}")

        return suggestions[:5]  # Limit to 5 suggestions

    async def _enrich_with_threads(
        self,
        results: List[EmailSearchResult],
        db_session: Any = None
    ) -> List[EmailSearchResult]:
        """Enrich results with thread information."""
        # This is a placeholder - actual implementation would group emails by thread
        # and add thread metadata to results
        return results

    def _get_date_range(self, date: datetime) -> str:
        """Get date range category for faceting."""
        now = datetime.now()
        diff_days = (now - date).days

        if diff_days <= 1:
            return "today"
        elif diff_days <= 7:
            return "this_week"
        elif diff_days <= 30:
            return "this_month"
        elif diff_days <= 90:
            return "last_3_months"
        else:
            return "older"

    def _get_importance_level(self, score: float) -> str:
        """Get importance level category."""
        if score >= 0.8:
            return "urgent"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"

    async def search_email_threads(
        self,
        query: EmailSearchQuery,
        db_session: Any = None
    ) -> List[EmailThreadResult]:
        """
        Search for email threads matching the query.

        Args:
            query: Search query
            db_session: Database session

        Returns:
            List of email threads matching the query
        """
        try:
            # First perform regular search
            search_response = await self.search_emails(query, db_session)

            # Group results by thread
            thread_groups = {}
            for result in search_response.results:
                thread_id = result.thread_id or result.content_item_id

                if thread_id not in thread_groups:
                    thread_groups[thread_id] = []

                thread_groups[thread_id].append(result)

            # Convert to thread results
            thread_results = []
            for thread_id, emails in thread_groups.items():
                if len(emails) > 1:  # Only include actual threads
                    thread_result = await self._create_thread_result(thread_id, emails, db_session)
                    if thread_result:
                        thread_results.append(thread_result)

            # Sort by thread importance
            thread_results.sort(key=lambda x: x.importance_score, reverse=True)

            return thread_results[:query.limit]

        except Exception as e:
            self.logger.error(f"Thread search failed: {e}")
            return []

    async def _create_thread_result(
        self,
        thread_id: str,
        emails: List[EmailSearchResult],
        db_session: Any = None
    ) -> Optional[EmailThreadResult]:
        """Create a thread result from email results."""
        try:
            # Sort emails by date
            emails.sort(key=lambda x: x.sent_date)

            # Extract thread information
            subject = emails[0].subject
            participants = list(set(email.sender for email in emails))
            latest_date = max(email.sent_date for email in emails)
            avg_importance = sum(email.importance_score or 0 for email in emails) / len(emails)

            # Generate thread summary
            thread_summary = await self._generate_thread_summary(emails)

            return EmailThreadResult(
                thread_id=thread_id,
                subject=subject,
                participants=participants,
                message_count=len(emails),
                latest_message_date=latest_date,
                importance_score=avg_importance,
                emails=emails,
                thread_summary=thread_summary
            )

        except Exception as e:
            self.logger.error(f"Failed to create thread result: {e}")
            return None

    async def _generate_thread_summary(self, emails: List[EmailSearchResult]) -> str:
        """Generate a summary for an email thread."""
        try:
            # Extract key information from thread
            subjects = list(set(email.subject for email in emails))
            senders = list(set(email.sender for email in emails))

            # Create a simple summary
            summary = f"Thread with {len(emails)} messages"

            if len(subjects) == 1:
                summary += f" about '{subjects[0]}'"
            else:
                summary += f" with subjects: {', '.join(subjects[:3])}"

            summary += f" involving {len(senders)} participants"

            return summary

        except Exception as e:
            self.logger.warning(f"Thread summary generation failed: {e}")
            return f"Email thread with {len(emails)} messages"

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "query_cache_size": len(self.query_cache),
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_results": self.max_results,
            "min_relevance_threshold": self.min_relevance_threshold,
            "query_expansion_enabled": self.query_expansion_enabled,
            "supported_search_types": ["semantic", "keyword", "hybrid"]
        }


# Global instance
email_semantic_search = EmailSemanticSearch()