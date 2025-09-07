"""
Content Recommendation Engine for intelligent content suggestions.

This service provides AI-powered content recommendations based on user behavior,
content similarity, popularity, and contextual relevance.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy import text, desc, and_, or_, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentEmbedding, ContentAnalytics
from app.services.vector_search_service import vector_search_service, SearchQuery
from app.services.semantic_processing import embedding_service
from app.utils.logging import get_logger

logger = get_logger("content_recommendation_service")


@dataclass
class UserContext:
    """User context for personalization."""
    user_id: Optional[str] = None
    recent_interactions: List[str] = field(default_factory=list)  # Content IDs
    preferred_content_types: List[str] = field(default_factory=list)
    preferred_sources: List[str] = field(default_factory=list)
    interaction_history: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationRequest:
    """Request for content recommendations."""
    user_context: Optional[UserContext] = None
    content_type_filter: Optional[str] = None
    source_filter: Optional[str] = None
    max_recommendations: int = 10
    diversity_factor: float = 0.7  # 0.0 = no diversity, 1.0 = maximum diversity
    freshness_weight: float = 0.3
    popularity_weight: float = 0.2
    similarity_weight: float = 0.5


@dataclass
class ContentRecommendation:
    """Individual content recommendation."""
    content_item_id: str
    title: Optional[str]
    content_type: str
    source_type: str
    recommendation_score: float
    recommendation_reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationResponse:
    """Complete recommendation response."""
    recommendations: List[ContentRecommendation]
    total_recommendations: int
    processing_time_ms: float
    recommendation_strategy: str


class ContentRecommendationEngine:
    """AI-powered content recommendation engine."""

    def __init__(self):
        self.cache = {}
        self.cache_expiry = 300  # 5 minutes

    async def get_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Generate personalized content recommendations.

        Args:
            request: RecommendationRequest with user context and filters

        Returns:
            RecommendationResponse with personalized recommendations
        """
        start_time = time.time()

        try:
            # Determine recommendation strategy
            if request.user_context and request.user_context.recent_interactions:
                strategy = "personalized"
                recommendations = await self._get_personalized_recommendations(request)
            else:
                strategy = "popular"
                recommendations = await self._get_popular_recommendations(request)

            # Apply diversity filtering
            if request.diversity_factor > 0:
                recommendations = self._apply_diversity_filtering(
                    recommendations, request.diversity_factor
                )

            # Limit results
            recommendations = recommendations[:request.max_recommendations]

            processing_time = (time.time() - start_time) * 1000

            response = RecommendationResponse(
                recommendations=recommendations,
                total_recommendations=len(recommendations),
                processing_time_ms=processing_time,
                recommendation_strategy=strategy
            )

            logger.info(f"Generated {len(recommendations)} recommendations using {strategy} strategy")
            return response

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            raise

    async def _get_personalized_recommendations(self, request: RecommendationRequest) -> List[ContentRecommendation]:
        """Generate personalized recommendations based on user behavior."""
        user_context = request.user_context
        if not user_context or not user_context.recent_interactions:
            return await self._get_popular_recommendations(request)

        # Get embeddings for user's recent interactions
        recent_embeddings = await self._get_embeddings_for_content(user_context.recent_interactions)

        if not recent_embeddings:
            return await self._get_popular_recommendations(request)

        # Calculate average user embedding
        user_embedding = self._calculate_average_embedding(recent_embeddings)

        # Find similar content
        similar_query = SearchQuery(
            query_text="",  # We'll use the embedding directly
            top_k=request.max_recommendations * 2,  # Get more for filtering
            filters={
                'content_type': request.content_type_filter,
                'source_type': request.source_filter
            },
            min_score=0.3
        )

        # Perform custom similarity search
        similar_content = await self._find_similar_by_embedding(
            user_embedding, similar_query, exclude_ids=user_context.recent_interactions
        )

        # Convert to recommendations
        recommendations = []
        for content_id, similarity_score, metadata in similar_content:
            recommendation = ContentRecommendation(
                content_item_id=content_id,
                title=metadata.get('title'),
                content_type=metadata.get('content_type', ''),
                source_type=metadata.get('source_type', ''),
                recommendation_score=similarity_score * request.similarity_weight,
                recommendation_reason="Based on your recent interactions",
                metadata=metadata
            )
            recommendations.append(recommendation)

        return recommendations

    async def _get_popular_recommendations(self, request: RecommendationRequest) -> List[ContentRecommendation]:
        """Generate recommendations based on popularity and recency."""
        db = next(get_db())

        try:
            # Build query for popular content
            query = db.query(
                ContentItem.id,
                ContentItem.title,
                ContentItem.content_type,
                ContentItem.source_type,
                ContentItem.quality_score,
                ContentItem.discovered_at,
                ContentAnalytics.view_count,
                ContentAnalytics.engagement_score
            ).outerjoin(
                ContentAnalytics,
                and_(
                    ContentAnalytics.content_item_id == ContentItem.id,
                    ContentAnalytics.analytics_type == 'engagement'
                )
            )

            # Apply filters
            if request.content_type_filter:
                query = query.filter(ContentItem.content_type == request.content_type_filter)
            if request.source_filter:
                query = query.filter(ContentItem.source_type == request.source_filter)

            # Calculate popularity score
            # Score = (view_count * 0.4) + (engagement_score * 0.4) + (quality_score * 0.2)
            results = query.all()

            recommendations = []
            for row in results:
                popularity_score = self._calculate_popularity_score(
                    row.view_count or 0,
                    row.engagement_score or 0.5,
                    row.quality_score or 0.5
                )

                # Apply freshness bonus
                freshness_bonus = self._calculate_freshness_bonus(row.discovered_at)
                final_score = popularity_score * (1 - request.freshness_weight) + freshness_bonus * request.freshness_weight

                recommendation = ContentRecommendation(
                    content_item_id=str(row.id),
                    title=row.title,
                    content_type=row.content_type,
                    source_type=row.source_type,
                    recommendation_score=final_score,
                    recommendation_reason="Popular and recent content",
                    metadata={
                        'view_count': row.view_count or 0,
                        'engagement_score': row.engagement_score or 0.5,
                        'quality_score': row.quality_score or 0.5,
                        'discovered_at': row.discovered_at.isoformat() if row.discovered_at else None
                    }
                )
                recommendations.append(recommendation)

            # Sort by score
            recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)

            return recommendations

        finally:
            db.close()

    async def _get_embeddings_for_content(self, content_ids: List[str]) -> List[List[float]]:
        """Get embeddings for a list of content items."""
        db = next(get_db())

        try:
            embeddings = []
            for content_id in content_ids[:5]:  # Limit to recent 5 items
                embedding_record = db.query(ContentEmbedding).filter(
                    ContentEmbedding.content_item_id == content_id
                ).first()

                if embedding_record:
                    embeddings.append(embedding_record.embedding_vector)

            return embeddings

        finally:
            db.close()

    def _calculate_average_embedding(self, embeddings: List[List[float]]) -> List[float]:
        """Calculate average embedding from multiple embeddings."""
        if not embeddings:
            return []

        # Convert to numpy for easier calculation
        import numpy as np
        embedding_arrays = [np.array(emb) for emb in embeddings]
        average_embedding = np.mean(embedding_arrays, axis=0)

        return average_embedding.tolist()

    async def _find_similar_by_embedding(
        self,
        query_embedding: List[float],
        search_query: SearchQuery,
        exclude_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Find similar content using direct embedding comparison."""
        db = next(get_db())

        try:
            # Build similarity query
            exclude_condition = ""
            if exclude_ids:
                exclude_condition = f"AND ce.content_item_id NOT IN ({','.join(['%s'] * len(exclude_ids))})"

            similarity_query = text(f"""
                SELECT
                    ce.content_item_id,
                    ce.embedding_vector <=> :query_embedding as distance,
                    ci.title,
                    ci.content_type,
                    ci.source_type,
                    ci.metadata
                FROM content_embeddings ce
                JOIN content_items ci ON ce.content_item_id = ci.id
                WHERE ce.embedding_vector <=> :query_embedding < :max_distance
                {exclude_condition}
                ORDER BY ce.embedding_vector <=> :query_embedding
                LIMIT :limit
            """)

            max_distance = 1.0 - search_query.min_score
            params = {
                'query_embedding': query_embedding,
                'max_distance': max_distance,
                'limit': search_query.top_k
            }

            if exclude_ids:
                params.update({f'param_{i}': cid for i, cid in enumerate(exclude_ids)})

            result = db.execute(similarity_query, params)
            rows = result.fetchall()

            similar_content = []
            for row in rows:
                similarity_score = 1.0 - row.distance  # Convert distance to similarity
                metadata = {
                    'title': row.title,
                    'content_type': row.content_type,
                    'source_type': row.source_type,
                    'metadata': row.metadata or {}
                }
                similar_content.append((str(row.content_item_id), similarity_score, metadata))

            return similar_content

        finally:
            db.close()

    def _calculate_popularity_score(self, view_count: int, engagement_score: float, quality_score: float) -> float:
        """Calculate popularity score from various metrics."""
        # Normalize view count (log scale to handle large ranges)
        normalized_views = min(1.0, (view_count ** 0.5) / 100) if view_count > 0 else 0

        # Weighted combination
        score = (
            normalized_views * 0.4 +
            engagement_score * 0.4 +
            quality_score * 0.2
        )

        return min(1.0, score)  # Cap at 1.0

    def _calculate_freshness_bonus(self, discovered_at: Optional[datetime]) -> float:
        """Calculate freshness bonus based on content age."""
        if not discovered_at:
            return 0.0

        age_hours = (datetime.now() - discovered_at).total_seconds() / 3600

        # Exponential decay: newer content gets higher bonus
        if age_hours < 24:  # Less than 1 day
            return 1.0
        elif age_hours < 168:  # Less than 1 week
            return 0.8
        elif age_hours < 720:  # Less than 1 month
            return 0.6
        else:
            return 0.2

    def _apply_diversity_filtering(
        self,
        recommendations: List[ContentRecommendation],
        diversity_factor: float
    ) -> List[ContentRecommendation]:
        """Apply diversity filtering to ensure varied recommendations."""
        if diversity_factor <= 0 or not recommendations:
            return recommendations

        # Group by content type and source
        type_groups = defaultdict(list)
        source_groups = defaultdict(list)

        for rec in recommendations:
            type_groups[rec.content_type].append(rec)
            source_groups[rec.source_type].append(rec)

        # Select diverse items
        diverse_recommendations = []
        used_types = set()
        used_sources = set()

        # First pass: ensure type diversity
        for rec in recommendations:
            if rec.content_type not in used_types:
                diverse_recommendations.append(rec)
                used_types.add(rec.content_type)
                used_sources.add(rec.source_type)

                if len(diverse_recommendations) >= len(recommendations) * (1 - diversity_factor):
                    break

        # Second pass: fill remaining slots
        remaining_slots = len(recommendations) - len(diverse_recommendations)
        if remaining_slots > 0:
            remaining_recs = [r for r in recommendations if r not in diverse_recommendations]
            diverse_recommendations.extend(remaining_recs[:remaining_slots])

        return diverse_recommendations

    async def get_trending_content(
        self,
        time_window_hours: int = 24,
        limit: int = 10
    ) -> List[ContentRecommendation]:
        """Get trending content based on recent engagement."""
        db = next(get_db())

        try:
            # Calculate time window
            time_window = datetime.now() - timedelta(hours=time_window_hours)

            # Query for trending content
            trending_query = db.query(
                ContentItem.id,
                ContentItem.title,
                ContentItem.content_type,
                ContentItem.source_type,
                func.sum(ContentAnalytics.view_count).label('total_views'),
                func.avg(ContentAnalytics.engagement_score).label('avg_engagement')
            ).join(
                ContentAnalytics,
                ContentAnalytics.content_item_id == ContentItem.id
            ).filter(
                ContentAnalytics.period_start >= time_window
            ).group_by(
                ContentItem.id,
                ContentItem.title,
                ContentItem.content_type,
                ContentItem.source_type
            ).order_by(
                desc(func.sum(ContentAnalytics.view_count)),
                desc(func.avg(ContentAnalytics.engagement_score))
            ).limit(limit)

            results = trending_query.all()

            trending_recommendations = []
            for row in results:
                trend_score = self._calculate_trend_score(
                    row.total_views or 0,
                    row.avg_engagement or 0.5
                )

                recommendation = ContentRecommendation(
                    content_item_id=str(row.id),
                    title=row.title,
                    content_type=row.content_type,
                    source_type=row.source_type,
                    recommendation_score=trend_score,
                    recommendation_reason=f"Trending in last {time_window_hours} hours",
                    metadata={
                        'total_views': row.total_views or 0,
                        'avg_engagement': row.avg_engagement or 0.5,
                        'time_window_hours': time_window_hours
                    }
                )
                trending_recommendations.append(recommendation)

            return trending_recommendations

        finally:
            db.close()

    def _calculate_trend_score(self, total_views: int, avg_engagement: float) -> float:
        """Calculate trend score for content."""
        # Simple trend score based on views and engagement
        view_score = min(1.0, total_views / 1000)  # Normalize to 0-1
        engagement_score = avg_engagement

        return (view_score * 0.6 + engagement_score * 0.4)

    async def get_similar_content(
        self,
        content_item_id: str,
        limit: int = 5
    ) -> List[ContentRecommendation]:
        """Get content similar to a given item."""
        # Get embedding for the source content
        db = next(get_db())

        try:
            embedding_record = db.query(ContentEmbedding).filter(
                ContentEmbedding.content_item_id == content_item_id
            ).first()

            if not embedding_record:
                return []

            # Find similar content
            similar_query = SearchQuery(
                query_text="",  # Use embedding directly
                top_k=limit + 1,  # +1 to exclude the source item
                min_score=0.3
            )

            similar_content = await self._find_similar_by_embedding(
                embedding_record.embedding_vector,
                similar_query,
                exclude_ids=[content_item_id]
            )

            # Convert to recommendations
            recommendations = []
            for content_id, similarity_score, metadata in similar_content[:limit]:
                recommendation = ContentRecommendation(
                    content_item_id=content_id,
                    title=metadata.get('title'),
                    content_type=metadata.get('content_type', ''),
                    source_type=metadata.get('source_type', ''),
                    recommendation_score=similarity_score,
                    recommendation_reason="Similar to content you viewed",
                    metadata=metadata
                )
                recommendations.append(recommendation)

            return recommendations

        finally:
            db.close()


# Global instance
content_recommendation_engine = ContentRecommendationEngine()