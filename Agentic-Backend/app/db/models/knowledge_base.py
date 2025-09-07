"""
Knowledge Base Database Models
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.database import Base


class KnowledgeBaseItem(Base):
    """Database model for knowledge base items"""
    __tablename__ = "knowledge_base_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)  # 'twitter_bookmark', 'web_content', 'email', etc.
    source_id = Column(String(255), nullable=True)  # Original content identifier
    content_type = Column(String(50), nullable=False)  # 'text', 'image', 'video', 'mixed'
    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    full_content = Column(Text, nullable=True)
    item_metadata = Column(JSON, default=dict)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Phase tracking fields for workflow management
    processing_phase = Column(String(50), default="not_started")  # Current processing phase
    phase_started_at = Column(DateTime, nullable=True)  # When current phase started
    phase_completed_at = Column(DateTime, nullable=True)  # When current phase completed
    last_successful_phase = Column(String(50), nullable=True)  # Last successfully completed phase
    needs_reprocessing = Column(Boolean, default=False)  # Flag for reprocessing
    reprocessing_reason = Column(Text, nullable=True)  # Reason for reprocessing

    # Relationships
    categories = relationship("KnowledgeBaseCategory", back_populates="item")
    embeddings = relationship("KnowledgeBaseEmbedding", back_populates="item")
    analysis_results = relationship("KnowledgeBaseAnalysis", back_populates="item")
    media_assets = relationship("KnowledgeBaseMedia", back_populates="item")
    processing_phases = relationship("KnowledgeBaseProcessingPhase", back_populates="item")

    # Indexes for performance
    __table_args__ = (
        Index('idx_kb_items_source_type', 'source_type'),
        Index('idx_kb_items_content_type', 'content_type'),
        Index('idx_kb_items_created_at', 'created_at'),
        Index('idx_kb_items_active', 'is_active'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "source_type": self.source_type,
            "source_id": self.source_id,
            "content_type": self.content_type,
            "title": self.title,
            "summary": self.summary,
            "full_content": self.full_content,
            "metadata": self.item_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "is_active": self.is_active,
            # Phase tracking fields
            "processing_phase": self.processing_phase,
            "phase_started_at": self.phase_started_at.isoformat() if self.phase_started_at else None,
            "phase_completed_at": self.phase_completed_at.isoformat() if self.phase_completed_at else None,
            "last_successful_phase": self.last_successful_phase,
            "needs_reprocessing": self.needs_reprocessing,
            "reprocessing_reason": self.reprocessing_reason
        }


class KnowledgeBaseCategory(Base):
    """Database model for knowledge base categories"""
    __tablename__ = "knowledge_base_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base_items.id"), nullable=False)
    category = Column(String(100), nullable=False)
    sub_category = Column(String(100), nullable=True)
    confidence_score = Column(Float, default=0.0)
    auto_generated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(100), nullable=True)  # Which model generated this category

    # Relationships
    item = relationship("KnowledgeBaseItem", back_populates="categories")

    # Indexes
    __table_args__ = (
        Index('idx_kb_categories_item_id', 'item_id'),
        Index('idx_kb_categories_category', 'category'),
        Index('idx_kb_categories_confidence', 'confidence_score'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "category": self.category,
            "sub_category": self.sub_category,
            "confidence_score": self.confidence_score,
            "auto_generated": self.auto_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "model_used": self.model_used
        }


class KnowledgeBaseEmbedding(Base):
    """Database model for knowledge base embeddings"""
    __tablename__ = "knowledge_base_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base_items.id"), nullable=False)
    embedding_model = Column(String(100), nullable=False)  # Model used to generate embedding
    embedding_vector = Column(JSON, nullable=False)  # Vector data (could be pgvector in production)
    content_chunk = Column(Text, nullable=True)  # Original text chunk
    chunk_index = Column(Integer, default=0)  # Index of chunk in document
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    item = relationship("KnowledgeBaseItem", back_populates="embeddings")

    # Indexes
    __table_args__ = (
        Index('idx_kb_embeddings_item_id', 'item_id'),
        Index('idx_kb_embeddings_model', 'embedding_model'),
        Index('idx_kb_embeddings_chunk_index', 'chunk_index'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "embedding_model": self.embedding_model,
            "embedding_vector": self.embedding_vector,
            "content_chunk": self.content_chunk,
            "chunk_index": self.chunk_index,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeBaseAnalysis(Base):
    """Database model for AI analysis results"""
    __tablename__ = "knowledge_base_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base_items.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # 'llm_explanation', 'vision_interpretation', etc.
    model_used = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    model_capabilities = Column(JSON, default=list)  # Array of model capabilities used
    processing_duration_ms = Column(Integer, nullable=True)
    content = Column(Text, nullable=True)  # Analysis result content
    confidence_score = Column(Float, default=0.0)
    tokens_used = Column(Integer, nullable=True)
    analysis_metadata = Column(JSON, default=dict)  # Additional analysis metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    item = relationship("KnowledgeBaseItem", back_populates="analysis_results")

    # Indexes
    __table_args__ = (
        Index('idx_kb_analysis_item_id', 'item_id'),
        Index('idx_kb_analysis_type', 'analysis_type'),
        Index('idx_kb_analysis_model', 'model_used'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "analysis_type": self.analysis_type,
            "model_used": self.model_used,
            "model_version": self.model_version,
            "model_capabilities": self.model_capabilities,
            "processing_duration_ms": self.processing_duration_ms,
            "content": self.content,
            "confidence_score": self.confidence_score,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeBaseMedia(Base):
    """Database model for media assets"""
    __tablename__ = "knowledge_base_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base_items.id"), nullable=False)
    media_type = Column(String(50), nullable=False)  # 'image', 'video', 'audio'
    file_path = Column(Text, nullable=True)  # Local file path
    original_url = Column(Text, nullable=True)  # Original source URL
    cached_path = Column(Text, nullable=True)  # Cached file path
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    media_metadata = Column(JSON, default=dict)  # Media-specific metadata
    vision_analysis = Column(JSON, default=dict)  # Vision AI analysis results
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    item = relationship("KnowledgeBaseItem", back_populates="media_assets")

    # Indexes
    __table_args__ = (
        Index('idx_kb_media_item_id', 'item_id'),
        Index('idx_kb_media_type', 'media_type'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "media_type": self.media_type,
            "file_path": self.file_path,
            "original_url": self.original_url,
            "cached_path": self.cached_path,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "metadata": self.metadata,
            "vision_analysis": self.vision_analysis,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeBaseSearchLog(Base):
    """Database model for search logs"""
    __tablename__ = "knowledge_base_search_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    search_type = Column(String(50), default="semantic")  # 'semantic', 'keyword', 'hybrid'
    search_duration_ms = Column(Integer, nullable=True)
    filters_used = Column(JSON, default=dict)  # Search filters applied
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_kb_search_user_id', 'user_id'),
        Index('idx_kb_search_type', 'search_type'),
        Index('idx_kb_search_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "query": self.query,
            "results_count": self.results_count,
            "search_type": self.search_type,
            "search_duration_ms": self.search_duration_ms,
            "filters_used": self.filters_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KnowledgeBaseProcessingPhase(Base):
    """Database model for tracking individual processing phases of knowledge base items"""
    __tablename__ = "knowledge_base_processing_phases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base_items.id"), nullable=False)
    phase_name = Column(String(50), nullable=False)  # Phase identifier (e.g., 'fetch_bookmarks', 'media_interpretation')
    status = Column(String(20), default="pending")  # pending, running, completed, failed, skipped
    model_used = Column(String(100), nullable=True)  # Which Ollama model was used
    model_version = Column(String(50), nullable=True)  # Model version/tag
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Processing time and progress tracking
    processing_duration_ms = Column(Integer, nullable=True)  # Total processing time in milliseconds
    current_item_index = Column(Integer, default=0)  # Current item being processed (for batch operations)
    total_items = Column(Integer, default=1)  # Total items to process in this phase
    estimated_time_remaining_ms = Column(Integer, nullable=True)  # Estimated time to completion
    progress_percentage = Column(Float, default=0.0)  # Progress as percentage (0.0 to 100.0)
    status_message = Column(Text, nullable=True)  # Rich status message (e.g., "Processing item 5 of 30")

    processing_metadata = Column(JSON, default=dict)  # Additional processing metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    item = relationship("KnowledgeBaseItem", back_populates="processing_phases")

    # Indexes for performance
    __table_args__ = (
        Index('idx_kb_phases_item_id', 'item_id'),
        Index('idx_kb_phases_status', 'status'),
        Index('idx_kb_phases_phase_name', 'phase_name'),
        Index('idx_kb_phases_model_used', 'model_used'),
        Index('idx_kb_phases_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "phase_name": self.phase_name,
            "status": self.status,
            "model_used": self.model_used,
            "model_version": self.model_version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            # Processing time and progress tracking
            "processing_duration_ms": self.processing_duration_ms,
            "current_item_index": self.current_item_index,
            "total_items": self.total_items,
            "estimated_time_remaining_ms": self.estimated_time_remaining_ms,
            "progress_percentage": self.progress_percentage,
            "status_message": self.status_message,
            "processing_metadata": self.processing_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class KnowledgeBaseWorkflowSettings(Base):
    """Database model for user-configurable workflow settings"""
    __tablename__ = "knowledge_base_workflow_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Null for system defaults
    settings_name = Column(String(100), nullable=False)  # Name of settings profile
    is_default = Column(Boolean, default=False)  # Whether this is the default settings
    is_system_default = Column(Boolean, default=False)  # System-wide default settings

    # Model selection per phase
    phase_models = Column(JSON, default=dict)  # {
    #     "fetch_bookmarks": {"model": "llama2", "fallback_models": ["mistral"]},
    #     "cache_content": {"model": "llama2", "fallback_models": ["codellama"]},
    #     "interpret_media": {"model": "llava:13b", "fallback_models": ["llava:7b"]},
    #     "categorize_content": {"model": "llama2:13b", "fallback_models": ["llama2:7b"]},
    #     "holistic_understanding": {"model": "llama2:13b", "fallback_models": ["llama2:7b"]},
    #     "synthesized_learning": {"model": "llama2:13b", "fallback_models": ["llama2:7b"]},
    #     "embeddings": {"model": "all-minilm", "fallback_models": ["paraphrase-multilingual"]}
    # }

    # Phase control settings
    phase_settings = Column(JSON, default=dict)  # {
    #     "fetch_bookmarks": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "cache_content": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "cache_media": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "interpret_media": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "categorize_content": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "holistic_understanding": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "synthesized_learning": {"skip": false, "force_reprocess": false, "enabled": true},
    #     "embeddings": {"skip": false, "force_reprocess": false, "enabled": true}
    # }

    # Global workflow settings
    global_settings = Column(JSON, default=dict)  # {
    #     "max_concurrent_items": 5,
    #     "retry_attempts": 3,
    #     "timeout_seconds": 1800,
    #     "auto_start_processing": true,
    #     "enable_progress_tracking": true,
    #     "notification_settings": {
    #         "on_completion": true,
    #         "on_error": true,
    #         "progress_updates": false
    #     }
    # }

    # Usage tracking
    usage_count = Column(Integer, default=0)  # How many times this settings profile has been used
    last_used_at = Column(DateTime, nullable=True)  # When this settings was last used

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index('idx_kb_workflow_settings_user_id', 'user_id'),
        Index('idx_kb_workflow_settings_default', 'is_default'),
        Index('idx_kb_workflow_settings_system_default', 'is_system_default'),
        Index('idx_kb_workflow_settings_name', 'settings_name'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "settings_name": self.settings_name,
            "is_default": self.is_default,
            "is_system_default": self.is_system_default,
            "phase_models": self.phase_models,
            "phase_settings": self.phase_settings,
            "global_settings": self.global_settings,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_default_phase_models(cls):
        """Get default model configuration for all phases"""
        return {
            "fetch_bookmarks": {
                "model": "llama2",
                "fallback_models": ["mistral", "codellama"],
                "task_type": "general"
            },
            "cache_content": {
                "model": "llama2",
                "fallback_models": ["mistral", "codellama"],
                "task_type": "text_processing"
            },
            "cache_media": {
                "model": "llama2",
                "fallback_models": ["mistral", "codellama"],
                "task_type": "general"
            },
            "interpret_media": {
                "model": "llava:13b",
                "fallback_models": ["llava:7b", "bakllava"],
                "task_type": "vision_analysis"
            },
            "categorize_content": {
                "model": "llama2:13b",
                "fallback_models": ["llama2:7b", "mistral"],
                "task_type": "classification"
            },
            "holistic_understanding": {
                "model": "llama2:13b",
                "fallback_models": ["llama2:7b", "codellama"],
                "task_type": "text_synthesis"
            },
            "synthesized_learning": {
                "model": "llama2:13b",
                "fallback_models": ["llama2:7b", "mistral"],
                "task_type": "content_synthesis"
            },
            "embeddings": {
                "model": "all-minilm",
                "fallback_models": ["paraphrase-multilingual", "sentence-transformers"],
                "task_type": "embedding"
            }
        }

    @classmethod
    def get_default_phase_settings(cls):
        """Get default phase control settings"""
        return {
            "fetch_bookmarks": {"skip": False, "force_reprocess": False, "enabled": True},
            "cache_content": {"skip": False, "force_reprocess": False, "enabled": True},
            "cache_media": {"skip": False, "force_reprocess": False, "enabled": True},
            "interpret_media": {"skip": False, "force_reprocess": False, "enabled": True},
            "categorize_content": {"skip": False, "force_reprocess": False, "enabled": True},
            "holistic_understanding": {"skip": False, "force_reprocess": False, "enabled": True},
            "synthesized_learning": {"skip": False, "force_reprocess": False, "enabled": True},
            "embeddings": {"skip": False, "force_reprocess": False, "enabled": True}
        }

    @classmethod
    def get_default_global_settings(cls):
        """Get default global workflow settings"""
        return {
            "max_concurrent_items": 5,
            "retry_attempts": 3,
            "timeout_seconds": 1800,
            "auto_start_processing": True,
            "enable_progress_tracking": True,
            "notification_settings": {
                "on_completion": True,
                "on_error": True,
                "progress_updates": False
            }
        }


class TwitterBookmarkTracker(Base):
    """Database model for tracking processed Twitter bookmarks to avoid duplicates"""
    __tablename__ = "twitter_bookmark_tracker"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tweet_id = Column(String(50), nullable=False, unique=True)  # Twitter tweet ID
    tweet_url = Column(Text, nullable=False)  # Full tweet URL
    author_username = Column(String(100), nullable=True)  # Tweet author username
    author_id = Column(String(50), nullable=True)  # Twitter user ID
    is_thread = Column(Boolean, default=False)  # Whether this tweet is part of a thread
    thread_root_id = Column(String(50), nullable=True)  # Root tweet ID if part of thread
    thread_position = Column(Integer, nullable=True)  # Position in thread (0-based)
    content_hash = Column(String(64), nullable=True)  # SHA256 hash of tweet content
    processed_at = Column(DateTime, default=datetime.utcnow)  # When bookmark was processed
    last_seen_at = Column(DateTime, default=datetime.utcnow)  # Last time this bookmark was seen
    processing_status = Column(String(20), default="processed")  # processed, failed, skipped
    error_message = Column(Text, nullable=True)  # Error message if processing failed
    tweet_metadata = Column(JSON, default=dict)  # Additional metadata

    # Indexes for performance
    __table_args__ = (
        Index('idx_twitter_bookmarks_tweet_id', 'tweet_id'),
        Index('idx_twitter_bookmarks_author', 'author_username'),
        Index('idx_twitter_bookmarks_thread', 'thread_root_id'),
        Index('idx_twitter_bookmarks_processed_at', 'processed_at'),
        Index('idx_twitter_bookmarks_status', 'processing_status'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url,
            "author_username": self.author_username,
            "author_id": self.author_id,
            "is_thread": self.is_thread,
            "thread_root_id": self.thread_root_id,
            "thread_position": self.thread_position,
            "content_hash": self.content_hash,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "processing_status": self.processing_status,
            "error_message": self.error_message,
            "tweet_metadata": self.tweet_metadata
        }