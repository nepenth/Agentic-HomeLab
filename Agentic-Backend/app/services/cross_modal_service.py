"""
Cross-Modal Processing Service for correlating text, images, and audio.

This service provides cross-modal AI capabilities including:
- Text-image alignment and correlation
- Audio-visual correlation
- Multi-modal content understanding
- Cross-modal search and retrieval
- Content consistency validation
- Multi-modal summarization
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.services.ollama_client import ollama_client
from app.services.vision_ai_service import vision_ai_service, VisionAIResult
from app.services.audio_ai_service import audio_ai_service, AudioAIResult
from app.utils.logging import get_logger

logger = get_logger("cross_modal_service")


class CrossModalError(Exception):
    """Raised when cross-modal processing fails."""
    pass


class CrossModalResult:
    """Result of cross-modal processing."""

    def __init__(
        self,
        content_id: str,
        text_image_alignment: Dict[str, Any] = None,
        audio_visual_correlation: Dict[str, Any] = None,
        multi_modal_summary: str = None,
        consistency_score: float = None,
        cross_modal_search_results: List[Dict[str, Any]] = None,
        processing_time_ms: float = None,
        models_used: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.text_image_alignment = text_image_alignment or {}
        self.audio_visual_correlation = audio_visual_correlation or {}
        self.multi_modal_summary = multi_modal_summary
        self.consistency_score = consistency_score
        self.cross_modal_search_results = cross_modal_search_results or []
        self.processing_time_ms = processing_time_ms
        self.models_used = models_used or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "text_image_alignment": self.text_image_alignment,
            "audio_visual_correlation": self.audio_visual_correlation,
            "multi_modal_summary": self.multi_modal_summary,
            "consistency_score": self.consistency_score,
            "cross_modal_search_results": self.cross_modal_search_results,
            "processing_time_ms": self.processing_time_ms,
            "models_used": self.models_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class CrossModalService:
    """Service for cross-modal AI processing."""

    def __init__(self):
        self.default_text_model = getattr(settings, 'cross_modal_default_text_model', 'llama2:13b')
        self.default_vision_model = getattr(settings, 'cross_modal_default_vision_model', 'llava:13b')
        self.default_audio_model = getattr(settings, 'cross_modal_default_audio_model', 'whisper-base')
        self.processing_timeout = getattr(settings, 'cross_modal_processing_timeout_seconds', 180)

    async def process_multi_modal_content(
        self,
        content_data: Dict[str, Any],
        operations: List[str] = None,
        **kwargs
    ) -> CrossModalResult:
        """
        Process multi-modal content (text, image, audio combinations).

        Args:
            content_data: Dictionary containing different content modalities
                {
                    'text': str,
                    'image': bytes|str|Path,
                    'audio': bytes|str|Path,
                    'content_id': str
                }
            operations: List of operations to perform
            **kwargs: Additional processing options

        Returns:
            CrossModalResult with cross-modal analysis
        """
        start_time = datetime.now()
        content_id = content_data.get('content_id', 'unknown')

        try:
            # Determine available modalities
            modalities = {}
            if 'text' in content_data and content_data['text']:
                modalities['text'] = content_data['text']
            if 'image' in content_data and content_data['image']:
                modalities['image'] = content_data['image']
            if 'audio' in content_data and content_data['audio']:
                modalities['audio'] = content_data['audio']

            if len(modalities) < 2:
                raise CrossModalError("Cross-modal processing requires at least 2 modalities")

            # Determine operations to perform
            operations = operations or ['alignment', 'correlation', 'summary']

            # Process modalities
            processing_results = await self._process_modalities(modalities, **kwargs)

            # Perform cross-modal operations
            result = CrossModalResult(content_id=content_id)

            if 'alignment' in operations and 'text' in modalities and 'image' in modalities:
                result.text_image_alignment = await self._align_text_image(
                    processing_results.get('text', {}),
                    processing_results.get('vision', {}),
                    **kwargs
                )

            if 'correlation' in operations and 'audio' in modalities and 'image' in modalities:
                result.audio_visual_correlation = await self._correlate_audio_visual(
                    processing_results.get('audio', {}),
                    processing_results.get('vision', {}),
                    **kwargs
                )

            if 'summary' in operations:
                result.multi_modal_summary = await self._generate_multi_modal_summary(
                    processing_results,
                    **kwargs
                )

            if 'consistency' in operations:
                result.consistency_score = await self._assess_consistency(
                    processing_results,
                    **kwargs
                )

            # Collect models used
            result.models_used = [
                processing_results.get('text', {}).get('model_used'),
                processing_results.get('vision', {}).get('model_used'),
                processing_results.get('audio', {}).get('model_used')
            ]
            result.models_used = [m for m in result.models_used if m]

            # Calculate processing time
            result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"Cross-modal processing completed for content {content_id} in {result.processing_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Cross-modal processing failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise CrossModalError(f"Cross-modal processing failed: {str(e)}")

    async def _process_modalities(
        self,
        modalities: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Process individual modalities in parallel."""
        tasks = {}

        if 'text' in modalities:
            tasks['text'] = self._process_text_modality(modalities['text'], **kwargs)

        if 'image' in modalities:
            tasks['vision'] = self._process_vision_modality(modalities['image'], **kwargs)

        if 'audio' in modalities:
            tasks['audio'] = self._process_audio_modality(modalities['audio'], **kwargs)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Organize results
        processing_results = {}
        for i, (modality, task) in enumerate(tasks.items()):
            if isinstance(results[i], Exception):
                logger.error(f"Failed to process {modality} modality: {results[i]}")
                processing_results[modality] = {"error": str(results[i])}
            else:
                processing_results[modality] = results[i]

        return processing_results

    async def _process_text_modality(self, text: str, **kwargs) -> Dict[str, Any]:
        """Process text modality."""
        try:
            # Use Ollama for text analysis
            response = await ollama_client.generate(
                model=self.default_text_model,
                prompt=f"Analyze this text for key information, themes, and sentiment: {text[:1000]}...",
                system="You are an expert at text analysis. Provide structured analysis.",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 300)
                }
            )

            return {
                "content": text,
                "analysis": response.get('response', ''),
                "model_used": self.default_text_model,
                "word_count": len(text.split()),
                "language": "en"  # Placeholder
            }

        except Exception as e:
            logger.error(f"Text modality processing failed: {e}")
            return {"error": str(e)}

    async def _process_vision_modality(self, image_data: Any, **kwargs) -> Dict[str, Any]:
        """Process vision modality."""
        try:
            # Use vision AI service
            result = await vision_ai_service.process_image(
                image_data=image_data,
                operations=['caption', 'objects', 'scene'],
                model=self.default_vision_model,
                **kwargs
            )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Vision modality processing failed: {e}")
            return {"error": str(e)}

    async def _process_audio_modality(self, audio_data: Any, **kwargs) -> Dict[str, Any]:
        """Process audio modality."""
        try:
            # Use audio AI service
            result = await audio_ai_service.process_audio(
                audio_data=audio_data,
                operations=['transcription', 'classification'],
                model=self.default_audio_model,
                **kwargs
            )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Audio modality processing failed: {e}")
            return {"error": str(e)}

    async def _align_text_image(
        self,
        text_result: Dict[str, Any],
        vision_result: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Align text and image content."""
        prompt = kwargs.get('alignment_prompt',
            "Compare and align the text content with the image description. Determine if they are consistent, what they have in common, and any discrepancies. Provide a structured analysis.")

        try:
            text_content = text_result.get('content', '')
            image_caption = vision_result.get('caption', '')
            image_objects = vision_result.get('objects_detected', [])

            alignment_prompt = f"""
Text Content: {text_content[:500]}...
Image Caption: {image_caption}
Detected Objects: {json.dumps(image_objects[:5])}

{prompt}
Format as JSON with: consistency_score (0-1), alignment_analysis, common_elements, discrepancies.
"""

            response = await ollama_client.generate(
                model=self.default_text_model,
                prompt=alignment_prompt,
                system="You are an expert at cross-modal analysis. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 400)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                alignment = json.loads(result_text)
                return alignment
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse alignment JSON: {result_text}")
                return {
                    "consistency_score": 0.5,
                    "alignment_analysis": "Analysis failed to parse",
                    "raw_response": result_text
                }

        except Exception as e:
            logger.error(f"Text-image alignment failed: {e}")
            return {"error": str(e)}

    async def _correlate_audio_visual(
        self,
        audio_result: Dict[str, Any],
        vision_result: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Correlate audio and visual content."""
        prompt = kwargs.get('correlation_prompt',
            "Compare the audio transcription with the image content. Determine if they are related, what they have in common, and how they complement each other. Provide a structured analysis.")

        try:
            transcription = audio_result.get('transcription', '')
            image_caption = vision_result.get('caption', '')
            scene_analysis = vision_result.get('scene_analysis', {})

            correlation_prompt = f"""
Audio Transcription: {transcription[:500]}...
Image Caption: {image_caption}
Scene Analysis: {json.dumps(scene_analysis)}

{prompt}
Format as JSON with: correlation_score (0-1), relationship_analysis, complementary_elements, conflicts.
"""

            response = await ollama_client.generate(
                model=self.default_text_model,
                prompt=correlation_prompt,
                system="You are an expert at audio-visual correlation. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 400)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                correlation = json.loads(result_text)
                return correlation
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse correlation JSON: {result_text}")
                return {
                    "correlation_score": 0.5,
                    "relationship_analysis": "Analysis failed to parse",
                    "raw_response": result_text
                }

        except Exception as e:
            logger.error(f"Audio-visual correlation failed: {e}")
            return {"error": str(e)}

    async def _generate_multi_modal_summary(
        self,
        processing_results: Dict[str, Any],
        **kwargs
    ) -> str:
        """Generate a comprehensive multi-modal summary."""
        prompt = kwargs.get('summary_prompt',
            "Create a comprehensive summary that integrates information from all available modalities (text, image, audio). Provide a cohesive understanding of the content.")

        try:
            # Build context from all modalities
            context_parts = []

            if 'text' in processing_results:
                text_info = processing_results['text']
                context_parts.append(f"Text Content: {text_info.get('content', '')[:300]}...")

            if 'vision' in processing_results:
                vision_info = processing_results['vision']
                context_parts.append(f"Visual Content: {vision_info.get('caption', '')}")
                if vision_info.get('objects_detected'):
                    context_parts.append(f"Visual Objects: {json.dumps(vision_info['objects_detected'][:3])}")

            if 'audio' in processing_results:
                audio_info = processing_results['audio']
                context_parts.append(f"Audio Content: {audio_info.get('transcription', '')[:300]}...")

            summary_prompt = f"""
{chr(10).join(context_parts)}

{prompt}
Provide a well-structured, comprehensive summary that integrates all modalities.
"""

            response = await ollama_client.generate(
                model=self.default_text_model,
                prompt=summary_prompt,
                system="You are an expert at multi-modal content synthesis. Provide comprehensive, well-structured summaries.",
                options={
                    "temperature": kwargs.get('temperature', 0.4),
                    "num_predict": kwargs.get('max_tokens', 500)
                }
            )

            return response.get('response', '').strip()

        except Exception as e:
            logger.error(f"Multi-modal summary generation failed: {e}")
            return "Summary generation failed due to processing error."

    async def _assess_consistency(
        self,
        processing_results: Dict[str, Any],
        **kwargs
    ) -> float:
        """Assess consistency across modalities."""
        prompt = kwargs.get('consistency_prompt',
            "Evaluate the consistency between different modalities. Rate how well they align and complement each other on a scale of 0.0 to 1.0, where 1.0 means perfect consistency.")

        try:
            # Build consistency evaluation context
            context_parts = []

            if 'text' in processing_results and 'vision' in processing_results:
                text_caption = processing_results['text'].get('content', '')[:200]
                vision_caption = processing_results['vision'].get('caption', '')
                context_parts.append(f"Text-Image: '{text_caption}' vs '{vision_caption}'")

            if 'audio' in processing_results and 'vision' in processing_results:
                audio_transcript = processing_results['audio'].get('transcription', '')[:200]
                vision_caption = processing_results['vision'].get('caption', '')
                context_parts.append(f"Audio-Visual: '{audio_transcript}' vs '{vision_caption}'")

            consistency_prompt = f"""
Evaluate consistency across modalities:
{chr(10).join(context_parts)}

{prompt}
Provide only the numerical consistency score (0.0 to 1.0).
"""

            response = await ollama_client.generate(
                model=self.default_text_model,
                prompt=consistency_prompt,
                system="You are an expert at evaluating cross-modal consistency. Always respond with only a numerical score.",
                options={
                    "temperature": kwargs.get('temperature', 0.1),
                    "num_predict": kwargs.get('max_tokens', 50)
                }
            )

            result_text = response.get('response', '').strip()

            # Extract numerical score
            import re
            score_match = re.search(r'(\d+\.?\d*)', result_text)
            if score_match:
                score = float(score_match.group(1))
                return max(0.0, min(1.0, score))  # Clamp to 0.0-1.0 range
            else:
                logger.warning(f"Could not extract consistency score from: {result_text}")
                return 0.5  # Default neutral score

        except Exception as e:
            logger.error(f"Consistency assessment failed: {e}")
            return 0.5

    async def search_cross_modal(
        self,
        query: str,
        content_items: List[Dict[str, Any]],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Perform cross-modal search across content items.

        Args:
            query: Search query
            content_items: List of content items with their processing results
            **kwargs: Search options

        Returns:
            List of search results with relevance scores
        """
        try:
            search_results = []

            for item in content_items:
                relevance_score = await self._calculate_relevance(query, item, **kwargs)
                if relevance_score > kwargs.get('threshold', 0.1):
                    search_results.append({
                        "content_id": item.get('content_id'),
                        "relevance_score": relevance_score,
                        "matched_modalities": item.get('matched_modalities', []),
                        "excerpts": item.get('excerpts', [])
                    })

            # Sort by relevance
            search_results.sort(key=lambda x: x['relevance_score'], reverse=True)

            return search_results[:kwargs.get('max_results', 10)]

        except Exception as e:
            logger.error(f"Cross-modal search failed: {e}")
            return []

    async def _calculate_relevance(
        self,
        query: str,
        content_item: Dict[str, Any],
        **kwargs
    ) -> float:
        """Calculate relevance score for a content item against a query."""
        try:
            # Build content context
            context_parts = []

            if 'text' in content_item:
                context_parts.append(f"Text: {content_item['text'][:300]}...")
            if 'caption' in content_item:
                context_parts.append(f"Visual: {content_item['caption']}")
            if 'transcription' in content_item:
                context_parts.append(f"Audio: {content_item['transcription'][:300]}...")

            relevance_prompt = f"""
Query: {query}

Content:
{chr(10).join(context_parts)}

Rate how relevant this content is to the query on a scale of 0.0 to 1.0.
Consider semantic meaning, keywords, and cross-modal relationships.
Provide only the numerical score.
"""

            response = await ollama_client.generate(
                model=self.default_text_model,
                prompt=relevance_prompt,
                system="You are an expert at relevance assessment. Always respond with only a numerical score.",
                options={
                    "temperature": kwargs.get('temperature', 0.1),
                    "num_predict": kwargs.get('max_tokens', 50)
                }
            )

            result_text = response.get('response', '').strip()

            # Extract numerical score
            import re
            score_match = re.search(r'(\d+\.?\d*)', result_text)
            if score_match:
                return float(score_match.group(1))
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Relevance calculation failed: {e}")
            return 0.0

    def get_supported_operations(self) -> List[str]:
        """Get list of supported cross-modal operations."""
        return ['alignment', 'correlation', 'summary', 'consistency', 'search']

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the cross-modal service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "cross_modal",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "supported_operations": self.get_supported_operations(),
                "default_models": {
                    "text": self.default_text_model,
                    "vision": self.default_vision_model,
                    "audio": self.default_audio_model
                }
            }

        except Exception as e:
            return {
                "service": "cross_modal",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
cross_modal_service = CrossModalService()