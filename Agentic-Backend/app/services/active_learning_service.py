"""
Active Learning Service for intelligent selection of content for manual review.

This service provides active learning capabilities including:
- Uncertainty sampling for content selection
- Query-by-committee for diverse model opinions
- Expected model change for maximum learning impact
- Representative sampling for dataset diversity
- Adaptive sampling strategies based on learning progress
- Manual review queue optimization
"""

import asyncio
import json
import random
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import math

from app.config import settings
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("active_learning_service")


class ActiveLearningError(Exception):
    """Raised when active learning fails."""
    pass


class LearningSample:
    """Represents a content sample for active learning."""

    def __init__(
        self,
        content_id: str,
        content_data: Dict[str, Any],
        uncertainty_score: float = None,
        diversity_score: float = None,
        expected_change: float = None,
        selection_reason: str = None,
        model_predictions: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.content_data = content_data
        self.uncertainty_score = uncertainty_score
        self.diversity_score = diversity_score
        self.expected_change = expected_change
        self.selection_reason = selection_reason
        self.model_predictions = model_predictions or {}
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert sample to dictionary."""
        return {
            "content_id": self.content_id,
            "content_data": self.content_data,
            "uncertainty_score": self.uncertainty_score,
            "diversity_score": self.diversity_score,
            "expected_change": self.expected_change,
            "selection_reason": self.selection_reason,
            "model_predictions": self.model_predictions,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ActiveLearningResult:
    """Result of active learning sample selection."""

    def __init__(
        self,
        selection_id: str,
        selected_samples: List[LearningSample] = None,
        selection_strategy: str = None,
        total_candidates: int = None,
        selection_criteria: Dict[str, Any] = None,
        processing_time_ms: float = None,
        metadata: Dict[str, Any] = None
    ):
        self.selection_id = selection_id
        self.selected_samples = selected_samples or []
        self.selection_strategy = selection_strategy
        self.total_candidates = total_candidates
        self.selection_criteria = selection_criteria or {}
        self.processing_time_ms = processing_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "selection_id": self.selection_id,
            "selected_samples": [sample.to_dict() for sample in self.selected_samples],
            "selection_strategy": self.selection_strategy,
            "total_candidates": self.total_candidates,
            "selection_criteria": self.selection_criteria,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ActiveLearningService:
    """Service for intelligent selection of content for manual review and learning."""

    def __init__(self):
        self.default_model = getattr(settings, 'active_learning_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'active_learning_timeout_seconds', 120)

        # Active learning strategies
        self.strategies = {
            "uncertainty_sampling": self._uncertainty_sampling,
            "query_by_committee": self._query_by_committee,
            "expected_model_change": self._expected_model_change,
            "representative_sampling": self._representative_sampling,
            "diversity_sampling": self._diversity_sampling,
            "adaptive_sampling": self._adaptive_sampling
        }

        # Learning progress tracking
        self.learning_progress: Dict[str, Dict[str, Any]] = defaultdict(dict)

    async def select_learning_samples(
        self,
        candidate_content: List[Dict[str, Any]],
        selection_strategy: str = "adaptive_sampling",
        sample_size: int = 10,
        **kwargs
    ) -> ActiveLearningResult:
        """
        Select content samples for manual review using active learning strategies.

        Args:
            candidate_content: List of content candidates for selection
            selection_strategy: Strategy to use for selection
            sample_size: Number of samples to select
            **kwargs: Additional selection parameters

        Returns:
            ActiveLearningResult with selected samples
        """
        start_time = datetime.now()
        selection_id = f"selection_{int(datetime.now().timestamp())}"

        try:
            if not candidate_content:
                raise ActiveLearningError("No candidate content provided")

            if selection_strategy not in self.strategies:
                logger.warning(f"Unknown strategy {selection_strategy}, using adaptive_sampling")
                selection_strategy = "adaptive_sampling"

            # Apply selection strategy
            strategy_func = self.strategies[selection_strategy]
            selected_samples = await strategy_func(
                candidate_content,
                sample_size=sample_size,
                **kwargs
            )

            # Create result
            result = ActiveLearningResult(
                selection_id=selection_id,
                selected_samples=selected_samples,
                selection_strategy=selection_strategy,
                total_candidates=len(candidate_content),
                selection_criteria={
                    "sample_size": sample_size,
                    "strategy": selection_strategy,
                    **kwargs
                },
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

            logger.info(f"Active learning selection completed: {len(selected_samples)} samples selected using {selection_strategy}")
            return result

        except Exception as e:
            logger.error(f"Active learning selection failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise ActiveLearningError(f"Active learning selection failed: {str(e)}")

    async def _uncertainty_sampling(
        self,
        candidate_content: List[Dict[str, Any]],
        sample_size: int = 10,
        **kwargs
    ) -> List[LearningSample]:
        """Select samples with highest model uncertainty."""
        try:
            scored_candidates = []

            for content in candidate_content:
                # Get model predictions and uncertainty
                uncertainty_score = await self._calculate_uncertainty(content, **kwargs)

                sample = LearningSample(
                    content_id=content.get('content_id', f'candidate_{len(scored_candidates)}'),
                    content_data=content,
                    uncertainty_score=uncertainty_score,
                    selection_reason="High model uncertainty - needs human review"
                )
                scored_candidates.append(sample)

            # Sort by uncertainty (highest first)
            scored_candidates.sort(key=lambda x: x.uncertainty_score or 0, reverse=True)

            return scored_candidates[:sample_size]

        except Exception as e:
            logger.error(f"Uncertainty sampling failed: {e}")
            return []

    async def _query_by_committee(
        self,
        candidate_content: List[Dict[str, Any]],
        sample_size: int = 10,
        **kwargs
    ) -> List[LearningSample]:
        """Select samples where committee members disagree most."""
        try:
            committee_size = kwargs.get('committee_size', 3)
            scored_candidates = []

            for content in candidate_content:
                # Get predictions from multiple models/committee members
                committee_predictions = await self._get_committee_predictions(
                    content, committee_size, **kwargs
                )

                # Calculate disagreement score
                disagreement_score = self._calculate_committee_disagreement(committee_predictions)

                sample = LearningSample(
                    content_id=content.get('content_id', f'candidate_{len(scored_candidates)}'),
                    content_data=content,
                    uncertainty_score=disagreement_score,
                    model_predictions=committee_predictions,
                    selection_reason="High disagreement among model committee"
                )
                scored_candidates.append(sample)

            # Sort by disagreement (highest first)
            scored_candidates.sort(key=lambda x: x.uncertainty_score or 0, reverse=True)

            return scored_candidates[:sample_size]

        except Exception as e:
            logger.error(f"Query by committee sampling failed: {e}")
            return []

    async def _expected_model_change(
        self,
        candidate_content: List[Dict[str, Any]],
        sample_size: int = 10,
        **kwargs
    ) -> List[LearningSample]:
        """Select samples that would cause maximum model change if labeled."""
        try:
            scored_candidates = []

            for content in candidate_content:
                # Calculate expected model change
                expected_change = await self._calculate_expected_change(content, **kwargs)

                sample = LearningSample(
                    content_id=content.get('content_id', f'candidate_{len(scored_candidates)}'),
                    content_data=content,
                    expected_change=expected_change,
                    selection_reason="High expected model improvement potential"
                )
                scored_candidates.append(sample)

            # Sort by expected change (highest first)
            scored_candidates.sort(key=lambda x: x.expected_change or 0, reverse=True)

            return scored_candidates[:sample_size]

        except Exception as e:
            logger.error(f"Expected model change sampling failed: {e}")
            return []

    async def _representative_sampling(
        self,
        candidate_content: List[Dict[str, Any]],
        sample_size: int = 10,
        **kwargs
    ) -> List[LearningSample]:
        """Select samples that best represent the overall dataset."""
        try:
            # Cluster content and select representatives
            clusters = await self._cluster_content(candidate_content, **kwargs)

            # Select representative from each cluster
            representatives = []
            samples_per_cluster = max(1, sample_size // len(clusters)) if clusters else sample_size

            for cluster_content in clusters.values():
                cluster_representatives = await self._select_cluster_representatives(
                    cluster_content, samples_per_cluster, **kwargs
                )
                representatives.extend(cluster_representatives)

            # Fill remaining slots if needed
            remaining_slots = sample_size - len(representatives)
            if remaining_slots > 0:
                unselected = [c for c in candidate_content if c.get('content_id') not in
                            {r.content_id for r in representatives}]
                additional_samples = await self._uncertainty_sampling(
                    unselected, sample_size=remaining_slots, **kwargs
                )
                representatives.extend(additional_samples)

            return representatives[:sample_size]

        except Exception as e:
            logger.error(f"Representative sampling failed: {e}")
            return []

    async def _diversity_sampling(
        self,
        candidate_content: List[Dict[str, Any]],
        sample_size: int = 10,
        **kwargs
    ) -> List[LearningSample]:
        """Select diverse samples to maximize coverage."""
        try:
            selected_samples = []
            remaining_candidates = candidate_content.copy()

            # Select first sample randomly
            if remaining_candidates:
                first_sample = random.choice(remaining_candidates)
                selected_samples.append(LearningSample(
                    content_id=first_sample.get('content_id', 'sample_0'),
                    content_data=first_sample,
                    selection_reason="Initial diverse sample"
                ))
                remaining_candidates.remove(first_sample)

            # Select subsequent samples to maximize diversity
            while len(selected_samples) < sample_size and remaining_candidates:
                best_candidate = None
                best_diversity_score = -1

                for candidate in remaining_candidates:
                    diversity_score = await self._calculate_diversity_score(
                        candidate, selected_samples, **kwargs
                    )

                    if diversity_score > best_diversity_score:
                        best_diversity_score = diversity_score
                        best_candidate = candidate

                if best_candidate:
                    selected_samples.append(LearningSample(
                        content_id=best_candidate.get('content_id', f'sample_{len(selected_samples)}'),
                        content_data=best_candidate,
                        diversity_score=best_diversity_score,
                        selection_reason="Maximum diversity from existing samples"
                    ))
                    remaining_candidates.remove(best_candidate)

            return selected_samples

        except Exception as e:
            logger.error(f"Diversity sampling failed: {e}")
            return []

    async def _adaptive_sampling(
        self,
        candidate_content: List[Dict[str, Any]],
        sample_size: int = 10,
        **kwargs
    ) -> List[LearningSample]:
        """Adaptively select samples based on learning progress."""
        try:
            # Analyze current learning progress
            learning_state = self._analyze_learning_progress()

            # Choose strategy based on learning state
            if learning_state["needs_uncertainty"]:
                strategy = "uncertainty_sampling"
            elif learning_state["needs_diversity"]:
                strategy = "diversity_sampling"
            elif learning_state["needs_committee"]:
                strategy = "query_by_committee"
            else:
                strategy = "representative_sampling"

            logger.info(f"Adaptive sampling chose strategy: {strategy}")

            # Apply chosen strategy
            strategy_func = self.strategies[strategy]
            return await strategy_func(candidate_content, sample_size=sample_size, **kwargs)

        except Exception as e:
            logger.error(f"Adaptive sampling failed: {e}")
            # Fallback to uncertainty sampling
            return await self._uncertainty_sampling(candidate_content, sample_size=sample_size, **kwargs)

    async def _calculate_uncertainty(self, content: Dict[str, Any], **kwargs) -> float:
        """Calculate model uncertainty for content."""
        try:
            # Get multiple predictions with different parameters
            predictions = []

            for i in range(3):  # Get 3 predictions with different temperatures
                temperature = 0.1 + (i * 0.4)  # 0.1, 0.5, 0.9
                prediction = await self._get_model_prediction(content, temperature=temperature, **kwargs)
                predictions.append(prediction)

            # Calculate uncertainty as variance in predictions
            if len(predictions) > 1:
                # Simple uncertainty measure: number of different predictions
                unique_predictions = set(str(p) for p in predictions)
                uncertainty = len(unique_predictions) / len(predictions)
                return uncertainty
            else:
                return 0.5  # Default uncertainty

        except Exception as e:
            logger.error(f"Uncertainty calculation failed: {e}")
            return 0.5

    async def _get_committee_predictions(
        self,
        content: Dict[str, Any],
        committee_size: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Get predictions from a committee of models/approaches."""
        try:
            committee_predictions = {}

            # Use different models or parameters as committee members
            models = kwargs.get('committee_models', [self.default_model])

            for i, model in enumerate(models[:committee_size]):
                prediction = await self._get_model_prediction(
                    content, model=model, temperature=0.3, **kwargs
                )
                committee_predictions[f"member_{i}"] = {
                    "model": model,
                    "prediction": prediction
                }

            return committee_predictions

        except Exception as e:
            logger.error(f"Committee prediction failed: {e}")
            return {}

    def _calculate_committee_disagreement(self, committee_predictions: Dict[str, Any]) -> float:
        """Calculate disagreement score among committee members."""
        try:
            if len(committee_predictions) < 2:
                return 0.0

            predictions = [member["prediction"] for member in committee_predictions.values()]

            # Count unique predictions
            unique_predictions = set(str(p) for p in predictions)
            disagreement = len(unique_predictions) / len(predictions)

            return disagreement

        except Exception as e:
            logger.error(f"Committee disagreement calculation failed: {e}")
            return 0.0

    async def _calculate_expected_change(self, content: Dict[str, Any], **kwargs) -> float:
        """Calculate expected model change if this sample were labeled."""
        try:
            # Simplified: use uncertainty as proxy for expected change
            uncertainty = await self._calculate_uncertainty(content, **kwargs)

            # Add content complexity factor
            content_text = self._extract_content_text(content)
            complexity = min(1.0, len(content_text.split()) / 1000)  # Normalize by 1000 words

            expected_change = (uncertainty + complexity) / 2
            return expected_change

        except Exception as e:
            logger.error(f"Expected change calculation failed: {e}")
            return 0.0

    async def _cluster_content(
        self,
        content_list: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Cluster content for representative sampling."""
        try:
            # Simple clustering based on content type and length
            clusters = defaultdict(list)

            for content in content_list:
                # Create cluster key based on content characteristics
                content_type = content.get('type', 'unknown')
                content_length = len(self._extract_content_text(content).split())

                if content_length < 50:
                    length_category = "short"
                elif content_length < 200:
                    length_category = "medium"
                else:
                    length_category = "long"

                cluster_key = f"{content_type}_{length_category}"
                clusters[cluster_key].append(content)

            return dict(clusters)

        except Exception as e:
            logger.error(f"Content clustering failed: {e}")
            return {"default": content_list}

    async def _select_cluster_representatives(
        self,
        cluster_content: List[Dict[str, Any]],
        num_representatives: int,
        **kwargs
    ) -> List[LearningSample]:
        """Select representative samples from a cluster."""
        try:
            if not cluster_content:
                return []

            # Sort by some representative metric (e.g., length, complexity)
            sorted_content = sorted(
                cluster_content,
                key=lambda x: len(self._extract_content_text(x).split()),
                reverse=True  # Prefer longer/more complex content
            )

            representatives = []
            for i, content in enumerate(sorted_content[:num_representatives]):
                representatives.append(LearningSample(
                    content_id=content.get('content_id', f'rep_{i}'),
                    content_data=content,
                    selection_reason="Representative sample from cluster"
                ))

            return representatives

        except Exception as e:
            logger.error(f"Cluster representative selection failed: {e}")
            return []

    async def _calculate_diversity_score(
        self,
        candidate: Dict[str, Any],
        selected_samples: List[LearningSample],
        **kwargs
    ) -> float:
        """Calculate diversity score relative to already selected samples."""
        try:
            if not selected_samples:
                return 1.0

            candidate_text = self._extract_content_text(candidate)

            # Calculate average similarity to selected samples
            similarities = []
            for sample in selected_samples:
                sample_text = self._extract_content_text(sample.content_data)
                similarity = self._calculate_text_similarity(candidate_text, sample_text)
                similarities.append(similarity)

            avg_similarity = sum(similarities) / len(similarities) if similarities else 0

            # Diversity score is inverse of average similarity
            diversity_score = 1.0 - avg_similarity
            return diversity_score

        except Exception as e:
            logger.error(f"Diversity score calculation failed: {e}")
            return 0.5

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        try:
            # Jaccard similarity on words
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            if not words1 or not words2:
                return 0.0

            intersection = words1 & words2
            union = words1 | words2

            return len(intersection) / len(union)

        except Exception:
            return 0.0

    def _extract_content_text(self, content: Dict[str, Any]) -> str:
        """Extract text content for analysis."""
        text_parts = []

        if 'text' in content and content['text']:
            text_parts.append(str(content['text']))

        if 'caption' in content and content['caption']:
            text_parts.append(str(content['caption']))

        if 'transcription' in content and content['transcription']:
            text_parts.append(str(content['transcription']))

        return " ".join(text_parts).strip()

    async def _get_model_prediction(self, content: Dict[str, Any], **kwargs) -> Any:
        """Get prediction from model for content."""
        try:
            content_text = self._extract_content_text(content)

            if not content_text:
                return "no_content"

            # Simple classification prompt
            prompt = f"Analyze this content and provide a brief classification or summary: {content_text[:500]}..."

            response = await ollama_client.generate(
                model=kwargs.get('model', self.default_model),
                prompt=prompt,
                system="You are a content analysis AI. Provide concise, accurate analysis.",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 100)
                }
            )

            return response.get('response', '').strip()

        except Exception as e:
            logger.error(f"Model prediction failed: {e}")
            return "prediction_failed"

    def _analyze_learning_progress(self) -> Dict[str, Any]:
        """Analyze current learning progress to inform adaptive sampling."""
        try:
            # Simple analysis based on recent activity
            # In a real implementation, this would track actual learning metrics

            return {
                "needs_uncertainty": True,  # Default to uncertainty sampling
                "needs_diversity": False,
                "needs_committee": False,
                "learning_phase": "exploration"
            }

        except Exception as e:
            logger.error(f"Learning progress analysis failed: {e}")
            return {
                "needs_uncertainty": True,
                "needs_diversity": False,
                "needs_committee": False,
                "learning_phase": "exploration"
            }

    def get_available_strategies(self) -> List[str]:
        """Get list of available sampling strategies."""
        return list(self.strategies.keys())

    def get_strategy_description(self, strategy: str) -> str:
        """Get description of a sampling strategy."""
        descriptions = {
            "uncertainty_sampling": "Select samples where the model is most uncertain",
            "query_by_committee": "Select samples where different models disagree most",
            "expected_model_change": "Select samples that would most improve the model",
            "representative_sampling": "Select samples that best represent the dataset",
            "diversity_sampling": "Select diverse samples to maximize coverage",
            "adaptive_sampling": "Automatically choose the best strategy based on learning progress"
        }
        return descriptions.get(strategy, "Unknown strategy")

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the active learning service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "active_learning",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "available_strategies": self.get_available_strategies(),
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "active_learning",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
active_learning_service = ActiveLearningService()