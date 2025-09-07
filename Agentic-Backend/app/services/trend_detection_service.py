"""
Trend Detection and Insights Service.

This service provides advanced trend detection, predictive analytics,
and actionable insights for content patterns and user behavior.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pandas as pd

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentAnalytics, ContentEmbedding
from app.services.advanced_analytics_service import advanced_analytics_service
from app.utils.logging import get_logger

logger = get_logger("trend_detection_service")


@dataclass
class TrendPattern:
    """Detected trend pattern."""
    pattern_id: str
    pattern_type: str  # emerging, declining, seasonal, viral, sustained
    trend_name: str
    description: str
    confidence_score: float
    growth_rate: float
    time_period_days: int
    related_content: List[str]
    affected_metrics: List[str]
    predictions: Dict[str, Any]
    insights: List[str]
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class PredictiveInsight:
    """Predictive insight based on trend analysis."""
    insight_type: str  # content_performance, user_engagement, platform_growth
    prediction: str
    confidence_level: str  # high, medium, low
    time_horizon: str  # short_term, medium_term, long_term
    supporting_data: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnomalyDetection:
    """Detected anomaly in metrics or patterns."""
    anomaly_id: str
    anomaly_type: str  # spike, drop, unusual_pattern, outlier
    affected_metric: str
    severity: str  # critical, high, medium, low
    description: str
    detected_value: float
    expected_value: float
    deviation_percentage: float
    time_period: str
    potential_causes: List[str]
    recommendations: List[str]
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class TrendAnalysisReport:
    """Comprehensive trend analysis report."""
    report_id: str
    time_period: str
    trends_detected: List[TrendPattern]
    predictive_insights: List[PredictiveInsight]
    anomalies_detected: List[AnomalyDetection]
    key_findings: List[str]
    recommendations: List[str]
    confidence_summary: Dict[str, int]
    generated_at: datetime = field(default_factory=datetime.now)


class TrendDetectionService:
    """Advanced trend detection and predictive analytics service."""

    def __init__(self):
        self.detected_trends: List[TrendPattern] = []
        self.anomaly_thresholds = {
            'view_count': {'spike': 2.0, 'drop': 0.5},
            'engagement_score': {'spike': 1.5, 'drop': 0.7},
            'quality_score': {'spike': 1.3, 'drop': 0.8}
        }

    async def analyze_trends_comprehensive(
        self,
        time_period_days: int = 30,
        min_confidence: float = 0.7,
        include_predictions: bool = True
    ) -> TrendAnalysisReport:
        """
        Perform comprehensive trend analysis.

        Args:
            time_period_days: Analysis time period
            min_confidence: Minimum confidence threshold
            include_predictions: Whether to include predictive insights

        Returns:
            Comprehensive trend analysis report
        """
        start_time = time.time()

        try:
            # Detect trend patterns
            trends = await self._detect_trend_patterns(time_period_days, min_confidence)

            # Generate predictive insights
            predictive_insights = []
            if include_predictions:
                predictive_insights = await self._generate_predictive_insights(trends, time_period_days)

            # Detect anomalies
            anomalies = await self._detect_anomalies(time_period_days)

            # Generate key findings
            key_findings = self._generate_key_findings(trends, predictive_insights, anomalies)

            # Generate recommendations
            recommendations = self._generate_recommendations(trends, predictive_insights, anomalies)

            # Calculate confidence summary
            confidence_summary = self._calculate_confidence_summary(trends, predictive_insights)

            report = TrendAnalysisReport(
                report_id=f"trend_report_{int(time.time())}",
                time_period=f"{time_period_days} days",
                trends_detected=trends,
                predictive_insights=predictive_insights,
                anomalies_detected=anomalies,
                key_findings=key_findings,
                recommendations=recommendations,
                confidence_summary=confidence_summary,
                generated_at=datetime.now()
            )

            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Generated comprehensive trend analysis: {len(trends)} trends, {len(predictive_insights)} insights, {len(anomalies)} anomalies in {processing_time:.2f}ms")

            return report

        except Exception as e:
            logger.error(f"Comprehensive trend analysis failed: {e}")
            raise

    async def _detect_trend_patterns(
        self,
        time_period_days: int,
        min_confidence: float
    ) -> List[TrendPattern]:
        """Detect various types of trend patterns."""
        trends = []

        # Get time series data
        time_series_data = await self._get_time_series_data(time_period_days)

        # Analyze different metrics
        metrics_to_analyze = ['view_count', 'engagement_score', 'quality_score']

        for metric in metrics_to_analyze:
            if metric in time_series_data:
                metric_trends = await self._analyze_metric_trends(
                    time_series_data[metric], metric, time_period_days, min_confidence
                )
                trends.extend(metric_trends)

        # Detect content-specific trends
        content_trends = await self._detect_content_specific_trends(time_period_days, min_confidence)
        trends.extend(content_trends)

        # Detect seasonal patterns
        seasonal_trends = await self._detect_seasonal_patterns(time_series_data, time_period_days)
        trends.extend(seasonal_trends)

        return trends

    async def _get_time_series_data(self, time_period_days: int) -> Dict[str, List[Dict]]:
        """Get time series data for trend analysis."""
        db = next(get_db())

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            # Query analytics data
            analytics_data = db.query(ContentAnalytics).filter(
                ContentAnalytics.period_start >= start_date
            ).order_by(ContentAnalytics.period_start).all()

            # Group by date and metric
            time_series = defaultdict(lambda: defaultdict(float))

            for record in analytics_data:
                date_key = record.period_start.date().isoformat()
                time_series[date_key]['view_count'] += record.view_count or 0
                time_series[date_key]['engagement_score'] += record.engagement_score or 0
                time_series[date_key]['quality_score'] += record.quality_score or 0
                time_series[date_key]['record_count'] += 1

            # Convert to list format
            result = {}
            for metric in ['view_count', 'engagement_score', 'quality_score']:
                result[metric] = [
                    {'date': date, 'value': data[metric], 'count': data['record_count']}
                    for date, data in time_series.items()
                ]
                # Sort by date
                result[metric].sort(key=lambda x: x['date'])

            return result

        finally:
            db.close()

    async def _analyze_metric_trends(
        self,
        time_series: List[Dict],
        metric: str,
        time_period_days: int,
        min_confidence: float
    ) -> List[TrendPattern]:
        """Analyze trends for a specific metric."""
        if len(time_series) < 7:  # Need at least a week of data
            return []

        trends = []

        # Extract values and dates
        dates = [datetime.fromisoformat(item['date']) for item in time_series]
        values = [item['value'] for item in time_series]

        # Calculate overall trend
        overall_trend = self._calculate_trend_direction(values)

        if overall_trend['confidence'] >= min_confidence:
            # Determine trend type
            trend_type = self._classify_trend_type(overall_trend, values)

            # Generate insights
            insights = self._generate_trend_insights(trend_type, metric, overall_trend)

            # Get related content
            related_content = await self._get_related_content_for_trend(metric, trend_type, time_period_days)

            # Generate predictions
            predictions = self._generate_trend_predictions(values, dates)

            trend = TrendPattern(
                pattern_id=f"{metric}_{trend_type}_{int(time.time())}",
                pattern_type=trend_type,
                trend_name=f"{metric.replace('_', ' ').title()} {trend_type.title()}",
                description=f"{trend_type.title()} trend detected in {metric} over {time_period_days} days",
                confidence_score=overall_trend['confidence'],
                growth_rate=overall_trend['slope'],
                time_period_days=time_period_days,
                related_content=related_content,
                affected_metrics=[metric],
                predictions=predictions,
                insights=insights
            )

            trends.append(trend)

        return trends

    def _calculate_trend_direction(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and strength."""
        if len(values) < 2:
            return {'direction': 'stable', 'slope': 0.0, 'confidence': 0.0}

        try:
            # Use linear regression
            x = np.array(range(len(values))).reshape(-1, 1)
            y = np.array(values)

            model = LinearRegression()
            model.fit(x, y)

            slope = model.coef_[0]
            r_squared = model.score(x, y)

            # Classify direction
            if abs(slope) < 0.01:
                direction = 'stable'
            elif slope > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'

            confidence = min(r_squared, 1.0)

            return {
                'direction': direction,
                'slope': slope,
                'confidence': confidence,
                'r_squared': r_squared
            }

        except Exception:
            return {'direction': 'stable', 'slope': 0.0, 'confidence': 0.0}

    def _classify_trend_type(self, trend_data: Dict[str, Any], values: List[float]) -> str:
        """Classify the type of trend."""
        direction = trend_data['direction']
        slope = trend_data['slope']
        confidence = trend_data['confidence']

        if direction == 'increasing':
            if slope > 0.1 and confidence > 0.8:
                return 'emerging'
            elif slope > 0.05:
                return 'growing'
            else:
                return 'sustained'
        elif direction == 'decreasing':
            if abs(slope) > 0.1 and confidence > 0.8:
                return 'declining'
            else:
                return 'gradual_decline'
        else:
            # Check for volatility
            if np.std(values) / max(np.mean(values), 1) > 0.5:
                return 'volatile'
            else:
                return 'stable'

    def _generate_trend_insights(
        self,
        trend_type: str,
        metric: str,
        trend_data: Dict[str, Any]
    ) -> List[str]:
        """Generate insights for a detected trend."""
        insights = []

        if trend_type == 'emerging':
            insights.append(f"Strong upward trend in {metric} indicates growing interest")
            insights.append("Consider increasing content production in this area")
        elif trend_type == 'declining':
            insights.append(f"Declining trend in {metric} suggests decreasing engagement")
            insights.append("Review content strategy and user preferences")
        elif trend_type == 'volatile':
            insights.append(f"High volatility in {metric} indicates inconsistent performance")
            insights.append("Focus on stabilizing content quality and consistency")
        elif trend_type == 'stable':
            insights.append(f"Stable performance in {metric} indicates consistent engagement")
            insights.append("Maintain current content strategy")

        if trend_data['confidence'] > 0.8:
            insights.append("High confidence in trend detection")
        elif trend_data['confidence'] < 0.6:
            insights.append("Trend detection has moderate confidence - monitor closely")

        return insights

    async def _get_related_content_for_trend(
        self,
        metric: str,
        trend_type: str,
        time_period_days: int
    ) -> List[str]:
        """Get content items related to a trend."""
        db = next(get_db())

        try:
            # Get top content by the metric
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            if metric == 'view_count':
                query = db.query(ContentItem.id, ContentItem.title).join(
                    ContentAnalytics,
                    ContentAnalytics.content_item_id == ContentItem.id
                ).filter(
                    ContentAnalytics.period_start >= start_date
                ).group_by(ContentItem.id, ContentItem.title).order_by(
                    func.sum(ContentAnalytics.view_count).desc()
                ).limit(5)
            else:
                # For other metrics, get recent high-performing content
                query = db.query(ContentItem.id, ContentItem.title).filter(
                    ContentItem.discovered_at >= start_date
                ).order_by(ContentItem.quality_score.desc()).limit(5)

            results = query.all()
            return [str(row.id) for row in results]

        finally:
            db.close()

    def _generate_trend_predictions(self, values: List[float], dates: List[datetime]) -> Dict[str, Any]:
        """Generate predictions for trend continuation."""
        if len(values) < 5:
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

            # Calculate prediction confidence
            r_squared = model.score(x.reshape(-1, 1), y)

            return {
                "next_7_days": predictions.tolist(),
                "confidence": r_squared,
                "trend_slope": model.coef_[0],
                "predicted_change": (predictions[-1] - values[-1]) / max(values[-1], 1) * 100
            }

        except Exception:
            return {"error": "Prediction failed"}

    async def _detect_content_specific_trends(
        self,
        time_period_days: int,
        min_confidence: float
    ) -> List[TrendPattern]:
        """Detect trends specific to content types or topics."""
        trends = []

        # Analyze content type popularity trends
        content_type_trends = await self._analyze_content_type_trends(time_period_days, min_confidence)
        trends.extend(content_type_trends)

        # Analyze source performance trends
        source_trends = await self._analyze_source_trends(time_period_days, min_confidence)
        trends.extend(source_trends)

        return trends

    async def _analyze_content_type_trends(
        self,
        time_period_days: int,
        min_confidence: float
    ) -> List[TrendPattern]:
        """Analyze trends in content type popularity."""
        db = next(get_db())

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            # Get content type distribution over time
            type_data = db.query(
                ContentItem.content_type,
                ContentAnalytics.period_start,
                func.count(ContentItem.id).label('count')
            ).join(
                ContentAnalytics,
                ContentAnalytics.content_item_id == ContentItem.id
            ).filter(
                ContentAnalytics.period_start >= start_date
            ).group_by(
                ContentItem.content_type,
                ContentAnalytics.period_start
            ).all()

            # Group by content type
            type_series = defaultdict(list)
            for row in type_data:
                type_series[row.content_type].append({
                    'date': row.period_start.date(),
                    'count': row.count
                })

            trends = []
            for content_type, series in type_series.items():
                if len(series) >= 7:
                    values = [item['count'] for item in sorted(series, key=lambda x: x['date'])]
                    trend_data = self._calculate_trend_direction(values)

                    if trend_data['confidence'] >= min_confidence:
                        trend_type = self._classify_trend_type(trend_data, values)

                        trend = TrendPattern(
                            pattern_id=f"content_type_{content_type}_{trend_type}_{int(time.time())}",
                            pattern_type=trend_type,
                            trend_name=f"{content_type} Content {trend_type.title()}",
                            description=f"{trend_type.title()} trend in {content_type} content popularity",
                            confidence_score=trend_data['confidence'],
                            growth_rate=trend_data['slope'],
                            time_period_days=time_period_days,
                            related_content=[],  # Would need more complex query
                            affected_metrics=['content_type_popularity'],
                            predictions=self._generate_trend_predictions(values, []),
                            insights=[f"{content_type} content showing {trend_type} pattern"]
                        )

                        trends.append(trend)

            return trends

        finally:
            db.close()

    async def _analyze_source_trends(
        self,
        time_period_days: int,
        min_confidence: float
    ) -> List[TrendPattern]:
        """Analyze trends in source performance."""
        # Similar to content type analysis but for sources
        return []  # Simplified implementation

    async def _detect_seasonal_patterns(
        self,
        time_series_data: Dict[str, List[Dict]],
        time_period_days: int
    ) -> List[TrendPattern]:
        """Detect seasonal patterns in the data."""
        seasonal_trends = []

        # Check for weekly patterns
        for metric, series in time_series_data.items():
            if len(series) >= 14:  # At least 2 weeks
                weekly_pattern = self._analyze_weekly_pattern(series)
                if weekly_pattern:
                    seasonal_trends.append(weekly_pattern)

        return seasonal_trends

    def _analyze_weekly_pattern(self, series: List[Dict]) -> Optional[TrendPattern]:
        """Analyze weekly patterns in time series."""
        # Group by day of week
        day_patterns = defaultdict(list)

        for item in series:
            try:
                date = datetime.fromisoformat(item['date'])
                day_patterns[date.weekday()].append(item['value'])
            except:
                continue

        # Calculate average for each day
        day_averages = {}
        for day, values in day_patterns.items():
            if values:
                day_averages[day] = sum(values) / len(values)

        if len(day_averages) >= 5:  # At least 5 days of data
            max_day = max(day_averages, key=day_averages.get)
            min_day = min(day_averages, key=day_averages.get)

            if day_averages[max_day] / max(day_averages[min_day], 1) > 1.5:
                # Significant weekly pattern detected
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

                return TrendPattern(
                    pattern_id=f"weekly_pattern_{int(time.time())}",
                    pattern_type="seasonal",
                    trend_name="Weekly Engagement Pattern",
                    description=f"Peak engagement on {day_names[max_day]}, lowest on {day_names[min_day]}",
                    confidence_score=0.8,
                    growth_rate=0.0,  # Not applicable for seasonal
                    time_period_days=7,
                    related_content=[],
                    affected_metrics=['engagement_score'],
                    predictions={},
                    insights=[
                        f"Content performs best on {day_names[max_day]}",
                        f"Consider scheduling important content for {day_names[max_day]}",
                        f"Lower engagement expected on {day_names[min_day]}"
                    ]
                )

        return None

    async def _generate_predictive_insights(
        self,
        trends: List[TrendPattern],
        time_period_days: int
    ) -> List[PredictiveInsight]:
        """Generate predictive insights based on detected trends."""
        insights = []

        # Analyze trend implications
        for trend in trends:
            if trend.pattern_type == 'emerging' and trend.confidence_score > 0.8:
                insight = PredictiveInsight(
                    insight_type="content_performance",
                    prediction=f"High growth expected in {trend.affected_metrics[0]} content",
                    confidence_level="high",
                    time_horizon="medium_term",
                    supporting_data={
                        "trend_name": trend.trend_name,
                        "growth_rate": trend.growth_rate,
                        "confidence": trend.confidence_score
                    },
                    recommendations=[
                        "Increase content production in trending areas",
                        "Monitor performance closely for optimization opportunities",
                        "Prepare resources for scaling successful content"
                    ]
                )
                insights.append(insight)

            elif trend.pattern_type == 'declining' and trend.confidence_score > 0.7:
                insight = PredictiveInsight(
                    insight_type="content_performance",
                    prediction=f"Continued decline expected in {trend.affected_metrics[0]} engagement",
                    confidence_level="medium",
                    time_horizon="short_term",
                    supporting_data={
                        "trend_name": trend.trend_name,
                        "growth_rate": trend.growth_rate,
                        "confidence": trend.confidence_score
                    },
                    recommendations=[
                        "Review content strategy for declining areas",
                        "Experiment with new content formats",
                        "Analyze user feedback for improvement opportunities"
                    ]
                )
                insights.append(insight)

        # Generate platform-level predictions
        platform_insight = await self._generate_platform_prediction(time_period_days)
        if platform_insight:
            insights.append(platform_insight)

        return insights

    async def _generate_platform_prediction(self, time_period_days: int) -> Optional[PredictiveInsight]:
        """Generate platform-level predictive insights."""
        try:
            # Get overall platform metrics
            key_metrics = await advanced_analytics_service._calculate_key_metrics(time_period_days)

            total_views = key_metrics.get('total_views', 0)
            avg_engagement = key_metrics.get('average_engagement', 0)

            # Simple prediction based on current trajectory
            if total_views > 1000 and avg_engagement > 0.6:
                return PredictiveInsight(
                    insight_type="platform_growth",
                    prediction="Platform showing strong growth trajectory",
                    confidence_level="high",
                    time_horizon="medium_term",
                    supporting_data={
                        "total_views": total_views,
                        "avg_engagement": avg_engagement,
                        "time_period_days": time_period_days
                    },
                    recommendations=[
                        "Continue current content strategy",
                        "Consider expanding to new content types",
                        "Monitor for scaling opportunities"
                    ]
                )
            elif total_views < 100:
                return PredictiveInsight(
                    insight_type="platform_growth",
                    prediction="Platform needs growth acceleration",
                    confidence_level="medium",
                    time_horizon="short_term",
                    supporting_data={
                        "total_views": total_views,
                        "avg_engagement": avg_engagement,
                        "time_period_days": time_period_days
                    },
                    recommendations=[
                        "Focus on content quality improvement",
                        "Increase content discovery and promotion",
                        "Analyze user acquisition strategies"
                    ]
                )

        except Exception:
            pass

        return None

    async def _detect_anomalies(self, time_period_days: int) -> List[AnomalyDetection]:
        """Detect anomalies in metrics and patterns."""
        anomalies = []

        # Get recent metrics
        key_metrics = await advanced_analytics_service._calculate_key_metrics(time_period_days)

        # Check for metric anomalies
        for metric, thresholds in self.anomaly_thresholds.items():
            metric_value = key_metrics.get(metric, 0)

            # This is a simplified anomaly detection
            # In production, you'd use statistical methods like Z-score, IQR, etc.
            if metric == 'view_count' and metric_value > 10000:  # Arbitrary threshold
                anomaly = AnomalyDetection(
                    anomaly_id=f"anomaly_{metric}_{int(time.time())}",
                    anomaly_type="spike",
                    affected_metric=metric,
                    severity="high",
                    description=f"Unusual spike in {metric}",
                    detected_value=metric_value,
                    expected_value=5000,  # Would be calculated from historical data
                    deviation_percentage=100.0,
                    time_period=f"{time_period_days} days",
                    potential_causes=[
                        "Viral content discovery",
                        "Marketing campaign success",
                        "Seasonal event"
                    ],
                    recommendations=[
                        "Monitor closely for sustainability",
                        "Prepare for potential scaling needs",
                        "Analyze what drove the spike"
                    ]
                )
                anomalies.append(anomaly)

        return anomalies

    def _generate_key_findings(
        self,
        trends: List[TrendPattern],
        insights: List[PredictiveInsight],
        anomalies: List[AnomalyDetection]
    ) -> List[str]:
        """Generate key findings from analysis."""
        findings = []

        if trends:
            trend_types = Counter(trend.pattern_type for trend in trends)
            findings.append(f"Detected {len(trends)} trends: {dict(trend_types)}")

        if insights:
            high_confidence = sum(1 for i in insights if i.confidence_level == 'high')
            findings.append(f"Generated {len(insights)} predictive insights ({high_confidence} high confidence)")

        if anomalies:
            critical_anomalies = sum(1 for a in anomalies if a.severity == 'critical')
            findings.append(f"Detected {len(anomalies)} anomalies ({critical_anomalies} critical)")

        if not trends and not insights and not anomalies:
            findings.append("No significant trends or anomalies detected in the analysis period")

        return findings

    def _generate_recommendations(
        self,
        trends: List[TrendPattern],
        insights: List[PredictiveInsight],
        anomalies: List[AnomalyDetection]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Trend-based recommendations
        emerging_trends = [t for t in trends if t.pattern_type == 'emerging']
        if emerging_trends:
            recommendations.append("Capitalize on emerging trends by increasing content production")

        declining_trends = [t for t in trends if t.pattern_type == 'declining']
        if declining_trends:
            recommendations.append("Address declining trends through content strategy review")

        # Insight-based recommendations
        for insight in insights:
            recommendations.extend(insight.recommendations[:2])  # Limit to 2 per insight

        # Anomaly-based recommendations
        for anomaly in anomalies:
            if anomaly.severity in ['critical', 'high']:
                recommendations.extend(anomaly.recommendations[:1])  # Limit to 1 per anomaly

        # Remove duplicates and limit total
        unique_recommendations = list(set(recommendations))[:10]

        return unique_recommendations

    def _calculate_confidence_summary(
        self,
        trends: List[TrendPattern],
        insights: List[PredictiveInsight]
    ) -> Dict[str, int]:
        """Calculate confidence level summary."""
        trend_confidence = {'high': 0, 'medium': 0, 'low': 0}
        insight_confidence = {'high': 0, 'medium': 0, 'low': 0}

        for trend in trends:
            if trend.confidence_score > 0.8:
                trend_confidence['high'] += 1
            elif trend.confidence_score > 0.6:
                trend_confidence['medium'] += 1
            else:
                trend_confidence['low'] += 1

        for insight in insights:
            insight_confidence[insight.confidence_level] += 1

        return {
            'trends': trend_confidence,
            'insights': insight_confidence
        }


# Global instance
trend_detection_service = TrendDetectionService()