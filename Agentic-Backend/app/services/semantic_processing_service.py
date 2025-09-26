"""
Semantic Processing Service for embeddings, vector search, and knowledge graph.

This service provides comprehensive semantic processing capabilities including:
- Text embeddings using Ollama models
- Vector similarity search
- Knowledge graph construction and querying
- Semantic duplicate detection
- Entity extraction and relationship mapping
- Content chunking and indexing
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.ollama_client import ollama_client
from app.services.model_capability_service import model_capability_service, ModelCapability
from app.utils.logging import get_logger

logger = get_logger("semantic_processing_service")


@dataclass
class SemanticChunk:
    """Represents a chunk of semantically related content."""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    source_id: str
    chunk_index: int
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeEntity:
    """Represents an entity in the knowledge graph."""
    id: str
    name: str
    entity_type: str
    description: str
    properties: Dict[str, Any]
    embedding: List[float]
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeRelation:
    """Represents a relationship between entities in the knowledge graph."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    description: str
    properties: Dict[str, Any]
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SemanticSearchResult:
    """Result of a semantic search operation."""
    content_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    source_id: str


@dataclass
class DuplicateDetectionResult:
    """Result of duplicate detection analysis."""
    original_content_id: str
    duplicate_content_id: str
    similarity_score: float
    duplicate_type: str  # exact, near_exact, semantic
    confidence: float


class VectorStore:
    """Simple in-memory vector store for homelab setup."""

    def __init__(self):
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("vector_store")

    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict[str, Any]):
        """Add a vector to the store."""
        self.vectors[vector_id] = vector
        self.metadata[vector_id] = metadata

    def get_vector(self, vector_id: str) -> Optional[List[float]]:
        """Get a vector by ID."""
        return self.vectors.get(vector_id)

    def search_similar(self, query_vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        """Search for similar vectors using cosine similarity."""
        if not self.vectors:
            return []

        # Convert to numpy arrays for efficient computation
        query_vec = np.array(query_vector).reshape(1, -1)
        vector_ids = list(self.vectors.keys())
        vectors = np.array([self.vectors[vid] for vid in vector_ids])

        # Calculate cosine similarities
        similarities = cosine_similarity(query_vec, vectors)[0]

        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(vector_ids[i], float(similarities[i])) for i in top_indices]

        return results

    def delete_vector(self, vector_id: str) -> bool:
        """Delete a vector from the store."""
        if vector_id in self.vectors:
            del self.vectors[vector_id]
            del self.metadata[vector_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_vectors": len(self.vectors),
            "vector_dimensions": len(next(iter(self.vectors.values()))) if self.vectors else 0,
            "metadata_keys": list(set().union(*[m.keys() for m in self.metadata.values()])) if self.metadata else []
        }


class SemanticProcessingService:
    """Service for semantic processing, embeddings, and knowledge graph operations."""

    def __init__(self):
        self.logger = get_logger("semantic_processing_service")
        self.vector_store = VectorStore()
        self.chunks: Dict[str, SemanticChunk] = {}
        self.entities: Dict[str, KnowledgeEntity] = {}
        self.relations: Dict[str, KnowledgeRelation] = {}
        self.embedding_model = None

        # Semantic processing configuration
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        self.similarity_threshold = 0.85  # Threshold for duplicate detection
        self.entity_confidence_threshold = 0.7  # Minimum confidence for entity extraction

    async def initialize(self):
        """Initialize the semantic processing service."""
        try:
            # Ensure model capability service is initialized
            await model_capability_service.initialize()

            # Prioritize known working embedding models
            preferred_models = ["snowflake-arctic-embed2:latest", "embeddinggemma:latest"]

            # Check if preferred models are available
            available_embedding_models = await model_capability_service.get_embedding_models()
            available_model_names = [model.name for model in available_embedding_models]

            # Use first available preferred model
            self.embedding_model = None
            for preferred in preferred_models:
                if preferred in available_model_names:
                    self.embedding_model = preferred
                    break

            # If no preferred model found, use whatever the capability service suggests
            if not self.embedding_model:
                detected_model = await model_capability_service.get_best_model_for_task(
                    ModelCapability.EMBEDDING_GENERATION
                )
                if detected_model:
                    self.embedding_model = detected_model
                    self.logger.info(f"Using detected embedding model: {detected_model}")
                else:
                    self.logger.error("No embedding models available")

            if self.embedding_model:
                self.logger.info(f"Semantic Processing Service initialized successfully with model: {self.embedding_model}")
            else:
                raise ValueError("No embedding model could be selected")

        except Exception as e:
            self.logger.error(f"Failed to initialize Semantic Processing Service: {e}")
            raise

    async def generate_embedding(self, text: str, model_name: Optional[str] = None) -> List[float]:
        """
        Generate embeddings for text using Ollama.

        Args:
            text: Text to embed
            model_name: Specific model to use (optional)

        Returns:
            List of embedding values
        """
        # Get list of models to try
        models_to_try = []
        if model_name:
            models_to_try.append(model_name)
        else:
            # Try primary model first, then fallbacks
            if self.embedding_model:
                models_to_try.append(self.embedding_model)

            # Add known working fallback models
            fallback_models = ["snowflake-arctic-embed2:latest", "embeddinggemma:latest"]
            for fallback in fallback_models:
                if fallback not in models_to_try:
                    models_to_try.append(fallback)

        last_error = None
        for model in models_to_try:
            try:
                self.logger.debug(f"Trying to generate embedding with model: {model}")

                # Use Ollama embeddings API
                response = await ollama_client.embeddings(prompt=text, model=model)

                if response and 'embedding' in response:
                    embedding = response['embedding']
                    self.logger.debug(f"Generated embedding with {len(embedding)} dimensions using {model}")

                    # If we succeeded with a different model, update the primary model
                    if not model_name and model != self.embedding_model:
                        self.logger.info(f"Switching to working embedding model: {model}")
                        self.embedding_model = model

                    return embedding
                else:
                    raise ValueError("Invalid embedding response from Ollama")

            except Exception as e:
                last_error = e
                self.logger.warning(f"Failed to generate embedding with model {model}: {e}")
                continue

        # If all models failed, raise the last error
        self.logger.error(f"All embedding models failed. Last error: {last_error}")
        raise last_error or ValueError("No embedding model available")

    async def chunk_text(
        self,
        text: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[SemanticChunk]:
        """
        Split text into semantically meaningful chunks.

        Args:
            text: Text to chunk
            source_id: Source identifier
            metadata: Additional metadata

        Returns:
            List of SemanticChunk objects
        """
        try:
            chunks = []
            metadata = metadata or {}

            # Simple character-based chunking with overlap
            start = 0
            chunk_index = 0

            while start < len(text):
                # Find end of chunk
                end = min(start + self.chunk_size, len(text))

                # Adjust to word boundaries if possible
                if end < len(text):
                    # Look for sentence endings
                    sentence_endings = ['. ', '! ', '? ', '\n\n']
                    for ending in sentence_endings:
                        last_ending = text.rfind(ending, start, end)
                        if last_ending != -1 and last_ending > start + self.chunk_size // 2:
                            end = last_ending + len(ending)
                            break

                    # Fallback to word boundaries
                    if end == start + self.chunk_size:
                        last_space = text.rfind(' ', start, end)
                        if last_space != -1:
                            end = last_space + 1

                chunk_text = text[start:end].strip()
                if chunk_text:
                    # Generate embedding for chunk
                    embedding = await self.generate_embedding(chunk_text)

                    chunk = SemanticChunk(
                        id=str(uuid.uuid4()),
                        content=chunk_text,
                        embedding=embedding,
                        metadata=metadata.copy(),
                        source_id=source_id,
                        chunk_index=chunk_index
                    )

                    chunks.append(chunk)
                    self.chunks[chunk.id] = chunk

                    # Store in vector store
                    self.vector_store.add_vector(
                        chunk.id,
                        embedding,
                        {
                            "content": chunk_text,
                            "source_id": source_id,
                            "chunk_index": chunk_index,
                            "type": "chunk",
                            **metadata
                        }
                    )

                # Move start position with overlap
                start = max(start + 1, end - self.chunk_overlap)
                chunk_index += 1

            self.logger.info(f"Created {len(chunks)} chunks for source {source_id}")
            return chunks

        except Exception as e:
            self.logger.error(f"Failed to chunk text: {e}")
            raise

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7,
        source_filter: Optional[str] = None
    ) -> List[SemanticSearchResult]:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            source_filter: Filter by source ID

        Returns:
            List of SemanticSearchResult objects
        """
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query)

            # Search vector store
            similar_vectors = self.vector_store.search_similar(query_embedding, top_k * 2)  # Get more candidates

            results = []
            for vector_id, similarity in similar_vectors:
                if similarity < threshold:
                    continue

                # Get metadata
                metadata = self.vector_store.metadata.get(vector_id, {})
                if source_filter and metadata.get('source_id') != source_filter:
                    continue

                # Get chunk content
                chunk = self.chunks.get(vector_id)
                if chunk:
                    result = SemanticSearchResult(
                        content_id=vector_id,
                        content=chunk.content,
                        similarity_score=similarity,
                        metadata=metadata,
                        source_id=chunk.source_id
                    )
                    results.append(result)

                if len(results) >= top_k:
                    break

            self.logger.info(f"Semantic search returned {len(results)} results for query: {query[:50]}...")
            return results

        except Exception as e:
            self.logger.error(f"Failed to perform semantic search: {e}")
            raise

    async def detect_duplicates(
        self,
        content_id: str,
        content: str,
        threshold: Optional[float] = None
    ) -> List[DuplicateDetectionResult]:
        """
        Detect duplicate or similar content.

        Args:
            content_id: ID of the content to check
            content: Content text to analyze
            threshold: Similarity threshold (uses default if None)

        Returns:
            List of DuplicateDetectionResult objects
        """
        try:
            threshold = threshold or self.similarity_threshold

            # Generate embedding for content
            content_embedding = await self.generate_embedding(content)

            # Search for similar content
            similar_content = self.vector_store.search_similar(content_embedding, 20)

            duplicates = []
            for similar_id, similarity in similar_content:
                if similar_id == content_id:
                    continue

                if similarity >= threshold:
                    # Determine duplicate type
                    if similarity >= 0.95:
                        duplicate_type = "exact"
                    elif similarity >= 0.90:
                        duplicate_type = "near_exact"
                    else:
                        duplicate_type = "semantic"

                    result = DuplicateDetectionResult(
                        original_content_id=content_id,
                        duplicate_content_id=similar_id,
                        similarity_score=similarity,
                        duplicate_type=duplicate_type,
                        confidence=min(similarity * 1.2, 1.0)  # Boost confidence for high similarity
                    )
                    duplicates.append(result)

            self.logger.info(f"Found {len(duplicates)} potential duplicates for content {content_id}")
            return duplicates

        except Exception as e:
            self.logger.error(f"Failed to detect duplicates: {e}")
            raise

    async def extract_entities(self, text: str, source_id: str) -> List[KnowledgeEntity]:
        """
        Extract entities from text for knowledge graph construction.

        Args:
            text: Text to analyze
            source_id: Source identifier

        Returns:
            List of KnowledgeEntity objects
        """
        try:
            # Use LLM to extract entities
            prompt = f"""
            Extract named entities from the following text. For each entity, provide:
            - Name: The entity name
            - Type: The entity type (person, organization, location, concept, product, etc.)
            - Description: A brief description of the entity
            - Properties: Any additional properties as key-value pairs

            Format your response as a JSON array of entity objects.

            Text: {text[:2000]}  # Limit text length
            """

            # Get response from LLM
            response = await ollama_client.generate(prompt=prompt, stream=False)

            if not response or 'response' not in response:
                return []

            # Parse entities from response
            entities = []
            try:
                # Try to extract JSON from response
                response_text = response['response']
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1

                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                    entity_data = json.loads(json_str)

                    for item in entity_data:
                        if isinstance(item, dict) and 'name' in item and 'type' in item:
                            # Generate embedding for entity
                            entity_text = f"{item['name']} {item.get('description', '')}"
                            embedding = await self.generate_embedding(entity_text)

                            entity = KnowledgeEntity(
                                id=str(uuid.uuid4()),
                                name=item['name'],
                                entity_type=item['type'],
                                description=item.get('description', ''),
                                properties=item.get('properties', {}),
                                embedding=embedding,
                                confidence=self.entity_confidence_threshold
                            )

                            entities.append(entity)
                            self.entities[entity.id] = entity

            except json.JSONDecodeError:
                self.logger.warning("Failed to parse entity extraction response as JSON")

            self.logger.info(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            self.logger.error(f"Failed to extract entities: {e}")
            return []

    async def build_knowledge_graph(
        self,
        entities: List[KnowledgeEntity],
        source_text: str
    ) -> List[KnowledgeRelation]:
        """
        Build relationships between entities for knowledge graph.

        Args:
            entities: List of entities to connect
            source_text: Original text for context

        Returns:
            List of KnowledgeRelation objects
        """
        try:
            relations = []

            # Use LLM to identify relationships
            entity_names = [e.name for e in entities]
            entity_types = [e.entity_type for e in entities]

            prompt = f"""
            Based on the following text, identify relationships between these entities:
            Entities: {', '.join(entity_names)}
            Entity Types: {', '.join(entity_types)}

            For each relationship, provide:
            - Source: The source entity name
            - Target: The target entity name
            - Type: The relationship type (works_for, located_in, related_to, part_of, etc.)
            - Description: Brief description of the relationship

            Format as JSON array of relationship objects.

            Text: {source_text[:1500]}
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                try:
                    response_text = response['response']
                    json_start = response_text.find('[')
                    json_end = response_text.rfind(']') + 1

                    if json_start != -1 and json_end != -1:
                        json_str = response_text[json_start:json_end]
                        relation_data = json.loads(json_str)

                        # Create entity name to ID mapping
                        name_to_entity = {e.name: e for e in entities}

                        for item in relation_data:
                            if isinstance(item, dict):
                                source_name = item.get('source')
                                target_name = item.get('target')
                                relation_type = item.get('type', 'related_to')

                                if source_name in name_to_entity and target_name in name_to_entity:
                                    source_entity = name_to_entity[source_name]
                                    target_entity = name_to_entity[target_name]

                                    relation = KnowledgeRelation(
                                        id=str(uuid.uuid4()),
                                        source_entity_id=source_entity.id,
                                        target_entity_id=target_entity.id,
                                        relation_type=relation_type,
                                        description=item.get('description', ''),
                                        properties={},
                                        confidence=0.8
                                    )

                                    relations.append(relation)
                                    self.relations[relation.id] = relation

                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse relationship extraction response as JSON")

            self.logger.info(f"Created {len(relations)} relationships in knowledge graph")
            return relations

        except Exception as e:
            self.logger.error(f"Failed to build knowledge graph: {e}")
            return []

    async def classify_content(self, content: str, categories: List[str]) -> Dict[str, float]:
        """
        Classify content into predefined categories.

        Args:
            content: Content to classify
            categories: List of possible categories

        Returns:
            Dictionary mapping categories to confidence scores
        """
        try:
            categories_str = ', '.join(categories)

            prompt = f"""
            Classify the following content into these categories: {categories_str}

            For each category, provide a relevance score from 0.0 to 1.0.
            Return results as a JSON object with category names as keys and scores as values.

            Content: {content[:1000]}
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                try:
                    response_text = response['response']
                    # Try to extract JSON
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1

                    if json_start != -1 and json_end != -1:
                        json_str = response_text[json_start:json_end]
                        classification = json.loads(json_str)
                        return classification
                except json.JSONDecodeError:
                    pass

            # Fallback: return equal scores
            return {category: 0.5 for category in categories}

        except Exception as e:
            self.logger.error(f"Failed to classify content: {e}")
            return {category: 0.0 for category in categories}

    async def score_importance(self, content: str, context: Optional[str] = None) -> float:
        """
        Score the importance of content based on context.

        Args:
            content: Content to score
            context: Optional context for scoring

        Returns:
            Importance score from 0.0 to 1.0
        """
        try:
            context_str = f" in the context of: {context}" if context else ""

            prompt = f"""
            Rate the importance of the following content{context_str} on a scale from 0.0 to 1.0,
            where 1.0 is extremely important and 0.0 is not important at all.

            Consider factors like:
            - Uniqueness of information
            - Relevance to main topics
            - Potential impact or usefulness
            - Timeliness and recency

            Return only a single number between 0.0 and 1.0.

            Content: {content[:800]}
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                try:
                    # Extract number from response
                    response_text = response['response'].strip()
                    # Look for a number pattern
                    import re
                    numbers = re.findall(r'(\d+\.?\d*)', response_text)
                    if numbers:
                        score = float(numbers[0])
                        return max(0.0, min(1.0, score))  # Clamp to 0-1 range
                except ValueError:
                    pass

            # Default score
            return 0.5

        except Exception as e:
            self.logger.error(f"Failed to score importance: {e}")
            return 0.5

    def get_stats(self) -> Dict[str, Any]:
        """Get semantic processing service statistics."""
        return {
            "chunks": len(self.chunks),
            "entities": len(self.entities),
            "relations": len(self.relations),
            "vector_store": self.vector_store.get_stats(),
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "similarity_threshold": self.similarity_threshold
        }


# Global instance
semantic_processing_service = SemanticProcessingService()