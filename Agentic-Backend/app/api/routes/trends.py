"""
Trend Detection and Predictive Analytics API Routes.

This module provides REST endpoints for trend analysis, predictive insights,
and anomaly detection in content and user behavior patterns.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from app.services.trend_detection_service import trend_detection_service
from app.utils.logging import get_logger

logger = get_logger("trends_routes")

router = APIRouter(prefix="/trends", tags=["Trend Detection & Analytics"])


# Pydantic models for request/response
class TrendAnalysisRequest(BaseModel):
    """Trend analysis request."""
    time_period_days: int = 30
    min_confidence: float = 0.7
    include_predictions: bool = True
    focus_areas: Optional[List[str]] = None  # content, users, performance, etc.


class TrendAnalysisResponse(BaseModel):
    """Trend analysis response."""
    report_id: str
    time_period: str
    trends_detected: List[Dict[str, Any]]
    predictive_insights: List[Dict[str, Any]]
    anomalies_detected: List[Dict[str, Any]]
    key_findings: List[str]
    recommendations: List[str]
    confidence_summary: Dict[str, int]
    generated_at: datetime


class PredictiveInsightsRequest(BaseModel):
    """Predictive insights request."""
    time_period_days: int = 30
    insight_types: Optional[List[str]] = None
    confidence_threshold: float = 0.7


class PredictiveInsightsResponse(BaseModel):
    """Predictive insights response."""
    total_insights: int
    insights: List[Dict[str, Any]]
    time_horizon: str
    generated_at: datetime


class AnomalyDetectionRequest(BaseModel):
    """Anomaly detection request."""
    time_period_days: int = 7
    severity_threshold: str = "medium"  # low, medium, high, critical
    anomaly_types: Optional[List[str]] = None


class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection response."""
    total_anomalies: int
    anomalies: List[Dict[str, Any]]
    severity_distribution: Dict[str, int]
    time_period: str
    generated_at: datetime


class TrendDetailsRequest(BaseModel):
    """Trend details request."""
    trend_id: str
    include_historical_data: bool = False
    data_points_limit: int = 50


class TrendDetailsResponse(BaseModel):
    """Trend details response."""
    trend_id: str
    pattern_type: str
    trend_name: str
    description: str
    confidence_score: float
    growth_rate: float
    time_period_days: int
    related_content: List[str]
    affected_metrics: List[str]
    predictions: Dict[str, Any]
    insights: List[str]
    historical_data: Optional[List[Dict[str, Any]]] = None
    generated_at: datetime


# Trend analysis endpoints
@router.post("/analyze", response_model=TrendAnalysisResponse)
async def analyze_trends_comprehensive(request: TrendAnalysisRequest) -> TrendAnalysisResponse:
    """
    Perform comprehensive trend analysis.

    This endpoint provides a complete analysis of trends, predictive insights,
    and anomalies across content, users, and system performance.
    """
    try:
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=request.time_period_days,
            min_confidence=request.min_confidence,
            include_predictions=request.include_predictions
        )

        # Convert dataclasses to dicts for JSON serialization
        response = TrendAnalysisResponse(
            report_id=report.report_id,
            time_period=report.time_period,
            trends_detected=[trend.__dict__ for trend in report.trends_detected],
            predictive_insights=[insight.__dict__ for insight in report.predictive_insights],
            anomalies_detected=[anomaly.__dict__ for anomaly in report.anomalies_detected],
            key_findings=report.key_findings,
            recommendations=report.recommendations,
            confidence_summary=report.confidence_summary,
            generated_at=report.generated_at
        )

        logger.info(f"Generated comprehensive trend analysis: {len(response.trends_detected)} trends, {len(response.predictive_insights)} insights")
        return response

    except Exception as e:
        logger.error(f"Comprehensive trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comprehensive trend analysis failed: {str(e)}")


@router.post("/predictive-insights", response_model=PredictiveInsightsResponse)
async def get_predictive_insights(request: PredictiveInsightsRequest) -> PredictiveInsightsResponse:
    """
    Get predictive insights and forecasts.

    This endpoint provides AI-powered predictions about future trends,
    content performance, and user behavior patterns.
    """
    try:
        # Get comprehensive report and extract predictive insights
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=request.time_period_days,
            min_confidence=request.confidence_threshold,
            include_predictions=True
        )

        # Filter insights by type if specified
        insights = report.predictive_insights
        if request.insight_types:
            insights = [
                insight for insight in insights
                if insight.insight_type in request.insight_types
            ]

        # Convert to dicts
        insights_data = [insight.__dict__ for insight in insights]

        response = PredictiveInsightsResponse(
            total_insights=len(insights),
            insights=insights_data,
            time_horizon=f"{request.time_period_days} days",
            generated_at=datetime.now()
        )

        logger.info(f"Generated {len(insights_data)} predictive insights")
        return response

    except Exception as e:
        logger.error(f"Predictive insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Predictive insights generation failed: {str(e)}")


@router.post("/anomalies", response_model=AnomalyDetectionResponse)
async def detect_anomalies(request: AnomalyDetectionRequest) -> AnomalyDetectionResponse:
    """
    Detect anomalies in metrics and patterns.

    This endpoint identifies unusual patterns, spikes, drops, or other
    anomalies in content performance and user behavior.
    """
    try:
        # Get comprehensive report and extract anomalies
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=request.time_period_days,
            min_confidence=0.5,  # Lower threshold for anomaly detection
            include_predictions=False
        )

        # Filter anomalies by severity and type
        anomalies = report.anomalies_detected

        if request.severity_threshold != "low":
            severity_levels = ["low", "medium", "high", "critical"]
            min_severity_index = severity_levels.index(request.severity_threshold)
            anomalies = [
                anomaly for anomaly in anomalies
                if severity_levels.index(anomaly.severity) >= min_severity_index
            ]

        if request.anomaly_types:
            anomalies = [
                anomaly for anomaly in anomalies
                if anomaly.anomaly_type in request.anomaly_types
            ]

        # Calculate severity distribution
        severity_distribution = {}
        for anomaly in anomalies:
            severity = anomaly.severity
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1

        # Convert to dicts
        anomalies_data = [anomaly.__dict__ for anomaly in anomalies]

        response = AnomalyDetectionResponse(
            total_anomalies=len(anomalies),
            anomalies=anomalies_data,
            severity_distribution=severity_distribution,
            time_period=f"{request.time_period_days} days",
            generated_at=datetime.now()
        )

        logger.info(f"Detected {len(anomalies_data)} anomalies")
        return response

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


@router.get("/trends", response_model=List[Dict[str, Any]])
async def get_detected_trends(
    time_period_days: int = Query(default=30, description="Time period in days"),
    pattern_type: Optional[str] = Query(default=None, description="Filter by pattern type"),
    min_confidence: float = Query(default=0.6, description="Minimum confidence score")
) -> List[Dict[str, Any]]:
    """
    Get currently detected trends.

    Returns a list of active trends with their characteristics and predictions.
    """
    try:
        # Get comprehensive report
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=time_period_days,
            min_confidence=min_confidence,
            include_predictions=True
        )

        # Filter trends
        trends = report.trends_detected
        if pattern_type:
            trends = [trend for trend in trends if trend.pattern_type == pattern_type]

        # Convert to dicts
        trends_data = [trend.__dict__ for trend in trends]

        logger.info(f"Retrieved {len(trends_data)} trends")
        return trends_data

    except Exception as e:
        logger.error(f"Trend retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend retrieval failed: {str(e)}")


@router.get("/trends/{trend_id}", response_model=TrendDetailsResponse)
async def get_trend_details(
    trend_id: str,
    include_historical_data: bool = Query(default=False, description="Include historical data points"),
    data_points_limit: int = Query(default=50, description="Maximum historical data points")
) -> TrendDetailsResponse:
    """
    Get detailed information about a specific trend.

    Returns comprehensive details about a trend including historical data,
    predictions, and related insights.
    """
    try:
        # Find trend in recent analysis
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=30,
            min_confidence=0.5,
            include_predictions=True
        )

        trend = None
        for t in report.trends_detected:
            if t.pattern_id == trend_id:
                trend = t
                break

        if not trend:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")

        # Get historical data if requested
        historical_data = None
        if include_historical_data:
            # This would query actual historical data
            historical_data = [
                {"date": "2024-01-01", "value": 100, "trend": "baseline"},
                {"date": "2024-01-02", "value": 105, "trend": "increasing"},
                # ... more data points
            ][:data_points_limit]

        response = TrendDetailsResponse(
            trend_id=trend.pattern_id,
            pattern_type=trend.pattern_type,
            trend_name=trend.trend_name,
            description=trend.description,
            confidence_score=trend.confidence_score,
            growth_rate=trend.growth_rate,
            time_period_days=trend.time_period_days,
            related_content=trend.related_content,
            affected_metrics=trend.affected_metrics,
            predictions=trend.predictions,
            insights=trend.insights,
            historical_data=historical_data,
            generated_at=datetime.now()
        )

        logger.info(f"Retrieved details for trend {trend_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trend details retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend details retrieval failed: {str(e)}")


@router.get("/forecast/{metric}", response_model=Dict[str, Any])
async def get_metric_forecast(
    metric: str,
    time_period_days: int = Query(default=30, description="Historical data period"),
    forecast_days: int = Query(default=7, description="Forecast period")
) -> Dict[str, Any]:
    """
    Get forecast for a specific metric.

    Returns predictive forecast for the specified metric based on historical trends.
    """
    try:
        # Get trend analysis for the metric
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=time_period_days,
            min_confidence=0.5,
            include_predictions=True
        )

        # Find relevant trends for the metric
        relevant_trends = [
            trend for trend in report.trends_detected
            if metric in trend.affected_metrics
        ]

        if not relevant_trends:
            return {
                "metric": metric,
                "forecast_available": False,
                "message": f"No trend data available for metric: {metric}",
                "generated_at": datetime.now().isoformat()
            }

        # Use the most confident trend for forecasting
        best_trend = max(relevant_trends, key=lambda t: t.confidence_score)

        # Generate forecast based on trend
        forecast_data = []
        base_value = 100  # Would be actual current value

        for i in range(forecast_days):
            # Apply trend growth rate
            forecasted_value = base_value * (1 + best_trend.growth_rate) ** (i + 1)
            forecast_data.append({
                "day": i + 1,
                "forecasted_value": forecasted_value,
                "confidence_interval": {
                    "lower": forecasted_value * 0.9,
                    "upper": forecasted_value * 1.1
                }
            })

        response = {
            "metric": metric,
            "forecast_available": True,
            "forecast_period_days": forecast_days,
            "based_on_trend": best_trend.trend_name,
            "trend_confidence": best_trend.confidence_score,
            "forecast_data": forecast_data,
            "insights": best_trend.insights,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Generated {forecast_days}-day forecast for metric {metric}")
        return response

    except Exception as e:
        logger.error(f"Metric forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metric forecast failed: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def get_trends_health() -> Dict[str, Any]:
    """
    Get trend detection service health status.

    Returns health information about the trend detection service.
    """
    try:
        health_status = {
            "service": "trend_detection",
            "status": "healthy",
            "detected_trends": len(trend_detection_service.detected_trends),
            "anomaly_thresholds": trend_detection_service.anomaly_thresholds,
            "timestamp": datetime.now().isoformat()
        }

        return health_status

    except Exception as e:
        logger.error(f"Trend detection health check failed: {e}")
        return {
            "service": "trend_detection",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_trends_capabilities() -> Dict[str, Any]:
    """
    Get trend detection service capabilities.

    Returns information about available trend detection features and algorithms.
    """
    try:
        capabilities = {
            "trend_types": [
                "emerging",
                "declining",
                "growing",
                "sustained",
                "volatile",
                "seasonal"
            ],
            "analysis_methods": [
                "linear_regression",
                "time_series_analysis",
                "statistical_significance_testing",
                "pattern_recognition",
                "correlation_analysis"
            ],
            "predictive_models": [
                "trend_extrapolation",
                "seasonal_decomposition",
                "machine_learning_forecasting",
                "confidence_interval_calculation"
            ],
            "anomaly_detection": [
                "statistical_outlier_detection",
                "threshold_based_alerting",
                "pattern_anomaly_identification",
                "spike_drop_detection"
            ],
            "metrics_supported": [
                "view_count",
                "engagement_score",
                "quality_score",
                "user_interactions",
                "content_discovery_rate",
                "search_performance"
            ],
            "features": [
                "real_time_trend_detection",
                "predictive_analytics",
                "anomaly_alerting",
                "automated_insights",
                "historical_analysis",
                "forecasting"
            ]
        }

        response = {
            "capabilities": capabilities,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get trend detection capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trend detection capabilities: {str(e)}")


@router.get("/patterns/{pattern_type}", response_model=List[Dict[str, Any]])
async def get_trends_by_pattern(
    pattern_type: str,
    time_period_days: int = Query(default=30, description="Time period in days"),
    limit: int = Query(default=20, description="Maximum results")
) -> List[Dict[str, Any]]:
    """
    Get trends filtered by pattern type.

    Returns trends of a specific pattern type (emerging, declining, seasonal, etc.).
    """
    try:
        # Get comprehensive report
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=time_period_days,
            min_confidence=0.5,
            include_predictions=True
        )

        # Filter by pattern type
        filtered_trends = [
            trend for trend in report.trends_detected
            if trend.pattern_type == pattern_type
        ][:limit]

        # Convert to dicts
        trends_data = [trend.__dict__ for trend in filtered_trends]

        logger.info(f"Retrieved {len(trends_data)} {pattern_type} trends")
        return trends_data

    except Exception as e:
        logger.error(f"Pattern-based trend retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern-based trend retrieval failed: {str(e)}")


@router.post("/analyze-metric", response_model=Dict[str, Any])
async def analyze_specific_metric(
    metric: str = Query(..., description="Metric to analyze"),
    time_period_days: int = Query(default=30, description="Time period in days")
) -> Dict[str, Any]:
    """
    Analyze a specific metric for trends and patterns.

    Performs detailed analysis on a single metric to identify trends,
    seasonality, and predictive patterns.
    """
    try:
        # This would perform detailed analysis on the specific metric
        # For now, return mock analysis

        analysis = {
            "metric": metric,
            "time_period_days": time_period_days,
            "trend_analysis": {
                "direction": "increasing",
                "strength": "moderate",
                "confidence": 0.82,
                "growth_rate": 0.045
            },
            "seasonal_patterns": {
                "detected": True,
                "peak_days": ["Tuesday", "Wednesday"],
                "seasonal_strength": 0.65
            },
            "statistical_summary": {
                "mean": 125.4,
                "std_dev": 15.2,
                "min": 95.1,
                "max": 158.9,
                "data_points": 30
            },
            "forecast": {
                "next_7_days": [130.2, 132.1, 134.5, 136.8, 139.2, 141.7, 144.3],
                "confidence_interval": 0.85
            },
            "insights": [
                f"{metric} showing consistent upward trend",
                "Weekly pattern detected with mid-week peaks",
                "Forecast indicates continued growth"
            ],
            "generated_at": datetime.now().isoformat()
        }

        logger.info(f"Analyzed metric {metric} over {time_period_days} days")
        return analysis

    except Exception as e:
        logger.error(f"Specific metric analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Specific metric analysis failed: {str(e)}")


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_trend_alerts(
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    time_period_hours: int = Query(default=24, description="Time period in hours")
) -> List[Dict[str, Any]]:
    """
    Get trend-based alerts and notifications.

    Returns recent alerts about significant trends, anomalies, or
    important changes in the system.
    """
    try:
        # Get recent anomalies and significant trends
        report = await trend_detection_service.analyze_trends_comprehensive(
            time_period_days=max(1, time_period_hours // 24),
            min_confidence=0.7,
            include_predictions=False
        )

        alerts = []

        # Add anomaly alerts
        for anomaly in report.anomalies_detected:
            if not severity or anomaly.severity == severity:
                alerts.append({
                    "alert_type": "anomaly",
                    "severity": anomaly.severity,
                    "title": f"Anomaly Detected: {anomaly.affected_metric}",
                    "description": anomaly.description,
                    "detected_value": anomaly.detected_value,
                    "expected_value": anomaly.expected_value,
                    "deviation_percentage": anomaly.deviation_percentage,
                    "recommendations": anomaly.recommendations,
                    "timestamp": datetime.now().isoformat()
                })

        # Add significant trend alerts
        for trend in report.trends_detected:
            if trend.confidence_score > 0.8 and abs(trend.growth_rate) > 0.1:
                alerts.append({
                    "alert_type": "trend",
                    "severity": "medium" if trend.confidence_score > 0.9 else "low",
                    "title": f"Significant Trend: {trend.trend_name}",
                    "description": trend.description,
                    "confidence": trend.confidence_score,
                    "growth_rate": trend.growth_rate,
                    "insights": trend.insights,
                    "timestamp": datetime.now().isoformat()
                })

        # Sort by severity and timestamp
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: (severity_order.get(x["severity"], 4), x["timestamp"]), reverse=True)

        logger.info(f"Retrieved {len(alerts)} trend alerts")
        return alerts

    except Exception as e:
        logger.error(f"Trend alerts retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend alerts retrieval failed: {str(e)}")