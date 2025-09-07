"""
Search Analytics and Metrics Service.

This service provides comprehensive analytics for search behavior, performance metrics,
and user interaction patterns to optimize search experience and content discoverability.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentAnalytics, SearchLog
from app.services.vector_search_service import vector_search_service
from app.services.query_understanding_service import query_understanding_service
from app.utils.logging import get_logger

logger = get_logger("search_analytics_service")


@dataclass
class SearchPerformanceMetrics:
    """Search performance metrics."""
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    average_response_time_ms: float = 0.0
    success_rate: float = 0.0
    no_results_rate: float = 0.0
    average_results_per_query: float = 0.0
    top_clicked_positions: List[int] = field(default_factory=list)
    search_type_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class QueryAnalytics:
    """Analytics for search queries."""
    total_queries: int = 0
    unique_queries: int = 0
    top_queries: List[Dict[str, Any]] = field(default_factory=list)
    query_length_distribution: Dict[str, int] = field(default_factory=dict)
    query_complexity_distribution: Dict[str, int] = field(default_factory=dict)
    popular_query_patterns: List[str] = field(default_factory=list)
    seasonal_query_trends: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class UserSearchBehavior:
    """User search behavior analytics."""
    session_length_avg: float = 0.0
    queries_per_session_avg: float = 0.0
    click_through_rate: float = 0.0
    abandonment_rate: float = 0.0
    refinement_rate: float = 0.0
    popular_search_times: List[str] = field(default_factory=list)
    device_type_distribution: Dict[str, int] = field(default_factory=dict)
    user_segments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ContentDiscoveryMetrics:
    """Content discovery and engagement metrics."""
    total_content_discovered: int = 0
    content_engagement_rate: float = 0.0
    popular_content_types: List[Dict[str, Any]] = field(default_factory=list)
    content_freshness_distribution: Dict[str, int] = field(default_factory=dict)
    source_performance: List[Dict[str, Any]] = field(default_factory=list)
    topic_discovery_trends: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SearchOptimizationInsights:
    """Insights for search optimization."""
    low_performance_queries: List[Dict[str, Any]] = field(default_factory=list)
    high_opportunity_content: List[Dict[str, Any]] = field(default_factory=list)
    search_experience_issues: List[str] = field(default_factory=list)
    recommended_improvements: List[str] = field(default_factory=list)
    predicted_search_trends: List[Dict[str, Any]] = field(default_factory=list)
    content_gap_analysis: List[str] = field(default_factory=list)


@dataclass
class SearchAnalyticsReport:
    """Comprehensive search analytics report."""
    report_id: str
    time_period: str
    performance_metrics: SearchPerformanceMetrics
    query_analytics: QueryAnalytics
    user_behavior: UserSearchBehavior
    content_discovery: ContentDiscoveryMetrics
    optimization_insights: SearchOptimizationInsights
    key_findings: List[str]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)


class SearchAnalyticsService:
    """Comprehensive search analytics and optimization service."""

    def __init__(self):
        self.search_logs: List[Dict[str, Any]] = []
        self.performance_cache: Dict[str, Any] = {}

    async def generate_comprehensive_report(
        self,
        time_period_days: int = 30,
        include_user_behavior: bool = True,
        include_optimization_insights: bool = True
    ) -> SearchAnalyticsReport:
        """
        Generate comprehensive search analytics report.

        Args:
            time_period_days: Analysis time period
            include_user_behavior: Include user behavior analysis
            include_optimization_insights: Include optimization insights

        Returns:
            Comprehensive search analytics report
        """
        start_time = time.time()

        try:
            # Get time range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)

            # Generate all analytics components
            performance_metrics = await self._analyze_search_performance(start_date, end_date)
            query_analytics = await self._analyze_query_patterns(start_date, end_date)

            user_behavior = UserSearchBehavior()
            if include_user_behavior:
                user_behavior = await self._analyze_user_behavior(start_date, end_date)

            content_discovery = await self._analyze_content_discovery(start_date, end_date)

            optimization_insights = SearchOptimizationInsights()
            if include_optimization_insights:
                optimization_insights = await self._generate_optimization_insights(
                    performance_metrics, query_analytics, content_discovery
                )

            # Generate key findings and recommendations
            key_findings = self._generate_key_findings(
                performance_metrics, query_analytics, user_behavior, content_discovery
            )

            recommendations = self._generate_recommendations(
                performance_metrics, query_analytics, optimization_insights
            )

            report = SearchAnalyticsReport(
                report_id=f"search_analytics_{int(time.time())}",
                time_period=f"{time_period_days} days",
                performance_metrics=performance_metrics,
                query_analytics=query_analytics,
                user_behavior=user_behavior,
                content_discovery=content_discovery,
                optimization_insights=optimization_insights,
                key_findings=key_findings,
                recommendations=recommendations,
                generated_at=datetime.now()
            )

            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Generated comprehensive search analytics report in {processing_time:.2f}ms")

            return report

        except Exception as e:
            logger.error(f"Search analytics report generation failed: {e}")
            raise

    async def _analyze_search_performance(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> SearchPerformanceMetrics:
        """Analyze search performance metrics."""
        # This is a simplified implementation
        # In production, this would query actual search logs

        # Mock data for demonstration
        metrics = SearchPerformanceMetrics(
            total_searches=1250,
            successful_searches=1180,
            failed_searches=70,
            average_response_time_ms=245.6,
            success_rate=0.944,
            no_results_rate=0.056,
            average_results_per_query=18.5,
            top_clicked_positions=[1, 2, 3, 4, 5],
            search_type_distribution={
                "semantic": 850,
                "keyword": 320,
                "hybrid": 80
            }
        )

        return metrics

    async def _analyze_query_patterns(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> QueryAnalytics:
        """Analyze search query patterns."""
        # Mock data for demonstration
        analytics = QueryAnalytics(
            total_queries=1250,
            unique_queries=890,
            top_queries=[
                {"query": "machine learning", "count": 45, "avg_results": 23, "success_rate": 0.98},
                {"query": "artificial intelligence", "count": 38, "avg_results": 31, "success_rate": 0.95},
                {"query": "data science", "count": 29, "avg_results": 18, "success_rate": 0.92},
                {"query": "python programming", "count": 27, "avg_results": 15, "success_rate": 0.89},
                {"query": "deep learning", "count": 24, "avg_results": 12, "success_rate": 0.87}
            ],
            query_length_distribution={
                "short (1-3 words)": 420,
                "medium (4-7 words)": 580,
                "long (8+ words)": 250
            },
            query_complexity_distribution={
                "simple": 650,
                "moderate": 480,
                "complex": 120
            },
            popular_query_patterns=[
                "how to *",
                "* tutorial",
                "* vs *",
                "best *",
                "* examples"
            ],
            seasonal_query_trends=[
                {"period": "2024-01-01", "queries": 120, "top_topic": "AI"},
                {"period": "2024-01-02", "queries": 135, "top_topic": "ML"},
                {"period": "2024-01-03", "queries": 142, "top_topic": "Data Science"}
            ]
        )

        return analytics

    async def _analyze_user_behavior(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> UserSearchBehavior:
        """Analyze user search behavior patterns."""
        # Mock data for demonstration
        behavior = UserSearchBehavior(
            session_length_avg=12.5,  # minutes
            queries_per_session_avg=3.2,
            click_through_rate=0.68,
            abandonment_rate=0.32,
            refinement_rate=0.45,
            popular_search_times=[
                "10:00-12:00",
                "14:00-16:00",
                "19:00-21:00"
            ],
            device_type_distribution={
                "desktop": 650,
                "mobile": 480,
                "tablet": 120
            },
            user_segments=[
                {
                    "segment": "power_users",
                    "count": 150,
                    "characteristics": ["frequent_searcher", "technical_queries"],
                    "engagement_rate": 0.85
                },
                {
                    "segment": "casual_users",
                    "count": 800,
                    "characteristics": ["occasional_searcher", "simple_queries"],
                    "engagement_rate": 0.45
                },
                {
                    "segment": "researchers",
                    "count": 300,
                    "characteristics": ["complex_queries", "multiple_sessions"],
                    "engagement_rate": 0.72
                }
            ]
        )

        return behavior

    async def _analyze_content_discovery(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> ContentDiscoveryMetrics:
        """Analyze content discovery and engagement metrics."""
        db = next(get_db())

        try:
            # Get content discovery metrics
            total_content = db.query(ContentItem).filter(
                ContentItem.discovered_at >= start_date
            ).count()

            # Get engagement metrics
            engagement_data = db.query(
                func.avg(ContentAnalytics.engagement_score).label('avg_engagement'),
                func.count(ContentAnalytics.id).label('total_analytics')
            ).filter(
                ContentAnalytics.period_start >= start_date
            ).first()

            avg_engagement = engagement_data.avg_engagement or 0.0

            # Get content type distribution
            content_types = db.query(
                ContentItem.content_type,
                func.count(ContentItem.id).label('count')
            ).filter(
                ContentItem.discovered_at >= start_date
            ).group_by(ContentItem.content_type).all()

            popular_types = [
                {"type": row.content_type, "count": row.count}
                for row in content_types
            ]

            # Get source performance
            source_performance = db.query(
                ContentItem.source_type,
                func.count(ContentItem.id).label('content_count'),
                func.avg(ContentItem.quality_score).label('avg_quality')
            ).filter(
                ContentItem.discovered_at >= start_date
            ).group_by(ContentItem.source_type).all()

            source_perf = [
                {
                    "source": row.source_type,
                    "content_count": row.content_count,
                    "avg_quality": row.avg_quality or 0.0
                }
                for row in source_performance
            ]

            metrics = ContentDiscoveryMetrics(
                total_content_discovered=total_content,
                content_engagement_rate=avg_engagement,
                popular_content_types=popular_types,
                content_freshness_distribution={
                    "fresh (< 1 day)": 120,
                    "recent (1-7 days)": 380,
                    "older (> 7 days)": 750
                },
                source_performance=source_perf,
                topic_discovery_trends=[
                    {"topic": "AI", "trend": "increasing", "growth_rate": 0.15},
                    {"topic": "ML", "trend": "stable", "growth_rate": 0.02},
                    {"topic": "Data Science", "trend": "increasing", "growth_rate": 0.08}
                ]
            )

            return metrics

        finally:
            db.close()

    async def _generate_optimization_insights(
        self,
        performance: SearchPerformanceMetrics,
        queries: QueryAnalytics,
        content: ContentDiscoveryMetrics
    ) -> SearchOptimizationInsights:
        """Generate insights for search optimization."""
        insights = SearchOptimizationInsights()

        # Identify low-performance queries
        low_performance = [
            query for query in queries.top_queries
            if query.get('success_rate', 1.0) < 0.8
        ][:5]
        insights.low_performance_queries = low_performance

        # Identify high-opportunity content
        high_opportunity = [
            source for source in content.source_performance
            if source.get('avg_quality', 0) > 0.8 and source.get('content_count', 0) > 10
        ][:5]
        insights.high_opportunity_content = high_opportunity

        # Identify search experience issues
        issues = []
        if performance.no_results_rate > 0.1:
            issues.append("High no-results rate indicates content gaps")
        if performance.average_response_time_ms > 500:
            issues.append("Slow search response times affecting user experience")
        if performance.success_rate < 0.9:
            issues.append("Low search success rate needs improvement")
        insights.search_experience_issues = issues

        # Generate recommendations
        recommendations = []
        if performance.no_results_rate > 0.1:
            recommendations.append("Expand content coverage for frequently searched topics")
        if performance.average_response_time_ms > 500:
            recommendations.append("Optimize search indexing and query processing")
        if performance.success_rate < 0.9:
            recommendations.append("Improve query understanding and result ranking")
        insights.recommended_improvements = recommendations

        # Predict search trends
        insights.predicted_search_trends = [
            {"trend": "AI content growth", "prediction": "15% increase", "timeframe": "3 months"},
            {"trend": "Mobile search increase", "prediction": "20% increase", "timeframe": "6 months"},
            {"trend": "Voice search adoption", "prediction": "25% increase", "timeframe": "1 year"}
        ]

        # Content gap analysis
        insights.content_gap_analysis = [
            "Missing content for advanced AI topics",
            "Limited coverage of emerging technologies",
            "Need more practical tutorials and examples"
        ]

        return insights

    def _generate_key_findings(
        self,
        performance: SearchPerformanceMetrics,
        queries: QueryAnalytics,
        behavior: UserSearchBehavior,
        content: ContentDiscoveryMetrics
    ) -> List[str]:
        """Generate key findings from analytics."""
        findings = []

        # Performance findings
        if performance.success_rate > 0.9:
            findings.append(f"Strong search performance with {performance.success_rate:.1%} success rate")
        else:
            findings.append(f"Search performance needs improvement: {performance.success_rate:.1%} success rate")

        # Query findings
        if queries.unique_queries > 0:
            findings.append(f"High query diversity: {queries.unique_queries} unique queries from {queries.total_queries} total")

        # Behavior findings
        if behavior.click_through_rate > 0.6:
            findings.append(f"Good user engagement: {behavior.click_through_rate:.1%} click-through rate")
        else:
            findings.append(f"User engagement needs improvement: {behavior.click_through_rate:.1%} click-through rate")

        # Content findings
        if content.total_content_discovered > 100:
            findings.append(f"Strong content discovery: {content.total_content_discovered} items added")

        return findings

    def _generate_recommendations(
        self,
        performance: SearchPerformanceMetrics,
        queries: QueryAnalytics,
        insights: SearchOptimizationInsights
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Performance-based recommendations
        if performance.average_response_time_ms > 300:
            recommendations.append("Optimize search performance to reduce response times")

        if performance.no_results_rate > 0.05:
            recommendations.append("Improve content coverage to reduce no-results queries")

        # Query-based recommendations
        if len(queries.popular_query_patterns) > 0:
            recommendations.append("Create dedicated content for popular query patterns")

        # Add optimization insights recommendations
        recommendations.extend(insights.recommended_improvements[:3])

        return recommendations[:10]  # Limit to top 10

    async def track_search_event(
        self,
        user_id: Optional[str],
        query: str,
        search_type: str,
        results_count: int,
        response_time_ms: float,
        clicked_results: Optional[List[int]] = None,
        session_id: Optional[str] = None
    ):
        """
        Track a search event for analytics.

        Args:
            user_id: User performing the search
            query: Search query
            search_type: Type of search (semantic, keyword, hybrid)
            results_count: Number of results returned
            response_time_ms: Search response time
            clicked_results: Positions of clicked results
            session_id: Search session identifier
        """
        try:
            search_event = {
                "user_id": user_id,
                "query": query,
                "search_type": search_type,
                "results_count": results_count,
                "response_time_ms": response_time_ms,
                "clicked_results": clicked_results or [],
                "session_id": session_id,
                "timestamp": datetime.now(),
                "has_results": results_count > 0,
                "click_through": len(clicked_results or []) > 0
            }

            # Store in memory (in production, this would go to database)
            self.search_logs.append(search_event)

            # Keep only recent logs (last 10000)
            if len(self.search_logs) > 10000:
                self.search_logs = self.search_logs[-5000:]

            logger.debug(f"Tracked search event: '{query}' -> {results_count} results")

        except Exception as e:
            logger.error(f"Failed to track search event: {e}")

    async def get_search_suggestions(
        self,
        partial_query: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get search suggestions based on partial query and user history.

        Args:
            partial_query: Partial query string
            user_id: User ID for personalized suggestions
            limit: Maximum suggestions to return

        Returns:
            List of search suggestions with metadata
        """
        try:
            suggestions = []

            # Get popular queries starting with partial query
            matching_queries = [
                log for log in self.search_logs[-1000:]  # Last 1000 searches
                if log['query'].lower().startswith(partial_query.lower())
            ]

            # Count occurrences
            query_counts = Counter(log['query'] for log in matching_queries)

            # Get top suggestions
            top_queries = query_counts.most_common(limit)

            for query, count in top_queries:
                suggestions.append({
                    "query": query,
                    "popularity": count,
                    "type": "popular",
                    "confidence": min(count / 10, 1.0)  # Normalize confidence
                })

            # Add query expansions if partial query is meaningful
            if len(partial_query.split()) >= 2:
                try:
                    expansion = await query_understanding_service.expand_query(partial_query)
                    if expansion.expanded_query != partial_query:
                        suggestions.append({
                            "query": expansion.expanded_query,
                            "popularity": 1,
                            "type": "expansion",
                            "confidence": expansion.confidence_score
                        })
                except Exception:
                    pass

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []

    async def get_search_insights(
        self,
        time_period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Get real-time search insights for monitoring.

        Args:
            time_period_days: Time period for insights

        Returns:
            Search insights and metrics
        """
        try:
            # Get recent logs
            cutoff_time = datetime.now() - timedelta(days=time_period_days)
            recent_logs = [
                log for log in self.search_logs
                if log['timestamp'] > cutoff_time
            ]

            if not recent_logs:
                return {"message": "No recent search data available"}

            # Calculate metrics
            total_searches = len(recent_logs)
            successful_searches = sum(1 for log in recent_logs if log['has_results'])
            click_through_searches = sum(1 for log in recent_logs if log['click_through'])

            avg_response_time = sum(log['response_time_ms'] for log in recent_logs) / total_searches
            success_rate = successful_searches / total_searches if total_searches > 0 else 0
            ctr = click_through_searches / total_searches if total_searches > 0 else 0

            # Popular queries
            query_counts = Counter(log['query'] for log in recent_logs)
            popular_queries = query_counts.most_common(5)

            insights = {
                "time_period_days": time_period_days,
                "total_searches": total_searches,
                "success_rate": success_rate,
                "click_through_rate": ctr,
                "average_response_time_ms": avg_response_time,
                "popular_queries": [
                    {"query": query, "count": count}
                    for query, count in popular_queries
                ],
                "search_type_distribution": Counter(log['search_type'] for log in recent_logs),
                "generated_at": datetime.now().isoformat()
            }

            return insights

        except Exception as e:
            logger.error(f"Failed to get search insights: {e}")
            return {"error": str(e)}

    async def export_search_data(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export search data for external analysis.

        Args:
            start_date: Start date for export
            end_date: End date for export
            format: Export format (json, csv)

        Returns:
            Exported search data
        """
        try:
            # Filter logs by date range
            filtered_logs = [
                log for log in self.search_logs
                if start_date <= log['timestamp'] <= end_date
            ]

            if format == "json":
                return {
                    "export_format": "json",
                    "time_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "total_records": len(filtered_logs),
                    "data": filtered_logs
                }
            else:
                # For CSV format, return structured data
                return {
                    "export_format": "csv",
                    "time_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "total_records": len(filtered_logs),
                    "headers": ["timestamp", "user_id", "query", "search_type", "results_count", "response_time_ms", "has_results", "click_through"],
                    "data": [
                        [
                            log['timestamp'].isoformat(),
                            log.get('user_id', ''),
                            log['query'],
                            log['search_type'],
                            log['results_count'],
                            log['response_time_ms'],
                            log['has_results'],
                            log['click_through']
                        ]
                        for log in filtered_logs
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to export search data: {e}")
            return {"error": str(e)}


# Global instance
search_analytics_service = SearchAnalyticsService()