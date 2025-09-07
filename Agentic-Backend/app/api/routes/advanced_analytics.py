"""
API routes for Advanced Analytics service.

Provides endpoints for analytics dashboard, insights, forecasting,
and custom reporting capabilities.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.advanced_analytics import (
    advanced_analytics_service,
    MetricType,
    AnalyticsTimeframe
)
from app.utils.logging import get_logger

logger = get_logger("advanced_analytics_api")
router = APIRouter(prefix="/api/v1/analytics", tags=["Advanced Analytics"])


# Pydantic models for API
class RecordMetricRequest(BaseModel):
    """Request model for recording metrics."""
    metric_type: str
    metric_name: str
    value: float
    metadata: Optional[Dict[str, Any]] = None


class DashboardResponse(BaseModel):
    """Response model for analytics dashboard."""
    timeframe: str
    metrics: Dict[str, Any]
    insights: List[Dict[str, Any]]
    generated_at: str


class ReportRequest(BaseModel):
    """Request model for generating reports."""
    report_type: str
    timeframe: Optional[str] = "week"
    filters: Optional[Dict[str, Any]] = None


class ReportResponse(BaseModel):
    """Response model for analytics reports."""
    report_id: str
    report_type: str
    timeframe: str
    generated_at: str
    data: Dict[str, Any]


class ForecastRequest(BaseModel):
    """Request model for generating forecasts."""
    metric_type: str
    metric_name: Optional[str] = None
    forecast_periods: int = 7


class ForecastResponse(BaseModel):
    """Response model for predictive forecasts."""
    forecast_id: str
    metric_name: str
    forecast_type: str
    forecast_values: List[Dict[str, Any]]
    confidence_intervals: List[Dict[str, Any]]
    accuracy_score: float
    created_at: str


class InsightsResponse(BaseModel):
    """Response model for analytics insights."""
    insights: List[Dict[str, Any]]
    total_count: int
    generated_at: str


@router.post("/metrics/record")
async def record_metric(request: RecordMetricRequest):
    """Record a metric for analytics tracking."""
    try:
        # Validate metric type
        try:
            metric_type = MetricType(request.metric_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid metric type: {request.metric_type}")

        # Record the metric
        await advanced_analytics_service.record_metric(
            metric_type=metric_type,
            metric_name=request.metric_name,
            value=request.value,
            metadata=request.metadata
        )

        return {
            "message": "Metric recorded successfully",
            "metric_type": request.metric_type,
            "metric_name": request.metric_name,
            "value": request.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record metric: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record metric: {str(e)}")


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    timeframe: str = Query("day", description="Timeframe for analytics (hour, day, week, month, quarter, year)")
):
    """Get comprehensive analytics dashboard data."""
    try:
        # Validate timeframe
        try:
            tf_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        # Get dashboard data
        dashboard_data = await advanced_analytics_service.get_dashboard_data(tf_enum)

        return DashboardResponse(
            timeframe=dashboard_data["timeframe"],
            metrics=dashboard_data["metrics"],
            insights=dashboard_data["insights"],
            generated_at=dashboard_data["generated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """Generate a custom analytics report."""
    try:
        # Validate timeframe
        try:
            tf_enum = AnalyticsTimeframe(request.timeframe or "week")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {request.timeframe}")

        # Generate report
        report = await advanced_analytics_service.generate_report(
            report_type=request.report_type,
            timeframe=tf_enum,
            filters=request.filters
        )

        return ReportResponse(
            report_id=report["report_id"],
            report_type=report["report_type"],
            timeframe=report["timeframe"],
            generated_at=report["generated_at"],
            data=report["data"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get a previously generated report."""
    try:
        # Try to get from cache first
        from app.services.performance_cache import performance_cache
        cached_report = await performance_cache.get(f"analytics_report:{report_id}")

        if cached_report:
            return cached_report
        else:
            raise HTTPException(status_code=404, detail="Report not found or expired")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")


@router.post("/forecast", response_model=ForecastResponse)
async def generate_forecast(request: ForecastRequest):
    """Generate a predictive forecast for a metric."""
    try:
        # Validate metric type
        try:
            metric_type = MetricType(request.metric_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid metric type: {request.metric_type}")

        # Generate forecast
        forecast = await advanced_analytics_service.get_forecast(
            metric_type=metric_type,
            metric_name=request.metric_name,
            forecast_periods=request.forecast_periods
        )

        if not forecast:
            raise HTTPException(status_code=404, detail="Insufficient data for forecasting")

        return ForecastResponse(
            forecast_id=forecast["forecast_id"],
            metric_name=forecast["metric_name"],
            forecast_type=forecast["forecast_type"],
            forecast_values=forecast["forecast_values"],
            confidence_intervals=forecast["confidence_intervals"],
            accuracy_score=forecast["accuracy_score"],
            created_at=forecast["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    timeframe: str = Query("week", description="Timeframe for insights analysis"),
    insight_type: Optional[str] = Query(None, description="Filter by insight type"),
    min_severity: Optional[str] = Query(None, description="Minimum severity level (low, medium, high, critical)")
):
    """Get analytics insights with optional filtering."""
    try:
        # Validate timeframe
        try:
            tf_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        # Get insights
        from app.services.advanced_analytics import InsightGenerator
        insight_generator = InsightGenerator(advanced_analytics_service.collector)
        all_insights = await insight_generator.generate_insights(tf_enum)

        # Apply filters
        filtered_insights = all_insights

        if insight_type:
            filtered_insights = [i for i in filtered_insights if i.insight_type == insight_type]

        if min_severity:
            severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            min_level = severity_levels.get(min_severity, 0)
            filtered_insights = [
                i for i in filtered_insights
                if severity_levels.get(i.severity, 0) >= min_level
            ]

        # Convert to response format
        insights_data = []
        for insight in filtered_insights:
            insights_data.append({
                "id": insight.insight_id,
                "title": insight.title,
                "description": insight.description,
                "type": insight.insight_type,
                "severity": insight.severity,
                "confidence": insight.confidence,
                "data": insight.data,
                "recommendations": insight.recommendations,
                "created_at": insight.created_at.isoformat()
            })

        return InsightsResponse(
            insights=insights_data,
            total_count=len(insights_data),
            generated_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/metrics")
async def get_metrics(
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    timeframe: str = Query("day", description="Timeframe for metrics"),
    aggregation: str = Query("sum", description="Aggregation method (sum, avg, min, max, count)"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)")
):
    """Get aggregated metrics data."""
    try:
        # Validate inputs
        try:
            tf_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        if metric_type:
            try:
                mt_enum = MetricType(metric_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid metric type: {metric_type}")
        else:
            mt_enum = None

        # Parse time filters
        from datetime import datetime
        start_dt = None
        end_dt = None

        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")

        # Get metrics
        aggregated = await advanced_analytics_service.collector.get_aggregated_metrics(
            metric_type=mt_enum,
            metric_name=metric_name,
            timeframe=tf_enum,
            aggregation=aggregation
        )

        return {
            "metric_type": metric_type,
            "metric_name": metric_name,
            "timeframe": timeframe,
            "aggregation": aggregation,
            "start_time": start_time,
            "end_time": end_time,
            "data": aggregated
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/metrics/types")
async def get_metric_types():
    """Get available metric types and names."""
    try:
        # Get all available metrics from recent data
        all_data_points = advanced_analytics_service.collector.data_points[-1000:]  # Last 1000 points

        metric_types = set()
        metric_names = set()

        for point in all_data_points:
            metric_types.add(point.metric_type.value)
            metric_names.add(point.metric_name)

        return {
            "available_metric_types": sorted(list(metric_types)),
            "available_metric_names": sorted(list(metric_names)),
            "total_data_points": len(all_data_points)
        }

    except Exception as e:
        logger.error(f"Failed to get metric types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metric types: {str(e)}")


@router.get("/health")
async def analytics_health_check():
    """Health check for analytics service."""
    try:
        # Check service components
        collector_status = "healthy"
        data_points = len(advanced_analytics_service.collector.data_points)

        if data_points == 0:
            collector_status = "initializing"

        # Check if collection task is running
        collection_active = (
            advanced_analytics_service.collector.collection_task is not None and
            not advanced_analytics_service.collector.collection_task.done()
        )

        return {
            "overall_health": "healthy" if collection_active else "degraded",
            "components": {
                "data_collector": collector_status,
                "collection_task": "running" if collection_active else "stopped"
            },
            "metrics": {
                "data_points_collected": data_points,
                "max_data_points": advanced_analytics_service.collector.max_data_points
            },
            "last_check": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return {
            "overall_health": "unhealthy",
            "components": {},
            "metrics": {},
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


@router.post("/maintenance/cleanup")
async def cleanup_old_data(days_to_keep: int = 30):
    """Clean up old analytics data."""
    try:
        if days_to_keep < 1:
            raise HTTPException(status_code=400, detail="days_to_keep must be at least 1")

        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Count data points before cleanup
        before_count = len(advanced_analytics_service.collector.data_points)

        # Remove old data points
        advanced_analytics_service.collector.data_points = [
            point for point in advanced_analytics_service.collector.data_points
            if point.timestamp >= cutoff_date
        ]

        after_count = len(advanced_analytics_service.collector.data_points)
        removed_count = before_count - after_count

        logger.info(f"Cleaned up {removed_count} old analytics data points")

        return {
            "message": f"Successfully cleaned up {removed_count} old data points",
            "days_kept": days_to_keep,
            "data_points_before": before_count,
            "data_points_after": after_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup analytics data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup data: {str(e)}")


@router.get("/export/metrics")
async def export_metrics(
    metric_type: Optional[str] = Query(None),
    timeframe: str = Query("week"),
    format: str = Query("json", description="Export format (json, csv)")
):
    """Export metrics data for external analysis."""
    try:
        # Validate inputs
        try:
            tf_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        if metric_type:
            try:
                mt_enum = MetricType(metric_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid metric type: {metric_type}")
        else:
            mt_enum = None

        # Get metrics data
        data_points = await advanced_analytics_service.collector.get_metrics(
            metric_type=mt_enum,
            timeframe=tf_enum
        )

        if format.lower() == "csv":
            # Convert to CSV format
            csv_data = "timestamp,metric_type,metric_name,value\n"
            for point in data_points:
                csv_data += f"{point.timestamp.isoformat()},{point.metric_type.value},{point.metric_name},{point.value}\n"

            return {
                "format": "csv",
                "data": csv_data,
                "record_count": len(data_points)
            }
        else:
            # JSON format
            json_data = []
            for point in data_points:
                json_data.append({
                    "timestamp": point.timestamp.isoformat(),
                    "metric_type": point.metric_type.value,
                    "metric_name": point.metric_name,
                    "value": point.value,
                    "metadata": point.metadata
                })

            return {
                "format": "json",
                "data": json_data,
                "record_count": len(data_points)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export metrics: {str(e)}")