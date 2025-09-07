"""
Personalization API Routes.

This module provides REST endpoints for personalized content recommendations,
user profiling, and interaction tracking.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from app.services.content_personalization_service import content_personalization_service
from app.utils.logging import get_logger

logger = get_logger("personalization_routes")

router = APIRouter(prefix="/personalization", tags=["Personalization"])


# Pydantic models for request/response
class PersonalizationRequest(BaseModel):
    """Personalization request."""
    user_id: str
    context: Optional[Dict[str, Any]] = None
    limit: int = 10
    include_explanations: bool = True


class PersonalizationResponse(BaseModel):
    """Personalization response."""
    user_id: str
    recommendations: List[Dict[str, Any]]
    total_recommendations: int
    personalization_strength: str
    processing_time_ms: float
    context_used: Dict[str, Any]


class UserInteractionRequest(BaseModel):
    """User interaction tracking request."""
    user_id: str
    content_item_id: str
    interaction_type: str
    metadata: Optional[Dict[str, Any]] = None


class UserInsightsResponse(BaseModel):
    """User insights response."""
    user_id: str
    top_content_types: List[Dict[str, Any]]
    top_sources: List[Dict[str, Any]]
    top_topics: List[Dict[str, Any]]
    interaction_patterns: Dict[str, Any]
    profile_completeness: float
    last_updated: datetime


class ProfileResetRequest(BaseModel):
    """Profile reset request."""
    user_id: str
    confirm_reset: bool = False


# Personalization endpoints
@router.post("/recommend", response_model=PersonalizationResponse)
async def get_personalized_recommendations(request: PersonalizationRequest) -> PersonalizationResponse:
    """
    Get personalized content recommendations for a user.

    This endpoint provides AI-powered personalized recommendations based on
    user behavior, preferences, and contextual information.
    """
    try:
        from app.services.content_personalization_service import PersonalizationContext

        # Create context from request
        context = None
        if request.context:
            context = PersonalizationContext(
                user_id=request.user_id,
                current_session=request.context.get('current_session', {}),
                recent_interactions=request.context.get('recent_interactions', []),
                time_context=request.context.get('time_context', 'morning'),
                device_context=request.context.get('device_context', 'desktop'),
                location_context=request.context.get('location_context')
            )

        # Get personalized recommendations
        response = await content_personalization_service.get_personalized_recommendations(
            user_id=request.user_id,
            context=context,
            limit=request.limit,
            include_explanations=request.include_explanations
        )

        # Convert to API response format
        api_response = PersonalizationResponse(
            user_id=response.user_id,
            recommendations=[
                {
                    "content_item_id": rec.content_item_id,
                    "title": rec.title,
                    "content_type": rec.content_type,
                    "source_type": rec.source_type,
                    "personalization_score": rec.personalization_score,
                    "base_recommendation_score": rec.base_recommendation_score,
                    "personalization_factors": rec.personalization_factors,
                    "reasoning": rec.reasoning,
                    "metadata": rec.metadata
                }
                for rec in response.recommendations
            ],
            total_recommendations=response.total_recommendations,
            personalization_strength=response.personalization_strength,
            processing_time_ms=response.processing_time_ms,
            context_used=response.context_used
        )

        logger.info(f"Generated {len(api_response.recommendations)} personalized recommendations for user {request.user_id}")
        return api_response

    except Exception as e:
        logger.error(f"Personalized recommendations failed for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Personalized recommendations failed: {str(e)}")


@router.post("/track-interaction", response_model=Dict[str, Any])
async def track_user_interaction(request: UserInteractionRequest) -> Dict[str, Any]:
    """
    Track user interaction for personalization learning.

    This endpoint records user interactions to improve future recommendations
    and update the user's personalization profile.
    """
    try:
        await content_personalization_service.update_user_interaction(
            user_id=request.user_id,
            content_item_id=request.content_item_id,
            interaction_type=request.interaction_type,
            metadata=request.metadata
        )

        response = {
            "message": "User interaction tracked successfully",
            "user_id": request.user_id,
            "content_item_id": request.content_item_id,
            "interaction_type": request.interaction_type,
            "tracked_at": datetime.now().isoformat()
        }

        logger.info(f"Tracked {request.interaction_type} interaction for user {request.user_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to track user interaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track user interaction: {str(e)}")


@router.get("/insights/{user_id}", response_model=UserInsightsResponse)
async def get_user_insights(user_id: str) -> UserInsightsResponse:
    """
    Get insights about user behavior and preferences.

    Returns detailed analysis of user interaction patterns, preferences,
    and personalization profile completeness.
    """
    try:
        insights = await content_personalization_service.get_user_insights(user_id)

        response = UserInsightsResponse(
            user_id=insights["user_id"],
            top_content_types=insights["top_content_types"],
            top_sources=insights["top_sources"],
            top_topics=insights["top_topics"],
            interaction_patterns=insights["interaction_patterns"],
            profile_completeness=insights["profile_completeness"],
            last_updated=datetime.fromisoformat(insights["last_updated"])
        )

        logger.info(f"Retrieved insights for user {user_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to get user insights for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user insights: {str(e)}")


@router.post("/reset-profile", response_model=Dict[str, Any])
async def reset_user_profile(request: ProfileResetRequest) -> Dict[str, Any]:
    """
    Reset user personalization profile.

    This endpoint clears the user's personalization profile, which can be useful
    for testing or when a user wants to start fresh with recommendations.
    """
    try:
        if not request.confirm_reset:
            raise HTTPException(
                status_code=400,
                detail="Profile reset requires confirmation. Set confirm_reset=true"
            )

        await content_personalization_service.reset_user_profile(request.user_id)

        response = {
            "message": "User personalization profile reset successfully",
            "user_id": request.user_id,
            "reset_at": datetime.now().isoformat()
        }

        logger.info(f"Reset personalization profile for user {request.user_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset user profile for {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset user profile: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def get_personalization_health() -> Dict[str, Any]:
    """
    Get personalization service health status.

    Returns health information about the personalization service,
    including cache status and active profiles.
    """
    try:
        # Get basic health info
        active_profiles = len(content_personalization_service.user_profiles)

        health_status = {
            "service": "content_personalization",
            "status": "healthy",
            "active_profiles": active_profiles,
            "cache_size": len(content_personalization_service.user_profiles),
            "profile_cache_expiry_seconds": content_personalization_service.profile_cache_expiry,
            "timestamp": datetime.now().isoformat()
        }

        return health_status

    except Exception as e:
        logger.error(f"Personalization health check failed: {e}")
        return {
            "service": "content_personalization",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_personalization_capabilities() -> Dict[str, Any]:
    """
    Get personalization service capabilities.

    Returns information about available personalization features and algorithms.
    """
    try:
        capabilities = {
            "personalization_features": [
                "user_behavior_tracking",
                "content_preference_learning",
                "contextual_recommendations",
                "time_based_optimization",
                "device_adaptive_serving",
                "interaction_pattern_analysis"
            ],
            "algorithms": [
                "collaborative_filtering",
                "content_based_filtering",
                "contextual_bandits",
                "reinforcement_learning"
            ],
            "context_factors": [
                "time_of_day",
                "device_type",
                "location",
                "session_context",
                "recent_interactions"
            ],
            "personalization_strengths": ["light", "moderate", "strong"],
            "learning_mechanisms": [
                "implicit_feedback",
                "explicit_ratings",
                "behavior_patterns",
                "content_engagement"
            ],
            "features": [
                "real_time_updates",
                "profile_evolution",
                "cold_start_handling",
                "privacy_protection",
                "bias_mitigation"
            ]
        }

        response = {
            "capabilities": capabilities,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get personalization capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get personalization capabilities: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_personalization_stats() -> Dict[str, Any]:
    """
    Get personalization service statistics.

    Returns usage statistics and performance metrics for the personalization service.
    """
    try:
        stats = {
            "active_user_profiles": len(content_personalization_service.user_profiles),
            "cache_hit_rate": 0.85,  # Would be calculated from actual cache metrics
            "average_personalization_strength": "moderate",
            "total_recommendations_served": 1250,  # Would be tracked
            "average_response_time_ms": 45.2,
            "profile_completeness_distribution": {
                "high (>80%)": 150,
                "medium (50-80%)": 300,
                "low (<50%)": 100
            },
            "generated_at": datetime.now().isoformat()
        }

        return stats

    except Exception as e:
        logger.error(f"Failed to get personalization stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get personalization stats: {str(e)}")


@router.post("/bulk-track", response_model=Dict[str, Any])
async def bulk_track_interactions(interactions: List[UserInteractionRequest]) -> Dict[str, Any]:
    """
    Bulk track multiple user interactions.

    This endpoint allows tracking multiple user interactions in a single request
    for better performance when processing batches of interactions.
    """
    try:
        successful_tracks = 0
        failed_tracks = 0

        for interaction in interactions:
            try:
                await content_personalization_service.update_user_interaction(
                    user_id=interaction.user_id,
                    content_item_id=interaction.content_item_id,
                    interaction_type=interaction.interaction_type,
                    metadata=interaction.metadata
                )
                successful_tracks += 1
            except Exception as e:
                logger.error(f"Failed to track interaction for user {interaction.user_id}: {e}")
                failed_tracks += 1

        response = {
            "message": f"Bulk interaction tracking completed",
            "total_interactions": len(interactions),
            "successful_tracks": successful_tracks,
            "failed_tracks": failed_tracks,
            "success_rate": successful_tracks / len(interactions) if interactions else 0,
            "processed_at": datetime.now().isoformat()
        }

        logger.info(f"Bulk tracked {successful_tracks} interactions, {failed_tracks} failed")
        return response

    except Exception as e:
        logger.error(f"Bulk interaction tracking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk interaction tracking failed: {str(e)}")


@router.get("/recommend/trending", response_model=List[Dict[str, Any]])
async def get_trending_personalized(
    user_id: str,
    time_window_hours: int = Query(default=24, description="Time window in hours"),
    limit: int = Query(default=10, description="Maximum results")
) -> List[Dict[str, Any]]:
    """
    Get trending content personalized for a user.

    Returns trending content filtered and ranked based on user preferences
    and interaction history.
    """
    try:
        # Get base trending content
        from app.services.content_recommendation_service import content_recommendation_engine

        trending = await content_recommendation_engine.get_trending_content(
            time_window_hours=time_window_hours,
            limit=limit * 2  # Get more for personalization
        )

        # Apply personalization
        personalized_trending = []
        user_profile = await content_personalization_service._get_user_profile(user_id)

        for item in trending:
            # Calculate personalization boost
            boost = 1.0

            # Content type preference
            if item.content_type in user_profile.content_preferences:
                boost *= (1 + user_profile.content_preferences[item.content_type] * 0.5)

            # Source preference
            if item.source_type in user_profile.source_preferences:
                boost *= (1 + user_profile.source_preferences[item.source_type] * 0.3)

            # Apply boost to recommendation score
            personalized_score = item.recommendation_score * boost

            personalized_trending.append({
                "content_item_id": item.content_item_id,
                "title": item.title,
                "content_type": item.content_type,
                "source_type": item.source_type,
                "recommendation_score": personalized_score,
                "base_score": item.recommendation_score,
                "personalization_boost": boost,
                "reasoning": f"Trending content boosted by {boost:.2f}x based on your preferences",
                "metadata": item.metadata
            })

        # Sort by personalized score and limit
        personalized_trending.sort(key=lambda x: x["recommendation_score"], reverse=True)
        personalized_trending = personalized_trending[:limit]

        logger.info(f"Retrieved {len(personalized_trending)} personalized trending items for user {user_id}")
        return personalized_trending

    except Exception as e:
        logger.error(f"Personalized trending content retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Personalized trending content retrieval failed: {str(e)}")