"""
Relationship Extraction Service for entity linking and knowledge graph construction.

This service provides advanced relationship extraction capabilities including:
- Named Entity Recognition (NER)
- Entity linking and disambiguation
- Relationship extraction between entities
- Knowledge graph construction
- Semantic relationship analysis
- Entity co-occurrence analysis
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from app.config import settings
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("relationship_extraction_service")


class RelationshipExtractionError(Exception):
    """Raised when relationship extraction fails."""
    pass


class Entity:
    """Represents an extracted entity."""

    def __init__(
        self,
        entity_id: str,
        text: str,
        entity_type: str,
        start_pos: int,
        end_pos: int,
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None
    ):
        self.entity_id = entity_id
        self.text = text
        self.entity_type = entity_type
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "entity_id": self.entity_id,
            "text": self.text,
            "entity_type": self.entity_type,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class Relationship:
    """Represents a relationship between entities."""

    def __init__(
        self,
        source_entity: str,
        target_entity: str,
        relationship_type: str,
        confidence: float = 1.0,
        context: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.source_entity = source_entity
        self.target_entity = target_entity
        self.relationship_type = relationship_type
        self.confidence = confidence
        self.context = context
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "context": self.context,
            "metadata": self.metadata
        }


class KnowledgeGraph:
    """Represents a knowledge graph of entities and relationships."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.entity_types: Set[str] = set()
        self.relationship_types: Set[str] = set()

    def add_entity(self, entity: Entity):
        """Add an entity to the graph."""
        self.entities[entity.entity_id] = entity
        self.entity_types.add(entity.entity_type)

    def add_relationship(self, relationship: Relationship):
        """Add a relationship to the graph."""
        self.relationships.append(relationship)
        self.relationship_types.add(relationship.relationship_type)

    def get_entity_by_text(self, text: str) -> Optional[Entity]:
        """Get entity by text content."""
        for entity in self.entities.values():
            if entity.text == text:
                return entity
        return None

    def get_relationships_for_entity(self, entity_id: str) -> List[Relationship]:
        """Get all relationships for a specific entity."""
        return [
            rel for rel in self.relationships
            if rel.source_entity == entity_id or rel.target_entity == entity_id
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge graph to dictionary."""
        return {
            "entities": {eid: entity.to_dict() for eid, entity in self.entities.items()},
            "relationships": [rel.to_dict() for rel in self.relationships],
            "entity_types": list(self.entity_types),
            "relationship_types": list(self.relationship_types),
            "stats": {
                "entity_count": len(self.entities),
                "relationship_count": len(self.relationships),
                "entity_type_count": len(self.entity_types),
                "relationship_type_count": len(self.relationship_types)
            }
        }


class RelationshipExtractionResult:
    """Result of relationship extraction processing."""

    def __init__(
        self,
        content_id: str,
        entities: List[Entity] = None,
        relationships: List[Relationship] = None,
        knowledge_graph: KnowledgeGraph = None,
        entity_cooccurrences: Dict[str, List[str]] = None,
        processing_time_ms: float = None,
        model_used: str = None,
        metadata: Dict[str, Any] = None
    ):
        self.content_id = content_id
        self.entities = entities or []
        self.relationships = relationships or []
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.entity_cooccurrences = entity_cooccurrences or {}
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "content_id": self.content_id,
            "entities": [entity.to_dict() for entity in self.entities],
            "relationships": [rel.to_dict() for rel in self.relationships],
            "knowledge_graph": self.knowledge_graph.to_dict(),
            "entity_cooccurrences": self.entity_cooccurrences,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class RelationshipExtractionService:
    """Service for extracting relationships and building knowledge graphs."""

    def __init__(self):
        self.default_model = getattr(settings, 'relationship_extraction_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'relationship_extraction_timeout_seconds', 90)

        # Entity types for NER
        self.entity_types = [
            "PERSON", "ORGANIZATION", "LOCATION", "DATE", "TIME", "MONEY",
            "PERCENT", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE",
            "NORP", "FACILITY", "GPE", "MISC"
        ]

        # Relationship types
        self.relationship_types = [
            "works_for", "located_in", "part_of", "related_to", "causes",
            "affects", "owns", "created", "participates_in", "collaborates_with",
            "competes_with", "succeeds", "precedes", "contains", "belongs_to"
        ]

    async def extract_relationships(
        self,
        content_data: Dict[str, Any],
        extraction_types: List[str] = None,
        **kwargs
    ) -> RelationshipExtractionResult:
        """
        Extract relationships and build knowledge graph from content.

        Args:
            content_data: Content data dictionary
            extraction_types: Types of extraction to perform
            **kwargs: Additional extraction options

        Returns:
            RelationshipExtractionResult with entities and relationships
        """
        start_time = datetime.now()
        content_id = content_data.get('content_id', 'unknown')

        try:
            # Determine extraction types
            extraction_types = extraction_types or [
                'entities', 'relationships', 'knowledge_graph'
            ]

            # Extract content text
            content_text = self._extract_content_text(content_data)

            if not content_text:
                raise RelationshipExtractionError("No analyzable content found")

            # Perform extractions
            result = RelationshipExtractionResult(content_id=content_id)

            if 'entities' in extraction_types:
                result.entities = await self._extract_entities(content_text, **kwargs)

            if 'relationships' in extraction_types and result.entities:
                result.relationships = await self._extract_relationships(
                    content_text, result.entities, **kwargs
                )

            if 'knowledge_graph' in extraction_types:
                result.knowledge_graph = await self._build_knowledge_graph(
                    result.entities, result.relationships, **kwargs
                )

            if 'cooccurrences' in extraction_types and result.entities:
                result.entity_cooccurrences = await self._analyze_cooccurrences(
                    content_text, result.entities, **kwargs
                )

            # Set processing metadata
            result.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.model_used = self.default_model

            logger.info(f"Relationship extraction completed for {content_id} in {result.processing_time_ms:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            raise RelationshipExtractionError(f"Relationship extraction failed: {str(e)}")

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
                text_parts.append(f"Visual description: {vision['caption']}")

        # Extract from audio results
        if 'audio_result' in content_data:
            audio = content_data['audio_result']
            if isinstance(audio, dict) and 'transcription' in audio:
                text_parts.append(f"Audio transcription: {audio['transcription']}")

        return " ".join(text_parts).strip()

    async def _extract_entities(self, content_text: str, **kwargs) -> List[Entity]:
        """Extract named entities from text."""
        try:
            max_entities = kwargs.get('max_entities', 20)

            entities_prompt = f"""
Extract named entities from this text. Identify people, organizations, locations, dates, and other proper nouns.

Text: {content_text[:1500]}...

For each entity, provide:
- text: The entity text exactly as it appears
- entity_type: The type of entity (PERSON, ORGANIZATION, LOCATION, DATE, etc.)
- start_pos: Approximate starting position in the text
- end_pos: Approximate ending position in the text
- confidence: Confidence score (0.0 to 1.0)

Format as JSON array of entity objects.
Limit to {max_entities} most important entities.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=entities_prompt,
                system="You are an expert at Named Entity Recognition (NER). Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.2),
                    "num_predict": kwargs.get('max_tokens', 600)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                entities_data = json.loads(result_text)
                if isinstance(entities_data, list):
                    entities = []
                    for i, entity_data in enumerate(entities_data):
                        if isinstance(entity_data, dict) and 'text' in entity_data:
                            entity = Entity(
                                entity_id=f"entity_{i}",
                                text=entity_data.get('text', ''),
                                entity_type=entity_data.get('entity_type', 'MISC'),
                                start_pos=entity_data.get('start_pos', 0),
                                end_pos=entity_data.get('end_pos', 0),
                                confidence=min(1.0, max(0.0, entity_data.get('confidence', 0.8)))
                            )
                            entities.append(entity)
                    return entities[:max_entities]
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse entities JSON: {result_text}")
                return []

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    async def _extract_relationships(
        self,
        content_text: str,
        entities: List[Entity],
        **kwargs
    ) -> List[Relationship]:
        """Extract relationships between entities."""
        try:
            max_relationships = kwargs.get('max_relationships', 15)

            # Create entity mapping for reference
            entity_map = {entity.entity_id: entity for entity in entities}

            relationships_prompt = f"""
Analyze the relationships between these entities in the text:

Text: {content_text[:1000]}...

Entities:
{chr(10).join([f"- {entity.entity_id}: {entity.text} ({entity.entity_type})" for entity in entities])}

Identify relationships between entities. For each relationship, provide:
- source_entity: ID of the source entity
- target_entity: ID of the target entity
- relationship_type: Type of relationship (works_for, located_in, part_of, related_to, etc.)
- confidence: Confidence score (0.0 to 1.0)
- context: Brief explanation of the relationship

Format as JSON array of relationship objects.
Limit to {max_relationships} most important relationships.
"""

            response = await ollama_client.generate(
                model=self.default_model,
                prompt=relationships_prompt,
                system="You are an expert at relationship extraction and knowledge graph construction. Always respond with valid JSON.",
                format="json",
                options={
                    "temperature": kwargs.get('temperature', 0.3),
                    "num_predict": kwargs.get('max_tokens', 800)
                }
            )

            result_text = response.get('response', '').strip()

            try:
                relationships_data = json.loads(result_text)
                if isinstance(relationships_data, list):
                    relationships = []
                    for rel_data in relationships_data:
                        if isinstance(rel_data, dict) and 'source_entity' in rel_data and 'target_entity' in rel_data:
                            # Validate entity IDs exist
                            source_id = rel_data.get('source_entity')
                            target_id = rel_data.get('target_entity')

                            if source_id in entity_map and target_id in entity_map:
                                relationship = Relationship(
                                    source_entity=source_id,
                                    target_entity=target_id,
                                    relationship_type=rel_data.get('relationship_type', 'related_to'),
                                    confidence=min(1.0, max(0.0, rel_data.get('confidence', 0.7))),
                                    context=rel_data.get('context', '')
                                )
                                relationships.append(relationship)
                    return relationships[:max_relationships]
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse relationships JSON: {result_text}")
                return []

        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")
            return []

    async def _build_knowledge_graph(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        **kwargs
    ) -> KnowledgeGraph:
        """Build a knowledge graph from entities and relationships."""
        try:
            knowledge_graph = KnowledgeGraph()

            # Add entities to graph
            for entity in entities:
                knowledge_graph.add_entity(entity)

            # Add relationships to graph
            for relationship in relationships:
                knowledge_graph.add_relationship(relationship)

            # Enhance graph with additional analysis if requested
            if kwargs.get('enhance_graph', True):
                enhanced_graph = await self._enhance_knowledge_graph(
                    knowledge_graph, **kwargs
                )
                return enhanced_graph

            return knowledge_graph

        except Exception as e:
            logger.error(f"Knowledge graph construction failed: {e}")
            return KnowledgeGraph()

    async def _enhance_knowledge_graph(
        self,
        knowledge_graph: KnowledgeGraph,
        **kwargs
    ) -> KnowledgeGraph:
        """Enhance knowledge graph with additional analysis."""
        try:
            # Find missing relationships
            missing_relationships = await self._find_missing_relationships(
                knowledge_graph, **kwargs
            )

            # Add missing relationships
            for rel in missing_relationships:
                knowledge_graph.add_relationship(rel)

            # Validate graph consistency
            await self._validate_graph_consistency(knowledge_graph, **kwargs)

            return knowledge_graph

        except Exception as e:
            logger.error(f"Knowledge graph enhancement failed: {e}")
            return knowledge_graph

    async def _find_missing_relationships(
        self,
        knowledge_graph: KnowledgeGraph,
        **kwargs
    ) -> List[Relationship]:
        """Find potentially missing relationships in the knowledge graph."""
        try:
            # Simple heuristic: connect entities of related types
            missing_relationships = []

            entities_list = list(knowledge_graph.entities.values())

            for i, entity1 in enumerate(entities_list):
                for j, entity2 in enumerate(entities_list[i+1:], i+1):
                    # Check for potential relationships based on entity types
                    if self._should_connect_entities(entity1, entity2):
                        relationship = Relationship(
                            source_entity=entity1.entity_id,
                            target_entity=entity2.entity_id,
                            relationship_type="related_to",
                            confidence=0.3,  # Low confidence for inferred relationships
                            context="Inferred relationship based on entity types"
                        )
                        missing_relationships.append(relationship)

            return missing_relationships[:kwargs.get('max_missing_relationships', 5)]

        except Exception as e:
            logger.error(f"Finding missing relationships failed: {e}")
            return []

    def _should_connect_entities(self, entity1: Entity, entity2: Entity) -> bool:
        """Determine if two entities should potentially be connected."""
        # Simple rules for entity connection
        type_combinations = [
            ("PERSON", "ORGANIZATION"),
            ("PERSON", "LOCATION"),
            ("ORGANIZATION", "LOCATION"),
            ("PERSON", "PERSON"),
            ("ORGANIZATION", "ORGANIZATION")
        ]

        entity_types = (entity1.entity_type, entity2.entity_type)
        return entity_types in type_combinations or entity_types[::-1] in type_combinations

    async def _validate_graph_consistency(
        self,
        knowledge_graph: KnowledgeGraph,
        **kwargs
    ) -> None:
        """Validate and improve knowledge graph consistency."""
        try:
            # Check for duplicate entities
            text_to_entities = defaultdict(list)
            for entity in knowledge_graph.entities.values():
                text_to_entities[entity.text.lower()].append(entity)

            # Merge duplicate entities
            for text, entities in text_to_entities.items():
                if len(entities) > 1:
                    # Keep the entity with highest confidence
                    entities.sort(key=lambda e: e.confidence, reverse=True)
                    primary_entity = entities[0]

                    # Update relationships to point to primary entity
                    for entity in entities[1:]:
                        # Update relationships
                        for rel in knowledge_graph.relationships:
                            if rel.source_entity == entity.entity_id:
                                rel.source_entity = primary_entity.entity_id
                            if rel.target_entity == entity.entity_id:
                                rel.target_entity = primary_entity.entity_id

                        # Remove duplicate entity
                        del knowledge_graph.entities[entity.entity_id]

        except Exception as e:
            logger.error(f"Graph consistency validation failed: {e}")

    async def _analyze_cooccurrences(
        self,
        content_text: str,
        entities: List[Entity],
        **kwargs
    ) -> Dict[str, List[str]]:
        """Analyze entity co-occurrences in the text."""
        try:
            cooccurrences = defaultdict(list)

            # Simple co-occurrence analysis based on proximity
            entity_positions = {}
            for entity in entities:
                entity_positions[entity.entity_id] = (entity.start_pos, entity.end_pos)

            # Find co-occurring entities within a window
            window_size = kwargs.get('cooccurrence_window', 100)  # characters

            for i, entity1 in enumerate(entities):
                for j, entity2 in enumerate(entities[i+1:], i+1):
                    pos1 = entity_positions[entity1.entity_id]
                    pos2 = entity_positions[entity2.entity_id]

                    # Check if entities are within window
                    if abs(pos1[0] - pos2[0]) <= window_size:
                        cooccurrences[entity1.entity_id].append(entity2.entity_id)
                        cooccurrences[entity2.entity_id].append(entity1.entity_id)

            return dict(cooccurrences)

        except Exception as e:
            logger.error(f"Co-occurrence analysis failed: {e}")
            return {}

    async def batch_extract_relationships(
        self,
        content_batch: List[Dict[str, Any]],
        extraction_types: List[str] = None,
        max_concurrent: int = 2
    ) -> List[RelationshipExtractionResult]:
        """
        Extract relationships from multiple content items in batch.

        Args:
            content_batch: List of content data dictionaries
            extraction_types: Types of extraction to perform
            max_concurrent: Maximum concurrent extraction tasks

        Returns:
            List of RelationshipExtractionResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_single_item(content_data: Dict[str, Any]) -> RelationshipExtractionResult:
            async with semaphore:
                return await self.extract_relationships(
                    content_data,
                    extraction_types=extraction_types
                )

        tasks = [extract_single_item(item) for item in content_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch extraction failed for item {i}: {result}")
                # Create error result
                error_result = RelationshipExtractionResult(
                    content_id=content_batch[i].get('content_id', f'batch_item_{i}'),
                    metadata={"error": str(result)}
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    def get_supported_entity_types(self) -> List[str]:
        """Get list of supported entity types."""
        return self.entity_types.copy()

    def get_supported_relationship_types(self) -> List[str]:
        """Get list of supported relationship types."""
        return self.relationship_types.copy()

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the relationship extraction service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            return {
                "service": "relationship_extraction",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "supported_entity_types": self.get_supported_entity_types(),
                "supported_relationship_types": self.get_supported_relationship_types(),
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "relationship_extraction",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
relationship_extraction_service = RelationshipExtractionService()