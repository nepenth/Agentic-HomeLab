"""
Database models for content items and processing results.

This module defines the database schema for storing content items discovered
through various connectors and their processing results.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

# Import VECTOR type from pgvector if available, otherwise use a fallback
try:
    from pgvector.sqlalchemy import Vector
    VECTOR = Vector
except ImportError:
    # Fallback for systems without pgvector extension
    from sqlalchemy import String as VECTOR

from app.db.database import Base


class ContentItem(Base):
    """Model for storing discovered content items."""
    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(500), nullable=False, index=True)  # Original source identifier
    source_type = Column(String(100), nullable=False, index=True)  # 'rss', 'twitter', 'email', etc.
    connector_type = Column(String(100), nullable=False)  # Type of connector used
    content_type = Column(String(50), nullable=False)  # 'text', 'image', 'audio', 'video', 'structured'

    # Content metadata
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    author = Column(String(500), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    discovered_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Content location and storage
    original_url = Column(Text, nullable=True)
    cached_path = Column(Text, nullable=True)  # Local path if cached
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(200), nullable=True)

    # Content quality and processing status
    quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    processing_status = Column(String(50), default="discovered")  # discovered, processing, processed, failed
    last_processed_at = Column(DateTime, nullable=True)

    # Flexible metadata storage
    content_metadata = Column(JSONB, nullable=True)  # Additional metadata as JSON
    tags = Column(JSONB, nullable=True)  # Tags as JSON array
    custom_fields = Column(JSONB, nullable=True)  # Custom fields as JSON

    # Relationships
    processing_results = relationship("ContentProcessingResult", back_populates="content_item", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_content_items_source_type_published', 'source_type', 'published_at'),
        Index('idx_content_items_content_type_status', 'content_type', 'processing_status'),
        Index('idx_content_items_discovered_at', 'discovered_at'),
        Index('idx_content_items_quality_score', 'quality_score'),
    )

    def __repr__(self):
        return f"<ContentItem(id={self.id}, source_type={self.source_type}, title={self.title[:50] if self.title else None})>"


class ContentProcessingResult(Base):
    """Model for storing content processing results."""
    __tablename__ = "content_processing_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=False, index=True)

    # Processing metadata
    processing_type = Column(String(100), nullable=False)  # 'text_analysis', 'image_processing', etc.
    operation = Column(String(100), nullable=False)  # 'summarize', 'extract_entities', etc.
    processor_version = Column(String(50), nullable=True)
    processing_started_at = Column(DateTime, default=func.now(), nullable=False)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)

    # Processing results
    success = Column(Boolean, default=True, nullable=False)
    result_data = Column(JSONB, nullable=True)  # Main processing results as JSON
    error_message = Column(Text, nullable=True)
    warning_messages = Column(JSONB, nullable=True)  # Array of warning messages

    # Model usage tracking (for AI processing)
    model_used = Column(String(200), nullable=True)
    model_version = Column(String(50), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_cost = Column(Float, nullable=True)  # Cost in USD or tokens

    # Quality metrics
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    accuracy_score = Column(Float, nullable=True)  # 0.0 to 1.0

    # Additional metadata
    processing_metadata = Column(JSONB, nullable=True)  # Additional processing metadata
    custom_metrics = Column(JSONB, nullable=True)  # Custom metrics as JSON

    # Relationships
    content_item = relationship("ContentItem", back_populates="processing_results")

    # Indexes for performance
    __table_args__ = (
        Index('idx_processing_results_content_operation', 'content_item_id', 'operation'),
        Index('idx_processing_results_type_success', 'processing_type', 'success'),
        Index('idx_processing_results_started_at', 'processing_started_at'),
        Index('idx_processing_results_model_used', 'model_used'),
    )

    def __repr__(self):
        return f"<ContentProcessingResult(id={self.id}, operation={self.operation}, success={self.success})>"


class ContentEmbedding(Base):
    """Model for storing content embeddings for semantic search."""
    __tablename__ = "content_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=False, index=True)
    processing_result_id = Column(UUID(as_uuid=True), ForeignKey('content_processing_results.id'), nullable=True, index=True)

    # Embedding metadata
    embedding_model = Column(String(200), nullable=False)  # Model used to generate embedding
    embedding_version = Column(String(50), nullable=True)
    embedding_dimensions = Column(Integer, nullable=False)

    # The actual embedding vector
    embedding_vector = Column(VECTOR, nullable=False)  # Vector type for embeddings

    # Content chunk information (for large content)
    content_chunk = Column(Text, nullable=True)  # The actual text chunk
    chunk_index = Column(Integer, nullable=True)  # Index of chunk in original content
    total_chunks = Column(Integer, nullable=True)  # Total number of chunks

    # Generation metadata
    generated_at = Column(DateTime, default=func.now(), nullable=False)
    generation_duration_ms = Column(Integer, nullable=True)

    # Quality and validation
    embedding_quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    validation_status = Column(String(50), default="valid")  # valid, invalid, pending

    # Additional metadata
    embedding_metadata = Column(JSONB, nullable=True)

    # Relationships
    content_item = relationship("ContentItem")
    processing_result = relationship("ContentProcessingResult")

    # Indexes for performance
    __table_args__ = (
        Index('idx_embeddings_content_model', 'content_item_id', 'embedding_model'),
        Index('idx_embeddings_generated_at', 'generated_at'),
        Index('idx_embeddings_vector', 'embedding_vector'),  # For vector similarity search
    )

    def __repr__(self):
        return f"<ContentEmbedding(id={self.id}, model={self.embedding_model}, dimensions={self.embedding_dimensions})>"


class ContentSource(Base):
    """Model for storing content source configurations."""
    __tablename__ = "content_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    source_type = Column(String(100), nullable=False, index=True)  # 'rss', 'twitter', 'email', etc.
    connector_type = Column(String(100), nullable=False)

    # Source configuration
    config = Column(JSONB, nullable=False)  # Connector configuration as JSON
    credentials = Column(JSONB, nullable=True)  # Encrypted credentials if needed

    # Source status and monitoring
    is_active = Column(Boolean, default=True, nullable=False)
    last_discovery_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Discovery statistics
    total_items_discovered = Column(Integer, default=0, nullable=False)
    total_items_processed = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, nullable=True)  # 0.0 to 1.0

    # Scheduling
    discovery_interval_minutes = Column(Integer, default=60, nullable=False)
    next_discovery_at = Column(DateTime, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_content_sources_active_type', 'is_active', 'source_type'),
        Index('idx_content_sources_next_discovery', 'next_discovery_at'),
        Index('idx_content_sources_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ContentSource(id={self.id}, name={self.name}, type={self.source_type}, active={self.is_active})>"


class ContentBatch(Base):
    """Model for tracking content processing batches."""
    __tablename__ = "content_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_name = Column(String(200), nullable=True)
    batch_type = Column(String(100), nullable=False)  # 'discovery', 'processing', 'embedding'

    # Batch status
    status = Column(String(50), default="pending")  # pending, running, completed, failed, cancelled
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_duration_ms = Column(Integer, nullable=True)

    # Batch configuration
    config = Column(JSONB, nullable=True)  # Batch processing configuration
    source_ids = Column(JSONB, nullable=True)  # List of source IDs for discovery batches

    # Statistics
    total_items = Column(Integer, default=0, nullable=False)
    processed_items = Column(Integer, default=0, nullable=False)
    successful_items = Column(Integer, default=0, nullable=False)
    failed_items = Column(Integer, default=0, nullable=False)

    # Error tracking
    error_messages = Column(JSONB, nullable=True)  # Array of error messages
    warning_messages = Column(JSONB, nullable=True)  # Array of warning messages

    # Metadata
    created_by = Column(String(200), nullable=True)  # User or system that created the batch
    priority = Column(Integer, default=0, nullable=False)  # 0=low, 1=normal, 2=high, 3=critical
    batch_metadata = Column(JSONB, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_content_batches_status_started', 'status', 'started_at'),
        Index('idx_content_batches_type_status', 'batch_type', 'status'),
        Index('idx_content_batches_priority_status', 'priority', 'status'),
    )

    def __repr__(self):
        return f"<ContentBatch(id={self.id}, type={self.batch_type}, status={self.status}, items={self.total_items})>"


class ContentBatchItem(Base):
    """Model for tracking individual items within a batch."""
    __tablename__ = "content_batch_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('content_batches.id'), nullable=False, index=True)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=True, index=True)

    # Item information
    item_identifier = Column(String(500), nullable=False)  # URL, file path, or other identifier
    item_type = Column(String(50), nullable=False)  # 'url', 'file_path', 'api_endpoint', etc.

    # Processing status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed, skipped
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)

    # Results
    success = Column(Boolean, nullable=True)
    result_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    warning_message = Column(Text, nullable=True)

    # Ordering within batch
    item_order = Column(Integer, nullable=False)

    # Metadata
    item_metadata = Column(JSONB, nullable=True)

    # Relationships
    batch = relationship("ContentBatch")
    content_item = relationship("ContentItem")

    # Indexes for performance
    __table_args__ = (
        Index('idx_batch_items_batch_status', 'batch_id', 'status'),
        Index('idx_batch_items_content_status', 'content_item_id', 'status'),
        Index('idx_batch_items_order', 'batch_id', 'item_order'),
    )

    def __repr__(self):
        return f"<ContentBatchItem(id={self.id}, batch_id={self.batch_id}, status={self.status})>"


class ContentCache(Base):
    """Model for tracking cached content."""
    __tablename__ = "content_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=False, index=True)

    # Cache metadata
    cache_key = Column(String(500), nullable=False, unique=True, index=True)
    cache_type = Column(String(50), nullable=False)  # 'file', 'metadata', 'processed_data'
    file_path = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    # Cache lifecycle
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    # Cache status
    is_valid = Column(Boolean, default=True, nullable=False)
    compression_type = Column(String(50), nullable=True)  # 'gzip', 'brotli', etc.
    checksum = Column(String(128), nullable=True)  # SHA256 or similar

    # Metadata
    cache_metadata = Column(JSONB, nullable=True)

    # Relationships
    content_item = relationship("ContentItem")

    # Indexes for performance
    __table_args__ = (
        Index('idx_content_cache_expires', 'expires_at'),
        Index('idx_content_cache_accessed', 'last_accessed_at'),
        Index('idx_content_cache_valid_type', 'is_valid', 'cache_type'),
    )

    def __repr__(self):
        return f"<ContentCache(id={self.id}, key={self.cache_key[:50]}, type={self.cache_type})>"


class ContentAnalytics(Base):
    """Model for storing content analytics and insights."""
    __tablename__ = "content_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=False, index=True)

    # Analytics type and period
    analytics_type = Column(String(100), nullable=False)  # 'popularity', 'engagement', 'quality', 'usage'
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Metrics
    view_count = Column(Integer, default=0, nullable=False)
    processing_count = Column(Integer, default=0, nullable=False)
    search_hit_count = Column(Integer, default=0, nullable=False)
    share_count = Column(Integer, default=0, nullable=False)

    # Quality and engagement scores
    quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    engagement_score = Column(Float, nullable=True)  # 0.0 to 1.0
    relevance_score = Column(Float, nullable=True)  # 0.0 to 1.0

    # Additional metrics as JSON
    custom_metrics = Column(JSONB, nullable=True)

    # Metadata
    calculated_at = Column(DateTime, default=func.now(), nullable=False)
    data_source = Column(String(200), nullable=True)  # Source of analytics data
    analytics_metadata = Column(JSONB, nullable=True)

    # Relationships
    content_item = relationship("ContentItem")

    # Indexes for performance
    __table_args__ = (
        Index('idx_content_analytics_type_period', 'analytics_type', 'period_start', 'period_end'),
        Index('idx_content_analytics_calculated', 'calculated_at'),
        Index('idx_content_analytics_quality', 'quality_score'),
    )

    def __repr__(self):
        return f"<ContentAnalytics(id={self.id}, type={self.analytics_type}, quality={self.quality_score})>"


class UserInteraction(Base):
    """Model for tracking user interactions with content."""
    __tablename__ = "user_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=False, index=True)

    # Interaction details
    interaction_type = Column(String(50), nullable=False)  # view, like, share, bookmark, comment, click, dismiss, skip
    content_type = Column(String(50), nullable=True)  # Cached for performance
    source_type = Column(String(100), nullable=True)  # Cached for performance
    topics = Column(JSONB, nullable=True)  # Topics associated with the content

    # Timing and context
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    session_id = Column(String(200), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    user_agent = Column(Text, nullable=True)

    # Additional metadata
    interaction_metadata = Column(JSONB, nullable=True)  # Additional interaction metadata

    # Relationships
    content_item = relationship("ContentItem")

    # Indexes for performance
    __table_args__ = (
        Index('idx_user_interactions_user_type', 'user_id', 'interaction_type'),
        Index('idx_user_interactions_content_user', 'content_item_id', 'user_id'),
        Index('idx_user_interactions_created_at', 'created_at'),
        Index('idx_user_interactions_type_created', 'interaction_type', 'created_at'),
    )

    def __repr__(self):
        return f"<UserInteraction(id={self.id}, user={self.user_id}, type={self.interaction_type})>"


class SearchLog(Base):
    """Model for tracking search queries and results."""
    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=True, index=True)
    query = Column(Text, nullable=False)
    search_type = Column(String(50), nullable=False)  # semantic, keyword, hybrid
    results_count = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    has_results = Column(Boolean, default=True)
    click_through = Column(Boolean, default=False)
    clicked_positions = Column(JSONB, nullable=True)  # Array of clicked result positions
    session_id = Column(String(200), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # Support IPv4 and IPv6
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Additional metadata
    search_metadata = Column(JSONB, nullable=True)  # Additional search metadata

    # Indexes for performance
    __table_args__ = (
        Index('idx_search_logs_user_query', 'user_id', 'query'),
        Index('idx_search_logs_type_created', 'search_type', 'created_at'),
        Index('idx_search_logs_created_at', 'created_at'),
        Index('idx_search_logs_has_results', 'has_results'),
    )

    def __repr__(self):
        return f"<SearchLog(id={self.id}, query='{self.query[:50]}...', type={self.search_type})>"