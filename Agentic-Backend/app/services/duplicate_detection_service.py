"""
Duplicate Detection Service for semantic similarity analysis.

This service provides intelligent duplicate detection capabilities including:
- Semantic similarity analysis using embeddings
- Text similarity comparison
- Image similarity detection
- Audio similarity analysis
- Cross-modal duplicate detection
- Near-duplicate identification
- Similarity scoring and ranking
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
import hashlib

from app.config import settings
from app.services.ollama_client import ollama_client
from app.services.semantic_processing_service import semantic_processing_service
from app.utils.logging import get_logger

logger = get_logger("duplicate_detection_service")


class DuplicateDetectionError(Exception):
    """Raised when duplicate detection fails."""
    pass


class SimilarityResult:
    """Result of similarity analysis between two content items."""

    def __init__(
        self,
        content_id_1: str,
        content_id_2: str,
        similarity_score: float,
        similarity_type: str,
        similarity_details: Dict[str, Any] = None,
        is_duplicate: bool = False,
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None
    ):
        self.content_id_1 = content_id_1
        self.content_id_2 = content_id_2
        self.similarity_score = similarity_score
        self.similarity_type = similarity_type  # 'text', 'image', 'audio', 'cross_modal'
        self.similarity_details = similarity_details or {}
        self.is_duplicate = is_duplicate
        self.confidence = confidence
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id_1": self.content_id_1,
            "content_id_2": self.content_id_2,
            "similarity_score": self.similarity_score,
            "similarity_type": self.similarity_type,
            "similarity_details": self.similarity_details,
            "is_duplicate": self.is_duplicate,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class DuplicateDetectionResult:
    """Result of duplicate detection analysis."""

    def __init__(
        self,
        content_id: str,
        duplicate_candidates: List[SimilarityResult] = None,
        is_duplicate: bool = False,
        canonical_content_id: str = None,
        duplicate_group: List[str] = None,
        processing_time_ms: float = None,
        model_used: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.duplicate_candidates = duplicate_candidates or []
        self.is_duplicate = is_duplicate
        self.canonical_content_id = canonical_content_id
        self.duplicate_group = duplicate_group or []
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "duplicate_candidates": [candidate.to_dict() for candidate in self.duplicate_candidates],
            "is_duplicate": self.is_duplicate,
            "canonical_content_id": self.canonical_content_id,
            "duplicate_group": self.duplicate_group,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class DuplicateDetectionService:
    """Service for intelligent duplicate detection using semantic similarity."""

    def __init__(self):
        self.default_model = getattr(settings, 'duplicate_detection_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'duplicate_detection_timeout_seconds', 120)

        # Similarity thresholds
        self.similarity_thresholds = {
            "exact_duplicate": 0.95,
            "near_duplicate": 0.80,
            "similar": 0.60,
            "related": 0.40
        }

        # Supported modalities
        self.supported_modalities = ['text', 'image', 'audio']

    async def detect_duplicates(
        self,
        content_data: Dict[str, Any],
        comparison_content: List[Dict[str, Any]] = None,
        similarity_threshold: float = None,
        **kwargs
    ) -> DuplicateDetectionResult:
        """
        Detect duplicates for content using semantic similarity analysis.

        Args:
            content_data: Content data to check for duplicates
            comparison_content: List of content to compare against
            similarity_threshold: Threshold for considering content as duplicate
            **kwargs: Additional detection options

        Returns:
            DuplicateDetectionResult with duplicate analysis
        """
        start_time = datetime.now()
        content_id = content_data.get('content_id', 'unknown')

        try:
            similarity_threshold = similarity_threshold or self.similarity_thresholds["near_duplicate"]

            # Extract content for analysis
            content_text = self._extract_content_text(content_data)
            content_modalities = self._identify_modalities(content_data)

            if not content_text and not content_modalities:
                raise DuplicateDetectionError("No analyzable content found")

            # Generate content signature for initial filtering
            content_signature = self._generate_content_signature(content_data)

            # Find candidate duplicates
            duplicate_candidates = []

            if comparison_content:
                # Compare against provided content
                for comp_content in comparison_content:
                    similarity = await self._calculate_similarity(
                        content_data, comp_content, **kwargs
                    )

                    if similarity.similarity_score >= similarity_threshold:
                        duplicate_candidates.append(similarity)

            # Sort candidates by similarity score
            duplicate_candidates.sort(key=lambda x: x.similarity_score, reverse=True)

            # Determine if content is a duplicate
            is_duplicate = len(duplicate_candidates) > 0
            canonical_content_id = None
            duplicate_group = []

            if is_duplicate:
                # Use the highest similarity content as canonical
                top_candidate = duplicate_candidates[0]
                canonical_content_id = top_candidate.content_id_2

                # Build duplicate group
                duplicate_group = [content_id]
                for candidate in duplicate_candidates:
                    if candidate.similarity_score >= similarity_threshold:
                        duplicate_group.append(candidate.content_id_2)

            # Create result
            result = DuplicateDetectionResult(
                content_id=content_id,
                duplicate_candidates=duplicate_candidates[:10],  # Limit to top 10
                is_duplicate=is_duplicate,
                canonical_content_id=canonical_content_id,
                duplicate_group=duplicate_group,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                model_used=self.default_model
            )

            logger.info(f"Duplicate detection completed for {content_id}: {len(duplicate_candidates)} candidates found")
            return result

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise DuplicateDetectionError(f"Duplicate detection failed: {str(e)}")

    async def _calculate_similarity(
        self,
        content_1: Dict[str, Any],
        content_2: Dict[str, Any],
        **kwargs
    ) -> SimilarityResult:
        """Calculate similarity between two content items."""
        content_id_1 = content_1.get('content_id', 'unknown_1')
        content_id_2 = content_2.get('content_id', 'unknown_2')

        try:
            # Determine similarity calculation method based on modalities
            modalities_1 = self._identify_modalities(content_1)
            modalities_2 = self._identify_modalities(content_2)

            similarity_scores = {}
            similarity_details = {}

            # Text similarity
            if 'text' in modalities_1 and 'text' in modalities_2:
                text_similarity = await self._calculate_text_similarity(
                    content_1, content_2, **kwargs
                )
                similarity_scores['text'] = text_similarity['score']
                similarity_details['text'] = text_similarity

            # Image similarity
            if 'image' in modalities_1 and 'image' in modalities_2:
                image_similarity = await self._calculate_image_similarity(
                    content_1, content_2, **kwargs
                )
                similarity_scores['image'] = image_similarity['score']
                similarity_details['image'] = image_similarity

            # Audio similarity
            if 'audio' in modalities_1 and 'audio' in modalities_2:
                audio_similarity = await self._calculate_audio_similarity(
                    content_1, content_2, **kwargs
                )
                similarity_scores['audio'] = audio_similarity['score']
                similarity_details['audio'] = audio_similarity

            # Cross-modal similarity
            if len(modalities_1) > 1 and len(modalities_2) > 1:
                cross_modal_similarity = await self._calculate_cross_modal_similarity(
                    content_1, content_2, modalities_1, modalities_2, **kwargs
                )
                similarity_scores['cross_modal'] = cross_modal_similarity['score']
                similarity_details['cross_modal'] = cross_modal_similarity

            # Calculate overall similarity
            if similarity_scores:
                # Weighted average based on available modalities
                weights = {modality: 1.0 / len(similarity_scores) for modality in similarity_scores}
                overall_score = sum(score * weights[modality] for modality, score in similarity_scores.items())
            else:
                overall_score = 0.0

            # Determine similarity type
            if 'cross_modal' in similarity_scores:
                similarity_type = 'cross_modal'
            elif 'text' in similarity_scores:
                similarity_type = 'text'
            elif 'image' in similarity_scores:
                similarity_type = 'image'
            elif 'audio' in similarity_scores:
                similarity_type = 'audio'
            else:
                similarity_type = 'unknown'

            # Determine if duplicate
            is_duplicate = overall_score >= self.similarity_thresholds["near_duplicate"]
            confidence = min(1.0, overall_score + 0.1)  # Add small confidence boost

            return SimilarityResult(
                content_id_1=content_id_1,
                content_id_2=content_id_2,
                similarity_score=overall_score,
                similarity_type=similarity_type,
                similarity_details=similarity_details,
                is_duplicate=is_duplicate,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return SimilarityResult(
                content_id_1=content_id_1,
                content_id_2=content_id_2,
                similarity_score=0.0,
                similarity_type='error',
                similarity_details={"error": str(e)},
                is_duplicate=False,
                confidence=0.0
            )

    async def _calculate_text_similarity(
        self,
        content_1: Dict[str, Any],
        content_2: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate text similarity between two content items."""
        try:
            text_1 = self._extract_content_text(content_1)
            text_2 = self._extract_content_text(content_2)

            if not text_1 or not text_2:
                return {"score": 0.0, "method": "text", "details": "Missing text content"}

            # Use semantic similarity if available
            if hasattr(semantic_processing_service, 'calculate_similarity'):
                similarity_score = await semantic_processing_service.calculate_similarity(text_1, text_2)
            else:
                # Fallback to basic text comparison
                similarity_score = self._calculate_basic_text_similarity(text_1, text_2)

            return {
                "score": similarity_score,
                "method": "semantic",
                "text_length_1": len(text_1),
                "text_length_2": len(text_2),
                "details": f"Semantic similarity: {similarity_score:.3f}"
            }

        except Exception as e:
            logger.error(f"Text similarity calculation failed: {e}")
            return {"score": 0.0, "method": "text", "error": str(e)}

    async def _calculate_image_similarity(
        self,
        content_1: Dict[str, Any],
        content_2: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate image similarity between two content items."""
        try:
            # Extract image data
            image_1 = content_1.get('image')
            image_2 = content_2.get('image')

            if not image_1 or not image_2:
                return {"score": 0.0, "method": "image", "details": "Missing image content"}

            # For now, use basic comparison - could be enhanced with image hashing
            similarity_score = self._calculate_basic_image_similarity(image_1, image_2)

            return {
                "score": similarity_score,
                "method": "perceptual_hash",
                "details": f"Image similarity: {similarity_score:.3f}"
            }

        except Exception as e:
            logger.error(f"Image similarity calculation failed: {e}")
            return {"score": 0.0, "method": "image", "error": str(e)}

    async def _calculate_audio_similarity(
        self,
        content_1: Dict[str, Any],
        content_2: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate audio similarity between two content items."""
        try:
            # Extract audio data
            audio_1 = content_1.get('audio')
            audio_2 = content_2.get('audio')

            if not audio_1 or not audio_2:
                return {"score": 0.0, "method": "audio", "details": "Missing audio content"}

            # For now, use basic comparison - could be enhanced with audio fingerprinting
            similarity_score = self._calculate_basic_audio_similarity(audio_1, audio_2)

            return {
                "score": similarity_score,
                "method": "audio_fingerprint",
                "details": f"Audio similarity: {similarity_score:.3f}"
            }

        except Exception as e:
            logger.error(f"Audio similarity calculation failed: {e}")
            return {"score": 0.0, "method": "audio", "error": str(e)}

    async def _calculate_cross_modal_similarity(
        self,
        content_1: Dict[str, Any],
        content_2: Dict[str, Any],
        modalities_1: List[str],
        modalities_2: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate cross-modal similarity."""
        try:
            # Extract content from all modalities
            combined_text_1 = self._extract_content_text(content_1)
            combined_text_2 = self._extract_content_text(content_2)

            # Use semantic similarity on combined content
            if hasattr(semantic_processing_service, 'calculate_similarity'):
                similarity_score = await semantic_processing_service.calculate_similarity(
                    combined_text_1, combined_text_2
                )
            else:
                similarity_score = self._calculate_basic_text_similarity(combined_text_1, combined_text_2)

            # Adjust score based on modality overlap
            modality_overlap = len(set(modalities_1) & set(modalities_2))
            modality_boost = modality_overlap * 0.1

            adjusted_score = min(1.0, similarity_score + modality_boost)

            return {
                "score": adjusted_score,
                "method": "cross_modal",
                "modalities_1": modalities_1,
                "modalities_2": modalities_2,
                "modality_overlap": modality_overlap,
                "details": f"Cross-modal similarity: {adjusted_score:.3f}"
            }

        except Exception as e:
            logger.error(f"Cross-modal similarity calculation failed: {e}")
            return {"score": 0.0, "method": "cross_modal", "error": str(e)}

    def _calculate_basic_text_similarity(self, text_1: str, text_2: str) -> float:
        """Calculate basic text similarity using simple methods."""
        try:
            # Simple Jaccard similarity on words
            words_1 = set(text_1.lower().split())
            words_2 = set(text_2.lower().split())

            if not words_1 or not words_2:
                return 0.0

            intersection = words_1 & words_2
            union = words_1 | words_2

            jaccard_similarity = len(intersection) / len(union)

            # Length difference penalty
            len_diff = abs(len(text_1) - len(text_2)) / max(len(text_1), len(text_2))
            length_penalty = len_diff * 0.2

            return max(0.0, jaccard_similarity - length_penalty)

        except Exception as e:
            logger.error(f"Basic text similarity calculation failed: {e}")
            return 0.0

    def _calculate_basic_image_similarity(self, image_1: Any, image_2: Any) -> float:
        """Calculate basic image similarity."""
        try:
            # Simple hash-based comparison
            hash_1 = self._calculate_image_hash(image_1)
            hash_2 = self._calculate_image_hash(image_2)

            if hash_1 and hash_2:
                # Hamming distance
                distance = sum(c1 != c2 for c1, c2 in zip(hash_1, hash_2))
                max_distance = len(hash_1)
                similarity = 1.0 - (distance / max_distance)
                return max(0.0, similarity)
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Basic image similarity calculation failed: {e}")
            return 0.0

    def _calculate_basic_audio_similarity(self, audio_1: Any, audio_2: Any) -> float:
        """Calculate basic audio similarity."""
        try:
            # Simple hash-based comparison for audio
            hash_1 = self._calculate_audio_hash(audio_1)
            hash_2 = self._calculate_audio_hash(audio_2)

            if hash_1 and hash_2:
                # Hamming distance
                distance = sum(c1 != c2 for c1, c2 in zip(hash_1, hash_2))
                max_distance = len(hash_1)
                similarity = 1.0 - (distance / max_distance)
                return max(0.0, similarity)
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Basic audio similarity calculation failed: {e}")
            return 0.0

    def _calculate_image_hash(self, image_data: Any) -> Optional[str]:
        """Calculate simple hash for image data."""
        try:
            if isinstance(image_data, (bytes, str)):
                return hashlib.md5(str(image_data).encode()).hexdigest()
            else:
                return None
        except Exception:
            return None

    def _calculate_audio_hash(self, audio_data: Any) -> Optional[str]:
        """Calculate simple hash for audio data."""
        try:
            if isinstance(audio_data, (bytes, str)):
                return hashlib.md5(str(audio_data).encode()).hexdigest()
            else:
                return None
        except Exception:
            return None

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

        return " ".join(text_parts).strip()

    def _identify_modalities(self, content_data: Dict[str, Any]) -> List[str]:
        """Identify available content modalities."""
        modalities = []
        if 'text' in content_data and content_data['text']:
            modalities.append('text')
        if 'image' in content_data and content_data['image']:
            modalities.append('image')
        if 'audio' in content_data and content_data['audio']:
            modalities.append('audio')
        return modalities

    def _generate_content_signature(self, content_data: Dict[str, Any]) -> str:
        """Generate a content signature for initial filtering."""
        try:
            content_text = self._extract_content_text(content_data)
            return hashlib.md5(content_text.encode()).hexdigest()
        except Exception:
            return "unknown"

    async def batch_duplicate_detection(
        self,
        content_batch: List[Dict[str, Any]],
        similarity_threshold: float = None,
        **kwargs
    ) -> List[DuplicateDetectionResult]:
        """
        Perform duplicate detection on a batch of content items.

        Args:
            content_batch: List of content data dictionaries
            similarity_threshold: Threshold for duplicate detection
            **kwargs: Additional detection options

        Returns:
            List of DuplicateDetectionResult objects
        """
        try:
            # Create all-vs-all comparison matrix
            detection_tasks = []

            for i, content_1 in enumerate(content_batch):
                # Compare with all subsequent items to avoid duplicates
                comparison_content = content_batch[i+1:]
                if comparison_content:
                    task = self.detect_duplicates(
                        content_1,
                        comparison_content=comparison_content,
                        similarity_threshold=similarity_threshold,
                        **kwargs
                    )
                    detection_tasks.append(task)

            # Execute detection tasks
            detection_results = await asyncio.gather(*detection_tasks, return_exceptions=True)

            # Process results
            results = []
            for i, result in enumerate(detection_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch detection failed for item {i}: {result}")
                    # Create error result
                    error_result = DuplicateDetectionResult(
                        content_id=content_batch[i].get('content_id', f'batch_item_{i}'),
                        metadata={"error": str(result)}
                    )
                    results.append(error_result)
                else:
                    results.append(result)

            # Add remaining items that weren't compared
            for i in range(len(detection_results), len(content_batch)):
                result = DuplicateDetectionResult(
                    content_id=content_batch[i].get('content_id', f'batch_item_{i}'),
                    duplicate_candidates=[],
                    is_duplicate=False
                )
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Batch duplicate detection failed: {e}")
            return []

    def get_similarity_thresholds(self) -> Dict[str, float]:
        """Get the similarity thresholds for different duplicate levels."""
        return self.similarity_thresholds.copy()

    def get_supported_modalities(self) -> List[str]:
        """Get list of supported modalities for duplicate detection."""
        return self.supported_modalities.copy()

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the duplicate detection service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "duplicate_detection",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "similarity_thresholds": self.get_similarity_thresholds(),
                "supported_modalities": self.get_supported_modalities(),
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "duplicate_detection",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
duplicate_detection_service = DuplicateDetectionService()