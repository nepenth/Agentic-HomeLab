"""
Content Classification Service for automatic categorization and tagging.

This service provides intelligent content classification capabilities including:
- Automatic content categorization
- Tag generation and assignment
- Topic modeling and clustering
- Sentiment analysis and mood detection
- Content type classification
- Hierarchical categorization
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("content_classification_service")


class ClassificationError(Exception):
    """Raised when content classification fails."""
    pass


class ClassificationResult:
    """Result of content classification processing."""

    def __init__(
        self,
        content_id: str,
        primary_category: str = None,
        sub_categories: List[str] = None,
        tags: List[str] = None,
        topics: List[Dict[str, Any]] = None,
        sentiment: Dict[str, float] = None,
        confidence_scores: Dict[str, float] = None,
        hierarchical_categories: Dict[str, Any] = None,
        processing_time_ms: float = None,
        model_used: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.primary_category = primary_category
        self.sub_categories = sub_categories or []
        self.tags = tags or []
        self.topics = topics or []
        self.sentiment = sentiment or {}
        self.confidence_scores = confidence_scores or {}
        self.hierarchical_categories = hierarchical_categories or {}
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "primary_category": self.primary_category,
            "sub_categories": self.sub_categories,
            "tags": self.tags,
            "topics": self.topics,
            "sentiment": self.sentiment,
            "confidence_scores": self.confidence_scores,
            "hierarchical_categories": self.hierarchical_categories,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ContentClassificationService:
    """Service for automatic content classification and categorization."""

    def __init__(self):
        self.default_model = getattr(settings, 'content_classification_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'content_classification_timeout_seconds', 60)

        # Predefined category hierarchies
        self.category_hierarchies = {
            "content_type": [
                "text", "image", "audio", "video", "document", "webpage", "social_media", "email"
            ],
            "topic_domains": [
                "technology", "business", "science", "health", "education", "entertainment",
                "sports", "politics", "environment", "lifestyle", "travel", "food"
            ],
            "content_purpose": [
                "informational", "educational", "entertainment", "promotional", "personal",
                "professional", "news", "opinion", "review", "tutorial", "documentation"
            ]
        }

    async def classify_content(
        self,
        content_data: Dict[str, Any],
        classification_types: List[str] = None,
        **kwargs
    ) -> ClassificationResult:
        """
        Classify content using AI-powered analysis.

        Args:
            content_data: Content data dictionary
            classification_types: Types of classification to perform
            **kwargs: Additional classification options

        Returns:
            ClassificationResult with categorization and tagging
        """
        start_time = datetime.now()
        content_id = content_data.get('content_id', 'unknown')

        try:
            # Determine classification types
            classification_types = classification_types or [
                'category', 'tags', 'topics', 'sentiment'
            ]

            # Extract content for analysis
            content_text = self._extract_content_text(content_data)

            if not content_text:
                raise ClassificationError("No analyzable content found")

            # Perform classifications
            result = ClassificationResult(content_id=content_id)

            if 'category' in classification_types:
                category_result = await self._classify_category(content_text, **kwargs)
                result.primary_category = category_result.get('primary_category')
                result.sub_categories = category_result.get('sub_categories', [])
                result.hierarchical_categories = category_result.get('hierarchical', {})

            if 'tags' in classification_types:
                result.tags = await self._generate_tags(content_text, **kwargs)

            if 'topics' in classification_types:
                result.topics = await self._extract_topics(content_text, **kwargs)

            if 'sentiment' in classification_types:
                result.sentiment = await self._analyze_sentiment(content_text, **kwargs)

            # Calculate confidence scores
            result.confidence_scores = await self._calculate_confidence_scores(
                result, content_text, **kwargs
            )

            # Set processing metadata
            result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.model_used = self.default_model

            logger.info(f"Content classification completed for {content_id} in {result.processing_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise ClassificationError(f"Content classification failed: {str(e)}")

    def _extract_content_text(self, content_data: Dict[str, Any]) -> str:
        """Extract analyzable text from content data."""
        text_parts = []

        # Extract text content
        if 'text' in content_data and content_data['text']:
            text_parts.append(str(content_data['text']))

        # Extract from vision results
        if 'vision_result' in content_data:
            vision = content_data['vision_result']
            if isinstance(vision, dict):
                if 'caption' in vision:
                    text_parts.append(f"Caption: {vision['caption']}")
                if 'objects_detected' in vision and vision['objects_detected']:
                    objects_text = ", ".join([obj.get('name', '') for obj in vision['objects_detected'][:5]])
                    text_parts.append(f"Objects: {objects_text}")

        # Extract from audio results
        if 'audio_result' in content_data:
            audio = content_data['audio_result']
            if isinstance(audio, dict) and 'transcription' in audio:
                text_parts.append(f"Transcription: {audio['transcription']}")

        return " ".join(text_parts).strip()

    async def _classify_category(self, content_text: str, **kwargs) -> Dict[str, Any]:
        """Classify content into categories."""
        try:
            category_prompt = f"""
Analyze this content and classify it into appropriate categories:

Content: {content_text[:1000]}...

Provide classification in this JSON format:
{{
  "primary_category": "main category name",
  "sub_categories": ["sub1", "sub2", "sub3"],
  "hierarchical": {{
    "content_type": "text|image|audio|video|document",
    "topic_domain": "technology|business|science|etc",
    "content_purpose": "informational|educational|entertainment|etc"
  }},
  "confidence": 0.85
}}

Choose from these predefined categories:
- Content Types: {', '.join(self.category_hierarchies['content_type'])}
- Topic Domains: {', '.join(self.category_hierarchies['topic_domains'])}
- Content Purposes: {', '.join(self.category_hierarchies['content_purpose'])}
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=category_prompt,
                system="You are an expert at content classification and categorization. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 400)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                classification = json.loads(result_text)
                return classification
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse category classification JSON: {result_text}")
                return {
                    "primary_category": "uncategorized",
                    "sub_categories": [],
                    "hierarchical": {},
                    "confidence": 0.0
                }

        except Exception as e:
            logger.error(f"Category classification failed: {e}")
            return {
                "primary_category": "error",
                "sub_categories": [],
                "hierarchical": {},
                "confidence": 0.0
            }

    async def _generate_tags(self, content_text: str, **kwargs) -> List[str]:
        """Generate relevant tags for the content."""
        try:
            max_tags = kwargs.get('max_tags', 10)

            tags_prompt = f"""
Analyze this content and generate relevant tags (keywords or phrases):

Content: {content_text[:1000]}...

Generate {max_tags} relevant tags that capture the main topics, themes, and key concepts.
Focus on specific, descriptive tags rather than generic ones.
Format as JSON array of strings.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=tags_prompt,
                system="You are an expert at keyword extraction and tagging. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.4),
                    "num_predict": kwargs.get('max_tokens', 300)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                tags = json.loads(result_text)
                if isinstance(tags, list):
                    # Filter and clean tags
                    cleaned_tags = []
                    for tag in tags:
                        if isinstance(tag, str) and len(tag.strip()) > 1:
                            cleaned_tags.append(tag.strip().lower())
                    return cleaned_tags[:max_tags]
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tags JSON: {result_text}")
                return []

        except Exception as e:
            logger.error(f"Tag generation failed: {e}")
            return []

    async def _extract_topics(self, content_text: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract main topics and themes from content."""
        try:
            max_topics = kwargs.get('max_topics', 5)

            topics_prompt = f"""
Analyze this content and extract the main topics and themes:

Content: {content_text[:1000]}...

For each topic, provide:
- topic_name: The main topic or theme
- relevance_score: How relevant this topic is (0.0 to 1.0)
- keywords: Key terms associated with this topic
- description: Brief description of the topic in context

Format as JSON array of topic objects.
Limit to {max_topics} most important topics.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=topics_prompt,
                system="You are an expert at topic modeling and thematic analysis. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 500)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                topics = json.loads(result_text)
                if isinstance(topics, list):
                    # Validate and clean topics
                    cleaned_topics = []
                    for topic in topics:
                        if isinstance(topic, dict) and 'topic_name' in topic:
                            cleaned_topic = {
                                "topic_name": topic.get('topic_name', ''),
                                "relevance_score": min(1.0, max(0.0, topic.get('relevance_score', 0.5))),
                                "keywords": topic.get('keywords', []) if isinstance(topic.get('keywords'), list) else [],
                                "description": topic.get('description', '')
                            }
                            cleaned_topics.append(cleaned_topic)
                    return cleaned_topics[:max_topics]
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse topics JSON: {result_text}")
                return []

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return []

    async def _analyze_sentiment(self, content_text: str, **kwargs) -> Dict[str, float]:
        """Analyze sentiment and emotional tone of content."""
        try:
            sentiment_prompt = f"""
Analyze the sentiment and emotional tone of this content:

Content: {content_text[:1000]}...

Provide sentiment scores for these emotions/categories:
- positive: Overall positive sentiment (0.0 to 1.0)
- negative: Overall negative sentiment (0.0 to 1.0)
- neutral: Neutral or objective tone (0.0 to 1.0)
- joy: Expression of happiness or joy (0.0 to 1.0)
- anger: Expression of anger or frustration (0.0 to 1.0)
- sadness: Expression of sadness or disappointment (0.0 to 1.0)
- fear: Expression of fear or anxiety (0.0 to 1.0)
- surprise: Expression of surprise or unexpectedness (0.0 to 1.0)

Format as JSON object with emotion names as keys and scores as values.
Scores should sum to approximately 1.0 across related emotions.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=sentiment_prompt,
                system="You are an expert at sentiment analysis and emotion detection. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.2),
                    "num_predict": kwargs.get('max_tokens', 400)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                sentiment = json.loads(result_text)
                if isinstance(sentiment, dict):
                    # Validate and normalize scores
                    normalized_sentiment = {}
                    for emotion, score in sentiment.items():
                        if isinstance(score, (int, float)):
                            normalized_sentiment[emotion] = min(1.0, max(0.0, float(score)))
                        else:
                            normalized_sentiment[emotion] = 0.0
                    return normalized_sentiment
                else:
                    return {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse sentiment JSON: {result_text}")
                return {}

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {}

    async def _calculate_confidence_scores(
        self,
        result: ClassificationResult,
        content_text: str,
        **kwargs
    ) -> Dict[str, float]:
        """Calculate confidence scores for classification results."""
        try:
            confidence_prompt = f"""
Evaluate the confidence of this content classification:

Content: {content_text[:500]}...

Classification Results:
- Primary Category: {result.primary_category}
- Sub-categories: {', '.join(result.sub_categories)}
- Tags: {', '.join(result.tags[:5])}
- Topics: {len(result.topics)} topics identified
- Sentiment: {len(result.sentiment)} emotions detected

Rate the confidence of each classification aspect (0.0 to 1.0):
- category_confidence: How well does the category fit?
- tags_confidence: How relevant are the generated tags?
- topics_confidence: How accurate are the topic identifications?
- sentiment_confidence: How accurate is the sentiment analysis?
- overall_confidence: Overall classification quality

Format as JSON object.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=confidence_prompt,
                system="You are an expert at evaluating classification quality. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.1),
                    "num_predict": kwargs.get('max_tokens', 300)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                confidence_scores = json.loads(result_text)
                if isinstance(confidence_scores, dict):
                    # Validate scores
                    validated_scores = {}
                    for key, score in confidence_scores.items():
                        if isinstance(score, (int, float)):
                            validated_scores[key] = min(1.0, max(0.0, float(score)))
                        else:
                            validated_scores[key] = 0.5
                    return validated_scores
                else:
                    return {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse confidence scores JSON: {result_text}")
                return {}

        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return {}

    async def batch_classify_content(
        self,
        content_batch: List[Dict[str, Any]],
        classification_types: List[str] = None,
        max_concurrent: int = 3
    ) -> List[ClassificationResult]:
        """
        Classify multiple content items in batch.

        Args:
            content_batch: List of content data dictionaries
            classification_types: Types of classification to perform
            max_concurrent: Maximum concurrent classification tasks

        Returns:
            List of ClassificationResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def classify_single_item(content_data: Dict[str, Any]) -> ClassificationResult:
            async with semaphore:
                return await self.classify_content(
                    content_data,
                    classification_types=classification_types
                )

        tasks = [classify_single_item(item) for item in content_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch classification failed for item {i}: {result}")
                # Create error result
                error_result = ClassificationResult(
                    content_id=content_batch[i].get('content_id', f'batch_item_{i}'),
                    metadata={"error": str(result)}
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    def get_supported_classification_types(self) -> List[str]:
        """Get list of supported classification types."""
        return ['category', 'tags', 'topics', 'sentiment']

    def get_category_hierarchies(self) -> Dict[str, List[str]]:
        """Get predefined category hierarchies."""
        return self.category_hierarchies.copy()

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the content classification service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "content_classification",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "supported_classification_types": self.get_supported_classification_types(),
                "category_hierarchies": self.get_category_hierarchies(),
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "content_classification",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
content_classification_service = ContentClassificationService()