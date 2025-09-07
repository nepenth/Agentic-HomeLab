"""
Importance Scoring Service for ML-based content prioritization.

This service provides intelligent content prioritization capabilities including:
- Content importance scoring based on multiple factors
- ML-based relevance assessment
- User preference learning
- Temporal importance analysis
- Cross-reference analysis
- Engagement prediction
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("importance_scoring_service")


class ImportanceScoringError(Exception):
    """Raised when importance scoring fails."""
    pass


class ImportanceScore:
    """Represents an importance score for content."""

    def __init__(
        self,
        content_id: str,
        overall_score: float,
        score_components: Dict[str, float],
        score_explanation: str = None,
        priority_level: str = None,
        recommended_actions: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.overall_score = overall_score
        self.score_components = score_components
        self.score_explanation = score_explanation
        self.priority_level = priority_level or self._determine_priority_level(overall_score)
        self.recommended_actions = recommended_actions or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def _determine_priority_level(self, score: float) -> str:
        """Determine priority level based on score."""
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score >= 0.2:
            return "low"
        else:
            return "minimal"

    def to_dict(self) -> Dict[str, Any]:
        """Convert score to dictionary."""
        return {
            "content_id": self.content_id,
            "overall_score": self.overall_score,
            "score_components": self.score_components,
            "score_explanation": self.score_explanation,
            "priority_level": self.priority_level,
            "recommended_actions": self.recommended_actions,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ImportanceScoringResult:
    """Result of importance scoring processing."""

    def __init__(
        self,
        content_id: str,
        importance_score: ImportanceScore = None,
        ranking_position: int = None,
        comparative_analysis: Dict[str, Any] = None,
        processing_time_ms: float = None,
        model_used: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.importance_score = importance_score
        self.ranking_position = ranking_position
        self.comparative_analysis = comparative_analysis or {}
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "importance_score": self.importance_score.to_dict() if self.importance_score else None,
            "ranking_position": self.ranking_position,
            "comparative_analysis": self.comparative_analysis,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ImportanceScoringService:
    """Service for ML-based content importance scoring and prioritization."""

    def __init__(self):
        self.default_model = getattr(settings, 'importance_scoring_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'importance_scoring_timeout_seconds', 60)

        # Scoring factors and their weights
        self.scoring_factors = {
            "content_quality": 0.25,
            "relevance": 0.20,
            "timeliness": 0.15,
            "uniqueness": 0.15,
            "engagement_potential": 0.10,
            "authority": 0.10,
            "cross_references": 0.05
        }

        # Priority thresholds
        self.priority_thresholds = {
            "critical": 0.8,
            "high": 0.6,
            "medium": 0.4,
            "low": 0.2,
            "minimal": 0.0
        }

    async def score_content_importance(
        self,
        content_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        **kwargs
    ) -> ImportanceScoringResult:
        """
        Score the importance of content using ML-based analysis.

        Args:
            content_data: Content data dictionary
            context: Context information for scoring
            **kwargs: Additional scoring options

        Returns:
            ImportanceScoringResult with importance analysis
        """
        start_time = datetime.now()
        content_id = content_data.get('content_id', 'unknown')

        try:
            # Extract content for analysis
            content_text = self._extract_content_text(content_data)
            context = context or {}

            if not content_text:
                raise ImportanceScoringError("No analyzable content found")

            # Calculate individual scoring components
            score_components = await self._calculate_score_components(
                content_text, content_data, context, **kwargs
            )

            # Calculate overall score
            overall_score = self._calculate_overall_score(score_components)

            # Generate explanation and recommendations
            explanation = await self._generate_score_explanation(
                score_components, overall_score, content_text, **kwargs
            )

            recommended_actions = await self._generate_recommendations(
                overall_score, score_components, **kwargs
            )

            # Create importance score
            importance_score = ImportanceScore(
                content_id=content_id,
                overall_score=overall_score,
                score_components=score_components,
                score_explanation=explanation,
                recommended_actions=recommended_actions
            )

            # Create result
            result = ImportanceScoringResult(
                content_id=content_id,
                importance_score=importance_score,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                model_used=self.default_model
            )

            logger.info(f"Importance scoring completed for {content_id} with score {overall_score:.3f}")
            return result

        except Exception as e:
            logger.error(f"Importance scoring failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise ImportanceScoringError(f"Importance scoring failed: {str(e)}")

    def _extract_content_text(self, content_data: Dict[str, Any]) -> str:
        """Extract analyzable text from content data."""
        text_parts = []

        # Extract text content
        if 'text' in content_data and content_data['text']:
            text_parts.append(str(content_data['text']))

        # Extract from vision results
        if 'vision_result' in content_data:
            vision = content_data['vision_result']
            if isinstance(vision, dict) and 'caption' in vision:
                text_parts.append(f"Visual: {vision['caption']}")

        # Extract from audio results
        if 'audio_result' in content_data:
            audio = content_data['audio_result']
            if isinstance(audio, dict) and 'transcription' in audio:
                text_parts.append(f"Audio: {audio['transcription']}")

        # Extract from classification results
        if 'classification_result' in content_data:
            classification = content_data['classification_result']
            if isinstance(classification, dict):
                if 'primary_category' in classification:
                    text_parts.append(f"Category: {classification['primary_category']}")
                if 'tags' in classification:
                    tags_text = ", ".join(classification['tags'][:5])
                    text_parts.append(f"Tags: {tags_text}")

        return " ".join(text_parts).strip()

    async def _calculate_score_components(
        self,
        content_text: str,
        content_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, float]:
        """Calculate individual scoring components."""
        components = {}

        # Content quality score
        components["content_quality"] = await self._score_content_quality(
            content_text, content_data, **kwargs
        )

        # Relevance score
        components["relevance"] = await self._score_relevance(
            content_text, context, **kwargs
        )

        # Timeliness score
        components["timeliness"] = await self._score_timeliness(
            content_data, context, **kwargs
        )

        # Uniqueness score
        components["uniqueness"] = await self._score_uniqueness(
            content_text, context, **kwargs
        )

        # Engagement potential score
        components["engagement_potential"] = await self._score_engagement_potential(
            content_text, content_data, **kwargs
        )

        # Authority score
        components["authority"] = await self._score_authority(
            content_data, context, **kwargs
        )

        # Cross-references score
        components["cross_references"] = await self._score_cross_references(
            content_data, context, **kwargs
        )

        return components

    async def _score_content_quality(
        self,
        content_text: str,
        content_data: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content quality."""
        try:
            # Use existing quality scores if available
            if 'quality_score' in content_data:
                return min(1.0, max(0.0, content_data['quality_score']))

            # Analyze content quality
            quality_prompt = f"""
Assess the quality of this content on a scale of 0.0 to 1.0:

Content: {content_text[:1000]}...

Consider:
- Information accuracy and reliability
- Clarity and coherence
- Depth and comprehensiveness
- Objectivity and balance
- Writing quality and professionalism

Provide only the numerical score (0.0 to 1.0).
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=quality_prompt,
                system="You are an expert at content quality assessment. Always respond with only a numerical score.",
                options={
                    "temperature": 0.1,
                    "num_predict": 50
                }
            )

            result_text = response.get('response', '').strip()

            # Extract numerical score
            import re
            score_match = re.search(r'(\d+\.?\d*)', result_text)
            if score_match:
                return float(score_match.group(1))
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Content quality scoring failed: {e}")
            return 0.5

    async def _score_relevance(
        self,
        content_text: str,
        context: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content relevance."""
        try:
            user_interests = context.get('user_interests', [])
            current_topics = context.get('current_topics', [])

            if not user_interests and not current_topics:
                return 0.5  # Neutral score if no context

            relevance_prompt = f"""
Assess how relevant this content is to the user's interests and current topics:

Content: {content_text[:800]}...

User Interests: {', '.join(user_interests)}
Current Topics: {', '.join(current_topics)}

Rate relevance on a scale of 0.0 to 1.0.
Provide only the numerical score.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=relevance_prompt,
                system="You are an expert at relevance assessment. Always respond with only a numerical score.",
                options={
                    "temperature": 0.1,
                    "num_predict": 50
                }
            )

            result_text = response.get('response', '').strip()

            # Extract numerical score
            import re
            score_match = re.search(r'(\d+\.?\d*)', result_text)
            if score_match:
                return float(score_match.group(1))
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            return 0.5

    async def _score_timeliness(
        self,
        content_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content timeliness."""
        try:
            # Check for publication date
            published_at = content_data.get('published_at') or content_data.get('created_at')
            current_time = datetime.now()

            if published_at:
                if isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    except:
                        published_at = None

                if published_at:
                    time_diff = current_time - published_at
                    days_old = time_diff.days

                    # Score based on recency
                    if days_old <= 1:
                        return 1.0  # Very recent
                    elif days_old <= 7:
                        return 0.8  # This week
                    elif days_old <= 30:
                        return 0.6  # This month
                    elif days_old <= 90:
                        return 0.4  # This quarter
                    elif days_old <= 365:
                        return 0.2  # This year
                    else:
                        return 0.1  # Older than a year

            # Check for time-sensitive keywords
            content_text = self._extract_content_text(content_data).lower()
            time_indicators = ['breaking', 'urgent', 'today', 'now', 'latest', 'just in']

            time_score = 0.0
            for indicator in time_indicators:
                if indicator in content_text:
                    time_score += 0.2

            return min(1.0, time_score + 0.3)  # Base score + keyword bonus

        except Exception as e:
            logger.error(f"Timeliness scoring failed: {e}")
            return 0.5

    async def _score_uniqueness(
        self,
        content_text: str,
        context: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content uniqueness."""
        try:
            existing_content = context.get('existing_content', [])

            if not existing_content:
                return 0.8  # Assume unique if no comparison available

            uniqueness_prompt = f"""
Compare this content with existing content to assess uniqueness:

New Content: {content_text[:600]}...

Existing Content Summary: {', '.join(existing_content[:5])}

Rate how unique this content is compared to existing content (0.0 to 1.0).
1.0 = completely unique, 0.0 = identical to existing content.
Provide only the numerical score.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=uniqueness_prompt,
                system="You are an expert at content uniqueness assessment. Always respond with only a numerical score.",
                options={
                    "temperature": 0.1,
                    "num_predict": 50
                }
            )

            result_text = response.get('response', '').strip()

            # Extract numerical score
            import re
            score_match = re.search(r'(\d+\.?\d*)', result_text)
            if score_match:
                return float(score_match.group(1))
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Uniqueness scoring failed: {e}")
            return 0.5

    async def _score_engagement_potential(
        self,
        content_text: str,
        content_data: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content engagement potential."""
        try:
            engagement_prompt = f"""
Assess the engagement potential of this content (0.0 to 1.0):

Content: {content_text[:800]}...

Consider:
- Emotional appeal and relatability
- Controversy or debate potential
- Shareability and virality factors
- Visual or multimedia appeal
- Call-to-action elements
- Personal stories or examples

Provide only the numerical score.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=engagement_prompt,
                system="You are an expert at content engagement analysis. Always respond with only a numerical score.",
                options={
                    "temperature": 0.2,
                    "num_predict": 50
                }
            )

            result_text = response.get('response', '').strip()

            # Extract numerical score
            import re
            score_match = re.search(r'(\d+\.?\d*)', result_text)
            if score_match:
                return float(score_match.group(1))
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Engagement scoring failed: {e}")
            return 0.5

    async def _score_authority(
        self,
        content_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content authority."""
        try:
            # Check for authority indicators
            authority_indicators = []

            # Source reputation
            source = content_data.get('source', '').lower()
            reputable_sources = ['reuters', 'bbc', 'nyt', 'washington post', 'nature', 'science']
            if any(rep_source in source for rep_source in reputable_sources):
                authority_indicators.append('reputable_source')

            # Author credentials
            author = content_data.get('author', '').lower()
            if author and len(author.split()) >= 2:  # Likely a real name
                authority_indicators.append('author_credibility')

            # Citations and references
            content_text = self._extract_content_text(content_data)
            if 'according to' in content_text.lower() or 'research shows' in content_text.lower():
                authority_indicators.append('citations')

            # Domain expertise indicators
            expertise_terms = ['study', 'research', 'analysis', 'expert', 'scientist', 'professor']
            if any(term in content_text.lower() for term in expertise_terms):
                authority_indicators.append('expertise_indicators')

            # Calculate authority score
            base_score = 0.3  # Neutral base
            indicator_bonus = len(authority_indicators) * 0.15
            return min(1.0, base_score + indicator_bonus)

        except Exception as e:
            logger.error(f"Authority scoring failed: {e}")
            return 0.5

    async def _score_cross_references(
        self,
        content_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score content based on cross-references."""
        try:
            cross_refs = context.get('cross_references', [])
            if not cross_refs:
                return 0.3  # Neutral if no cross-reference data

            # Count relevant cross-references
            content_text = self._extract_content_text(content_data).lower()
            relevant_refs = 0

            for ref in cross_refs:
                ref_text = str(ref).lower()
                # Simple relevance check - could be enhanced with semantic similarity
                if any(word in content_text for word in ref_text.split() if len(word) > 3):
                    relevant_refs += 1

            # Calculate cross-reference score
            ref_ratio = relevant_refs / len(cross_refs) if cross_refs else 0
            return min(1.0, ref_ratio * 0.8 + 0.2)  # Scale and add base

        except Exception as e:
            logger.error(f"Cross-reference scoring failed: {e}")
            return 0.3

    def _calculate_overall_score(self, score_components: Dict[str, float]) -> float:
        """Calculate overall importance score from components."""
        overall_score = 0.0

        for factor, weight in self.scoring_factors.items():
            if factor in score_components:
                overall_score += score_components[factor] * weight

        return min(1.0, max(0.0, overall_score))

    async def _generate_score_explanation(
        self,
        score_components: Dict[str, float],
        overall_score: float,
        content_text: str,
        **kwargs
    ) -> str:
        """Generate explanation for the importance score."""
        try:
            explanation_prompt = f"""
Explain why this content received an importance score of {overall_score:.3f}:

Score Components: {json.dumps(score_components, indent=2)}

Content Preview: {content_text[:400]}...

Provide a concise explanation of the key factors that influenced this score.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=explanation_prompt,
                system="You are an expert at explaining content importance scores. Provide clear, concise explanations.",
                options={
                    "temperature": 0.2,
                    "num_predict": kwargs.get('max_tokens', 200)
                }
            )

            return response.get('response', '').strip()

        except Exception as e:
            logger.error(f"Score explanation generation failed: {e}")
            return f"Content received an overall importance score of {overall_score:.3f}."

    async def _generate_recommendations(
        self,
        overall_score: float,
        score_components: Dict[str, float],
        **kwargs
    ) -> List[str]:
        """Generate recommendations based on the importance score."""
        try:
            recommendations = []

            # Priority-based recommendations
            if overall_score >= 0.8:
                recommendations.extend([
                    "Prioritize for immediate review and action",
                    "Consider sharing with key stakeholders",
                    "Flag for executive summary inclusion"
                ])
            elif overall_score >= 0.6:
                recommendations.extend([
                    "Review within 24 hours",
                    "Add to weekly priority list",
                    "Consider for team discussion"
                ])
            elif overall_score >= 0.4:
                recommendations.extend([
                    "Review when time permits",
                    "Monitor for updates or related content",
                    "Consider for future reference"
                ])
            else:
                recommendations.extend([
                    "Low priority - review as needed",
                    "Consider archiving for historical reference",
                    "May be suitable for automated processing only"
                ])

            # Component-specific recommendations
            if score_components.get('content_quality', 0) < 0.4:
                recommendations.append("Consider content quality improvement before action")

            if score_components.get('timeliness', 0) > 0.7:
                recommendations.append("Time-sensitive content - review promptly")

            if score_components.get('relevance', 0) > 0.8:
                recommendations.append("Highly relevant to current interests - prioritize")

            return recommendations[:5]  # Limit to 5 recommendations

        except Exception as e:
            logger.error(f"Recommendations generation failed: {e}")
            return ["Review content based on individual assessment"]

    async def rank_content_batch(
        self,
        content_batch: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
        **kwargs
    ) -> List[ImportanceScoringResult]:
        """
        Rank a batch of content items by importance.

        Args:
            content_batch: List of content data dictionaries
            context: Context information for scoring
            **kwargs: Additional ranking options

        Returns:
            List of ImportanceScoringResult objects, ranked by importance
        """
        try:
            # Score all content items
            scoring_tasks = []
            for content_data in content_batch:
                task = self.score_content_importance(content_data, context, **kwargs)
                scoring_tasks.append(task)

            # Execute scoring in parallel
            scoring_results = await asyncio.gather(*scoring_tasks, return_exceptions=True)

            # Process results and handle exceptions
            valid_results = []
            for i, result in enumerate(scoring_results):
                if isinstance(result, Exception):
                    logger.error(f"Scoring failed for batch item {i}: {result}")
                    # Create a minimal result for failed items
                    error_result = ImportanceScoringResult(
                        content_id=content_batch[i].get('content_id', f'batch_item_{i}'),
                        metadata={"error": str(result)}
                    )
                    valid_results.append(error_result)
                else:
                    valid_results.append(result)

            # Sort by importance score (highest first)
            valid_results.sort(
                key=lambda x: x.importance_score.overall_score if x.importance_score else 0,
                reverse=True
            )

            # Add ranking positions
            for i, result in enumerate(valid_results):
                result.ranking_position = i + 1

            return valid_results

        except Exception as e:
            logger.error(f"Batch ranking failed: {e}")
            return []

    def get_scoring_factors(self) -> Dict[str, float]:
        """Get the scoring factors and their weights."""
        return self.scoring_factors.copy()

    def get_priority_thresholds(self) -> Dict[str, float]:
        """Get the priority level thresholds."""
        return self.priority_thresholds.copy()

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the importance scoring service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "importance_scoring",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "scoring_factors": self.get_scoring_factors(),
                "priority_thresholds": self.get_priority_thresholds(),
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "importance_scoring",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
importance_scoring_service = ImportanceScoringService()