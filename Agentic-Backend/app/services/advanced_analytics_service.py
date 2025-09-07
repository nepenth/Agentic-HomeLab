"""
Advanced Analytics Service for content insights and trend analysis.

This service provides comprehensive analytics capabilities including usage patterns,
content insights, trend detection, and predictive analytics for the content platform.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy import text, desc, and_, or_, func, extract
from sqlalchemy.orm import Session
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentEmbedding, ContentAnalytics
from app.services.vector_search_service import vector_search_service
from app.utils.logging import get_logger

logger = get_logger("advanced_analytics_service")


@dataclass
class UsagePattern:
    """Usage pattern analysis result."""
    pattern_type: str  # daily, weekly, seasonal, trending
    time_period: str
    metric: str
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float
    peak_times: List[str]
    insights: List[str]


@dataclass
class ContentInsight:
    """Content performance insight."""
    content_id: str
    insight_type: str  # popularity, engagement, quality, trend
    metric: str
    value: float
    benchmark: float
    percentile: float
    recommendation: str
    confidence: float


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    trend_name: str
    trend_type: str  # emerging, declining, stable, seasonal
    growth_rate: float
    time_period: str
    related_content: List[str]
    predictions: Dict[str, Any]


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""
    report_type: str
    time_period: str
    total_content: int
    total_users: int
    key_metrics: Dict[str, float]
    usage_patterns: List[UsagePattern]
    content_insights: List[ContentInsight]
    trends: List[TrendAnalysis]
    recommendations: List[str]
    generated_at: datetime


class AdvancedAnalyticsService:
    """Advanced analytics service for content platform insights."""

    def __init__(self):
        self.cache = {}
        self.cache_expiry = 3600  # 1 hour

    async def generate_usage_patterns(
        self,
        time_period_days: int = 30,
        granularity: str = "daily"
    ) -> List[UsagePattern]:
        """
        Analyze usage patterns over a time period.

        Args:
            time_period_days: Number of days to analyze
            granularity: Time granularity (hourly, daily, weekly)

        Returns:
            List of usage patterns
        """
        db = next(get_db())

        try:
            # Calculate time range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            # Query analytics data
            analytics_query = db.query(
                ContentAnalytics.content_item_id,
                ContentAnalytics.analytics_type,
                ContentAnalytics.period_start,
                ContentAnalytics.view_count,
                ContentAnalytics.engagement_score,
                ContentAnalytics.quality_score
            ).filter(
                ContentAnalytics.period_start >= start_date
            ).order_by(ContentAnalytics.period_start)

            results = analytics_query.all()

            # Group by time periods
            time_groups = defaultdict(list)
            for row in results:
                period_key = self._get_period_key(row.period_start, granularity)
                time_groups[period_key].append({
                    'content_id': str(row.content_item_id),
                    'type': row.analytics_type,
                    'views': row.view_count or 0,
                    'engagement': row.engagement_score or 0,
                    'quality': row.quality_score or 0
                })

            # Analyze patterns for each metric
            patterns = []

            for metric in ['views', 'engagement', 'quality']:
                pattern = await self._analyze_metric_pattern(
                    time_groups, metric, granularity
                )
                if pattern:
                    patterns.append(pattern)

            return patterns

        finally:
            db.close()

    def _get_period_key(self, timestamp: datetime, granularity: str) -> str:
        """Get period key for grouping."""
        if granularity == "hourly":
            return timestamp.strftime("%Y-%m-%d-%H")
        elif granularity == "daily":
            return timestamp.strftime("%Y-%m-%d")
        elif granularity == "weekly":
            return timestamp.strftime("%Y-%U")
        else:
            return timestamp.strftime("%Y-%m-%d")

    async def _analyze_metric_pattern(
        self,
        time_groups: Dict[str, List[Dict]],
        metric: str,
        granularity: str
    ) -> Optional[UsagePattern]:
        """Analyze usage pattern for a specific metric."""
        if not time_groups:
            return None

        # Extract time series data
        sorted_periods = sorted(time_groups.keys())
        values = []

        for period in sorted_periods:
            period_data = time_groups[period]
            if metric == 'views':
                total = sum(item['views'] for item in period_data)
            elif metric == 'engagement':
                total = sum(item['engagement'] for item in period_data) / max(len(period_data), 1)
            else:  # quality
                total = sum(item['quality'] for item in period_data) / max(len(period_data), 1)

            values.append(total)

        if len(values) < 3:  # Need at least 3 points for trend analysis
            return None

        # Calculate trend
        trend_direction, trend_strength = self._calculate_trend(values)

        # Find peak times
        peak_times = self._find_peak_times(sorted_periods, values, granularity)

        # Generate insights
        insights = self._generate_pattern_insights(
            metric, trend_direction, trend_strength, peak_times, granularity
        )

        return UsagePattern(
            pattern_type=self._classify_pattern_type(trend_direction, trend_strength),
            time_period=f"{len(sorted_periods)} {granularity} periods",
            metric=metric,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            peak_times=peak_times,
            insights=insights
        )

    def _calculate_trend(self, values: List[float]) -> Tuple[str, float]:
        """Calculate trend direction and strength."""
        if len(values) < 2:
            return "stable", 0.0

        # Simple linear regression
        x = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values)

        try:
            model = LinearRegression()
            model.fit(x, y)

            slope = model.coef_[0]
            r_squared = model.score(x, y)

            # Classify trend
            if abs(slope) < 0.01:
                direction = "stable"
            elif slope > 0:
                direction = "increasing"
            else:
                direction = "decreasing"

            strength = min(abs(slope) * r_squared, 1.0)  # Normalize strength

            return direction, strength

        except Exception:
            return "stable", 0.0

    def _find_peak_times(self, periods: List[str], values: List[float], granularity: str) -> List[str]:
        """Find peak usage times."""
        if not values:
            return []

        # Find local maxima
        peaks = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(periods[i])

        # If no local maxima, find the highest value
        if not peaks:
            max_idx = np.argmax(values)
            peaks.append(periods[max_idx])

        return peaks[:3]  # Return top 3 peaks

    def _generate_pattern_insights(
        self,
        metric: str,
        trend_direction: str,
        trend_strength: float,
        peak_times: List[str],
        granularity: str
    ) -> List[str]:
        """Generate insights from pattern analysis."""
        insights = []

        if trend_direction == "increasing" and trend_strength > 0.5:
            insights.append(f"Strong upward trend in {metric} with {trend_strength:.1%} growth")
        elif trend_direction == "decreasing" and trend_strength > 0.5:
            insights.append(f"Strong downward trend in {metric} with {trend_strength:.1%} decline")

        if peak_times:
            insights.append(f"Peak {metric} activity during: {', '.join(peak_times[:2])}")

        if granularity == "daily":
            insights.append(f"Daily pattern suggests optimal content timing around peak periods")

        return insights

    def _classify_pattern_type(self, trend_direction: str, trend_strength: float) -> str:
        """Classify the type of usage pattern."""
        if trend_direction == "increasing" and trend_strength > 0.7:
            return "rapid_growth"
        elif trend_direction == "increasing":
            return "growing"
        elif trend_direction == "decreasing":
            return "declining"
        else:
            return "stable"

    async def generate_content_insights(
        self,
        content_ids: Optional[List[str]] = None,
        insight_types: Optional[List[str]] = None
    ) -> List[ContentInsight]:
        """
        Generate insights for content performance.

        Args:
            content_ids: Specific content IDs to analyze (None for all)
            insight_types: Types of insights to generate

        Returns:
            List of content insights
        """
        db = next(get_db())

        try:
            # Query content with analytics
            query = db.query(
                ContentItem.id,
                ContentItem.title,
                ContentItem.content_type,
                ContentItem.quality_score,
                ContentItem.discovered_at,
                func.sum(ContentAnalytics.view_count).label('total_views'),
                func.avg(ContentAnalytics.engagement_score).label('avg_engagement'),
                func.count(ContentAnalytics.id).label('analytics_count')
            ).outerjoin(
                ContentAnalytics,
                ContentAnalytics.content_item_id == ContentItem.id
            )

            if content_ids:
                query = query.filter(ContentItem.id.in_(content_ids))

            query = query.group_by(ContentItem.id).having(
                func.count(ContentAnalytics.id) > 0
            )

            results = query.all()

            insights = []
            for row in results:
                content_insights = await self._analyze_single_content(row)
                insights.extend(content_insights)

            return insights

        finally:
            db.close()

    async def _analyze_single_content(self, content_row) -> List[ContentInsight]:
        """Analyze a single content item for insights."""
        insights = []

        # Popularity insight
        if content_row.total_views:
            popularity_percentile = await self._calculate_percentile(
                content_row.total_views, 'view_count'
            )

            if popularity_percentile > 80:
                recommendation = "This content is highly popular. Consider promoting it more."
            elif popularity_percentile < 20:
                recommendation = "This content has low visibility. Consider improving discoverability."
            else:
                recommendation = "Content popularity is average. Monitor engagement metrics."

            insights.append(ContentInsight(
                content_id=str(content_row.id),
                insight_type="popularity",
                metric="view_count",
                value=content_row.total_views,
                benchmark=await self._get_benchmark('view_count'),
                percentile=popularity_percentile,
                recommendation=recommendation,
                confidence=0.8
            ))

        # Engagement insight
        if content_row.avg_engagement:
            engagement_percentile = await self._calculate_percentile(
                content_row.avg_engagement, 'engagement_score'
            )

            if engagement_percentile > 85:
                recommendation = "Excellent engagement. This content resonates well with users."
            elif engagement_percentile < 30:
                recommendation = "Low engagement. Consider revising content or presentation."

            insights.append(ContentInsight(
                content_id=str(content_row.id),
                insight_type="engagement",
                metric="engagement_score",
                value=content_row.avg_engagement,
                benchmark=await self._get_benchmark('engagement_score'),
                percentile=engagement_percentile,
                recommendation=recommendation,
                confidence=0.75
            ))

        # Quality insight
        if content_row.quality_score:
            quality_percentile = await self._calculate_percentile(
                content_row.quality_score, 'quality_score'
            )

            if quality_percentile > 90:
                recommendation = "High-quality content. Use as a benchmark for other content."
            elif quality_percentile < 40:
                recommendation = "Quality could be improved. Consider content enhancement."

            insights.append(ContentInsight(
                content_id=str(content_row.id),
                insight_type="quality",
                metric="quality_score",
                value=content_row.quality_score,
                benchmark=await self._get_benchmark('quality_score'),
                percentile=quality_percentile,
                recommendation=recommendation,
                confidence=0.7
            ))

        return insights

    async def _calculate_percentile(self, value: float, metric: str) -> float:
        """Calculate percentile for a metric value."""
        db = next(get_db())

        try:
            if metric == 'view_count':
                query = db.query(ContentAnalytics.view_count).filter(
                    ContentAnalytics.view_count.isnot(None)
                )
            elif metric == 'engagement_score':
                query = db.query(ContentAnalytics.engagement_score).filter(
                    ContentAnalytics.engagement_score.isnot(None)
                )
            else:  # quality_score
                query = db.query(ContentItem.quality_score).filter(
                    ContentItem.quality_score.isnot(None)
                )

            all_values = [row[0] for row in query.all()]
            if not all_values:
                return 50.0

            # Calculate percentile
            sorted_values = sorted(all_values)
            rank = sum(1 for v in sorted_values if v <= value)
            percentile = (rank / len(sorted_values)) * 100

            return percentile

        finally:
            db.close()

    async def _get_benchmark(self, metric: str) -> float:
        """Get benchmark value for a metric."""
        db = next(get_db())

        try:
            if metric == 'view_count':
                result = db.query(func.avg(ContentAnalytics.view_count)).first()
            elif metric == 'engagement_score':
                result = db.query(func.avg(ContentAnalytics.engagement_score)).first()
            else:  # quality_score
                result = db.query(func.avg(ContentItem.quality_score)).first()

            return result[0] if result and result[0] else 0.0

        finally:
            db.close()

    async def detect_trends(
        self,
        time_period_days: int = 30,
        min_growth_rate: float = 0.1
    ) -> List[TrendAnalysis]:
        """
        Detect emerging trends in content and usage.

        Args:
            time_period_days: Time period to analyze
            min_growth_rate: Minimum growth rate to consider as trending

        Returns:
            List of detected trends
        """
        db = next(get_db())

        try:
            # Calculate time range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            # Query content with time series data
            trend_query = db.query(
                ContentItem.id,
                ContentItem.title,
                ContentItem.content_type,
                ContentAnalytics.period_start,
                ContentAnalytics.view_count,
                ContentAnalytics.engagement_score
            ).join(
                ContentAnalytics,
                ContentAnalytics.content_item_id == ContentItem.id
            ).filter(
                ContentAnalytics.period_start >= start_date
            ).order_by(ContentItem.id, ContentAnalytics.period_start)

            results = trend_query.all()

            # Group by content
            content_trends = defaultdict(list)
            for row in results:
                content_trends[str(row.id)].append({
                    'date': row.period_start,
                    'views': row.view_count or 0,
                    'engagement': row.engagement_score or 0,
                    'title': row.title,
                    'content_type': row.content_type
                })

            # Analyze trends for each content
            trends = []
            for content_id, time_series in content_trends.items():
                if len(time_series) < 3:  # Need at least 3 data points
                    continue

                trend = self._analyze_content_trend(content_id, time_series, min_growth_rate)
                if trend:
                    trends.append(trend)

            # Sort by growth rate
            trends.sort(key=lambda x: x.growth_rate, reverse=True)

            return trends[:10]  # Return top 10 trends

        finally:
            db.close()

    def _analyze_content_trend(
        self,
        content_id: str,
        time_series: List[Dict],
        min_growth_rate: float
    ) -> Optional[TrendAnalysis]:
        """Analyze trend for a single content item."""
        # Extract view counts over time
        dates = [item['date'] for item in time_series]
        views = [item['views'] for item in time_series]

        if len(views) < 3:
            return None

        # Calculate growth rate
        growth_rate = self._calculate_growth_rate(views)

        if abs(growth_rate) < min_growth_rate:
            return None

        # Classify trend type
        if growth_rate > min_growth_rate * 2:
            trend_type = "emerging"
        elif growth_rate < -min_growth_rate:
            trend_type = "declining"
        else:
            trend_type = "stable"

        # Get related content (similar content type)
        related_content = []  # Could implement similarity search here

        # Generate predictions
        predictions = self._generate_trend_predictions(views, dates)

        return TrendAnalysis(
            trend_name=f"Content {content_id}",
            trend_type=trend_type,
            growth_rate=growth_rate,
            time_period=f"{len(time_series)} days",
            related_content=related_content,
            predictions=predictions
        )

    def _calculate_growth_rate(self, values: List[float]) -> float:
        """Calculate compound growth rate."""
        if len(values) < 2:
            return 0.0

        try:
            # Use linear regression on log-transformed values for compound growth
            x = np.array(range(len(values)))
            y = np.log(np.array(values) + 1)  # Add 1 to avoid log(0)

            model = LinearRegression()
            model.fit(x.reshape(-1, 1), y)

            # Annualized growth rate (assuming daily data)
            daily_growth = model.coef_[0]
            annualized_growth = (np.exp(daily_growth) - 1) * 365

            return annualized_growth

        except Exception:
            return 0.0

    def _generate_trend_predictions(self, values: List[float], dates: List[datetime]) -> Dict[str, Any]:
        """Generate trend predictions."""
        if len(values) < 3:
            return {"error": "Insufficient data for prediction"}

        try:
            # Simple linear extrapolation
            x = np.array(range(len(values)))
            y = np.array(values)

            model = LinearRegression()
            model.fit(x.reshape(-1, 1), y)

            # Predict next 7 days
            future_x = np.array(range(len(values), len(values) + 7))
            predictions = model.predict(future_x.reshape(-1, 1))

            return {
                "next_7_days": predictions.tolist(),
                "confidence": model.score(x.reshape(-1, 1), y),
                "trend_slope": model.coef_[0]
            }

        except Exception:
            return {"error": "Prediction failed"}

    async def generate_comprehensive_report(
        self,
        time_period_days: int = 30,
        include_trends: bool = True,
        include_insights: bool = True
    ) -> AnalyticsReport:
        """
        Generate a comprehensive analytics report.

        Args:
            time_period_days: Time period for the report
            include_trends: Whether to include trend analysis
            include_insights: Whether to include content insights

        Returns:
            Comprehensive analytics report
        """
        start_time = time.time()

        # Get basic metrics
        total_content, total_users = await self._get_basic_metrics()

        # Get usage patterns
        usage_patterns = await self.generate_usage_patterns(time_period_days)

        # Get content insights
        content_insights = []
        if include_insights:
            content_insights = await self.generate_content_insights()

        # Get trends
        trends = []
        if include_trends:
            trends = await self.detect_trends(time_period_days)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            usage_patterns, content_insights, trends
        )

        # Calculate key metrics
        key_metrics = await self._calculate_key_metrics(time_period_days)

        processing_time = (time.time() - start_time) * 1000

        return AnalyticsReport(
            report_type="comprehensive",
            time_period=f"{time_period_days} days",
            total_content=total_content,
            total_users=total_users,
            key_metrics=key_metrics,
            usage_patterns=usage_patterns,
            content_insights=content_insights,
            trends=trends,
            recommendations=recommendations,
            generated_at=datetime.now()
        )

    async def _get_basic_metrics(self) -> Tuple[int, int]:
        """Get basic platform metrics."""
        db = next(get_db())

        try:
            total_content = db.query(ContentItem).count()
            # For now, assume users = 1 (can be extended with user tracking)
            total_users = 1

            return total_content, total_users

        finally:
            db.close()

    async def _calculate_key_metrics(self, time_period_days: int) -> Dict[str, float]:
        """Calculate key performance metrics."""
        db = next(get_db())

        try:
            # Calculate time range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            # Total views in period
            total_views_result = db.query(func.sum(ContentAnalytics.view_count)).filter(
                ContentAnalytics.period_start >= start_date
            ).first()

            # Average engagement
            avg_engagement_result = db.query(func.avg(ContentAnalytics.engagement_score)).filter(
                ContentAnalytics.period_start >= start_date
            ).first()

            # Content discovery rate
            new_content_result = db.query(func.count(ContentItem.id)).filter(
                ContentItem.discovered_at >= start_date
            ).first()

            return {
                "total_views": total_views_result[0] or 0,
                "average_engagement": avg_engagement_result[0] or 0.0,
                "new_content_discovered": new_content_result[0] or 0,
                "content_per_day": (new_content_result[0] or 0) / max(time_period_days, 1)
            }

        finally:
            db.close()

    def _generate_recommendations(
        self,
        usage_patterns: List[UsagePattern],
        content_insights: List[ContentInsight],
        trends: List[TrendAnalysis]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Usage pattern recommendations
        for pattern in usage_patterns:
            if pattern.trend_direction == "increasing":
                recommendations.append(
                    f"Capitalize on growing {pattern.metric} trend by increasing content in peak periods"
                )
            elif pattern.trend_direction == "decreasing":
                recommendations.append(
                    f"Address declining {pattern.metric} trend by analyzing content quality and user engagement"
                )

        # Content insights recommendations
        high_performers = [i for i in content_insights if i.percentile > 80]
        if high_performers:
            recommendations.append(
                f"Analyze top-performing content (e.g., {high_performers[0].content_id}) for success patterns"
            )

        # Trend recommendations
        emerging_trends = [t for t in trends if t.trend_type == "emerging"]
        if emerging_trends:
            recommendations.append(
                f"Focus on emerging trend: {emerging_trends[0].trend_name} with {emerging_trends[0].growth_rate:.1%} growth"
            )

        # Default recommendations
        if not recommendations:
            recommendations.extend([
                "Increase content discovery by improving search and recommendation algorithms",
                "Monitor user engagement patterns to optimize content timing",
                "Focus on high-quality content creation based on user preferences"
            ])

        return recommendations[:5]  # Limit to top 5


# Global instance
advanced_analytics_service = AdvancedAnalyticsService()