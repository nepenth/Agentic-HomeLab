"""
Semantic Processing Infrastructure for embeddings and vector operations.

This module provides comprehensive semantic processing capabilities including
embedding generation, vector operations, content chunking, and quality assessment.
"""

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from enum import Enum
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import nltk

from app.config import settings
from app.services.ollama_client import OllamaClient
from app.services.model_selection_service import (
    ModelRegistry, ModelSelector, TaskType, ContentType, ProcessingTask
)
from app.services.content_framework import ContentData, ContentType as ContentTypeEnum
from app.utils.logging import get_logger

logger = get_logger("semantic_processing")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class ChunkingStrategy(Enum):
    """Content chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SENTENCE_BASED = "sentence_based"
    SEMANTIC = "semantic"
    OVERLAPPING = "overlapping"


class VectorOperation(Enum):
    """Supported vector operations."""
    COSINE_SIMILARITY = "cosine_similarity"
    EUCLIDEAN_DISTANCE = "euclidean_distance"
    DOT_PRODUCT = "dot_product"
    MANHATTAN_DISTANCE = "manhattan_distance"


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    content: str
    start_pos: int
    end_pos: int
    chunk_index: int
    token_count: int
    sentence_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    model_used: str
    token_count: int
    processing_time_ms: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SimilarityResult:
    """Result of similarity search."""
    query_text: str
    similar_items: List[Dict[str, Any]]
    search_time_ms: float
    total_candidates: int


@dataclass
class ClusteringResult:
    """Result of content clustering."""
    clusters: List[Dict[str, Any]]
    centroids: List[List[float]]
    labels: List[int]
    silhouette_score: Optional[float]
    processing_time_ms: float


@dataclass
class QualityScore:
    """Content quality assessment."""
    overall_score: float
    readability_score: float
    coherence_score: float
    informativeness_score: float
    metrics: Dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """Intelligent text chunking with multiple strategies."""

    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.stop_words = set(stopwords.words('english'))

    def chunk_text(
        self,
        text: str,
        strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
        **kwargs
    ) -> List[TextChunk]:
        """Chunk text using specified strategy."""
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text, **kwargs)
        elif strategy == ChunkingStrategy.SENTENCE_BASED:
            return self._chunk_sentence_based(text, **kwargs)
        elif strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(text, **kwargs)
        elif strategy == ChunkingStrategy.OVERLAPPING:
            return self._chunk_overlapping(text, **kwargs)
        else:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")

    def _chunk_fixed_size(self, text: str, chunk_size: Optional[int] = None) -> List[TextChunk]:
        """Chunk text into fixed-size pieces."""
        chunk_size = chunk_size or self.max_chunk_size
        chunks = []
        start_pos = 0
        chunk_index = 0

        while start_pos < len(text):
            end_pos = min(start_pos + chunk_size, len(text))

            # Try to break at word boundary
            if end_pos < len(text):
                # Find last space within chunk
                last_space = text.rfind(' ', start_pos, end_pos)
                if last_space > start_pos:
                    end_pos = last_space

            chunk_content = text[start_pos:end_pos].strip()
            if chunk_content:
                chunks.append(self._create_chunk(
                    chunk_content, start_pos, end_pos, chunk_index
                ))
                chunk_index += 1

            start_pos = end_pos

        return chunks

    def _chunk_sentence_based(self, text: str, max_sentences: int = 5) -> List[TextChunk]:
        """Chunk text based on sentence boundaries."""
        try:
            sentences = sent_tokenize(text)
        except Exception:
            # Fallback to simple sentence splitting
            sentences = re.split(r'[.!?]+', text)

        chunks = []
        current_chunk = []
        start_pos = 0
        chunk_index = 0

        for sentence in sentences:
            current_chunk.append(sentence)

            if len(current_chunk) >= max_sentences:
                chunk_content = ' '.join(current_chunk)
                end_pos = start_pos + len(chunk_content)

                chunks.append(self._create_chunk(
                    chunk_content, start_pos, end_pos, chunk_index
                ))

                start_pos = end_pos
                current_chunk = []
                chunk_index += 1

        # Add remaining sentences
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            end_pos = start_pos + len(chunk_content)

            chunks.append(self._create_chunk(
                chunk_content, start_pos, len(text), chunk_index
            ))

        return chunks

    def _chunk_semantic(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text based on semantic boundaries."""
        # Use sentence-based chunking as base
        sentence_chunks = self._chunk_sentence_based(text, **kwargs)

        # Could be enhanced with semantic analysis
        # For now, return sentence-based chunks
        return sentence_chunks

    def _chunk_overlapping(self, text: str, **kwargs) -> List[TextChunk]:
        """Create overlapping chunks."""
        base_chunks = self._chunk_fixed_size(text, **kwargs)
        overlapping_chunks = []

        for i, chunk in enumerate(base_chunks):
            overlapping_chunks.append(chunk)

            # Add overlapping chunk if not the last one
            if i < len(base_chunks) - 1:
                next_chunk = base_chunks[i + 1]
                overlap_content = text[chunk.end_pos - self.overlap: next_chunk.start_pos + self.overlap]

                if len(overlap_content.strip()) > 10:  # Minimum overlap size
                    overlapping_chunks.append(self._create_chunk(
                        overlap_content.strip(),
                        chunk.end_pos - self.overlap,
                        next_chunk.start_pos + self.overlap,
                        len(overlapping_chunks)
                    ))

        return overlapping_chunks

    def _create_chunk(self, content: str, start_pos: int, end_pos: int, chunk_index: int) -> TextChunk:
        """Create a TextChunk object."""
        # Count tokens (approximate)
        tokens = word_tokenize(content)
        token_count = len(tokens)

        # Count sentences
        try:
            sentences = sent_tokenize(content)
            sentence_count = len(sentences)
        except Exception:
            sentence_count = len(re.findall(r'[.!?]+', content))

        return TextChunk(
            content=content,
            start_pos=start_pos,
            end_pos=end_pos,
            chunk_index=chunk_index,
            token_count=token_count,
            sentence_count=sentence_count,
            metadata={
                'avg_word_length': sum(len(word) for word in tokens) / max(token_count, 1),
                'unique_words': len(set(word.lower() for word in tokens))
            }
        )


class EmbeddingService:
    """Unified embedding service for multiple models."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model_selector: Optional[ModelSelector] = None
    ):
        self.ollama_client = ollama_client or OllamaClient()
        self.model_selector = model_selector
        self.chunker = TextChunker()

    async def generate_embedding(
        self,
        text: str,
        model_name: Optional[str] = None,
        chunk_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    ) -> EmbeddingResult:
        """Generate embeddings for text."""
        start_time = time.time()

        # Select model if not provided
        if not model_name and self.model_selector:
            task = ProcessingTask(
                task_type=TaskType.EMBEDDING_GENERATION,
                content_type=ContentType.TEXT
            )
            selection = await self.model_selector.select_for_task(task)
            model_name = selection.model_name

        model_name = model_name or "nomic-embed-text"

        # Chunk text if needed
        if len(text) > 512:  # Rough token limit
            chunks = self.chunker.chunk_text(text, chunk_strategy)
            # Use first chunk for now (could be enhanced to combine chunks)
            text = chunks[0].content if chunks else text

        try:
            async with self.ollama_client:
                response = await self.ollama_client.embeddings(
                    prompt=text,
                    model=model_name
                )

            embedding = response.get('embedding', [])
            processing_time = (time.time() - start_time) * 1000

            # Estimate token count
            token_count = len(text.split())

            return EmbeddingResult(
                text=text,
                embedding=embedding,
                model_used=model_name,
                token_count=token_count,
                processing_time_ms=processing_time
            )

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def generate_multiple_embeddings(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
        batch_size: int = 10
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts."""
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_tasks = [
                self.generate_embedding(text, model_name)
                for text in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Embedding generation failed: {result}")
                else:
                    results.append(result)

        return results


class VectorOperations:
    """Vector operations for similarity search and clustering."""

    def __init__(self):
        self.embedding_cache: Dict[str, List[float]] = {}

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        v1 = np.array(vec1).reshape(1, -1)
        v2 = np.array(vec2).reshape(1, -1)
        return cosine_similarity(v1, v2)[0][0]

    def euclidean_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate Euclidean distance between two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.linalg.norm(v1 - v2)

    def dot_product(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate dot product of two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.dot(v1, v2)

    def manhattan_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate Manhattan distance between two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.sum(np.abs(v1 - v2))

    def find_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[Tuple[str, List[float]]],
        top_k: int = 5,
        operation: VectorOperation = VectorOperation.COSINE_SIMILARITY
    ) -> List[Tuple[str, float]]:
        """Find most similar embeddings to query."""
        similarities = []

        for item_id, embedding in candidate_embeddings:
            if operation == VectorOperation.COSINE_SIMILARITY:
                score = self.cosine_similarity(query_embedding, embedding)
            elif operation == VectorOperation.EUCLIDEAN_DISTANCE:
                score = -self.euclidean_distance(query_embedding, embedding)  # Negative for ranking
            elif operation == VectorOperation.DOT_PRODUCT:
                score = self.dot_product(query_embedding, embedding)
            elif operation == VectorOperation.MANHATTAN_DISTANCE:
                score = -self.manhattan_distance(query_embedding, embedding)  # Negative for ranking
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            similarities.append((item_id, score))

        # Sort by score (descending for similarity, ascending for distance)
        reverse = operation in [VectorOperation.COSINE_SIMILARITY, VectorOperation.DOT_PRODUCT]
        similarities.sort(key=lambda x: x[1], reverse=reverse)

        return similarities[:top_k]

    def cluster_embeddings(
        self,
        embeddings: List[Tuple[str, List[float]]],
        n_clusters: int = 5
    ) -> ClusteringResult:
        """Cluster embeddings using K-means."""
        start_time = time.time()

        # Extract vectors
        vectors = np.array([emb for _, emb in embeddings])
        item_ids = [item_id for item_id, _ in embeddings]

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(vectors)
        centroids = kmeans.cluster_centers_.tolist()

        # Calculate silhouette score
        from sklearn.metrics import silhouette_score
        try:
            silhouette = silhouette_score(vectors, labels)
        except Exception:
            silhouette = None

        # Group items by cluster
        clusters = []
        for i in range(n_clusters):
            cluster_items = [
                item_ids[j] for j in range(len(labels))
                if labels[j] == i
            ]
            clusters.append({
                'cluster_id': i,
                'items': cluster_items,
                'item_count': len(cluster_items),
                'centroid': centroids[i]
            })

        processing_time = (time.time() - start_time) * 1000

        return ClusteringResult(
            clusters=clusters,
            centroids=centroids,
            labels=labels.tolist(),
            silhouette_score=silhouette,
            processing_time_ms=processing_time
        )


class SemanticSearch:
    """Semantic search using embeddings."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_ops: VectorOperations
    ):
        self.embedding_service = embedding_service
        self.vector_ops = vector_ops
        self.index: Dict[str, Tuple[str, List[float]]] = {}  # item_id -> (content, embedding)

    async def index_content(self, item_id: str, content: str, model_name: Optional[str] = None):
        """Index content for semantic search."""
        embedding_result = await self.embedding_service.generate_embedding(content, model_name)
        self.index[item_id] = (content, embedding_result.embedding)

    def remove_from_index(self, item_id: str):
        """Remove item from search index."""
        if item_id in self.index:
            del self.index[item_id]

    async def search(
        self,
        query: str,
        top_k: int = 5,
        model_name: Optional[str] = None
    ) -> SimilarityResult:
        """Perform semantic search."""
        start_time = time.time()

        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query, model_name)
        query_embedding = query_embedding.embedding

        # Prepare candidates
        candidates = [(item_id, emb) for item_id, (_, emb) in self.index.items()]

        # Find similar items
        similar_items = self.vector_ops.find_similar(query_embedding, candidates, top_k)

        # Format results
        results = []
        for item_id, score in similar_items:
            content, _ = self.index[item_id]
            results.append({
                'item_id': item_id,
                'content': content[:200] + '...' if len(content) > 200 else content,
                'similarity_score': score
            })

        search_time = (time.time() - start_time) * 1000

        return SimilarityResult(
            query_text=query,
            similar_items=results,
            search_time_ms=search_time,
            total_candidates=len(candidates)
        )


class QualityScorer:
    """Content quality assessment."""

    def __init__(self):
        self.chunker = TextChunker()

    def score_content(self, content: str, content_type: ContentTypeEnum) -> QualityScore:
        """Score content quality."""
        if content_type == ContentTypeEnum.TEXT:
            return self._score_text_quality(content)
        elif content_type == ContentTypeEnum.IMAGE:
            return self._score_image_quality(content)
        else:
            return QualityScore(
                overall_score=0.5,
                readability_score=0.5,
                coherence_score=0.5,
                informativeness_score=0.5
            )

    def _score_text_quality(self, text: str) -> QualityScore:
        """Score text content quality."""
        # Readability metrics
        words = word_tokenize(text)
        sentences = sent_tokenize(text)

        avg_sentence_length = len(words) / max(len(sentences), 1)
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)

        # Simple readability score (lower is better readability)
        readability_score = max(0, 1 - (avg_sentence_length / 30 + avg_word_length / 8) / 2)

        # Coherence score (based on sentence transitions)
        coherence_score = self._calculate_coherence(text)

        # Informativeness score (based on unique words, length, etc.)
        unique_words = len(set(word.lower() for word in words))
        informativeness_score = min(unique_words / max(len(words), 1) * 2, 1.0)

        # Overall score
        overall_score = (readability_score + coherence_score + informativeness_score) / 3

        return QualityScore(
            overall_score=overall_score,
            readability_score=readability_score,
            coherence_score=coherence_score,
            informativeness_score=informativeness_score,
            metrics={
                'word_count': len(words),
                'sentence_count': len(sentences),
                'avg_sentence_length': avg_sentence_length,
                'avg_word_length': avg_word_length,
                'unique_words': unique_words,
                'vocabulary_richness': unique_words / max(len(words), 1)
            }
        )

    def _calculate_coherence(self, text: str) -> float:
        """Calculate text coherence score."""
        try:
            sentences = sent_tokenize(text)
            if len(sentences) < 2:
                return 0.5

            # Simple coherence based on sentence length variation
            lengths = [len(sent.split()) for sent in sentences]
            avg_length = sum(lengths) / len(lengths)
            variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            std_dev = variance ** 0.5

            # Lower variation suggests better coherence
            coherence = max(0, 1 - std_dev / avg_length)
            return coherence

        except Exception:
            return 0.5

    def _score_image_quality(self, image_path: str) -> QualityScore:
        """Score image quality (placeholder)."""
        # This would require image analysis libraries
        return QualityScore(
            overall_score=0.7,
            readability_score=0.5,
            coherence_score=0.8,
            informativeness_score=0.7
        )


class ModelUsageTracker:
    """Track model usage for processing tasks."""

    def __init__(self):
        self.usage_stats: Dict[str, Dict[str, Any]] = {}

    def record_usage(
        self,
        model_name: str,
        task_type: str,
        content_type: str,
        processing_time_ms: float,
        token_count: int,
        success: bool
    ):
        """Record model usage."""
        if model_name not in self.usage_stats:
            self.usage_stats[model_name] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_processing_time_ms': 0,
                'total_tokens': 0,
                'task_breakdown': {},
                'content_type_breakdown': {}
            }

        stats = self.usage_stats[model_name]
        stats['total_requests'] += 1

        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1

        stats['total_processing_time_ms'] += processing_time_ms
        stats['total_tokens'] += token_count

        # Update breakdowns
        if task_type not in stats['task_breakdown']:
            stats['task_breakdown'][task_type] = 0
        stats['task_breakdown'][task_type] += 1

        if content_type not in stats['content_type_breakdown']:
            stats['content_type_breakdown'][content_type] = 0
        stats['content_type_breakdown'][content_type] += 1

    def get_usage_stats(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics."""
        if model_name:
            return self.usage_stats.get(model_name, {})

        return dict(self.usage_stats)

    def get_model_performance_summary(self, model_name: str) -> Dict[str, Any]:
        """Get performance summary for a model."""
        if model_name not in self.usage_stats:
            return {}

        stats = self.usage_stats[model_name]

        total_requests = stats['total_requests']
        if total_requests == 0:
            return {}

        return {
            'model_name': model_name,
            'success_rate': stats['successful_requests'] / total_requests,
            'average_processing_time_ms': stats['total_processing_time_ms'] / total_requests,
            'average_tokens_per_request': stats['total_tokens'] / total_requests,
            'total_requests': total_requests,
            'task_distribution': stats['task_breakdown'],
            'content_type_distribution': stats['content_type_breakdown']
        }


# Global instances
text_chunker = TextChunker()
embedding_service = EmbeddingService()
vector_operations = VectorOperations()
semantic_search = SemanticSearch(embedding_service, vector_operations)
quality_scorer = QualityScorer()
model_usage_tracker = ModelUsageTracker()