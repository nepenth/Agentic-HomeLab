"""
Content Processing Pipeline Framework.

This service provides a pluggable pipeline framework for processing content through
multiple stages including validation, transformation, enrichment, and storage.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum
import asyncio

from app.services.content_validation_service import content_validation_service
from app.utils.logging import get_logger

logger = get_logger("content_processing_pipeline")


class ProcessingStage(Enum):
    """Stages in the content processing pipeline."""
    VALIDATION = "validation"
    SANITIZATION = "sanitization"
    EXTRACTION = "extraction"
    ENRICHMENT = "enrichment"
    TRANSFORMATION = "transformation"
    STORAGE = "storage"
    INDEXING = "indexing"


class PipelineResult:
    """Result of pipeline processing."""

    def __init__(self):
        self.success = True
        self.stage_results = {}
        self.errors = []
        self.warnings = []
        self.metadata = {}
        self.processing_time = {}
        self.final_content = None

    def add_stage_result(self, stage: ProcessingStage, success: bool,
                        result: Any = None, error: str = None):
        """Add result for a processing stage."""
        self.stage_results[stage.value] = {
            'success': success,
            'result': result,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }

        if not success and error:
            self.errors.append(f"{stage.value}: {error}")
            self.success = False

    def add_metadata(self, key: str, value: Any):
        """Add metadata to the result."""
        self.metadata[key] = value

    def get_stage_result(self, stage: ProcessingStage) -> Optional[Dict[str, Any]]:
        """Get result for a specific stage."""
        return self.stage_results.get(stage.value)


class PipelineProcessor(ABC):
    """Abstract base class for pipeline processors."""

    @abstractmethod
    async def process(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process content in this pipeline stage.

        Args:
            content: Content to process
            context: Processing context with metadata

        Returns:
            Processing result
        """
        pass

    @property
    @abstractmethod
    def stage(self) -> ProcessingStage:
        """Get the processing stage this processor handles."""
        pass

    def can_process(self, content_type: str, context: Dict[str, Any]) -> bool:
        """Check if this processor can handle the given content type."""
        return True


class ValidationProcessor(PipelineProcessor):
    """Content validation processor."""

    @property
    def stage(self) -> ProcessingStage:
        return ProcessingStage.VALIDATION

    async def process(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate content."""
        try:
            if not isinstance(content, bytes):
                return {'success': False, 'error': 'Content must be bytes for validation'}

            content_type = context.get('content_type', 'unknown')
            filename = context.get('filename')

            validation_result = await content_validation_service.validate_content(
                content, content_type, filename, context.get('metadata', {})
            )

            return {
                'success': validation_result['is_valid'],
                'validation_result': validation_result,
                'warnings': validation_result.get('warnings', []),
                'errors': validation_result.get('errors', [])
            }

        except Exception as e:
            logger.error(f"Validation processing failed: {e}")
            return {'success': False, 'error': str(e)}


class SanitizationProcessor(PipelineProcessor):
    """Content sanitization processor."""

    @property
    def stage(self) -> ProcessingStage:
        return ProcessingStage.SANITIZATION

    async def process(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize content."""
        try:
            if not isinstance(content, bytes):
                return {'success': False, 'error': 'Content must be bytes for sanitization'}

            content_type = context.get('content_type', 'unknown')

            # Use the validation service's sanitization method
            sanitized_content, was_sanitized = content_validation_service._sanitize_content(
                content, content_type
            )

            return {
                'success': True,
                'sanitized_content': sanitized_content,
                'was_sanitized': was_sanitized,
                'original_size': len(content),
                'sanitized_size': len(sanitized_content)
            }

        except Exception as e:
            logger.error(f"Sanitization processing failed: {e}")
            return {'success': False, 'error': str(e)}


class ExtractionProcessor(PipelineProcessor):
    """Content extraction processor."""

    @property
    def stage(self) -> ProcessingStage:
        return ProcessingStage.EXTRACTION

    async def process(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from content."""
        try:
            content_type = context.get('content_type', 'unknown')

            if content_type == 'text':
                return await self._extract_text_features(content, context)
            elif content_type == 'document':
                return await self._extract_document_features(content, context)
            else:
                return {'success': True, 'extracted_data': {}}

        except Exception as e:
            logger.error(f"Extraction processing failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _extract_text_features(self, content: bytes, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from text content."""
        try:
            text = content.decode('utf-8')

            # Basic text analytics
            features = {
                'word_count': len(text.split()),
                'character_count': len(text),
                'line_count': len(text.split('\n')),
                'sentence_count': len([s for s in text.split('.') if s.strip()]),
                'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
                'language': self._detect_language(text),
                'readability_score': self._calculate_readability(text)
            }

            return {'success': True, 'extracted_data': features}

        except Exception as e:
            return {'success': False, 'error': f"Text feature extraction failed: {str(e)}"}

    async def _extract_document_features(self, content: bytes, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from document content."""
        try:
            # Basic document structure analysis
            features = {
                'has_tables': b'<table' in content or b'<td' in content,
                'has_images': b'<img' in content,
                'has_links': b'<a href' in content,
                'page_count': 1,  # Would need proper PDF parsing
                'word_count': 0,  # Would need text extraction
            }

            return {'success': True, 'extracted_data': features}

        except Exception as e:
            return {'success': False, 'error': f"Document feature extraction failed: {str(e)}"}

    def _detect_language(self, text: str) -> str:
        """Simple language detection (placeholder)."""
        # This would use a proper language detection library
        return "en"

    def _calculate_readability(self, text: str) -> float:
        """Calculate basic readability score (placeholder)."""
        # This would use a proper readability algorithm
        return 0.0


class EnrichmentProcessor(PipelineProcessor):
    """Content enrichment processor."""

    @property
    def stage(self) -> ProcessingStage:
        return ProcessingStage.ENRICHMENT

    async def process(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich content with additional metadata."""
        try:
            enrichment_data = {}

            # Add timestamps
            enrichment_data['processed_at'] = datetime.now().isoformat()
            enrichment_data['content_hash'] = self._calculate_hash(content)

            # Add quality metrics
            if isinstance(content, bytes):
                enrichment_data['size_bytes'] = len(content)
                enrichment_data['compression_ratio'] = self._estimate_compression_ratio(content)

            # Add source information
            if 'source' in context:
                enrichment_data['source_info'] = context['source']

            return {'success': True, 'enrichment_data': enrichment_data}

        except Exception as e:
            logger.error(f"Enrichment processing failed: {e}")
            return {'success': False, 'error': str(e)}

    def _calculate_hash(self, content: Any) -> str:
        """Calculate content hash."""
        import hashlib
        if isinstance(content, bytes):
            return hashlib.sha256(content).hexdigest()
        elif isinstance(content, str):
            return hashlib.sha256(content.encode()).hexdigest()
        else:
            return hashlib.sha256(str(content).encode()).hexdigest()

    def _estimate_compression_ratio(self, content: bytes) -> float:
        """Estimate compression ratio (placeholder)."""
        # This would analyze the content for compressibility
        return 1.0


class ContentProcessingPipeline:
    """Main content processing pipeline."""

    def __init__(self):
        self.processors: Dict[ProcessingStage, List[PipelineProcessor]] = {}
        self.logger = get_logger("content_pipeline")

        # Register default processors
        self.register_processor(ValidationProcessor())
        self.register_processor(SanitizationProcessor())
        self.register_processor(ExtractionProcessor())
        self.register_processor(EnrichmentProcessor())

    def register_processor(self, processor: PipelineProcessor):
        """Register a processor for a specific stage."""
        stage = processor.stage
        if stage not in self.processors:
            self.processors[stage] = []

        self.processors[stage].append(processor)
        self.logger.info(f"Registered processor for stage: {stage.value}")

    def unregister_processor(self, processor: PipelineProcessor):
        """Unregister a processor."""
        stage = processor.stage
        if stage in self.processors and processor in self.processors[stage]:
            self.processors[stage].remove(processor)
            self.logger.info(f"Unregistered processor from stage: {stage.value}")

    async def process_content(
        self,
        content: Any,
        context: Dict[str, Any],
        stages: Optional[List[ProcessingStage]] = None
    ) -> PipelineResult:
        """
        Process content through the pipeline.

        Args:
            content: Content to process
            context: Processing context
            stages: Specific stages to run (None for all stages)

        Returns:
            PipelineResult with processing results
        """
        result = PipelineResult()
        current_content = content

        # Determine which stages to run
        if stages is None:
            stages = list(ProcessingStage)

        start_time = datetime.now()

        for stage in stages:
            if stage not in self.processors:
                self.logger.warning(f"No processors registered for stage: {stage.value}")
                continue

            stage_start = datetime.now()

            # Run all processors for this stage
            stage_results = []
            for processor in self.processors[stage]:
                if processor.can_process(context.get('content_type', 'unknown'), context):
                    try:
                        proc_result = await processor.process(current_content, context)
                        stage_results.append(proc_result)

                        # Update content if processor modified it
                        if 'sanitized_content' in proc_result:
                            current_content = proc_result['sanitized_content']

                    except Exception as e:
                        self.logger.error(f"Processor {processor.__class__.__name__} failed: {e}")
                        stage_results.append({'success': False, 'error': str(e)})

            # Aggregate stage results
            stage_success = all(r.get('success', False) for r in stage_results)
            result.add_stage_result(stage, stage_success, stage_results)

            # Track processing time
            stage_time = (datetime.now() - stage_start).total_seconds()
            result.processing_time[stage.value] = stage_time

            # Stop processing if validation failed
            if stage == ProcessingStage.VALIDATION and not stage_success:
                result.success = False
                break

        # Store final content
        result.final_content = current_content

        # Add overall processing time
        total_time = (datetime.now() - start_time).total_seconds()
        result.add_metadata('total_processing_time', total_time)
        result.add_metadata('stages_processed', len(stages))

        self.logger.info(f"Pipeline processing completed: success={result.success}, time={total_time:.2f}s")
        return result

    def get_available_stages(self) -> List[str]:
        """Get list of available processing stages."""
        return [stage.value for stage in self.processors.keys()]

    def get_stage_processors(self, stage: ProcessingStage) -> List[str]:
        """Get list of processors for a specific stage."""
        if stage not in self.processors:
            return []

        return [processor.__class__.__name__ for processor in self.processors[stage]]


# Global pipeline instance
content_processing_pipeline = ContentProcessingPipeline()