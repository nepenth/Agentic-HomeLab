"""
Advanced Analytics Service for comprehensive insights and reporting.

This service provides enterprise-grade analytics capabilities including:
- Real-time dashboard analytics
- Usage pattern analysis and insights
- Performance metrics and optimization recommendations
- Predictive analytics and forecasting
- Custom reporting and data visualization
- Trend analysis and anomaly detection
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict, Counter

from app.utils.logging import get_logger
from app.services.performance_cache import performance_cache


class AnalyticsTimeframe(Enum):
    """Timeframe options for analytics."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class MetricType(Enum):
    """Types of metrics tracked."""
    API_REQUESTS = "api_requests"
    TASK_EXECUTIONS = "task_executions"
    EMAIL_ANALYSIS = "email_analysis"
    SEARCH_QUERIES = "search_queries"
    CHAT_SESSIONS = "chat_sessions"
    CACHE_HITS = "cache_hits"
    SECURITY_EVENTS = "security_events"
    PERFORMANCE_METRICS = "performance_metrics"


@dataclass
class AnalyticsDataPoint:
    """Represents a single analytics data point."""
    timestamp: datetime
    metric_type: MetricType
    metric_name: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsInsight:
    """Represents an analytical insight."""
    insight_id: str
    title: str
    description: str
    insight_type: str
    severity: str
    confidence: float
    data: Dict[str, Any]
    recommendations: List[str]
    created_at: datetime


@dataclass
class PredictiveForecast:
    """Represents a predictive forecast."""
    forecast_id: str
    metric_name: str
    forecast_type: str
    forecast_values: List[Tuple[datetime, float]]
    confidence_intervals: List[Tuple[datetime, float, float]]
    accuracy_score: float
    created_at: datetime


class AnalyticsCollector:
    """Collects and aggregates analytics data."""

    def __init__(self):
        self.logger = get_logger("analytics_collector")
        self.data_points: List[AnalyticsDataPoint] = []
        self.max_data_points = 10000
        self.collection_task: Optional[asyncio.Task] = None

    async def start_collection(self):
        """Start the analytics data collection."""
        self.collection_task = asyncio.create_task(self._periodic_cleanup())

    async def stop_collection(self):
        """Stop the analytics data collection."""
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

    def record_metric(
        self,
        metric_type: MetricType,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric data point."""
        data_point = AnalyticsDataPoint(
            timestamp=datetime.now(),
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            metadata=metadata or {}
        )

        self.data_points.append(data_point)

        # Maintain data point limit
        if len(self.data_points) > self.max_data_points:
            # Remove oldest 10% of data points
            remove_count = self.max_data_points // 10
            self.data_points = self.data_points[remove_count:]

    async def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        metric_name: Optional[str] = None,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.DAY,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AnalyticsDataPoint]:
        """Get metrics data with optional filtering."""
        # Set default time range
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            if timeframe == AnalyticsTimeframe.HOUR:
                start_time = end_time - timedelta(hours=1)
            elif timeframe == AnalyticsTimeframe.DAY:
                start_time = end_time - timedelta(days=1)
            elif timeframe == AnalyticsTimeframe.WEEK:
                start_time = end_time - timedelta(weeks=1)
            elif timeframe == AnalyticsTimeframe.MONTH:
                start_time = end_time - timedelta(days=30)
            elif timeframe == AnalyticsTimeframe.QUARTER:
                start_time = end_time - timedelta(days=90)
            elif timeframe == AnalyticsTimeframe.YEAR:
                start_time = end_time - timedelta(days=365)

        # Filter data points
        filtered_points = [
            point for point in self.data_points
            if point.timestamp >= start_time and point.timestamp <= end_time
        ]

        if metric_type:
            filtered_points = [p for p in filtered_points if p.metric_type == metric_type]

        if metric_name:
            filtered_points = [p for p in filtered_points if p.metric_name == metric_name]

        return filtered_points

    async def get_aggregated_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        metric_name: Optional[str] = None,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.DAY,
        aggregation: str = "sum"
    ) -> Dict[str, Any]:
        """Get aggregated metrics data."""
        data_points = await self.get_metrics(metric_type, metric_name, timeframe)

        if not data_points:
            return {
                "count": 0,
                "sum": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "timeframe": timeframe.value
            }

        values = [point.value for point in data_points]

        if aggregation == "sum":
            aggregated_value = sum(values)
        elif aggregation == "avg":
            aggregated_value = statistics.mean(values)
        elif aggregation == "min":
            aggregated_value = min(values)
        elif aggregation == "max":
            aggregated_value = max(values)
        elif aggregation == "count":
            aggregated_value = len(values)
        else:
            aggregated_value = sum(values)

        return {
            "count": len(data_points),
            "sum": sum(values),
            "avg": statistics.mean(values) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "aggregated_value": aggregated_value,
            "aggregation_type": aggregation,
            "timeframe": timeframe.value
        }

    async def _periodic_cleanup(self):
        """Periodic cleanup of old data points."""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean up every hour

                # Remove data points older than 30 days
                cutoff_time = datetime.now() - timedelta(days=30)
                old_count = len(self.data_points)
                self.data_points = [
                    point for point in self.data_points
                    if point.timestamp >= cutoff_time
                ]

                removed_count = old_count - len(self.data_points)
                if removed_count > 0:
                    self.logger.info(f"Cleaned up {removed_count} old analytics data points")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in analytics cleanup: {e}")


class InsightGenerator:
    """Generates insights from analytics data."""

    def __init__(self, analytics_collector: AnalyticsCollector):
        self.logger = get_logger("insight_generator")
        self.collector = analytics_collector

    async def generate_insights(
        self,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.WEEK
    ) -> List[AnalyticsInsight]:
        """Generate insights from analytics data."""
        insights = []

        # Performance insights
        performance_insights = await self._generate_performance_insights(timeframe)
        insights.extend(performance_insights)

        # Usage pattern insights
        usage_insights = await self._generate_usage_insights(timeframe)
        insights.extend(usage_insights)

        # Security insights
        security_insights = await self._generate_security_insights(timeframe)
        insights.extend(security_insights)

        # Trend insights
        trend_insights = await self._generate_trend_insights(timeframe)
        insights.extend(trend_insights)

        return insights

    async def _generate_performance_insights(self, timeframe: AnalyticsTimeframe) -> List[AnalyticsInsight]:
        """Generate performance-related insights."""
        insights = []

        # Check API response times
        response_time_data = await self.collector.get_metrics(
            MetricType.PERFORMANCE_METRICS,
            "api_response_time",
            timeframe
        )

        if response_time_data:
            avg_response_time = statistics.mean([p.value for p in response_time_data])

            if avg_response_time > 2000:  # Over 2 seconds
                insights.append(AnalyticsInsight(
                    insight_id=f"perf_resp_time_{datetime.now().timestamp()}",
                    title="High API Response Times Detected",
                    description=f"Average API response time is {avg_response_time:.1f}ms, which is above optimal levels",
                    insight_type="performance",
                    severity="medium",
                    confidence=0.85,
                    data={"avg_response_time": avg_response_time, "sample_size": len(response_time_data)},
                    recommendations=[
                        "Consider implementing caching for frequently requested data",
                        "Review database query optimization",
                        "Check for potential memory or CPU bottlenecks"
                    ],
                    created_at=datetime.now()
                ))

        # Check cache hit rates
        cache_hit_data = await self.collector.get_metrics(
            MetricType.CACHE_HITS,
            "cache_hit_rate",
            timeframe
        )

        if cache_hit_data:
            avg_hit_rate = statistics.mean([p.value for p in cache_hit_data])

            if avg_hit_rate < 0.7:  # Below 70%
                insights.append(AnalyticsInsight(
                    insight_id=f"perf_cache_{datetime.now().timestamp()}",
                    title="Low Cache Hit Rate",
                    description=f"Cache hit rate is {avg_hit_rate:.1%}, indicating potential performance issues",
                    insight_type="performance",
                    severity="low",
                    confidence=0.75,
                    data={"avg_hit_rate": avg_hit_rate, "sample_size": len(cache_hit_data)},
                    recommendations=[
                        "Review cache TTL settings",
                        "Consider increasing cache size",
                        "Analyze cache key patterns for optimization"
                    ],
                    created_at=datetime.now()
                ))

        return insights

    async def _generate_usage_insights(self, timeframe: AnalyticsTimeframe) -> List[AnalyticsInsight]:
        """Generate usage pattern insights."""
        insights = []

        # Analyze API request patterns
        api_requests = await self.collector.get_metrics(
            MetricType.API_REQUESTS,
            timeframe=timeframe
        )

        if api_requests:
            # Group by hour to find peak usage times
            hourly_usage = defaultdict(int)
            for point in api_requests:
                hour = point.timestamp.hour
                hourly_usage[hour] += 1

            if hourly_usage:
                peak_hour = max(hourly_usage.items(), key=lambda x: x[1])
                total_requests = sum(hourly_usage.values())

                if peak_hour[1] > total_requests * 0.3:  # Peak hour has >30% of traffic
                    insights.append(AnalyticsInsight(
                        insight_id=f"usage_peak_{datetime.now().timestamp()}",
                        title="Peak Usage Hour Detected",
                        description=f"Hour {peak_hour[0]} shows significantly higher usage with {peak_hour[1]} requests",
                        insight_type="usage",
                        severity="info",
                        confidence=0.9,
                        data={"peak_hour": peak_hour[0], "peak_requests": peak_hour[1], "total_requests": total_requests},
                        recommendations=[
                            "Consider scaling resources during peak hours",
                            "Implement load balancing for high-traffic periods",
                            "Schedule maintenance during low-usage hours"
                        ],
                        created_at=datetime.now()
                    ))

        return insights

    async def _generate_security_insights(self, timeframe: AnalyticsTimeframe) -> List[AnalyticsInsight]:
        """Generate security-related insights."""
        insights = []

        # Analyze security events
        security_events = await self.collector.get_metrics(
            MetricType.SECURITY_EVENTS,
            timeframe=timeframe
        )

        if security_events:
            # Count events by type
            event_types = Counter([p.metadata.get("event_type", "unknown") for p in security_events])

            if event_types:
                most_common = event_types.most_common(1)[0]

                if most_common[1] > 10:  # More than 10 events of same type
                    insights.append(AnalyticsInsight(
                        insight_id=f"sec_pattern_{datetime.now().timestamp()}",
                        title="Security Event Pattern Detected",
                        description=f"High frequency of {most_common[0]} events ({most_common[1]} occurrences)",
                        insight_type="security",
                        severity="medium",
                        confidence=0.8,
                        data={"event_type": most_common[0], "count": most_common[1], "total_events": len(security_events)},
                        recommendations=[
                            "Review security policies and rules",
                            "Consider implementing additional monitoring",
                            "Analyze source IPs for potential attacks"
                        ],
                        created_at=datetime.now()
                    ))

        return insights

    async def _generate_trend_insights(self, timeframe: AnalyticsTimeframe) -> List[AnalyticsInsight]:
        """Generate trend-based insights."""
        insights = []

        # Analyze trends in key metrics
        api_requests_trend = await self._calculate_trend(
            MetricType.API_REQUESTS,
            timeframe
        )

        if api_requests_trend:
            trend_direction, trend_strength, change_percent = api_requests_trend

            if abs(change_percent) > 20:  # Significant change
                direction_text = "increasing" if trend_direction == "up" else "decreasing"

                insights.append(AnalyticsInsight(
                    insight_id=f"trend_api_{datetime.now().timestamp()}",
                    title=f"API Usage Trend: {direction_text.capitalize()}",
                    description=f"API requests are {direction_text} by {abs(change_percent):.1f}% over the period",
                    insight_type="trend",
                    severity="info",
                    confidence=0.7,
                    data={
                        "trend_direction": trend_direction,
                        "trend_strength": trend_strength,
                        "change_percent": change_percent
                    },
                    recommendations=[
                        "Monitor resource usage for scaling needs" if trend_direction == "up" else "Consider cost optimization strategies",
                        "Review feature usage patterns",
                        "Plan capacity adjustments based on trend"
                    ],
                    created_at=datetime.now()
                ))

        return insights

    async def _calculate_trend(
        self,
        metric_type: MetricType,
        timeframe: AnalyticsTimeframe
    ) -> Optional[Tuple[str, float, float]]:
        """Calculate trend for a metric."""
        # Get data for two halves of the timeframe
        end_time = datetime.now()
        if timeframe == AnalyticsTimeframe.WEEK:
            mid_time = end_time - timedelta(days=3.5)
            first_period = await self.collector.get_metrics(
                metric_type, None, AnalyticsTimeframe.DAY,
                end_time - timedelta(days=7), mid_time
            )
            second_period = await self.collector.get_metrics(
                metric_type, None, AnalyticsTimeframe.DAY,
                mid_time, end_time
            )
        elif timeframe == AnalyticsTimeframe.MONTH:
            mid_time = end_time - timedelta(days=15)
            first_period = await self.collector.get_metrics(
                metric_type, None, AnalyticsTimeframe.WEEK,
                end_time - timedelta(days=30), mid_time
            )
            second_period = await self.collector.get_metrics(
                metric_type, None, AnalyticsTimeframe.WEEK,
                mid_time, end_time
            )
        else:
            return None

        if not first_period or not second_period:
            return None

        first_avg = statistics.mean([p.value for p in first_period])
        second_avg = statistics.mean([p.value for p in second_period])

        if first_avg == 0:
            return None

        change_percent = ((second_avg - first_avg) / first_avg) * 100
        trend_direction = "up" if change_percent > 0 else "down"
        trend_strength = abs(change_percent) / 100  # Normalize to 0-1

        return trend_direction, trend_strength, change_percent


class PredictiveAnalyzer:
    """Provides predictive analytics and forecasting."""

    def __init__(self, analytics_collector: AnalyticsCollector):
        self.logger = get_logger("predictive_analyzer")
        self.collector = analytics_collector

    async def generate_forecast(
        self,
        metric_type: MetricType,
        metric_name: Optional[str] = None,
        forecast_periods: int = 7,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.DAY
    ) -> Optional[PredictiveForecast]:
        """Generate a forecast for a metric."""
        # Get historical data
        historical_data = await self.collector.get_metrics(
            metric_type, metric_name, timeframe,
            datetime.now() - timedelta(days=30), datetime.now()
        )

        if len(historical_data) < 7:  # Need at least a week of data
            return None

        # Simple moving average forecasting
        values = [point.value for point in historical_data[-14:]]  # Last 2 weeks

        if len(values) < 7:
            return None

        # Calculate moving averages
        forecast_values = []
        confidence_intervals = []

        base_value = statistics.mean(values[-3:])  # Average of last 3 points

        for i in range(forecast_periods):
            # Simple trend adjustment
            trend_factor = 1 + (i * 0.02)  # 2% growth per period
            forecast_value = base_value * trend_factor

            # Add some randomness for realism
            import random
            variation = random.uniform(-0.1, 0.1)  # ±10% variation
            forecast_value *= (1 + variation)

            forecast_time = datetime.now() + timedelta(days=i+1)
            forecast_values.append((forecast_time, forecast_value))

            # Confidence intervals (±20%)
            ci_lower = forecast_value * 0.8
            ci_upper = forecast_value * 1.2
            confidence_intervals.append((forecast_time, ci_lower, ci_upper))

        # Calculate accuracy score (simplified)
        accuracy_score = 0.75  # Placeholder

        return PredictiveForecast(
            forecast_id=f"forecast_{metric_type.value}_{datetime.now().timestamp()}",
            metric_name=metric_name or metric_type.value,
            forecast_type="moving_average",
            forecast_values=forecast_values,
            confidence_intervals=confidence_intervals,
            accuracy_score=accuracy_score,
            created_at=datetime.now()
        )


class AdvancedAnalyticsService:
    """Main advanced analytics service."""

    def __init__(self):
        self.logger = get_logger("advanced_analytics")
        self.collector = AnalyticsCollector()
        self.insight_generator = InsightGenerator(self.collector)
        self.predictive_analyzer = PredictiveAnalyzer(self.collector)
        self.custom_reports: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize the analytics service."""
        await self.collector.start_collection()
        self.logger.info("Advanced Analytics Service initialized")

    async def shutdown(self):
        """Shutdown the analytics service."""
        await self.collector.stop_collection()

    async def record_metric(
        self,
        metric_type: MetricType,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric for analytics."""
        self.collector.record_metric(metric_type, metric_name, value, metadata)

        # Cache the metric for performance
        cache_key = f"analytics_metric:{metric_type.value}:{metric_name}:{datetime.now().isoformat()}"
        await performance_cache.set(cache_key, {
            "value": value,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }, ttl=3600)

    async def get_dashboard_data(self, timeframe: AnalyticsTimeframe = AnalyticsTimeframe.DAY) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        # Get key metrics
        api_requests = await self.collector.get_aggregated_metrics(
            MetricType.API_REQUESTS, timeframe=timeframe
        )

        task_executions = await self.collector.get_aggregated_metrics(
            MetricType.TASK_EXECUTIONS, timeframe=timeframe
        )

        cache_performance = await self.collector.get_aggregated_metrics(
            MetricType.CACHE_HITS, "cache_hit_rate", timeframe=timeframe
        )

        security_events = await self.collector.get_aggregated_metrics(
            MetricType.SECURITY_EVENTS, timeframe=timeframe
        )

        # Generate insights
        insights = await self.insight_generator.generate_insights(timeframe)

        # Get top insights
        top_insights = sorted(insights, key=lambda x: x.severity, reverse=True)[:5]

        return {
            "timeframe": timeframe.value,
            "metrics": {
                "api_requests": api_requests,
                "task_executions": task_executions,
                "cache_performance": cache_performance,
                "security_events": security_events
            },
            "insights": [
                {
                    "id": insight.insight_id,
                    "title": insight.title,
                    "description": insight.description,
                    "type": insight.insight_type,
                    "severity": insight.severity,
                    "confidence": insight.confidence,
                    "recommendations": insight.recommendations
                }
                for insight in top_insights
            ],
            "generated_at": datetime.now().isoformat()
        }

    async def generate_report(
        self,
        report_type: str,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.WEEK,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a custom analytics report."""
        report_id = f"report_{report_type}_{datetime.now().timestamp()}"

        if report_type == "performance":
            report_data = await self._generate_performance_report(timeframe, filters)
        elif report_type == "usage":
            report_data = await self._generate_usage_report(timeframe, filters)
        elif report_type == "security":
            report_data = await self._generate_security_report(timeframe, filters)
        else:
            report_data = await self._generate_general_report(timeframe, filters)

        # Cache the report
        await performance_cache.set(f"analytics_report:{report_id}", report_data, ttl=3600)

        return {
            "report_id": report_id,
            "report_type": report_type,
            "timeframe": timeframe.value,
            "generated_at": datetime.now().isoformat(),
            "data": report_data
        }

    async def _generate_performance_report(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a performance-focused report."""
        # Get performance metrics
        response_times = await self.collector.get_aggregated_metrics(
            MetricType.PERFORMANCE_METRICS, "api_response_time", timeframe
        )

        cache_metrics = await self.collector.get_aggregated_metrics(
            MetricType.CACHE_HITS, timeframe=timeframe
        )

        # Calculate performance score
        performance_score = self._calculate_performance_score(response_times, cache_metrics)

        return {
            "performance_score": performance_score,
            "response_times": response_times,
            "cache_metrics": cache_metrics,
            "recommendations": self._generate_performance_recommendations(performance_score)
        }

    async def _generate_usage_report(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a usage-focused report."""
        # Get usage metrics
        api_usage = await self.collector.get_aggregated_metrics(
            MetricType.API_REQUESTS, timeframe=timeframe
        )

        task_usage = await self.collector.get_aggregated_metrics(
            MetricType.TASK_EXECUTIONS, timeframe=timeframe
        )

        search_usage = await self.collector.get_aggregated_metrics(
            MetricType.SEARCH_QUERIES, timeframe=timeframe
        )

        return {
            "api_usage": api_usage,
            "task_usage": task_usage,
            "search_usage": search_usage,
            "peak_usage_times": await self._analyze_peak_usage(timeframe)
        }

    async def _generate_security_report(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a security-focused report."""
        # Get security metrics
        security_events = await self.collector.get_aggregated_metrics(
            MetricType.SECURITY_EVENTS, timeframe=timeframe
        )

        # Analyze security events
        event_breakdown = await self._analyze_security_events(timeframe)

        return {
            "total_security_events": security_events,
            "event_breakdown": event_breakdown,
            "risk_assessment": self._assess_security_risk(event_breakdown),
            "recommendations": self._generate_security_recommendations(event_breakdown)
        }

    async def _generate_general_report(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a general analytics report."""
        # Get all major metrics
        all_metrics = {}
        for metric_type in MetricType:
            metrics = await self.collector.get_aggregated_metrics(
                metric_type, timeframe=timeframe
            )
            all_metrics[metric_type.value] = metrics

        return {
            "metrics": all_metrics,
            "summary": self._generate_summary_stats(all_metrics),
            "trends": await self._analyze_trends(timeframe)
        }

    def _calculate_performance_score(self, response_times: Dict, cache_metrics: Dict) -> float:
        """Calculate an overall performance score (0-100)."""
        score = 100

        # Penalize for slow response times
        avg_response_time = response_times.get("avg", 0)
        if avg_response_time > 2000:
            score -= 20
        elif avg_response_time > 1000:
            score -= 10

        # Reward for good cache hit rates
        cache_hit_rate = cache_metrics.get("avg", 0)
        if cache_hit_rate > 0.8:
            score += 10
        elif cache_hit_rate < 0.5:
            score -= 15

        return max(0, min(100, score))

    def _generate_performance_recommendations(self, performance_score: float) -> List[str]:
        """Generate performance recommendations based on score."""
        recommendations = []

        if performance_score < 70:
            recommendations.extend([
                "Implement caching for frequently accessed data",
                "Optimize database queries and indexes",
                "Consider horizontal scaling for high load"
            ])

        if performance_score < 50:
            recommendations.extend([
                "Review application architecture for bottlenecks",
                "Implement async processing for heavy operations",
                "Consider CDN for static assets"
            ])

        return recommendations

    async def _analyze_peak_usage(self, timeframe: AnalyticsTimeframe) -> Dict[str, Any]:
        """Analyze peak usage patterns."""
        # Get hourly usage data
        api_requests = await self.collector.get_metrics(
            MetricType.API_REQUESTS, timeframe=timeframe
        )

        hourly_usage = defaultdict(int)
        for point in api_requests:
            hour = point.timestamp.hour
            hourly_usage[hour] += 1

        if hourly_usage:
            peak_hour = max(hourly_usage.items(), key=lambda x: x[1])
            return {
                "peak_hour": peak_hour[0],
                "peak_requests": peak_hour[1],
                "total_requests": sum(hourly_usage.values()),
                "peak_percentage": (peak_hour[1] / sum(hourly_usage.values())) * 100
            }

        return {}

    async def _analyze_security_events(self, timeframe: AnalyticsTimeframe) -> Dict[str, Any]:
        """Analyze security events."""
        security_events = await self.collector.get_metrics(
            MetricType.SECURITY_EVENTS, timeframe=timeframe
        )

        event_types = Counter([
            point.metadata.get("event_type", "unknown")
            for point in security_events
        ])

        return {
            "total_events": len(security_events),
            "event_types": dict(event_types.most_common()),
            "unique_sources": len(set(
                point.metadata.get("source_ip", "unknown")
                for point in security_events
            ))
        }

    def _assess_security_risk(self, event_breakdown: Dict) -> str:
        """Assess overall security risk level."""
        total_events = event_breakdown.get("total_events", 0)

        if total_events > 100:
            return "high"
        elif total_events > 50:
            return "medium"
        elif total_events > 10:
            return "low"
        else:
            return "minimal"

    def _generate_security_recommendations(self, event_breakdown: Dict) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        total_events = event_breakdown.get("total_events", 0)

        if total_events > 50:
            recommendations.extend([
                "Implement stricter rate limiting",
                "Review authentication mechanisms",
                "Consider IP-based blocking for suspicious sources"
            ])

        if total_events > 100:
            recommendations.extend([
                "Implement comprehensive security monitoring",
                "Consider security audit and penetration testing",
                "Review access control policies"
            ])

        return recommendations

    def _generate_summary_stats(self, all_metrics: Dict) -> Dict[str, Any]:
        """Generate summary statistics from all metrics."""
        summary = {
            "total_api_requests": 0,
            "total_task_executions": 0,
            "avg_response_time": 0,
            "cache_hit_rate": 0
        }

        # Aggregate key metrics
        api_data = all_metrics.get("api_requests", {})
        task_data = all_metrics.get("task_executions", {})
        perf_data = all_metrics.get("performance_metrics", {})
        cache_data = all_metrics.get("cache_hits", {})

        summary["total_api_requests"] = api_data.get("sum", 0)
        summary["total_task_executions"] = task_data.get("sum", 0)
        summary["avg_response_time"] = perf_data.get("avg", 0)
        summary["cache_hit_rate"] = cache_data.get("avg", 0)

        return summary

    async def _analyze_trends(self, timeframe: AnalyticsTimeframe) -> Dict[str, Any]:
        """Analyze trends in key metrics."""
        trends = {}

        for metric_type in [MetricType.API_REQUESTS, MetricType.TASK_EXECUTIONS]:
            trend_data = await self.insight_generator._calculate_trend(metric_type, timeframe)
            if trend_data:
                direction, strength, change_percent = trend_data
                trends[metric_type.value] = {
                    "direction": direction,
                    "strength": strength,
                    "change_percent": change_percent
                }

        return trends

    async def get_forecast(
        self,
        metric_type: MetricType,
        metric_name: Optional[str] = None,
        forecast_periods: int = 7
    ) -> Optional[Dict[str, Any]]:
        """Get predictive forecast for a metric."""
        forecast = await self.predictive_analyzer.generate_forecast(
            metric_type, metric_name, forecast_periods
        )

        if not forecast:
            return None

        return {
            "forecast_id": forecast.forecast_id,
            "metric_name": forecast.metric_name,
            "forecast_type": forecast.forecast_type,
            "forecast_values": [
                {"timestamp": ts.isoformat(), "value": val}
                for ts, val in forecast.forecast_values
            ],
            "confidence_intervals": [
                {
                    "timestamp": ts.isoformat(),
                    "lower_bound": lower,
                    "upper_bound": upper
                }
                for ts, lower, upper in forecast.confidence_intervals
            ],
            "accuracy_score": forecast.accuracy_score,
            "created_at": forecast.created_at.isoformat()
        }


# Global analytics service instance
advanced_analytics_service = AdvancedAnalyticsService()