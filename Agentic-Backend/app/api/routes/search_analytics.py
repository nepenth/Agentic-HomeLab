"""
Search Analytics API Routes.

This module provides REST endpoints for search analytics, performance metrics,
and user behavior insights to optimize search experience.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from app.services.search_analytics_service import search_analytics_service
from app.utils.logging import get_logger

logger = get_logger("search_analytics_routes")

router = APIRouter(prefix="/search-analytics", tags=["Search Analytics"])


# Pydantic models for request/response
class SearchAnalyticsRequest(BaseModel):
    """Search analytics request."""
    time_period_days: int = 30
    include_user_behavior: bool = True
    include_optimization_insights: bool = True
    focus_areas: Optional[List[str]] = None


class SearchAnalyticsResponse(BaseModel):
    """Search analytics response."""
    report_id: str
    time_period: str
    performance_metrics: Dict[str, Any]
    query_analytics: Dict[str, Any]
    user_behavior: Dict[str, Any]
    content_discovery: Dict[str, Any]
    optimization_insights: Dict[str, Any]
    key_findings: List[str]
    recommendations: List[str]
    generated_at: datetime


class SearchEventRequest(BaseModel):
    """Search event tracking request."""
    user_id: Optional[str] = None
    query: str
    search_type: str = "semantic"
    results_count: int
    response_time_ms: float
    clicked_results: Optional[List[int]] = None
    session_id: Optional[str] = None


class SearchSuggestionsRequest(BaseModel):
    """Search suggestions request."""
    partial_query: str
    user_id: Optional[str] = None
    limit: int = 5


class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response."""
    query: str
    suggestions: List[Dict[str, Any]]
    generated_at: datetime


class SearchInsightsRequest(BaseModel):
    """Search insights request."""
    time_period_days: int = 7
    insight_types: Optional[List[str]] = None


class SearchInsightsResponse(BaseModel):
    """Search insights response."""
    time_period_days: int
    total_searches: int
    success_rate: float
    click_through_rate: float
    average_response_time_ms: float
    popular_queries: List[Dict[str, Any]]
    search_type_distribution: Dict[str, int]
    insights: List[str]
    generated_at: datetime


class ExportDataRequest(BaseModel):
    """Export data request."""
    start_date: str
    end_date: str
    format: str = "json"


# Search analytics endpoints
@router.post("/report", response_model=SearchAnalyticsResponse)
async def generate_search_analytics_report(request: SearchAnalyticsRequest) -> SearchAnalyticsResponse:
    """
    Generate comprehensive search analytics report.

    This endpoint provides a complete analysis of search performance,
    user behavior, and optimization opportunities.
    """
    try:
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=request.time_period_days,
            include_user_behavior=request.include_user_behavior,
            include_optimization_insights=request.include_optimization_insights
        )

        # Convert dataclasses to dicts for JSON serialization
        response = SearchAnalyticsResponse(
            report_id=report.report_id,
            time_period=report.time_period,
            performance_metrics=report.performance_metrics.__dict__,
            query_analytics=report.query_analytics.__dict__,
            user_behavior=report.user_behavior.__dict__,
            content_discovery=report.content_discovery.__dict__,
            optimization_insights=report.optimization_insights.__dict__,
            key_findings=report.key_findings,
            recommendations=report.recommendations,
            generated_at=report.generated_at
        )

        logger.info(f"Generated comprehensive search analytics report: {len(response.key_findings)} findings")
        return response

    except Exception as e:
        logger.error(f"Search analytics report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search analytics report generation failed: {str(e)}")


@router.post("/track-event", response_model=Dict[str, Any])
async def track_search_event(request: SearchEventRequest) -> Dict[str, Any]:
    """
    Track a search event for analytics.

    This endpoint records search events to build analytics and improve
    search experience over time.
    """
    try:
        await search_analytics_service.track_search_event(
            user_id=request.user_id,
            query=request.query,
            search_type=request.search_type,
            results_count=request.results_count,
            response_time_ms=request.response_time_ms,
            clicked_results=request.clicked_results,
            session_id=request.session_id
        )

        response = {
            "message": "Search event tracked successfully",
            "query": request.query,
            "search_type": request.search_type,
            "results_count": request.results_count,
            "tracked_at": datetime.now().isoformat()
        }

        logger.info(f"Tracked search event: '{request.query}' -> {request.results_count} results")
        return response

    except Exception as e:
        logger.error(f"Search event tracking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search event tracking failed: {str(e)}")


@router.post("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(request: SearchSuggestionsRequest) -> SearchSuggestionsResponse:
    """
    Get search suggestions based on partial query.

    This endpoint provides intelligent search suggestions to improve
    user experience and guide query formulation.
    """
    try:
        suggestions = await search_analytics_service.get_search_suggestions(
            partial_query=request.partial_query,
            user_id=request.user_id,
            limit=request.limit
        )

        response = SearchSuggestionsResponse(
            query=request.partial_query,
            suggestions=suggestions,
            generated_at=datetime.now()
        )

        logger.info(f"Generated {len(suggestions)} suggestions for query '{request.partial_query}'")
        return response

    except Exception as e:
        logger.error(f"Search suggestions generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search suggestions generation failed: {str(e)}")


@router.post("/insights", response_model=SearchInsightsResponse)
async def get_search_insights(request: SearchInsightsRequest) -> SearchInsightsResponse:
    """
    Get real-time search insights.

    This endpoint provides current search performance metrics and insights
    for monitoring and optimization.
    """
    try:
        insights = await search_analytics_service.get_search_insights(
            time_period_days=request.time_period_days
        )

        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])

        # Generate insights list
        insights_list = []
        if insights.get("success_rate", 0) > 0.9:
            insights_list.append("Search performance is excellent")
        elif insights.get("success_rate", 0) < 0.8:
            insights_list.append("Search success rate needs improvement")

        if insights.get("click_through_rate", 0) > 0.6:
            insights_list.append("Good user engagement with search results")
        else:
            insights_list.append("Click-through rate could be improved")

        if insights.get("average_response_time_ms", 0) > 500:
            insights_list.append("Search response time is slow")
        else:
            insights_list.append("Search response time is acceptable")

        response = SearchInsightsResponse(
            time_period_days=request.time_period_days,
            total_searches=insights.get("total_searches", 0),
            success_rate=insights.get("success_rate", 0.0),
            click_through_rate=insights.get("click_through_rate", 0.0),
            average_response_time_ms=insights.get("average_response_time_ms", 0.0),
            popular_queries=insights.get("popular_queries", []),
            search_type_distribution=insights.get("search_type_distribution", {}),
            insights=insights_list,
            generated_at=datetime.now()
        )

        logger.info(f"Generated search insights for {request.time_period_days} days")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search insights generation failed: {str(e)}")


@router.get("/performance", response_model=Dict[str, Any])
async def get_search_performance(
    time_period_days: int = Query(default=7, description="Time period in days")
) -> Dict[str, Any]:
    """
    Get search performance metrics.

    Returns detailed performance metrics for search operations.
    """
    try:
        # Get comprehensive report and extract performance metrics
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days,
            include_user_behavior=False,
            include_optimization_insights=False
        )

        performance = {
            "time_period_days": time_period_days,
            "total_searches": report.performance_metrics.total_searches,
            "successful_searches": report.performance_metrics.successful_searches,
            "failed_searches": report.performance_metrics.failed_searches,
            "average_response_time_ms": report.performance_metrics.average_response_time_ms,
            "success_rate": report.performance_metrics.success_rate,
            "no_results_rate": report.performance_metrics.no_results_rate,
            "average_results_per_query": report.performance_metrics.average_results_per_query,
            "top_clicked_positions": report.performance_metrics.top_clicked_positions,
            "search_type_distribution": report.performance_metrics.search_type_distribution,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Retrieved search performance metrics for {time_period_days} days")
        return performance

    except Exception as e:
        logger.error(f"Search performance retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search performance retrieval failed: {str(e)}")


@router.get("/queries", response_model=Dict[str, Any])
async def get_query_analytics(
    time_period_days: int = Query(default=30, description="Time period in days"),
    limit: int = Query(default=20, description="Maximum results")
) -> Dict[str, Any]:
    """
    Get query analytics and patterns.

    Returns detailed analysis of search queries, patterns, and user behavior.
    """
    try:
        # Get comprehensive report and extract query analytics
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days,
            include_user_behavior=True,
            include_optimization_insights=False
        )

        query_analytics = {
            "time_period_days": time_period_days,
            "total_queries": report.query_analytics.total_queries,
            "unique_queries": report.query_analytics.unique_queries,
            "top_queries": report.query_analytics.top_queries[:limit],
            "query_length_distribution": report.query_analytics.query_length_distribution,
            "query_complexity_distribution": report.query_analytics.query_complexity_distribution,
            "popular_query_patterns": report.query_analytics.popular_query_patterns,
            "seasonal_query_trends": report.query_analytics.seasonal_query_trends,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Retrieved query analytics for {time_period_days} days")
        return query_analytics

    except Exception as e:
        logger.error(f"Query analytics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query analytics retrieval failed: {str(e)}")


@router.get("/user-behavior", response_model=Dict[str, Any])
async def get_user_search_behavior(
    time_period_days: int = Query(default=30, description="Time period in days")
) -> Dict[str, Any]:
    """
    Get user search behavior analytics.

    Returns insights into how users interact with search functionality.
    """
    try:
        # Get comprehensive report and extract user behavior
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days,
            include_user_behavior=True,
            include_optimization_insights=False
        )

        user_behavior = {
            "time_period_days": time_period_days,
            "session_length_avg": report.user_behavior.session_length_avg,
            "queries_per_session_avg": report.user_behavior.queries_per_session_avg,
            "click_through_rate": report.user_behavior.click_through_rate,
            "abandonment_rate": report.user_behavior.abandonment_rate,
            "refinement_rate": report.user_behavior.refinement_rate,
            "popular_search_times": report.user_behavior.popular_search_times,
            "device_type_distribution": report.user_behavior.device_type_distribution,
            "user_segments": report.user_behavior.user_segments,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Retrieved user search behavior for {time_period_days} days")
        return user_behavior

    except Exception as e:
        logger.error(f"User search behavior retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"User search behavior retrieval failed: {str(e)}")


@router.get("/optimization", response_model=Dict[str, Any])
async def get_search_optimization_insights(
    time_period_days: int = Query(default=30, description="Time period in days")
) -> Dict[str, Any]:
    """
    Get search optimization insights and recommendations.

    Returns actionable insights for improving search performance and user experience.
    """
    try:
        # Get comprehensive report and extract optimization insights
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days,
            include_user_behavior=False,
            include_optimization_insights=True
        )

        optimization = {
            "time_period_days": time_period_days,
            "low_performance_queries": report.optimization_insights.low_performance_queries,
            "high_opportunity_content": report.optimization_insights.high_opportunity_content,
            "search_experience_issues": report.optimization_insights.search_experience_issues,
            "recommended_improvements": report.optimization_insights.recommended_improvements,
            "predicted_search_trends": report.optimization_insights.predicted_search_trends,
            "content_gap_analysis": report.optimization_insights.content_gap_analysis,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Retrieved search optimization insights for {time_period_days} days")
        return optimization

    except Exception as e:
        logger.error(f"Search optimization insights retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search optimization insights retrieval failed: {str(e)}")


@router.post("/export", response_model=Dict[str, Any])
async def export_search_data(request: ExportDataRequest) -> Dict[str, Any]:
    """
    Export search analytics data.

    This endpoint exports search data for external analysis and reporting.
    """
    try:
        from datetime import datetime

        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date)

        exported_data = await search_analytics_service.export_search_data(
            start_date=start_date,
            end_date=end_date,
            format=request.format
        )

        if "error" in exported_data:
            raise HTTPException(status_code=500, detail=exported_data["error"])

        response = {
            "export_format": request.format,
            "time_range": {
                "start": request.start_date,
                "end": request.end_date
            },
            "total_records": exported_data.get("total_records", 0),
            "data": exported_data.get("data", []),
            "exported_at": datetime.now().isoformat()
        }

        logger.info(f"Exported {exported_data.get('total_records', 0)} search records")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search data export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search data export failed: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def get_search_analytics_health() -> Dict[str, Any]:
    """
    Get search analytics service health status.

    Returns health information about the search analytics service.
    """
    try:
        health_status = {
            "service": "search_analytics",
            "status": "healthy",
            "tracked_events": len(search_analytics_service.search_logs),
            "performance_cache_size": len(search_analytics_service.performance_cache),
            "timestamp": datetime.now().isoformat()
        }

        return health_status

    except Exception as e:
        logger.error(f"Search analytics health check failed: {e}")
        return {
            "service": "search_analytics",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_search_analytics_capabilities() -> Dict[str, Any]:
    """
    Get search analytics service capabilities.

    Returns information about available search analytics features.
    """
    try:
        capabilities = {
            "analytics_features": [
                "search_performance_tracking",
                "query_pattern_analysis",
                "user_behavior_insights",
                "content_discovery_metrics",
                "optimization_recommendations",
                "real_time_monitoring"
            ],
            "metrics_tracked": [
                "search_success_rate",
                "response_time",
                "click_through_rate",
                "query_complexity",
                "user_engagement",
                "content_relevance"
            ],
            "export_formats": ["json", "csv"],
            "insights_types": [
                "performance_optimization",
                "user_experience_improvement",
                "content_gap_analysis",
                "trend_prediction",
                "behavioral_patterns"
            ],
            "features": [
                "real_time_event_tracking",
                "intelligent_suggestions",
                "automated_insights",
                "performance_monitoring",
                "user_segmentation",
                "trend_analysis"
            ]
        }

        response = {
            "capabilities": capabilities,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get search analytics capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get search analytics capabilities: {str(e)}")


@router.get("/trends", response_model=List[Dict[str, Any]])
async def get_search_trends(
    time_period_days: int = Query(default=30, description="Time period in days"),
    trend_type: Optional[str] = Query(default=None, description="Filter by trend type")
) -> List[Dict[str, Any]]:
    """
    Get search trends and patterns.

    Returns trending search queries and patterns over the specified time period.
    """
    try:
        # Get query analytics and extract trends
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days,
            include_user_behavior=True,
            include_optimization_insights=False
        )

        trends = []

        # Extract query trends
        for trend in report.query_analytics.seasonal_query_trends:
            if not trend_type or trend.get("trend", "").lower() == trend_type.lower():
                trends.append({
                    "trend_type": "query_popularity",
                    "query": trend.get("top_topic", "unknown"),
                    "period": trend.get("period", ""),
                    "searches": trend.get("queries", 0),
                    "change_direction": trend.get("trend", "stable"),
                    "insights": [f"Query '{trend.get('top_topic', '')}' showing {trend.get('trend', 'stable')} trend"]
                })

        # Add performance trends
        if report.performance_metrics.success_rate > 0.9:
            trends.append({
                "trend_type": "performance",
                "metric": "success_rate",
                "value": report.performance_metrics.success_rate,
                "change_direction": "stable_high",
                "insights": ["Search success rate is consistently high"]
            })

        logger.info(f"Retrieved {len(trends)} search trends")
        return trends

    except Exception as e:
        logger.error(f"Search trends retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search trends retrieval failed: {str(e)}")


@router.get("/popular-queries", response_model=List[Dict[str, Any]])
async def get_popular_queries(
    time_period_days: int = Query(default=7, description="Time period in days"),
    limit: int = Query(default=10, description="Maximum results"),
    min_searches: int = Query(default=1, description="Minimum search count")
) -> List[Dict[str, Any]]:
    """
    Get most popular search queries.

    Returns the most frequently searched queries in the specified time period.
    """
    try:
        # Get query analytics
        report = await search_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days,
            include_user_behavior=False,
            include_optimization_insights=False
        )

        # Filter and limit popular queries
        popular_queries = [
            query for query in report.query_analytics.top_queries
            if query.get("count", 0) >= min_searches
        ][:limit]

        logger.info(f"Retrieved {len(popular_queries)} popular queries")
        return popular_queries

    except Exception as e:
        logger.error(f"Popular queries retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Popular queries retrieval failed: {str(e)}")


@router.get("/performance-summary", response_model=Dict[str, Any])
async def get_performance_summary(
    time_period_days: int = Query(default=7, description="Time period in days")
) -> Dict[str, Any]:
    """
    Get search performance summary.

    Returns a quick overview of search performance metrics.
    """
    try:
        # Get performance metrics
        performance = await search_analytics_service._analyze_search_performance(
            datetime.now() - timedelta(days=time_period_days),
            datetime.now()
        )

        summary = {
            "time_period_days": time_period_days,
            "total_searches": performance.total_searches,
            "success_rate": performance.success_rate,
            "average_response_time_ms": performance.average_response_time_ms,
            "no_results_rate": performance.no_results_rate,
            "average_results_per_query": performance.average_results_per_query,
            "performance_score": self._calculate_performance_score(performance),
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Generated performance summary for {time_period_days} days")
        return summary

    except Exception as e:
        logger.error(f"Performance summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance summary generation failed: {str(e)}")


def _calculate_performance_score(self, performance) -> float:
    """Calculate overall performance score."""
    if performance.total_searches == 0:
        return 0.0

    # Weighted score based on different metrics
    success_weight = 0.4
    speed_weight = 0.3
    results_weight = 0.3

    success_score = performance.success_rate
    speed_score = max(0, 1 - (performance.average_response_time_ms / 1000))  # Penalize slow responses
    results_score = min(1.0, performance.average_results_per_query / 20)  # Reward more results

    return (success_score * success_weight +
            speed_score * speed_weight +
            results_score * results_weight)


@router.post("/bulk-track", response_model=Dict[str, Any])
async def bulk_track_search_events(events: List[SearchEventRequest]) -> Dict[str, Any]:
    """
    Bulk track multiple search events.

    This endpoint allows tracking multiple search events in a single request
    for better performance when processing batches of events.
    """
    try:
        successful_tracks = 0
        failed_tracks = 0

        for event in events:
            try:
                await search_analytics_service.track_search_event(
                    user_id=event.user_id,
                    query=event.query,
                    search_type=event.search_type,
                    results_count=event.results_count,
                    response_time_ms=event.response_time_ms,
                    clicked_results=event.clicked_results,
                    session_id=event.session_id
                )
                successful_tracks += 1
            except Exception as e:
                logger.error(f"Failed to track search event for query '{event.query}': {e}")
                failed_tracks += 1

        response = {
            "message": f"Bulk search event tracking completed",
            "total_events": len(events),
            "successful_tracks": successful_tracks,
            "failed_tracks": failed_tracks,
            "success_rate": successful_tracks / len(events) if events else 0,
            "processed_at": datetime.now().isoformat()
        }

        logger.info(f"Bulk tracked {successful_tracks} search events, {failed_tracks} failed")
        return response

    except Exception as e:
        logger.error(f"Bulk search event tracking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk search event tracking failed: {str(e)}")


@router.get("/real-time", response_model=Dict[str, Any])
async def get_real_time_search_metrics() -> Dict[str, Any]:
    """
    Get real-time search metrics.

    Returns current search performance metrics for monitoring dashboards.
    """
    try:
        # Get insights for last 24 hours
        insights = await search_analytics_service.get_search_insights(time_period_days=1)

        if "error" in insights:
            return {
                "status": "no_data",
                "message": "No recent search data available",
                "timestamp": datetime.now().isoformat()
            }

        real_time_metrics = {
            "status": "active",
            "current_searches_24h": insights.get("total_searches", 0),
            "success_rate_24h": insights.get("success_rate", 0.0),
            "click_through_rate_24h": insights.get("click_through_rate", 0.0),
            "average_response_time_ms_24h": insights.get("average_response_time_ms", 0.0),
            "top_queries_24h": insights.get("popular_queries", [])[:5],
            "timestamp": datetime.now().isoformat()
        }

        return real_time_metrics

    except Exception as e:
        logger.error(f"Real-time search metrics retrieval failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }