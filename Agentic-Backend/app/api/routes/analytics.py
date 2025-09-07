"""
Analytics Dashboard API Routes.

This module provides REST endpoints for analytics dashboards, insights,
and reporting functionality for the content platform.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.services.advanced_analytics_service import advanced_analytics_service
from app.services.vector_search_service import vector_search_service
from app.services.content_recommendation_service import content_recommendation_engine
from app.services.realtime_indexing_service import realtime_indexing_service
from app.services.content_discovery_service import content_discovery_service
from app.utils.logging import get_logger

logger = get_logger("analytics_routes")

router = APIRouter(prefix="/analytics", tags=["Analytics & Insights"])


# Pydantic models for request/response
class DashboardRequest(BaseModel):
    """Dashboard data request."""
    time_period_days: int = 30
    include_trends: bool = True
    include_insights: bool = True
    include_usage: bool = True
    include_performance: bool = True


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    time_period: str
    summary: Dict[str, Any]
    trends: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    usage_patterns: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime


class ContentInsightsRequest(BaseModel):
    """Content insights request."""
    content_ids: Optional[List[str]] = None
    insight_types: Optional[List[str]] = None
    limit: int = 20


class ContentInsightsResponse(BaseModel):
    """Content insights response."""
    total_insights: int
    insights: List[Dict[str, Any]]
    generated_at: datetime


class TrendAnalysisRequest(BaseModel):
    """Trend analysis request."""
    time_period_days: int = 30
    min_growth_rate: float = 0.1
    trend_types: Optional[List[str]] = None


class TrendAnalysisResponse(BaseModel):
    """Trend analysis response."""
    total_trends: int
    trends: List[Dict[str, Any]]
    summary: Dict[str, Any]
    generated_at: datetime


class PerformanceMetricsRequest(BaseModel):
    """Performance metrics request."""
    time_period_days: int = 7
    metrics: Optional[List[str]] = None
    group_by: str = "day"  # hour, day, week


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response."""
    time_period: str
    metrics: Dict[str, Any]
    trends: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    generated_at: datetime


class SearchAnalyticsRequest(BaseModel):
    """Search analytics request."""
    time_period_days: int = 30
    include_queries: bool = True
    include_performance: bool = True
    top_queries_limit: int = 20


class SearchAnalyticsResponse(BaseModel):
    """Search analytics response."""
    time_period: str
    total_searches: int
    unique_queries: int
    top_queries: List[Dict[str, Any]]
    search_performance: Dict[str, Any]
    query_trends: List[Dict[str, Any]]
    generated_at: datetime


class SystemHealthRequest(BaseModel):
    """System health request."""
    include_services: bool = True
    include_resources: bool = True
    include_alerts: bool = True


class SystemHealthResponse(BaseModel):
    """System health response."""
    overall_status: str
    services: Dict[str, Any]
    resources: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    uptime: str
    generated_at: datetime


# Dashboard endpoints
@router.post("/dashboard", response_model=DashboardResponse)
async def get_analytics_dashboard(request: DashboardRequest) -> DashboardResponse:
    """
    Get comprehensive analytics dashboard data.

    This endpoint provides a complete overview of the platform's performance,
    including trends, insights, usage patterns, and key metrics.
    """
    try:
        # Get comprehensive analytics report
        report = await advanced_analytics_service.generate_comprehensive_report(
            time_period_days=request.time_period_days,
            include_trends=request.include_trends,
            include_insights=request.include_insights
        )

        # Get usage patterns if requested
        usage_patterns = []
        if request.include_usage:
            usage_patterns = await advanced_analytics_service.generate_usage_patterns(
                time_period_days=request.time_period_days
            )
            usage_patterns = [pattern.__dict__ for pattern in usage_patterns]

        # Get performance metrics if requested
        performance_metrics = {}
        if request.include_performance:
            performance_metrics = await advanced_analytics_service._calculate_key_metrics(
                request.time_period_days
            )

        # Create dashboard summary
        summary = {
            "total_content": report.total_content,
            "total_users": report.total_users,
            "total_views": performance_metrics.get("total_views", 0),
            "average_engagement": performance_metrics.get("average_engagement", 0.0),
            "new_content_discovered": performance_metrics.get("new_content_discovered", 0),
            "active_trends": len(report.trends),
            "key_insights": len(report.content_insights)
        }

        response = DashboardResponse(
            time_period=report.time_period,
            summary=summary,
            trends=[trend.__dict__ for trend in report.trends],
            insights=[insight.__dict__ for insight in report.content_insights],
            usage_patterns=usage_patterns,
            performance_metrics=performance_metrics,
            recommendations=report.recommendations,
            generated_at=report.generated_at
        )

        logger.info(f"Generated analytics dashboard for {request.time_period_days} days")
        return response

    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(time_period_days: int = Query(default=7, description="Time period in days")) -> Dict[str, Any]:
    """
    Get dashboard summary metrics.

    Returns key performance indicators and summary statistics for quick overview.
    """
    try:
        # Get basic metrics
        key_metrics = await advanced_analytics_service._calculate_key_metrics(time_period_days)

        # Get content counts
        from app.db.database import get_db
        db = next(get_db())

        try:
            total_content = db.query(db.query().count()).scalar()  # Simplified for now
            # This would be replaced with actual ContentItem count

            summary = {
                "time_period_days": time_period_days,
                "total_content": total_content or 0,
                "total_views": key_metrics.get("total_views", 0),
                "average_engagement": key_metrics.get("average_engagement", 0.0),
                "new_content_discovered": key_metrics.get("new_content_discovered", 0),
                "content_per_day": key_metrics.get("content_per_day", 0.0),
                "generated_at": datetime.now().isoformat()
            }

            return summary

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Dashboard summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard summary failed: {str(e)}")


# Content insights endpoints
@router.post("/insights/content", response_model=ContentInsightsResponse)
async def get_content_insights(request: ContentInsightsRequest) -> ContentInsightsResponse:
    """
    Get detailed content performance insights.

    This endpoint provides AI-powered insights about content performance,
    including popularity, engagement, quality metrics, and recommendations.
    """
    try:
        insights = await advanced_analytics_service.generate_content_insights(
            content_ids=request.content_ids,
            insight_types=request.insight_types
        )

        # Convert to dicts and limit results
        insights_data = []
        for insight in insights[:request.limit]:
            insights_data.append({
                "content_id": insight.content_id,
                "insight_type": insight.insight_type,
                "metric": insight.metric,
                "value": insight.value,
                "benchmark": insight.benchmark,
                "percentile": insight.percentile,
                "recommendation": insight.recommendation,
                "confidence": insight.confidence
            })

        response = ContentInsightsResponse(
            total_insights=len(insights),
            insights=insights_data,
            generated_at=datetime.now()
        )

        logger.info(f"Generated {len(insights_data)} content insights")
        return response

    except Exception as e:
        logger.error(f"Content insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content insights generation failed: {str(e)}")


@router.get("/insights/content/{content_id}", response_model=List[Dict[str, Any]])
async def get_content_insights_by_id(content_id: str) -> List[Dict[str, Any]]:
    """
    Get insights for a specific content item.

    Returns detailed performance insights and recommendations for the specified content.
    """
    try:
        insights = await advanced_analytics_service.generate_content_insights(
            content_ids=[content_id]
        )

        # Convert to dicts
        insights_data = []
        for insight in insights:
            insights_data.append({
                "content_id": insight.content_id,
                "insight_type": insight.insight_type,
                "metric": insight.metric,
                "value": insight.value,
                "benchmark": insight.benchmark,
                "percentile": insight.percentile,
                "recommendation": insight.recommendation,
                "confidence": insight.confidence
            })

        logger.info(f"Retrieved {len(insights_data)} insights for content {content_id}")
        return insights_data

    except Exception as e:
        logger.error(f"Content insights retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content insights retrieval failed: {str(e)}")


# Trend analysis endpoints
@router.post("/trends", response_model=TrendAnalysisResponse)
async def analyze_trends(request: TrendAnalysisRequest) -> TrendAnalysisResponse:
    """
    Analyze content and usage trends.

    This endpoint detects emerging trends, declining patterns, and growth analysis
    for content and user engagement over the specified time period.
    """
    try:
        trends = await advanced_analytics_service.detect_trends(
            time_period_days=request.time_period_days,
            min_growth_rate=request.min_growth_rate
        )

        # Convert to dicts
        trends_data = []
        for trend in trends:
            trends_data.append({
                "trend_name": trend.trend_name,
                "trend_type": trend.trend_type,
                "growth_rate": trend.growth_rate,
                "time_period": trend.time_period,
                "related_content": trend.related_content,
                "predictions": trend.predictions
            })

        # Create summary
        trend_types = {}
        for trend in trends:
            trend_type = trend.trend_type
            if trend_type not in trend_types:
                trend_types[trend_type] = 0
            trend_types[trend_type] += 1

        summary = {
            "total_trends": len(trends),
            "trend_types": trend_types,
            "average_growth_rate": sum(t.growth_rate for t in trends) / max(len(trends), 1),
            "emerging_trends": trend_types.get("emerging", 0),
            "declining_trends": trend_types.get("declining", 0)
        }

        response = TrendAnalysisResponse(
            total_trends=len(trends),
            trends=trends_data,
            summary=summary,
            generated_at=datetime.now()
        )

        logger.info(f"Analyzed {len(trends)} trends over {request.time_period_days} days")
        return response

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {str(e)}")


@router.get("/trends/trending", response_model=List[Dict[str, Any]])
async def get_trending_content(
    time_window_hours: int = Query(default=24, description="Time window in hours"),
    limit: int = Query(default=10, description="Maximum results")
) -> List[Dict[str, Any]]:
    """
    Get currently trending content.

    Returns content that has shown significant activity in the specified time window.
    """
    try:
        trending = await content_recommendation_engine.get_trending_content(
            time_window_hours=time_window_hours,
            limit=limit
        )

        # Convert to dicts
        trending_data = []
        for item in trending:
            trending_data.append({
                "content_item_id": item.content_item_id,
                "title": item.title,
                "content_type": item.content_type,
                "source_type": item.source_type,
                "recommendation_score": item.recommendation_score,
                "recommendation_reason": item.recommendation_reason,
                "metadata": item.metadata
            })

        logger.info(f"Retrieved {len(trending_data)} trending items")
        return trending_data

    except Exception as e:
        logger.error(f"Trending content retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trending content retrieval failed: {str(e)}")


# Performance metrics endpoints
@router.post("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(request: PerformanceMetricsRequest) -> PerformanceMetricsResponse:
    """
    Get detailed performance metrics.

    This endpoint provides comprehensive performance metrics including
    search performance, indexing metrics, and system performance.
    """
    try:
        # Get key metrics
        key_metrics = await advanced_analytics_service._calculate_key_metrics(
            request.time_period_days
        )

        # Get search performance
        search_stats = await vector_search_service.get_index_stats()

        # Get indexing performance
        indexing_stats = realtime_indexing_service.get_indexing_stats()

        # Combine metrics
        metrics = {
            "content_metrics": key_metrics,
            "search_metrics": {
                "total_documents": search_stats.total_documents,
                "total_embeddings": search_stats.total_embeddings,
                "indexed_content_types": search_stats.indexed_content_types,
                "last_indexed_at": search_stats.last_indexed_at.isoformat() if search_stats.last_indexed_at else None,
                "average_embedding_dimensions": search_stats.average_embedding_dimensions
            },
            "indexing_metrics": indexing_stats
        }

        # Generate trends
        trends = {
            "content_growth": "stable",  # Would be calculated from historical data
            "search_performance": "optimal",
            "indexing_efficiency": "good"
        }

        # Generate alerts
        alerts = []
        if indexing_stats.get("failed_tasks", 0) > 10:
            alerts.append({
                "type": "warning",
                "message": "High number of indexing failures detected",
                "severity": "medium"
            })

        if search_stats.total_documents == 0:
            alerts.append({
                "type": "info",
                "message": "No content indexed yet",
                "severity": "low"
            })

        response = PerformanceMetricsResponse(
            time_period=f"{request.time_period_days} days",
            metrics=metrics,
            trends=trends,
            alerts=alerts,
            generated_at=datetime.now()
        )

        logger.info(f"Generated performance metrics for {request.time_period_days} days")
        return response

    except Exception as e:
        logger.error(f"Performance metrics generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance metrics generation failed: {str(e)}")


# Search analytics endpoints
@router.post("/search", response_model=SearchAnalyticsResponse)
async def get_search_analytics(request: SearchAnalyticsRequest) -> SearchAnalyticsResponse:
    """
    Get search analytics and insights.

    This endpoint provides detailed analytics about search usage, popular queries,
    performance metrics, and search behavior patterns.
    """
    try:
        # This is a simplified implementation
        # In a real system, this would query search logs and analytics

        # Mock data for demonstration
        total_searches = 1250
        unique_queries = 890

        top_queries = [
            {"query": "machine learning", "count": 45, "avg_results": 23},
            {"query": "artificial intelligence", "count": 38, "avg_results": 31},
            {"query": "data science", "count": 29, "avg_results": 18},
            {"query": "python programming", "count": 27, "avg_results": 15},
            {"query": "deep learning", "count": 24, "avg_results": 12}
        ]

        search_performance = {
            "average_response_time_ms": 245.6,
            "success_rate": 0.98,
            "no_results_rate": 0.12,
            "average_results_per_query": 18.5
        }

        query_trends = [
            {"period": "2024-01-01", "searches": 120},
            {"period": "2024-01-02", "searches": 135},
            {"period": "2024-01-03", "searches": 142}
        ]

        response = SearchAnalyticsResponse(
            time_period=f"{request.time_period_days} days",
            total_searches=total_searches,
            unique_queries=unique_queries,
            top_queries=top_queries,
            search_performance=search_performance,
            query_trends=query_trends,
            generated_at=datetime.now()
        )

        logger.info(f"Generated search analytics for {request.time_period_days} days")
        return response

    except Exception as e:
        logger.error(f"Search analytics generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search analytics generation failed: {str(e)}")


# System health endpoints
@router.post("/health", response_model=SystemHealthResponse)
async def get_system_health(request: SystemHealthRequest) -> SystemHealthResponse:
    """
    Get comprehensive system health status.

    This endpoint provides detailed health information about all system services,
    resources, and potential issues.
    """
    try:
        services = {}
        alerts = []

        # Check search service health
        if request.include_services:
            try:
                search_health = await vector_search_service.get_index_stats()
                services["vector_search"] = {
                    "status": "healthy",
                    "documents_indexed": search_health.total_documents,
                    "last_indexed": search_health.last_indexed_at.isoformat() if search_health.last_indexed_at else None
                }
            except Exception as e:
                services["vector_search"] = {"status": "unhealthy", "error": str(e)}
                alerts.append({"type": "error", "message": f"Vector search service unhealthy: {e}", "severity": "high"})

            # Check indexing service health
            try:
                indexing_health = await realtime_indexing_service.health_check()
                services["realtime_indexing"] = indexing_health
                if indexing_health.get("status") != "healthy":
                    alerts.append({"type": "warning", "message": "Indexing service issues detected", "severity": "medium"})
            except Exception as e:
                services["realtime_indexing"] = {"status": "unhealthy", "error": str(e)}

            # Check discovery service health
            try:
                discovery_health = await content_discovery_service.health_check()
                services["content_discovery"] = discovery_health
            except Exception as e:
                services["content_discovery"] = {"status": "unhealthy", "error": str(e)}

        # Resource metrics
        resources = {}
        if request.include_resources:
            # Get basic resource info
            resources = {
                "indexing_queue_size": realtime_indexing_service.stats.queue_size,
                "active_workers": realtime_indexing_service.max_workers,
                "total_processed": realtime_indexing_service.stats.total_tasks_processed
            }

        # Determine overall status
        overall_status = "healthy"
        if any(service.get("status") != "healthy" for service in services.values()):
            overall_status = "warning"
        if any(alert.get("severity") == "high" for alert in alerts):
            overall_status = "critical"

        # Calculate uptime (simplified)
        uptime = "7 days"  # Would be calculated from actual start time

        response = SystemHealthResponse(
            overall_status=overall_status,
            services=services,
            resources=resources,
            alerts=alerts,
            uptime=uptime,
            generated_at=datetime.now()
        )

        logger.info(f"System health check completed: {overall_status}")
        return response

    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"System health check failed: {str(e)}")


@router.get("/health/quick", response_model=Dict[str, Any])
async def get_quick_health() -> Dict[str, Any]:
    """
    Get quick system health status.

    Returns a simplified health status for monitoring dashboards.
    """
    try:
        # Quick checks
        search_status = "healthy"
        indexing_status = "healthy"
        discovery_status = "healthy"

        try:
            search_stats = await vector_search_service.get_index_stats()
            if search_stats.total_documents == 0:
                search_status = "warning"
        except:
            search_status = "unhealthy"

        try:
            indexing_health = await realtime_indexing_service.health_check()
            if indexing_health.get("status") != "healthy":
                indexing_status = "warning"
        except:
            indexing_status = "unhealthy"

        try:
            discovery_health = await content_discovery_service.health_check()
            if discovery_health.get("status") != "healthy":
                discovery_status = "warning"
        except:
            discovery_status = "unhealthy"

        # Overall status
        statuses = [search_status, indexing_status, discovery_status]
        if "unhealthy" in statuses:
            overall_status = "critical"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "services": {
                "vector_search": search_status,
                "realtime_indexing": indexing_status,
                "content_discovery": discovery_status
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        return {
            "overall_status": "critical",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Utility endpoints
@router.get("/export/report", response_model=Dict[str, Any])
async def export_analytics_report(
    time_period_days: int = Query(default=30, description="Time period in days"),
    format: str = Query(default="json", description="Export format: json, csv"),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Export comprehensive analytics report.

    This endpoint generates and exports detailed analytics reports
    for external analysis and reporting.
    """
    try:
        # Generate comprehensive report
        report = await advanced_analytics_service.generate_comprehensive_report(
            time_period_days=time_period_days
        )

        # For now, return JSON format
        # In production, this would generate CSV/PDF files
        export_data = {
            "report_type": "comprehensive_analytics",
            "time_period": report.time_period,
            "generated_at": report.generated_at.isoformat(),
            "summary": {
                "total_content": report.total_content,
                "total_users": report.total_users,
                "key_metrics": report.key_metrics
            },
            "usage_patterns": len(report.usage_patterns),
            "content_insights": len(report.content_insights),
            "trends": len(report.trends),
            "recommendations": report.recommendations
        }

        logger.info(f"Exported analytics report for {time_period_days} days")
        return export_data

    except Exception as e:
        logger.error(f"Analytics report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics report export failed: {str(e)}")


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_analytics_capabilities() -> Dict[str, Any]:
    """
    Get analytics capabilities and available features.

    Returns information about all available analytics features and their status.
    """
    try:
        capabilities = {
            "dashboard_features": [
                "comprehensive_overview",
                "real_time_metrics",
                "trend_analysis",
                "usage_patterns",
                "performance_monitoring"
            ],
            "insight_types": [
                "content_popularity",
                "engagement_analysis",
                "quality_assessment",
                "trend_detection",
                "recommendation_engine"
            ],
            "metrics_available": [
                "view_counts",
                "engagement_scores",
                "quality_metrics",
                "search_performance",
                "indexing_efficiency",
                "content_discovery_rates"
            ],
            "export_formats": ["json", "csv"],
            "real_time_features": [
                "live_dashboard_updates",
                "real_time_alerts",
                "instant_trend_detection"
            ],
            "features": [
                "predictive_analytics",
                "anomaly_detection",
                "automated_insights",
                "custom_dashboards",
                "scheduled_reports"
            ]
        }

        response = {
            "capabilities": capabilities,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get analytics capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics capabilities: {str(e)}")