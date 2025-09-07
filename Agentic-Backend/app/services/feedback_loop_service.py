"""
Feedback Loop Service for user feedback integration and model improvement.

This service provides learning and adaptation capabilities including:
- User feedback collection and analysis
- Model performance tracking and improvement
- Adaptive learning from user corrections
- Feedback-driven model fine-tuning
- Quality assessment and iterative improvement
- User preference learning and personalization
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from app.config import settings
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("feedback_loop_service")


class FeedbackError(Exception):
    """Raised when feedback processing fails."""
    pass


class UserFeedback:
    """Represents user feedback on content or model performance."""

    def __init__(
        self,
        feedback_id: str,
        user_id: str,
        content_id: str,
        feedback_type: str,  # 'correction', 'rating', 'preference', 'annotation'
        feedback_data: Dict[str, Any],
        original_prediction: Any = None,
        corrected_prediction: Any = None,
        confidence_score: float = None,
        processing_stage: str = None,
        model_used: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.content_id = content_id
        self.feedback_type = feedback_type
        self.feedback_data = feedback_data
        self.original_prediction = original_prediction
        self.corrected_prediction = corrected_prediction
        self.confidence_score = confidence_score
        self.processing_stage = processing_stage
        self.model_used = model_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "user_id": self.user_id,
            "content_id": self.content_id,
            "feedback_type": self.feedback_type,
            "feedback_data": self.feedback_data,
            "original_prediction": self.original_prediction,
            "corrected_prediction": self.corrected_prediction,
            "confidence_score": self.confidence_score,
            "processing_stage": self.processing_stage,
            "model_used": self.model_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ModelImprovement:
    """Represents a model improvement based on feedback."""

    def __init__(
        self,
        improvement_id: str,
        model_name: str,
        improvement_type: str,
        feedback_count: int,
        accuracy_improvement: float,
        applied_at: datetime = None,
        improvement_details: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        self.improvement_id = improvement_id
        self.model_name = model_name
        self.improvement_type = improvement_type
        self.feedback_count = feedback_count
        self.accuracy_improvement = accuracy_improvement
        self.applied_at = applied_at or datetime.now()
        self.improvement_details = improvement_details or {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert improvement to dictionary."""
        return {
            "improvement_id": self.improvement_id,
            "model_name": self.model_name,
            "improvement_type": self.improvement_type,
            "feedback_count": self.feedback_count,
            "accuracy_improvement": self.accuracy_improvement,
            "applied_at": self.applied_at.isoformat(),
            "improvement_details": self.improvement_details,
            "metadata": self.metadata
        }


class FeedbackAnalysisResult:
    """Result of feedback analysis and model improvement."""

    def __init__(
        self,
        analysis_id: str,
        feedback_processed: int,
        improvements_generated: List[ModelImprovement] = None,
        accuracy_gain: float = None,
        processing_time_ms: float = None,
        recommendations: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.analysis_id = analysis_id
        self.feedback_processed = feedback_processed
        self.improvements_generated = improvements_generated or []
        self.accuracy_gain = accuracy_gain
        self.processing_time_ms = processing_time_ms
        self.recommendations = recommendations or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "analysis_id": self.analysis_id,
            "feedback_processed": self.feedback_processed,
            "improvements_generated": [imp.to_dict() for imp in self.improvements_generated],
            "accuracy_gain": self.accuracy_gain,
            "processing_time_ms": self.processing_time_ms,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class FeedbackLoopService:
    """Service for collecting feedback and improving models through learning."""

    def __init__(self):
        self.default_model = getattr(settings, 'feedback_loop_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'feedback_loop_timeout_seconds', 60)

        # Feedback storage (in production, this would be a database)
        self.feedback_store: Dict[str, List[UserFeedback]] = defaultdict(list)
        self.model_performance: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Learning thresholds
        self.min_feedback_for_learning = getattr(settings, 'min_feedback_for_learning', 10)
        self.accuracy_improvement_threshold = getattr(settings, 'accuracy_improvement_threshold', 0.05)

    async def collect_feedback(
        self,
        user_id: str,
        content_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any],
        original_prediction: Any = None,
        corrected_prediction: Any = None,
        confidence_score: float = None,
        processing_stage: str = None,
        model_used: str = None,
        **kwargs
    ) -> str:
        """
        Collect user feedback for model improvement.

        Args:
            user_id: ID of the user providing feedback
            content_id: ID of the content being rated
            feedback_type: Type of feedback ('correction', 'rating', 'preference', 'annotation')
            feedback_data: The actual feedback data
            original_prediction: What the model originally predicted
            corrected_prediction: What the user corrected it to
            confidence_score: Model's confidence in original prediction
            processing_stage: Which processing stage this feedback relates to
            model_used: Which model was used
            **kwargs: Additional feedback metadata

        Returns:
            Feedback ID for tracking
        """
        try:
            feedback_id = f"feedback_{user_id}_{content_id}_{int(datetime.now().timestamp())}"

            feedback = UserFeedback(
                feedback_id=feedback_id,
                user_id=user_id,
                content_id=content_id,
                feedback_type=feedback_type,
                feedback_data=feedback_data,
                original_prediction=original_prediction,
                corrected_prediction=corrected_prediction,
                confidence_score=confidence_score,
                processing_stage=processing_stage,
                model_used=model_used,
                metadata=kwargs
            )

            # Store feedback
            self.feedback_store[user_id].append(feedback)

            # Update model performance tracking
            if model_used:
                self._update_model_performance(model_used, feedback)

            logger.info(f"Feedback collected: {feedback_id} from user {user_id} for content {content_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Feedback collection failed: {e}")
            raise FeedbackError(f"Feedback collection failed: {str(e)}")

    async def analyze_feedback_and_improve(
        self,
        user_id: str = None,
        model_name: str = None,
        min_feedback_count: int = None,
        **kwargs
    ) -> FeedbackAnalysisResult:
        """
        Analyze collected feedback and generate model improvements.

        Args:
            user_id: Specific user to analyze feedback for (optional)
            model_name: Specific model to improve (optional)
            min_feedback_count: Minimum feedback count for analysis
            **kwargs: Additional analysis options

        Returns:
            FeedbackAnalysisResult with improvements and analysis
        """
        start_time = datetime.now()
        analysis_id = f"analysis_{int(datetime.now().timestamp())}"

        try:
            min_feedback_count = min_feedback_count or self.min_feedback_for_learning

            # Collect feedback for analysis
            feedback_to_analyze = self._collect_feedback_for_analysis(
                user_id=user_id,
                model_name=model_name,
                min_count=min_feedback_count
            )

            if len(feedback_to_analyze) < min_feedback_count:
                logger.warning(f"Insufficient feedback for analysis: {len(feedback_to_analyze)} < {min_feedback_count}")
                return FeedbackAnalysisResult(
                    analysis_id=analysis_id,
                    feedback_processed=len(feedback_to_analyze),
                    recommendations=["Collect more feedback before analysis"]
                )

            # Analyze feedback patterns
            feedback_patterns = await self._analyze_feedback_patterns(feedback_to_analyze, **kwargs)

            # Generate model improvements
            improvements = await self._generate_model_improvements(
                feedback_patterns,
                feedback_to_analyze,
                **kwargs
            )

            # Calculate accuracy gain
            accuracy_gain = self._calculate_accuracy_gain(improvements)

            # Generate recommendations
            recommendations = await self._generate_improvement_recommendations(
                feedback_patterns,
                improvements,
                **kwargs
            )

            result = FeedbackAnalysisResult(
                analysis_id=analysis_id,
                feedback_processed=len(feedback_to_analyze),
                improvements_generated=improvements,
                accuracy_gain=accuracy_gain,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                recommendations=recommendations
            )

            logger.info(f"Feedback analysis completed: {len(improvements)} improvements generated")
            return result

        except Exception as e:
            logger.error(f"Feedback analysis failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise FeedbackError(f"Feedback analysis failed: {str(e)}")

    def _collect_feedback_for_analysis(
        self,
        user_id: str = None,
        model_name: str = None,
        min_count: int = 10
    ) -> List[UserFeedback]:
        """Collect feedback for analysis based on criteria."""
        feedback_list = []

        if user_id:
            # Collect feedback from specific user
            feedback_list.extend(self.feedback_store.get(user_id, []))
        else:
            # Collect feedback from all users
            for user_feedbacks in self.feedback_store.values():
                feedback_list.extend(user_feedbacks)

        # Filter by model if specified
        if model_name:
            feedback_list = [f for f in feedback_list if f.model_used == model_name]

        # Sort by timestamp (most recent first)
        feedback_list.sort(key=lambda x: x.timestamp, reverse=True)

        return feedback_list[:min_count * 2]  # Get more than minimum for analysis

    async def _analyze_feedback_patterns(
        self,
        feedback_list: List[UserFeedback],
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze patterns in collected feedback."""
        try:
            patterns = {
                "feedback_types": defaultdict(int),
                "processing_stages": defaultdict(int),
                "models_used": defaultdict(int),
                "error_patterns": defaultdict(int),
                "correction_patterns": defaultdict(list),
                "confidence_distribution": defaultdict(int),
                "temporal_patterns": defaultdict(int)
            }

            for feedback in feedback_list:
                # Count feedback types
                patterns["feedback_types"][feedback.feedback_type] += 1

                # Count processing stages
                if feedback.processing_stage:
                    patterns["processing_stages"][feedback.processing_stage] += 1

                # Count models used
                if feedback.model_used:
                    patterns["models_used"][feedback.model_used] += 1

                # Analyze confidence scores
                if feedback.confidence_score is not None:
                    confidence_bucket = int(feedback.confidence_score * 10) / 10  # Round to nearest 0.1
                    patterns["confidence_distribution"][confidence_bucket] += 1

                # Analyze corrections
                if feedback.feedback_type == "correction" and feedback.corrected_prediction:
                    correction_key = f"{feedback.processing_stage}_{type(feedback.original_prediction).__name__}"
                    patterns["correction_patterns"][correction_key].append({
                        "original": feedback.original_prediction,
                        "corrected": feedback.corrected_prediction,
                        "confidence": feedback.confidence_score
                    })

                # Temporal patterns (by hour of day)
                hour = feedback.timestamp.hour
                patterns["temporal_patterns"][hour] += 1

            # Convert defaultdicts to regular dicts
            return {
                key: dict(value) if isinstance(value, defaultdict) else value
                for key, value in patterns.items()
            }

        except Exception as e:
            logger.error(f"Feedback pattern analysis failed: {e}")
            return {}

    async def _generate_model_improvements(
        self,
        feedback_patterns: Dict[str, Any],
        feedback_list: List[UserFeedback],
        **kwargs
    ) -> List[ModelImprovement]:
        """Generate model improvements based on feedback patterns."""
        try:
            improvements = []

            # Analyze correction patterns for specific improvements
            correction_patterns = feedback_patterns.get("correction_patterns", {})

            for pattern_key, corrections in correction_patterns.items():
                if len(corrections) >= 5:  # Minimum corrections for pattern recognition
                    improvement = await self._create_pattern_based_improvement(
                        pattern_key, corrections, **kwargs
                    )
                    if improvement:
                        improvements.append(improvement)

            # Analyze confidence distribution for threshold adjustments
            confidence_dist = feedback_patterns.get("confidence_distribution", {})
            if confidence_dist:
                confidence_improvement = await self._create_confidence_based_improvement(
                    confidence_dist, **kwargs
                )
                if confidence_improvement:
                    improvements.append(confidence_improvement)

            # Analyze temporal patterns for scheduling improvements
            temporal_patterns = feedback_patterns.get("temporal_patterns", {})
            if temporal_patterns:
                temporal_improvement = await self._create_temporal_based_improvement(
                    temporal_patterns, **kwargs
                )
                if temporal_improvement:
                    improvements.append(temporal_improvement)

            return improvements

        except Exception as e:
            logger.error(f"Model improvement generation failed: {e}")
            return []

    async def _create_pattern_based_improvement(
        self,
        pattern_key: str,
        corrections: List[Dict[str, Any]],
        **kwargs
    ) -> Optional[ModelImprovement]:
        """Create improvement based on correction patterns."""
        try:
            processing_stage, data_type = pattern_key.split('_', 1)

            # Analyze correction patterns
            correction_analysis = await self._analyze_corrections(corrections)

            if correction_analysis["improvement_potential"] > self.accuracy_improvement_threshold:
                improvement = ModelImprovement(
                    improvement_id=f"imp_{pattern_key}_{int(datetime.now().timestamp())}",
                    model_name=f"pattern_{processing_stage}",
                    improvement_type="pattern_correction",
                    feedback_count=len(corrections),
                    accuracy_improvement=correction_analysis["improvement_potential"],
                    improvement_details={
                        "processing_stage": processing_stage,
                        "data_type": data_type,
                        "correction_patterns": correction_analysis["patterns"],
                        "recommended_adjustments": correction_analysis["recommendations"]
                    }
                )
                return improvement

            return None

        except Exception as e:
            logger.error(f"Pattern-based improvement creation failed: {e}")
            return None

    async def _create_confidence_based_improvement(
        self,
        confidence_dist: Dict[float, int],
        **kwargs
    ) -> Optional[ModelImprovement]:
        """Create improvement based on confidence distribution."""
        try:
            # Analyze confidence distribution
            total_feedbacks = sum(confidence_dist.values())
            low_confidence_feedbacks = sum(
                count for conf, count in confidence_dist.items()
                if conf < 0.7
            )

            if total_feedbacks > 0:
                low_confidence_ratio = low_confidence_feedbacks / total_feedbacks

                if low_confidence_ratio > 0.3:  # More than 30% low confidence
                    improvement = ModelImprovement(
                        improvement_id=f"imp_confidence_{int(datetime.now().timestamp())}",
                        model_name="confidence_calibration",
                        improvement_type="confidence_threshold_adjustment",
                        feedback_count=total_feedbacks,
                        accuracy_improvement=min(0.1, low_confidence_ratio * 0.2),
                        improvement_details={
                            "low_confidence_ratio": low_confidence_ratio,
                            "confidence_distribution": confidence_dist,
                            "recommended_threshold": 0.8 if low_confidence_ratio > 0.5 else 0.7
                        }
                    )
                    return improvement

            return None

        except Exception as e:
            logger.error(f"Confidence-based improvement creation failed: {e}")
            return None

    async def _create_temporal_based_improvement(
        self,
        temporal_patterns: Dict[int, int],
        **kwargs
    ) -> Optional[ModelImprovement]:
        """Create improvement based on temporal patterns."""
        try:
            # Find peak usage hours
            if temporal_patterns:
                peak_hour = max(temporal_patterns.keys(), key=lambda x: temporal_patterns[x])
                peak_feedback_count = temporal_patterns[peak_hour]

                total_feedbacks = sum(temporal_patterns.values())
                peak_ratio = peak_feedback_count / total_feedbacks if total_feedbacks > 0 else 0

                if peak_ratio > 0.3:  # More than 30% of feedback in peak hour
                    improvement = ModelImprovement(
                        improvement_id=f"imp_temporal_{int(datetime.now().timestamp())}",
                        model_name="temporal_optimization",
                        improvement_type="resource_scheduling",
                        feedback_count=total_feedbacks,
                        accuracy_improvement=0.05,  # Small but consistent improvement
                        improvement_details={
                            "peak_hour": peak_hour,
                            "peak_feedback_ratio": peak_ratio,
                            "temporal_distribution": temporal_patterns,
                            "recommended_schedule": f"Increase resources during hour {peak_hour}"
                        }
                    )
                    return improvement

            return None

        except Exception as e:
            logger.error(f"Temporal-based improvement creation failed: {e}")
            return None

    async def _analyze_corrections(self, corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correction patterns to identify improvement opportunities."""
        try:
            # Group corrections by type
            correction_groups = defaultdict(list)

            for correction in corrections:
                original = str(correction.get("original", "")).lower()
                corrected = str(correction.get("corrected", "")).lower()

                if original != corrected:
                    # Simple pattern: original -> corrected
                    pattern_key = f"{original} -> {corrected}"
                    correction_groups[pattern_key].append(correction)

            # Find most common correction patterns
            common_patterns = sorted(
                correction_groups.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:5]

            # Calculate improvement potential
            total_corrections = len(corrections)
            unique_patterns = len(correction_groups)

            # Improvement potential based on pattern consistency
            pattern_consistency = unique_patterns / total_corrections if total_corrections > 0 else 0
            improvement_potential = min(0.2, pattern_consistency * 0.1)  # Cap at 20% improvement

            return {
                "patterns": common_patterns,
                "total_corrections": total_corrections,
                "unique_patterns": unique_patterns,
                "pattern_consistency": pattern_consistency,
                "improvement_potential": improvement_potential,
                "recommendations": [
                    f"Add correction pattern: {pattern[0]}" for pattern, _ in common_patterns[:3]
                ]
            }

        except Exception as e:
            logger.error(f"Correction analysis failed: {e}")
            return {
                "patterns": [],
                "total_corrections": 0,
                "unique_patterns": 0,
                "pattern_consistency": 0.0,
                "improvement_potential": 0.0,
                "recommendations": []
            }

    def _calculate_accuracy_gain(self, improvements: List[ModelImprovement]) -> float:
        """Calculate overall accuracy gain from improvements."""
        if not improvements:
            return 0.0

        total_gain = sum(imp.accuracy_improvement for imp in improvements)
        avg_gain = total_gain / len(improvements)

        # Apply diminishing returns for multiple improvements
        if len(improvements) > 1:
            avg_gain *= (1 - (len(improvements) - 1) * 0.1)  # 10% reduction per additional improvement

        return max(0.0, min(0.5, avg_gain))  # Cap at 50% total improvement

    async def _generate_improvement_recommendations(
        self,
        feedback_patterns: Dict[str, Any],
        improvements: List[ModelImprovement],
        **kwargs
    ) -> List[str]:
        """Generate recommendations for further improvements."""
        try:
            recommendations = []

            # Feedback volume recommendations
            total_feedback = sum(feedback_patterns.get("feedback_types", {}).values())
            if total_feedback < 50:
                recommendations.append("Collect more feedback (target: 50+ samples) for better analysis")

            # Model-specific recommendations
            models_used = feedback_patterns.get("models_used", {})
            if len(models_used) > 1:
                recommendations.append("Consider specializing models for different processing stages")

            # Processing stage recommendations
            processing_stages = feedback_patterns.get("processing_stages", {})
            if processing_stages:
                most_feedback_stage = max(processing_stages.keys(), key=lambda x: processing_stages[x])
                recommendations.append(f"Focus improvements on {most_feedback_stage} processing stage")

            # Improvement-based recommendations
            if not improvements:
                recommendations.append("No significant improvement opportunities found - continue collecting feedback")

            if len(improvements) > 3:
                recommendations.append("Multiple improvement opportunities detected - prioritize top 3")

            return recommendations[:5]

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return ["Continue collecting user feedback for model improvement"]

    def _update_model_performance(self, model_name: str, feedback: UserFeedback):
        """Update model performance tracking."""
        try:
            if model_name not in self.model_performance:
                self.model_performance[model_name] = {
                    "total_feedback": 0,
                    "correct_predictions": 0,
                    "avg_confidence": 0.0,
                    "error_patterns": defaultdict(int),
                    "last_updated": datetime.now()
                }

            perf = self.model_performance[model_name]
            perf["total_feedback"] += 1

            # Update accuracy if correction feedback
            if feedback.feedback_type == "correction":
                if feedback.corrected_prediction != feedback.original_prediction:
                    perf["error_patterns"][feedback.processing_stage] += 1
                else:
                    perf["correct_predictions"] += 1

            # Update average confidence
            if feedback.confidence_score is not None:
                current_avg = perf["avg_confidence"]
                total_count = perf["total_feedback"]
                perf["avg_confidence"] = (current_avg * (total_count - 1) + feedback.confidence_score) / total_count

            perf["last_updated"] = datetime.now()

        except Exception as e:
            logger.error(f"Model performance update failed: {e}")

    def get_feedback_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get feedback statistics."""
        try:
            if user_id:
                user_feedback = self.feedback_store.get(user_id, [])
                return {
                    "user_id": user_id,
                    "total_feedback": len(user_feedback),
                    "feedback_types": self._count_feedback_types(user_feedback),
                    "recent_feedback": len([f for f in user_feedback if f.timestamp > datetime.now() - timedelta(days=7)])
                }
            else:
                all_feedback = []
                for user_feedbacks in self.feedback_store.values():
                    all_feedback.extend(user_feedbacks)

                return {
                    "total_users": len(self.feedback_store),
                    "total_feedback": len(all_feedback),
                    "feedback_types": self._count_feedback_types(all_feedback),
                    "recent_feedback": len([f for f in all_feedback if f.timestamp > datetime.now() - timedelta(days=7)])
                }

        except Exception as e:
            logger.error(f"Feedback stats retrieval failed: {e}")
            return {"error": str(e)}

    def _count_feedback_types(self, feedback_list: List[UserFeedback]) -> Dict[str, int]:
        """Count feedback types in a list."""
        counts = defaultdict(int)
        for feedback in feedback_list:
            counts[feedback.feedback_type] += 1
        return dict(counts)

    def get_model_performance(self, model_name: str = None) -> Dict[str, Any]:
        """Get model performance statistics."""
        try:
            if model_name:
                return self.model_performance.get(model_name, {})
            else:
                return dict(self.model_performance)

        except Exception as e:
            logger.error(f"Model performance retrieval failed: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the feedback loop service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            feedback_stats = self.get_feedback_stats()

            return {
                "service": "feedback_loop",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "feedback_stats": feedback_stats,
                "models_tracked": len(self.model_performance),
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "feedback_loop",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
feedback_loop_service = FeedbackLoopService()