"""
Quality Enhancement Service for AI-powered content improvement.

This service provides content quality enhancement capabilities including:
- Text quality improvement and correction
- Image enhancement suggestions
- Audio quality assessment and recommendations
- Multi-modal content optimization
- Automatic error detection and correction
- Content refinement and polishing
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.services.ollama_client import ollama_client
from app.services.vision_ai_service import vision_ai_service
from app.services.audio_ai_service import audio_ai_service
from app.utils.logging import get_logger

logger = get_logger("quality_enhancement_service")


class QualityEnhancementError(Exception):
    """Raised when quality enhancement fails."""
    pass


class EnhancementResult:
    """Result of quality enhancement processing."""

    def __init__(
        self,
        content_id: str,
        original_quality_score: float = None,
        enhanced_quality_score: float = None,
        improvements_made: List[Dict[str, Any]] = None,
        enhanced_content: Dict[str, Any] = None,
        recommendations: List[str] = None,
        processing_time_ms: float = None,
        model_used: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.original_quality_score = original_quality_score
        self.enhanced_quality_score = enhanced_quality_score
        self.improvements_made = improvements_made or []
        self.enhanced_content = enhanced_content or {}
        self.recommendations = recommendations or []
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "original_quality_score": self.original_quality_score,
            "enhanced_quality_score": self.enhanced_quality_score,
            "improvements_made": self.improvements_made,
            "enhanced_content": self.enhanced_content,
            "recommendations": self.recommendations,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class QualityEnhancementService:
    """Service for AI-powered content quality enhancement."""

    def __init__(self):
        self.default_model = getattr(settings, 'quality_enhancement_default_model', 'llama2:13b')
        self.vision_model = getattr(settings, 'quality_enhancement_vision_model', 'llava:13b')
        self.audio_model = getattr(settings, 'quality_enhancement_audio_model', 'whisper-base')
        self.processing_timeout = getattr(settings, 'quality_enhancement_timeout_seconds', 120)

    async def enhance_content_quality(
        self,
        content_data: Dict[str, Any],
        enhancement_types: List[str] = None,
        **kwargs
    ) -> EnhancementResult:
        """
        Enhance the quality of content using AI.

        Args:
            content_data: Content data dictionary with modalities
            enhancement_types: Types of enhancements to apply
            **kwargs: Additional enhancement options

        Returns:
            EnhancementResult with improvements and enhanced content
        """
        start_time = datetime.now()
        content_id = content_data.get('content_id', 'unknown')

        try:
            # Determine available modalities and enhancement types
            modalities = self._identify_modalities(content_data)
            enhancement_types = enhancement_types or self._determine_enhancement_types(modalities)

            # Assess original quality
            original_quality = await self._assess_overall_quality(content_data, modalities)

            # Apply enhancements
            result = EnhancementResult(
                content_id=content_id,
                original_quality_score=original_quality
            )

            enhanced_content = {}
            improvements_made = []

            # Apply enhancements by type
            if 'text' in enhancement_types and 'text' in modalities:
                text_enhancement = await self._enhance_text_quality(
                    content_data['text'],
                    **kwargs
                )
                enhanced_content['text'] = text_enhancement['enhanced_text']
                improvements_made.extend(text_enhancement['improvements'])

            if 'image' in enhancement_types and 'image' in modalities:
                image_enhancement = await self._enhance_image_quality(
                    content_data['image'],
                    **kwargs
                )
                enhanced_content['image'] = image_enhancement['enhanced_description']
                improvements_made.extend(image_enhancement['improvements'])

            if 'audio' in enhancement_types and 'audio' in modalities:
                audio_enhancement = await self._enhance_audio_quality(
                    content_data['audio'],
                    **kwargs
                )
                enhanced_content['audio'] = audio_enhancement['enhanced_transcription']
                improvements_made.extend(audio_enhancement['improvements'])

            if 'multi_modal' in enhancement_types and len(modalities) > 1:
                multi_modal_enhancement = await self._enhance_multi_modal_quality(
                    content_data,
                    modalities,
                    **kwargs
                )
                enhanced_content.update(multi_modal_enhancement['enhanced_content'])
                improvements_made.extend(multi_modal_enhancement['improvements'])

            # Assess enhanced quality
            enhanced_quality = await self._assess_overall_quality(
                {**content_data, **enhanced_content},
                modalities
            )

            # Generate recommendations
            recommendations = await self._generate_recommendations(
                original_quality,
                enhanced_quality,
                improvements_made,
                **kwargs
            )

            # Update result
            result.enhanced_quality_score = enhanced_quality
            result.improvements_made = improvements_made
            result.enhanced_content = enhanced_content
            result.recommendations = recommendations
            result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.model_used = self.default_model

            logger.info(f"Quality enhancement completed for content {content_id} in {result.processing_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Quality enhancement failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise QualityEnhancementError(f"Quality enhancement failed: {str(e)}")

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

    def _determine_enhancement_types(self, modalities: List[str]) -> List[str]:
        """Determine appropriate enhancement types based on modalities."""
        enhancement_types = []

        if 'text' in modalities:
            enhancement_types.append('text')
        if 'image' in modalities:
            enhancement_types.append('image')
        if 'audio' in modalities:
            enhancement_types.append('audio')
        if len(modalities) > 1:
            enhancement_types.append('multi_modal')

        return enhancement_types

    async def _assess_overall_quality(
        self,
        content_data: Dict[str, Any],
        modalities: List[str]
    ) -> float:
        """Assess the overall quality of content across modalities."""
        try:
            quality_scores = []

            # Assess text quality
            if 'text' in content_data and 'text' in modalities:
                text_quality = await self._assess_text_quality(content_data['text'])
                quality_scores.append(text_quality)

            # Assess image quality
            if 'image' in content_data and 'image' in modalities:
                image_quality = await vision_ai_service.process_image(
                    content_data['image'],
                    operations=['quality']
                )
                quality_scores.append(image_quality.quality_score or 0.5)

            # Assess audio quality
            if 'audio' in content_data and 'audio' in modalities:
                audio_quality = await audio_ai_service.process_audio(
                    content_data['audio'],
                    operations=['quality']
                )
                quality_scores.append(audio_quality.quality_score or 0.5)

            # Calculate weighted average
            if quality_scores:
                return sum(quality_scores) / len(quality_scores)
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 0.5

    async def _assess_text_quality(self, text: str) -> float:
        """Assess the quality of text content."""
        try:
            prompt = f"""
Assess the quality of this text on a scale of 0.0 to 1.0, where 1.0 is excellent quality and 0.0 is very poor. Consider:

1. Grammar and spelling accuracy
2. Clarity and coherence
3. Completeness and comprehensiveness
4. Professional tone and style
5. Factual accuracy (if applicable)
6. Readability and structure

Text to assess:
{text[:1000]}...

Provide only the numerical score (0.0 to 1.0).
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=prompt,
                system="You are an expert at text quality assessment. Always respond with only a numerical score.",
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
                score = float(score_match.group(1))
                return max(0.0, min(1.0, score))
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Text quality assessment failed: {e}")
            return 0.5

    async def _enhance_text_quality(self, text: str, **kwargs) -> Dict[str, Any]:
        """Enhance text quality through AI-powered improvements."""
        try:
            enhancement_prompt = f"""
Improve the quality of this text by:

1. Correcting grammar and spelling errors
2. Improving clarity and coherence
3. Enhancing readability and structure
4. Making the language more professional and engaging
5. Ensuring factual accuracy and completeness

Original text:
{text}

Provide the enhanced version and list the specific improvements made.
Format as JSON with 'enhanced_text' and 'improvements' (array of improvement descriptions).
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=enhancement_prompt,
                system="You are an expert at text enhancement and editing. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 800)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                enhancement = json.loads(result_text)
                return {
                    "enhanced_text": enhancement.get('enhanced_text', text),
                    "improvements": enhancement.get('improvements', [])
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse text enhancement JSON: {result_text}")
                return {
                    "enhanced_text": text,
                    "improvements": ["Enhancement failed to parse"]
                }

        except Exception as e:
            logger.error(f"Text enhancement failed: {e}")
            return {
                "enhanced_text": text,
                "improvements": [f"Enhancement failed: {str(e)}"]
            }

    async def _enhance_image_quality(self, image_data: Any, **kwargs) -> Dict[str, Any]:
        """Enhance image quality through improved descriptions and analysis."""
        try:
            # Get current image analysis
            vision_result = await vision_ai_service.process_image(
                image_data,
                operations=['caption', 'objects', 'scene', 'quality']
            )

            enhancement_prompt = f"""
Based on this image analysis, provide enhanced descriptions and quality improvement suggestions:

Current Analysis:
- Caption: {vision_result.caption}
- Objects: {json.dumps(vision_result.objects_detected[:5])}
- Scene: {json.dumps(vision_result.scene_analysis)}
- Quality Score: {vision_result.quality_score}

Provide:
1. An enhanced, more detailed caption
2. Quality improvement suggestions
3. Composition and lighting recommendations

Format as JSON with 'enhanced_description', 'improvements', and 'recommendations'.
"""

            response = await ollama_client.generate(
                model=self.vision_model,
                prompt=f"[IMAGE_DATA:{await vision_ai_service._prepare_image_data(image_data)}]\n{enhancement_prompt}",
                system="You are an expert at image analysis and enhancement. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 600)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                enhancement = json.loads(result_text)
                return {
                    "enhanced_description": enhancement.get('enhanced_description', vision_result.caption),
                    "improvements": enhancement.get('improvements', []),
                    "recommendations": enhancement.get('recommendations', [])
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse image enhancement JSON: {result_text}")
                return {
                    "enhanced_description": vision_result.caption,
                    "improvements": ["Enhancement analysis failed"],
                    "recommendations": []
                }

        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return {
                "enhanced_description": "Image enhancement failed",
                "improvements": [f"Enhancement failed: {str(e)}"],
                "recommendations": []
            }

    async def _enhance_audio_quality(self, audio_data: Any, **kwargs) -> Dict[str, Any]:
        """Enhance audio quality through improved transcription and analysis."""
        try:
            # Get current audio analysis
            audio_result = await audio_ai_service.process_audio(
                audio_data,
                operations=['transcription', 'classification', 'quality']
            )

            enhancement_prompt = f"""
Based on this audio analysis, provide enhanced transcription and quality improvement suggestions:

Current Analysis:
- Transcription: {audio_result.transcription[:500]}...
- Classification: {json.dumps(audio_result.classification)}
- Quality Score: {audio_result.quality_score}

Provide:
1. An enhanced, corrected transcription with proper punctuation
2. Quality improvement suggestions
3. Audio processing recommendations

Format as JSON with 'enhanced_transcription', 'improvements', and 'recommendations'.
"""

            response = await ollama_client.generate(
                model=self.audio_model,
                prompt=f"[AUDIO_DATA:{await audio_ai_service._prepare_audio_data(audio_data)}]\n{enhancement_prompt}",
                system="You are an expert at audio enhancement and transcription. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 600)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                enhancement = json.loads(result_text)
                return {
                    "enhanced_transcription": enhancement.get('enhanced_transcription', audio_result.transcription),
                    "improvements": enhancement.get('improvements', []),
                    "recommendations": enhancement.get('recommendations', [])
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse audio enhancement JSON: {result_text}")
                return {
                    "enhanced_transcription": audio_result.transcription,
                    "improvements": ["Enhancement analysis failed"],
                    "recommendations": []
                }

        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            return {
                "enhanced_transcription": "Audio enhancement failed",
                "improvements": [f"Enhancement failed: {str(e)}"],
                "recommendations": []
            }

    async def _enhance_multi_modal_quality(
        self,
        content_data: Dict[str, Any],
        modalities: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Enhance multi-modal content quality."""
        try:
            enhancement_prompt = f"""
Analyze this multi-modal content and provide quality enhancement suggestions:

Modalities present: {', '.join(modalities)}

Content Overview:
"""

            if 'text' in content_data:
                enhancement_prompt += f"- Text: {content_data['text'][:300]}...\n"
            if 'image' in content_data:
                enhancement_prompt += "- Image: [Present]\n"
            if 'audio' in content_data:
                enhancement_prompt += "- Audio: [Present]\n"

            enhancement_prompt += """
Provide:
1. Cross-modal consistency improvements
2. Integration suggestions between modalities
3. Overall quality enhancement recommendations

Format as JSON with 'enhanced_content' (object with modality keys) and 'improvements' (array).
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=enhancement_prompt,
                system="You are an expert at multi-modal content enhancement. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 600)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                enhancement = json.loads(result_text)
                return {
                    "enhanced_content": enhancement.get('enhanced_content', {}),
                    "improvements": enhancement.get('improvements', [])
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse multi-modal enhancement JSON: {result_text}")
                return {
                    "enhanced_content": {},
                    "improvements": ["Multi-modal enhancement analysis failed"]
                }

        except Exception as e:
            logger.error(f"Multi-modal enhancement failed: {e}")
            return {
                "enhanced_content": {},
                "improvements": [f"Multi-modal enhancement failed: {str(e)}"]
            }

    async def _generate_recommendations(
        self,
        original_quality: float,
        enhanced_quality: float,
        improvements_made: List[Dict[str, Any]],
        **kwargs
    ) -> List[str]:
        """Generate recommendations for further quality improvements."""
        try:
            quality_improvement = enhanced_quality - original_quality

            recommendations_prompt = f"""
Based on the quality enhancement results:

Original Quality Score: {original_quality:.2f}
Enhanced Quality Score: {enhanced_quality:.2f}
Quality Improvement: {quality_improvement:.2f}
Improvements Made: {json.dumps(improvements_made[:5])}

Provide 3-5 specific recommendations for further quality improvements.
Focus on actionable suggestions that could yield additional quality gains.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=recommendations_prompt,
                system="You are an expert at content quality optimization. Provide actionable recommendations.",
                options={
                    "temperature": kwargs.get('temperature', 0.4),
                    "num_predict": kwargs.get('max_tokens', 300)
                }
            )

            recommendations_text = response.get('response', '').strip()

            # Split into individual recommendations
            recommendations = []
            for line in recommendations_text.split('\n'):
                line = line.strip()
                if line and len(line) > 10:  # Filter out short/empty lines
                    # Remove numbering if present
                    line = line.lstrip('1234567890.- ')
                    if line:
                        recommendations.append(line)

            return recommendations[:5]  # Limit to 5 recommendations

        except Exception as e:
            logger.error(f"Recommendations generation failed: {e}")
            return ["Consider professional editing for further quality improvements"]

    async def batch_enhance_quality(
        self,
        content_batch: List[Dict[str, Any]],
        enhancement_types: List[str] = None,
        max_concurrent: int = 2
    ) -> List[EnhancementResult]:
        """
        Enhance quality for multiple content items in batch.

        Args:
            content_batch: List of content data dictionaries
            enhancement_types: Types of enhancements to apply
            max_concurrent: Maximum concurrent enhancement tasks

        Returns:
            List of EnhancementResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enhance_single_item(content_data: Dict[str, Any]) -> EnhancementResult:
            async with semaphore:
                return await self.enhance_content_quality(
                    content_data,
                    enhancement_types=enhancement_types
                )

        tasks = [enhance_single_item(item) for item in content_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch enhancement failed for item {i}: {result}")
                # Create error result
                error_result = EnhancementResult(
                    content_id=content_batch[i].get('content_id', f'batch_item_{i}'),
                    metadata={"error": str(result)}
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    def get_supported_enhancement_types(self) -> List[str]:
        """Get list of supported enhancement types."""
        return ['text', 'image', 'audio', 'multi_modal']

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the quality enhancement service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "quality_enhancement",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "supported_enhancement_types": self.get_supported_enhancement_types(),
                "default_models": {
                    "text": self.default_model,
                    "vision": self.vision_model,
                    "audio": self.audio_model
                }
            }

        except Exception as e:
            return {
                "service": "quality_enhancement",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
quality_enhancement_service = QualityEnhancementService()