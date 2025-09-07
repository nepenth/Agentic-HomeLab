"""
Content Processing Pipeline.

This module provides a comprehensive content processing system that can handle:
- Text processing (summarization, entity extraction, sentiment analysis)
- Image processing (OCR, object detection, scene understanding)
- Audio processing (transcription, speaker identification, emotion detection)
- Structured data processing (schema validation, transformation, enrichment)
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass
import hashlib

from app.connectors.base import ContentData, ContentType, ValidationResult, ValidationStatus
from app.services.model_selection_service import model_selector
from app.services.semantic_processing import embedding_service
from app.utils.logging import get_logger

logger = get_logger("content_pipeline")


@dataclass
class ProcessingResult:
    """Result of content processing."""
    content_data: ContentData
    processed_content: Dict[str, Any]
    processing_steps: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_time_ms: float
    success: bool
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ProcessingStep:
    """Configuration for a processing step."""
    name: str
    processor_type: str
    config: Dict[str, Any]
    depends_on: List[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class ContentProcessor:
    """Base class for content processors."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(f"processor_{self.__class__.__name__}")

    async def process(self, content_data: ContentData, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process content data."""
        raise NotImplementedError("Subclasses must implement process method")

    def get_supported_content_types(self) -> List[ContentType]:
        """Get supported content types."""
        return []

    def get_capabilities(self) -> Dict[str, Any]:
        """Get processor capabilities."""
        return {
            "supported_content_types": [ct.value for ct in self.get_supported_content_types()],
            "processing_operations": [],
            "requires_model": False,
            "batch_processing": False
        }


class TextProcessor(ContentProcessor):
    """Processor for text content."""

    def get_supported_content_types(self) -> List[ContentType]:
        return [ContentType.TEXT]

    async def process(self, content_data: ContentData, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process text content."""
        text_content = content_data.text_content or ""

        if not text_content.strip():
            return {"error": "No text content to process"}

        operations = self.config.get("operations", ["summarize"])

        results = {}

        for operation in operations:
            try:
                if operation == "summarize":
                    results["summary"] = await self._summarize_text(text_content)
                elif operation == "extract_entities":
                    results["entities"] = await self._extract_entities(text_content)
                elif operation == "sentiment_analysis":
                    results["sentiment"] = await self._analyze_sentiment(text_content)
                elif operation == "keyword_extraction":
                    results["keywords"] = await self._extract_keywords(text_content)
                elif operation == "language_detection":
                    results["language"] = await self._detect_language(text_content)
                elif operation == "readability_score":
                    results["readability"] = await self._calculate_readability(text_content)
            except Exception as e:
                self.logger.error(f"Failed to process text operation {operation}: {e}")
                results[operation] = {"error": str(e)}

        return results

    async def _summarize_text(self, text: str) -> Dict[str, Any]:
        """Summarize text content."""
        # Use LLM for summarization
        if model_selector:
            model = await model_selector.select_model_for_task("text_summarization")
            if model:
                # This would integrate with the LLM service
                summary_prompt = f"Please provide a concise summary of the following text:\n\n{text[:2000]}..."
                # summary = await llm_service.generate(summary_prompt, model=model)
                summary = f"Summary of {len(text)} characters of text"  # Placeholder
                return {
                    "summary": summary,
                    "original_length": len(text),
                    "compression_ratio": len(summary) / len(text) if text else 0
                }

        # Fallback: simple extractive summarization
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Simple scoring based on sentence length and position
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = len(sentence.split())  # Length score
            score += (len(sentences) - i) * 0.1  # Position score (prefer earlier sentences)
            scored_sentences.append((score, sentence))

        # Select top sentences
        top_sentences = sorted(scored_sentences, reverse=True)[:3]
        summary = ". ".join([s[1] for s in sorted(top_sentences, key=lambda x: sentences.index(x[1]))])

        return {
            "summary": summary,
            "method": "extractive",
            "sentences_used": len(top_sentences)
        }

    async def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        # Simple rule-based entity extraction
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "emails": [],
            "urls": []
        }

        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["emails"] = re.findall(email_pattern, text)

        # Extract URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        entities["urls"] = re.findall(url_pattern, text)

        # Extract dates (simple pattern)
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        entities["dates"] = re.findall(date_pattern, text)

        return entities

    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        # Simple rule-based sentiment analysis
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "like", "best"]
        negative_words = ["bad", "terrible", "awful", "hate", "worst", "horrible", "disappointing", "poor"]

        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            sentiment = "neutral"
            confidence = 0.5
        else:
            sentiment_score = (positive_count - negative_count) / total_sentiment_words
            if sentiment_score > 0.1:
                sentiment = "positive"
            elif sentiment_score < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            confidence = abs(sentiment_score)

        return {
            "sentiment": sentiment,
            "confidence": min(confidence, 1.0),
            "positive_words": positive_count,
            "negative_words": negative_count,
            "method": "rule_based"
        }

    async def _extract_keywords(self, text: str) -> Dict[str, Any]:
        """Extract keywords from text."""
        # Simple TF-IDF style keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())

        # Remove stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were"}
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]

        # Count word frequencies
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "keywords": [word for word, count in sorted_words[:10]],
            "frequencies": dict(sorted_words[:10]),
            "total_words": len(words),
            "unique_words": len(set(words))
        }

    async def _detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of text."""
        # Simple language detection based on common words
        text_lower = text.lower()

        # English indicators
        english_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
        english_count = sum(1 for word in english_words if word in text_lower)

        # Spanish indicators
        spanish_words = ["el", "la", "los", "las", "y", "o", "pero", "en", "sobre", "a", "para", "de"]
        spanish_count = sum(1 for word in spanish_words if word in text_lower)

        # French indicators
        french_words = ["le", "la", "les", "et", "ou", "mais", "dans", "sur", "à", "pour", "de", "avec"]
        french_count = sum(1 for word in french_words if word in text_lower)

        # Determine language
        max_count = max(english_count, spanish_count, french_count)

        if max_count == 0:
            language = "unknown"
            confidence = 0.0
        elif english_count == max_count:
            language = "en"
            confidence = english_count / len(english_words)
        elif spanish_count == max_count:
            language = "es"
            confidence = spanish_count / len(spanish_words)
        else:
            language = "fr"
            confidence = french_count / len(french_words)

        return {
            "language": language,
            "confidence": min(confidence, 1.0),
            "method": "rule_based"
        }

    async def _calculate_readability(self, text: str) -> Dict[str, Any]:
        """Calculate readability score."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = re.findall(r'\b\w+\b', text)
        syllables = sum(self._count_syllables(word) for word in words)

        if not sentences or not words:
            return {"error": "Insufficient text for readability calculation"}

        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllables / len(words)

        # Automated Readability Index (ARI)
        ari = 4.71 * avg_syllables_per_word + 0.5 * avg_sentence_length - 21.43

        # Flesch Reading Ease
        flesch = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word

        # Grade level interpretation
        if ari <= 1:
            grade_level = "Kindergarten"
        elif ari <= 2:
            grade_level = "1st Grade"
        elif ari <= 3:
            grade_level = "2nd Grade"
        elif ari <= 4:
            grade_level = "3rd Grade"
        elif ari <= 5:
            grade_level = "4th Grade"
        elif ari <= 6:
            grade_level = "5th Grade"
        elif ari <= 7:
            grade_level = "6th Grade"
        elif ari <= 8:
            grade_level = "7th Grade"
        elif ari <= 9:
            grade_level = "8th Grade"
        elif ari <= 10:
            grade_level = "9th Grade"
        elif ari <= 11:
            grade_level = "10th Grade"
        elif ari <= 12:
            grade_level = "11th Grade"
        elif ari <= 13:
            grade_level = "12th Grade"
        elif ari <= 16:
            grade_level = "College"
        else:
            grade_level = "Graduate"

        return {
            "automated_readability_index": round(ari, 1),
            "flesch_reading_ease": round(flesch, 1),
            "grade_level": grade_level,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_syllables_per_word": round(avg_syllables_per_word, 1),
            "total_sentences": len(sentences),
            "total_words": len(words),
            "total_syllables": syllables
        }

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word."""
        word = word.lower()
        count = 0
        vowels = "aeiouy"

        if word[0] in vowels:
            count += 1

        for i in range(1, len(word)):
            if word[i] in vowels and word[i - 1] not in vowels:
                count += 1

        if word.endswith("e"):
            count -= 1

        if count == 0:
            count += 1

        return count

    def get_capabilities(self) -> Dict[str, Any]:
        """Get text processor capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "processing_operations": ["summarize", "extract_entities", "sentiment_analysis", "keyword_extraction", "language_detection", "readability_score"],
            "requires_model": False,
            "batch_processing": True
        })
        return capabilities


class ImageProcessor(ContentProcessor):
    """Processor for image content."""

    def get_supported_content_types(self) -> List[ContentType]:
        return [ContentType.IMAGE]

    async def process(self, content_data: ContentData, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process image content."""
        operations = self.config.get("operations", ["describe"])

        results = {}

        for operation in operations:
            try:
                if operation == "describe":
                    results["description"] = await self._describe_image(content_data)
                elif operation == "extract_text":
                    results["ocr_text"] = await self._extract_text_from_image(content_data)
                elif operation == "detect_objects":
                    results["objects"] = await self._detect_objects(content_data)
                elif operation == "analyze_colors":
                    results["colors"] = await self._analyze_colors(content_data)
                elif operation == "classify_scene":
                    results["scene"] = await self._classify_scene(content_data)
            except Exception as e:
                self.logger.error(f"Failed to process image operation {operation}: {e}")
                results[operation] = {"error": str(e)}

        return results

    async def _describe_image(self, content_data: ContentData) -> Dict[str, Any]:
        """Generate description of image."""
        # This would use a vision model
        if model_selector:
            model = await model_selector.select_model_for_task("image_description")
            if model:
                # description = await vision_service.describe_image(content_data.raw_data, model=model)
                description = "Image description would be generated by vision model"  # Placeholder

                return {
                    "description": description,
                    "model_used": model,
                    "confidence": 0.85
                }

        # Fallback: basic image info
        return {
            "description": "Image processing requires vision model integration",
            "method": "placeholder",
            "image_size_bytes": len(content_data.raw_data)
        }

    async def _extract_text_from_image(self, content_data: ContentData) -> Dict[str, Any]:
        """Extract text from image using OCR."""
        # This would use OCR service
        extracted_text = "OCR text extraction requires Tesseract or similar service"  # Placeholder

        return {
            "text": extracted_text,
            "confidence": 0.75,
            "method": "placeholder"
        }

    async def _detect_objects(self, content_data: ContentData) -> Dict[str, Any]:
        """Detect objects in image."""
        # This would use object detection model
        objects = ["person", "car", "building"]  # Placeholder

        return {
            "objects": objects,
            "count": len(objects),
            "method": "placeholder"
        }

    async def _analyze_colors(self, content_data: ContentData) -> Dict[str, Any]:
        """Analyze colors in image."""
        # Basic color analysis
        colors = ["#FF0000", "#00FF00", "#0000FF"]  # Placeholder

        return {
            "dominant_colors": colors,
            "color_count": len(colors),
            "method": "placeholder"
        }

    async def _classify_scene(self, content_data: ContentData) -> Dict[str, Any]:
        """Classify scene in image."""
        # This would use scene classification model
        scene = "outdoor"  # Placeholder

        return {
            "scene": scene,
            "confidence": 0.80,
            "method": "placeholder"
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Get image processor capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "processing_operations": ["describe", "extract_text", "detect_objects", "analyze_colors", "classify_scene"],
            "requires_model": True,
            "batch_processing": False
        })
        return capabilities


class AudioProcessor(ContentProcessor):
    """Processor for audio content."""

    def get_supported_content_types(self) -> List[ContentType]:
        return [ContentType.AUDIO]

    async def process(self, content_data: ContentData, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio content."""
        operations = self.config.get("operations", ["transcribe"])

        results = {}

        for operation in operations:
            try:
                if operation == "transcribe":
                    results["transcription"] = await self._transcribe_audio(content_data)
                elif operation == "identify_speaker":
                    results["speakers"] = await self._identify_speakers(content_data)
                elif operation == "analyze_emotion":
                    results["emotion"] = await self._analyze_emotion(content_data)
                elif operation == "extract_features":
                    results["features"] = await self._extract_audio_features(content_data)
            except Exception as e:
                self.logger.error(f"Failed to process audio operation {operation}: {e}")
                results[operation] = {"error": str(e)}

        return results

    async def _transcribe_audio(self, content_data: ContentData) -> Dict[str, Any]:
        """Transcribe audio to text."""
        # This would use speech-to-text service
        transcription = "Audio transcription requires speech-to-text service integration"  # Placeholder

        return {
            "transcription": transcription,
            "duration_seconds": 60.0,  # Placeholder
            "confidence": 0.85,
            "method": "placeholder"
        }

    async def _identify_speakers(self, content_data: ContentData) -> Dict[str, Any]:
        """Identify speakers in audio."""
        # This would use speaker identification model
        speakers = ["Speaker 1", "Speaker 2"]  # Placeholder

        return {
            "speakers": speakers,
            "speaker_count": len(speakers),
            "method": "placeholder"
        }

    async def _analyze_emotion(self, content_data: ContentData) -> Dict[str, Any]:
        """Analyze emotion in audio."""
        # This would use emotion recognition model
        emotion = "neutral"  # Placeholder

        return {
            "emotion": emotion,
            "confidence": 0.70,
            "method": "placeholder"
        }

    async def _extract_audio_features(self, content_data: ContentData) -> Dict[str, Any]:
        """Extract audio features."""
        # Basic audio feature extraction
        features = {
            "duration": 60.0,
            "sample_rate": 44100,
            "channels": 2
        }

        return {
            "features": features,
            "method": "placeholder"
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Get audio processor capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "processing_operations": ["transcribe", "identify_speaker", "analyze_emotion", "extract_features"],
            "requires_model": True,
            "batch_processing": False
        })
        return capabilities


class StructuredDataProcessor(ContentProcessor):
    """Processor for structured data content."""

    def get_supported_content_types(self) -> List[ContentType]:
        return [ContentType.STRUCTURED]

    async def process(self, content_data: ContentData, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process structured data content."""
        operations = self.config.get("operations", ["validate"])

        results = {}

        for operation in operations:
            try:
                if operation == "validate":
                    results["validation"] = await self._validate_schema(content_data)
                elif operation == "transform":
                    results["transformed"] = await self._transform_data(content_data)
                elif operation == "enrich":
                    results["enriched"] = await self._enrich_data(content_data)
                elif operation == "analyze":
                    results["analysis"] = await self._analyze_data(content_data)
            except Exception as e:
                self.logger.error(f"Failed to process structured data operation {operation}: {e}")
                results[operation] = {"error": str(e)}

        return results

    async def _validate_schema(self, content_data: ContentData) -> Dict[str, Any]:
        """Validate data against schema."""
        data = content_data.structured_data

        if not data:
            return {"valid": False, "error": "No structured data found"}

        # Basic validation
        if isinstance(data, dict):
            field_count = len(data)
            has_nested = any(isinstance(v, (dict, list)) for v in data.values())

            return {
                "valid": True,
                "field_count": field_count,
                "has_nested": has_nested,
                "data_type": "object"
            }
        elif isinstance(data, list):
            item_count = len(data)
            if item_count > 0:
                first_item_type = type(data[0]).__name__
            else:
                first_item_type = "unknown"

            return {
                "valid": True,
                "item_count": item_count,
                "item_type": first_item_type,
                "data_type": "array"
            }
        else:
            return {
                "valid": True,
                "data_type": type(data).__name__
            }

    async def _transform_data(self, content_data: ContentData) -> Dict[str, Any]:
        """Transform data structure."""
        data = content_data.structured_data

        if not data:
            return {"error": "No data to transform"}

        # Simple transformation examples
        if isinstance(data, dict):
            # Flatten nested structure
            flattened = self._flatten_dict(data)
            return {
                "original_type": "object",
                "transformed_type": "flattened_object",
                "data": flattened
            }
        elif isinstance(data, list):
            # Convert to dict with indices
            indexed = {str(i): item for i, item in enumerate(data)}
            return {
                "original_type": "array",
                "transformed_type": "indexed_object",
                "data": indexed
            }

        return {"error": "Unsupported data type for transformation"}

    def _flatten_dict(self, d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary."""
        flattened = {}

        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, new_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flattened.update(self._flatten_dict(item, f"{new_key}[{i}]"))
                    else:
                        flattened[f"{new_key}[{i}]"] = item
            else:
                flattened[new_key] = value

        return flattened

    async def _enrich_data(self, content_data: ContentData) -> Dict[str, Any]:
        """Enrich data with additional information."""
        data = content_data.structured_data

        if not data:
            return {"error": "No data to enrich"}

        enriched = dict(data) if isinstance(data, dict) else {"original_data": data}

        # Add metadata
        enriched["_metadata"] = {
            "enriched_at": datetime.now().isoformat(),
            "original_type": type(data).__name__,
            "processing_timestamp": datetime.now().timestamp()
        }

        return {
            "enriched_data": enriched,
            "additions": ["_metadata"],
            "method": "metadata_enrichment"
        }

    async def _analyze_data(self, content_data: ContentData) -> Dict[str, Any]:
        """Analyze structured data."""
        data = content_data.structured_data

        if not data:
            return {"error": "No data to analyze"}

        analysis = {
            "data_type": type(data).__name__,
            "analysis_timestamp": datetime.now().isoformat()
        }

        if isinstance(data, dict):
            analysis.update({
                "field_count": len(data),
                "field_types": {k: type(v).__name__ for k, v in data.items()},
                "nested_fields": [k for k, v in data.items() if isinstance(v, (dict, list))]
            })
        elif isinstance(data, list):
            analysis.update({
                "item_count": len(data),
                "item_types": list(set(type(item).__name__ for item in data))
            })

        return analysis

    def get_capabilities(self) -> Dict[str, Any]:
        """Get structured data processor capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "processing_operations": ["validate", "transform", "enrich", "analyze"],
            "requires_model": False,
            "batch_processing": True
        })
        return capabilities


class ContentProcessingPipeline:
    """Main content processing pipeline."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("content_pipeline")
        self.processors = self._initialize_processors()

    def _initialize_processors(self) -> Dict[str, ContentProcessor]:
        """Initialize content processors."""
        processors = {}

        # Text processor
        processors["text"] = TextProcessor(self.config.get("text_processor", {}))

        # Image processor
        processors["image"] = ImageProcessor(self.config.get("image_processor", {}))

        # Audio processor
        processors["audio"] = AudioProcessor(self.config.get("audio_processor", {}))

        # Structured data processor
        processors["structured"] = StructuredDataProcessor(self.config.get("structured_processor", {}))

        return processors

    async def process_content(self, content_data: ContentData, processing_config: Dict[str, Any]) -> ProcessingResult:
        """Process content through the pipeline."""
        start_time = datetime.now()

        processing_steps = []
        processed_content = {}
        errors = []
        warnings = []

        try:
            # Determine content type and select appropriate processor
            content_type = content_data.item.content_type
            processor = self._get_processor_for_content_type(content_type)

            if not processor:
                errors.append(f"No processor available for content type: {content_type.value}")
                return ProcessingResult(
                    content_data=content_data,
                    processed_content={},
                    processing_steps=processing_steps,
                    metadata={},
                    processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    success=False,
                    errors=errors
                )

            # Process content
            step_start = datetime.now()
            result = await processor.process(content_data, processing_config)
            step_time = (datetime.now() - step_start).total_seconds() * 1000

            processing_steps.append({
                "step_name": "content_processing",
                "processor_type": processor.__class__.__name__,
                "execution_time_ms": step_time,
                "success": True
            })

            processed_content.update(result)

            # Additional semantic processing if configured
            if processing_config.get("enable_semantic_processing", False):
                semantic_result = await self._apply_semantic_processing(content_data, processed_content)
                processed_content["semantic_analysis"] = semantic_result

            success = True

        except Exception as e:
            self.logger.error(f"Content processing failed: {e}")
            errors.append(str(e))
            success = False

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ProcessingResult(
            content_data=content_data,
            processed_content=processed_content,
            processing_steps=processing_steps,
            metadata={
                "pipeline_version": "1.0",
                "processing_timestamp": datetime.now().isoformat(),
                "content_type": content_data.item.content_type.value
            },
            processing_time_ms=processing_time,
            success=success,
            errors=errors,
            warnings=warnings
        )

    def _get_processor_for_content_type(self, content_type: ContentType) -> Optional[ContentProcessor]:
        """Get appropriate processor for content type."""
        if content_type == ContentType.TEXT:
            return self.processors.get("text")
        elif content_type == ContentType.IMAGE:
            return self.processors.get("image")
        elif content_type == ContentType.AUDIO:
            return self.processors.get("audio")
        elif content_type == ContentType.STRUCTURED:
            return self.processors.get("structured")
        elif content_type == ContentType.MIXED:
            # For mixed content, use text processor as fallback
            return self.processors.get("text")

        return None

    async def _apply_semantic_processing(self, content_data: ContentData, processed_content: Dict[str, Any]) -> Dict[str, Any]:
        """Apply semantic processing to content."""
        if not embedding_service:
            return {"error": "Embedding service not available"}

        try:
            # Extract text for semantic analysis
            text_to_analyze = ""
            if content_data.text_content:
                text_to_analyze = content_data.text_content
            elif "summary" in processed_content:
                text_to_analyze = processed_content["summary"]
            elif "description" in processed_content:
                text_to_analyze = processed_content["description"]

            if text_to_analyze:
                # Generate embeddings
                embedding = await embedding_service.generate_embedding(text_to_analyze)

                # Find similar content (placeholder)
                similar_content = []

                return {
                    "embedding_generated": True,
                    "embedding_dimensions": len(embedding) if embedding else 0,
                    "similar_content_count": len(similar_content),
                    "semantic_analysis": "completed"
                }
            else:
                return {"error": "No text available for semantic analysis"}

        except Exception as e:
            return {"error": f"Semantic processing failed: {e}"}

    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the processing pipeline."""
        return {
            "pipeline_version": "1.0",
            "available_processors": list(self.processors.keys()),
            "supported_content_types": [
                "text", "image", "audio", "structured", "mixed"
            ],
            "processing_operations": {
                "text": ["summarize", "extract_entities", "sentiment_analysis", "keyword_extraction"],
                "image": ["describe", "extract_text", "detect_objects"],
                "audio": ["transcribe", "identify_speaker", "analyze_emotion"],
                "structured": ["validate", "transform", "enrich", "analyze"]
            },
            "capabilities": {
                processor_name: processor.get_capabilities()
                for processor_name, processor in self.processors.items()
            }
        }


# Global pipeline instance
content_pipeline = ContentProcessingPipeline({})