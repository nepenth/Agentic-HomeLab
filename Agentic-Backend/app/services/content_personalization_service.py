"""
Content Personalization Service for user-specific content recommendations.

This service provides personalized content experiences based on user behavior,
preferences, and interaction patterns to improve engagement and relevance.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentEmbedding, ContentAnalytics, UserInteraction
from app.services.content_recommendation_service import content_recommendation_engine
from app.services.vector_search_service import vector_search_service
from app.utils.logging import get_logger

logger = get_logger("content_personalization_service")


@dataclass
class UserProfile:
    """User profile for personalization."""
    user_id: str
    content_preferences: Dict[str, float] = field(default_factory=dict)  # content_type -> preference_score
    source_preferences: Dict[str, float] = field(default_factory=dict)  # source_type -> preference_score
    topic_interests: Dict[str, float] = field(default_factory=dict)  # topic -> interest_score
    interaction_patterns: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PersonalizationContext:
    """Context for personalization decisions."""
    user_id: str
    current_session: Dict[str, Any] = field(default_factory=dict)
    recent_interactions: List[Dict[str, Any]] = field(default_factory=list)
    time_context: str = "morning"  # morning, afternoon, evening, night
    device_context: str = "desktop"  # desktop, mobile, tablet
    location_context: Optional[str] = None


@dataclass
class PersonalizedRecommendation:
    """Personalized recommendation with user-specific scoring."""
    content_item_id: str
    title: Optional[str]
    content_type: str
    source_type: str
    personalization_score: float
    base_recommendation_score: float
    personalization_factors: List[str]
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonalizationResponse:
    """Response containing personalized recommendations."""
    user_id: str
    recommendations: List[PersonalizedRecommendation]
    total_recommendations: int
    personalization_strength: str
    processing_time_ms: float
    context_used: Dict[str, Any]


class ContentPersonalizationService:
    """Service for personalized content recommendations and user profiling."""

    def __init__(self):
        self.user_profiles: Dict[str, UserProfile] = {}
        self.profile_cache_expiry = 3600  # 1 hour

    async def get_personalized_recommendations(
        self,
        user_id: str,
        context: Optional[PersonalizationContext] = None,
        limit: int = 10,
        include_explanations: bool = True
    ) -> PersonalizationResponse:
        """
        Get personalized content recommendations for a user.

        Args:
            user_id: User identifier
            context: Personalization context
            limit: Maximum recommendations to return
            include_explanations: Whether to include reasoning

        Returns:
            Personalized recommendations
        """
        start_time = time.time()

        try:
            # Get or create user profile
            user_profile = await self._get_user_profile(user_id)

            # Create context if not provided
            if not context:
                context = await self._create_context_from_user(user_id)

            # Get base recommendations
            base_request = {
                'user_context': {
                    'user_id': user_id,
                    'recent_interactions': context.recent_interactions[:5] if context.recent_interactions else [],
                    'preferred_content_types': list(user_profile.content_preferences.keys()),
                    'preferred_sources': list(user_profile.source_preferences.keys()),
                    'interaction_history': user_profile.interaction_patterns
                },
                'max_recommendations': limit * 2,  # Get more for personalization
                'diversity_factor': 0.6,
                'freshness_weight': 0.2,
                'popularity_weight': 0.3,
                'similarity_weight': 0.5
            }

            base_response = await content_recommendation_engine.get_recommendations(base_request)

            # Personalize recommendations
            personalized_recs = await self._personalize_recommendations(
                base_response.recommendations,
                user_profile,
                context
            )

            # Sort by personalization score
            personalized_recs.sort(key=lambda x: x.personalization_score, reverse=True)

            # Limit results
            personalized_recs = personalized_recs[:limit]

            # Calculate personalization strength
            personalization_strength = self._calculate_personalization_strength(
                personalized_recs, base_response.recommendations
            )

            processing_time = (time.time() - start_time) * 1000

            response = PersonalizationResponse(
                user_id=user_id,
                recommendations=personalized_recs,
                total_recommendations=len(personalized_recs),
                personalization_strength=personalization_strength,
                processing_time_ms=processing_time,
                context_used={
                    'time_context': context.time_context,
                    'device_context': context.device_context,
                    'recent_interactions_count': len(context.recent_interactions),
                    'profile_preferences': len(user_profile.content_preferences)
                }
            )

            logger.info(f"Generated {len(personalized_recs)} personalized recommendations for user {user_id}")
            return response

        except Exception as e:
            logger.error(f"Personalized recommendations failed for user {user_id}: {e}")
            raise

    async def _get_user_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile."""
        # Check cache first
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            # Check if profile is still fresh
            if (datetime.now() - profile.last_updated).total_seconds() < self.profile_cache_expiry:
                return profile

        # Build profile from database
        profile = await self._build_user_profile(user_id)
        self.user_profiles[user_id] = profile

        return profile

    async def _build_user_profile(self, user_id: str) -> UserProfile:
        """Build user profile from interaction history."""
        db = next(get_db())

        try:
            # Get user interactions from last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)

            interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.created_at >= thirty_days_ago
            ).all()

            # Analyze content preferences
            content_preferences = defaultdict(float)
            source_preferences = defaultdict(float)
            topic_interests = defaultdict(float)

            for interaction in interactions:
                # Content type preferences
                content_type = interaction.content_type or "unknown"
                weight = self._get_interaction_weight(interaction.interaction_type)
                content_preferences[content_type] += weight

                # Source preferences
                source_type = interaction.source_type or "unknown"
                source_preferences[source_type] += weight

                # Topic interests (simplified)
                if interaction.topics:
                    for topic in interaction.topics:
                        topic_interests[topic] += weight

            # Normalize preferences
            total_content = sum(content_preferences.values())
            if total_content > 0:
                content_preferences = {k: v/total_content for k, v in content_preferences.items()}

            total_source = sum(source_preferences.values())
            if total_source > 0:
                source_preferences = {k: v/total_source for k, v in source_preferences.items()}

            total_topic = sum(topic_interests.values())
            if total_topic > 0:
                topic_interests = {k: v/total_topic for k, v in topic_interests.items()}

            # Build interaction patterns
            interaction_patterns = self._analyze_interaction_patterns(interactions)

            return UserProfile(
                user_id=user_id,
                content_preferences=dict(content_preferences),
                source_preferences=dict(source_preferences),
                topic_interests=dict(topic_interests),
                interaction_patterns=interaction_patterns,
                last_updated=datetime.now()
            )

        finally:
            db.close()

    def _get_interaction_weight(self, interaction_type: str) -> float:
        """Get weight for different interaction types."""
        weights = {
            'view': 1.0,
            'like': 2.0,
            'share': 3.0,
            'bookmark': 2.5,
            'comment': 2.0,
            'click': 1.5,
            'dismiss': -1.0,
            'skip': -0.5
        }
        return weights.get(interaction_type, 1.0)

    def _analyze_interaction_patterns(self, interactions: List[Any]) -> Dict[str, Any]:
        """Analyze user interaction patterns."""
        if not interactions:
            return {}

        # Time-based patterns
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)

        for interaction in interactions:
            if interaction.created_at:
                hour_counts[interaction.created_at.hour] += 1
                day_counts[interaction.created_at.weekday()] += 1

        # Find peak hours and days
        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
        peak_day = max(day_counts, key=day_counts.get) if day_counts else None

        return {
            'total_interactions': len(interactions),
            'peak_hour': peak_hour,
            'peak_day': peak_day,
            'avg_interactions_per_day': len(interactions) / 30,  # Assuming 30 days
            'preferred_interaction_types': Counter(i.interaction_type for i in interactions).most_common(3)
        }

    async def _create_context_from_user(self, user_id: str) -> PersonalizationContext:
        """Create personalization context from user data."""
        db = next(get_db())

        try:
            # Get recent interactions (last 24 hours)
            yesterday = datetime.now() - timedelta(hours=24)

            recent_interactions = db.query(UserInteraction).filter(
                UserInteraction.user_id == user_id,
                UserInteraction.created_at >= yesterday
            ).order_by(UserInteraction.created_at.desc()).limit(10).all()

            # Convert to dict format
            interactions_data = []
            for interaction in recent_interactions:
                interactions_data.append({
                    'content_id': interaction.content_item_id,
                    'interaction_type': interaction.interaction_type,
                    'timestamp': interaction.created_at.isoformat()
                })

            # Determine time context
            current_hour = datetime.now().hour
            if 6 <= current_hour < 12:
                time_context = "morning"
            elif 12 <= current_hour < 17:
                time_context = "afternoon"
            elif 17 <= current_hour < 22:
                time_context = "evening"
            else:
                time_context = "night"

            return PersonalizationContext(
                user_id=user_id,
                recent_interactions=interactions_data,
                time_context=time_context,
                device_context="desktop"  # Default, would be determined from request
            )

        finally:
            db.close()

    async def _personalize_recommendations(
        self,
        base_recommendations: List[Any],
        user_profile: UserProfile,
        context: PersonalizationContext
    ) -> List[PersonalizedRecommendation]:
        """Personalize base recommendations based on user profile and context."""
        personalized_recs = []

        for base_rec in base_recommendations:
            # Start with base recommendation score
            personalization_score = base_rec.recommendation_score
            personalization_factors = []
            reasoning_parts = []

            # Apply content type preference
            content_pref = user_profile.content_preferences.get(base_rec.content_type, 0.5)
            if content_pref > 0.7:
                personalization_score *= 1.2
                personalization_factors.append("content_type_preference")
                reasoning_parts.append(f"high preference for {base_rec.content_type}")
            elif content_pref < 0.3:
                personalization_score *= 0.8
                personalization_factors.append("content_type_avoidance")
                reasoning_parts.append(f"low preference for {base_rec.content_type}")

            # Apply source preference
            source_pref = user_profile.source_preferences.get(base_rec.source_type, 0.5)
            if source_pref > 0.7:
                personalization_score *= 1.1
                personalization_factors.append("source_preference")
                reasoning_parts.append(f"preferred source: {base_rec.source_type}")

            # Apply time context
            time_boost = self._calculate_time_boost(context.time_context, user_profile)
            if time_boost != 1.0:
                personalization_score *= time_boost
                personalization_factors.append("time_context")
                reasoning_parts.append(f"optimized for {context.time_context}")

            # Apply recency boost for recent interactions
            recency_boost = self._calculate_recency_boost(base_rec, context.recent_interactions)
            if recency_boost > 1.0:
                personalization_score *= recency_boost
                personalization_factors.append("recency_boost")
                reasoning_parts.append("recently interacted with similar content")

            # Apply topic interest boost
            topic_boost = await self._calculate_topic_boost(base_rec, user_profile)
            if topic_boost > 1.0:
                personalization_score *= topic_boost
                personalization_factors.append("topic_interest")
                reasoning_parts.append("matches your interests")

            # Create personalized recommendation
            reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Based on your general preferences"

            personalized_rec = PersonalizedRecommendation(
                content_item_id=base_rec.content_item_id,
                title=base_rec.title,
                content_type=base_rec.content_type,
                source_type=base_rec.source_type,
                personalization_score=min(personalization_score, 1.0),  # Cap at 1.0
                base_recommendation_score=base_rec.recommendation_score,
                personalization_factors=personalization_factors,
                reasoning=reasoning,
                metadata=base_rec.metadata
            )

            personalized_recs.append(personalized_rec)

        return personalized_recs

    def _calculate_time_boost(self, time_context: str, user_profile: UserProfile) -> float:
        """Calculate time-based personalization boost."""
        peak_hour = user_profile.interaction_patterns.get('peak_hour')

        if not peak_hour:
            return 1.0

        # Map time context to hour ranges
        time_ranges = {
            "morning": (6, 12),
            "afternoon": (12, 17),
            "evening": (17, 22),
            "night": (22, 6)
        }

        if time_context in time_ranges:
            start_hour, end_hour = time_ranges[time_context]
            if start_hour <= peak_hour < end_hour:
                return 1.1  # 10% boost for peak time
            else:
                return 0.95  # Slight penalty for off-peak

        return 1.0

    def _calculate_recency_boost(self, recommendation: Any, recent_interactions: List[Dict]) -> float:
        """Calculate boost based on recent interactions with similar content."""
        if not recent_interactions:
            return 1.0

        # Check if user recently interacted with similar content type
        recent_types = {interaction.get('content_type') for interaction in recent_interactions}
        if recommendation.content_type in recent_types:
            return 1.15  # 15% boost for similar recent interactions

        return 1.0

    async def _calculate_topic_boost(self, recommendation: Any, user_profile: UserProfile) -> float:
        """Calculate boost based on topic interests."""
        # This would require topic extraction from content
        # For now, return neutral boost
        return 1.0

    def _calculate_personalization_strength(
        self,
        personalized_recs: List[PersonalizedRecommendation],
        base_recs: List[Any]
    ) -> str:
        """Calculate how strong the personalization is."""
        if not personalized_recs or not base_recs:
            return "none"

        # Calculate average personalization boost
        total_boost = 0
        for pers_rec in personalized_recs:
            boost = pers_rec.personalization_score / max(pers_rec.base_recommendation_score, 0.1)
            total_boost += boost

        avg_boost = total_boost / len(personalized_recs)

        if avg_boost > 1.2:
            return "strong"
        elif avg_boost > 1.1:
            return "moderate"
        elif avg_boost > 1.05:
            return "light"
        else:
            return "minimal"

    async def update_user_interaction(
        self,
        user_id: str,
        content_item_id: str,
        interaction_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update user profile based on new interaction.

        Args:
            user_id: User identifier
            content_item_id: Content item identifier
            interaction_type: Type of interaction
            metadata: Additional interaction metadata
        """
        try:
            # Get content information
            db = next(get_db())

            try:
                content_item = db.query(ContentItem).filter(
                    ContentItem.id == content_item_id
                ).first()

                if content_item:
                    # Create interaction record
                    interaction = UserInteraction(
                        user_id=user_id,
                        content_item_id=content_item_id,
                        interaction_type=interaction_type,
                        content_type=content_item.content_type,
                        source_type=content_item.source_type,
                        topics=[],  # Would be extracted from content
                        metadata=metadata or {},
                        created_at=datetime.now()
                    )

                    db.add(interaction)
                    db.commit()

                    # Invalidate cached profile
                    if user_id in self.user_profiles:
                        del self.user_profiles[user_id]

                    logger.info(f"Recorded {interaction_type} interaction for user {user_id} on content {content_item_id}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to update user interaction: {e}")

    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user behavior and preferences."""
        try:
            profile = await self._get_user_profile(user_id)

            insights = {
                "user_id": user_id,
                "top_content_types": sorted(
                    profile.content_preferences.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3],
                "top_sources": sorted(
                    profile.source_preferences.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3],
                "top_topics": sorted(
                    profile.topic_interests.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3],
                "interaction_patterns": profile.interaction_patterns,
                "profile_completeness": self._calculate_profile_completeness(profile),
                "last_updated": profile.last_updated.isoformat()
            }

            return insights

        except Exception as e:
            logger.error(f"Failed to get user insights for {user_id}: {e}")
            return {"error": str(e)}

    def _calculate_profile_completeness(self, profile: UserProfile) -> float:
        """Calculate how complete the user profile is."""
        completeness = 0.0

        if profile.content_preferences:
            completeness += 0.3
        if profile.source_preferences:
            completeness += 0.3
        if profile.topic_interests:
            completeness += 0.2
        if profile.interaction_patterns:
            completeness += 0.2

        return completeness

    async def reset_user_profile(self, user_id: str):
        """Reset user profile (useful for testing or user request)."""
        if user_id in self.user_profiles:
            del self.user_profiles[user_id]

        logger.info(f"Reset profile for user {user_id}")


# Global instance
content_personalization_service = ContentPersonalizationService()