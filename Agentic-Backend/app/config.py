from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., env="CELERY_RESULT_BACKEND")
    
    # Ollama
    ollama_base_url: str = Field(..., env="OLLAMA_BASE_URL")
    ollama_default_model: str = Field(default="llama2", env="OLLAMA_DEFAULT_MODEL")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Application
    app_name: str = Field(default="Agentic Backend", env="APP_NAME")

    # Email Sync System Defaults (can be overridden per account)
    email_sync_default_days_back: int = Field(default=365, env="EMAIL_SYNC_DEFAULT_DAYS_BACK")
    email_sync_default_max_emails: int = Field(default=5000, env="EMAIL_SYNC_DEFAULT_MAX_EMAILS")
    email_sync_batch_size: int = Field(default=50, env="EMAIL_SYNC_BATCH_SIZE")

    # Email Embedding Configuration (can be overridden per account)
    default_embedding_model: str = Field(default="snowflake-arctic-embed2:latest", env="DEFAULT_EMBEDDING_MODEL")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Celery
    celery_worker_concurrency: int = Field(default=4, env="CELERY_WORKER_CONCURRENCY")
    celery_task_timeout: int = Field(default=300, env="CELERY_TASK_TIMEOUT")
    
    # Redis Streams
    log_stream_name: str = Field(default="agent_logs", env="LOG_STREAM_NAME")
    log_stream_max_len: int = Field(default=10000, env="LOG_STREAM_MAX_LEN")

    # Phase 1 New Services Configuration

    # HTTP Client Configuration
    http_client_circuit_breaker_enabled: bool = Field(default=True, env="HTTP_CLIENT_CIRCUIT_BREAKER_ENABLED")
    http_client_circuit_breaker_failure_threshold: int = Field(default=5, env="HTTP_CLIENT_CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    http_client_circuit_breaker_recovery_timeout: float = Field(default=60.0, env="HTTP_CLIENT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
    http_client_retry_max_attempts: int = Field(default=3, env="HTTP_CLIENT_RETRY_MAX_ATTEMPTS")
    http_client_retry_backoff_factor: float = Field(default=2.0, env="HTTP_CLIENT_RETRY_BACKOFF_FACTOR")
    http_client_rate_limit_requests_per_minute: int = Field(default=60, env="HTTP_CLIENT_RATE_LIMIT_REQUESTS_PER_MINUTE")
    http_client_connect_timeout: float = Field(default=10.0, env="HTTP_CLIENT_CONNECT_TIMEOUT")
    http_client_read_timeout: float = Field(default=30.0, env="HTTP_CLIENT_READ_TIMEOUT")
    http_client_total_timeout: float = Field(default=300.0, env="HTTP_CLIENT_TOTAL_TIMEOUT")
    http_client_max_connections: int = Field(default=100, env="HTTP_CLIENT_MAX_CONNECTIONS")
    http_client_max_connections_per_host: int = Field(default=30, env="HTTP_CLIENT_MAX_CONNECTIONS_PER_HOST")
    http_client_ssl_verify: bool = Field(default=True, env="HTTP_CLIENT_SSL_VERIFY")
    http_client_allowed_domains: str = Field(default="", env="HTTP_CLIENT_ALLOWED_DOMAINS")  # Comma-separated list

    # Model Selection Configuration
    model_selection_cache_ttl: int = Field(default=300, env="MODEL_SELECTION_CACHE_TTL")  # seconds
    model_selection_performance_tracking_enabled: bool = Field(default=True, env="MODEL_SELECTION_PERFORMANCE_TRACKING_ENABLED")
    model_selection_auto_discovery_enabled: bool = Field(default=True, env="MODEL_SELECTION_AUTO_DISCOVERY_ENABLED")
    model_selection_fallback_enabled: bool = Field(default=True, env="MODEL_SELECTION_FALLBACK_ENABLED")
    model_selection_default_embedding_model: str = Field(default="nomic-embed-text", env="MODEL_SELECTION_DEFAULT_EMBEDDING_MODEL")
    model_selection_default_text_model: str = Field(default="llama2", env="MODEL_SELECTION_DEFAULT_TEXT_MODEL")

    # Content Framework Configuration
    cache_dir: str = Field(default="/tmp/content_cache", env="CACHE_DIR")
    content_cache_max_size_mb: int = Field(default=1024, env="CONTENT_CACHE_MAX_SIZE_MB")
    content_cache_ttl_seconds: int = Field(default=3600, env="CONTENT_CACHE_TTL_SECONDS")
    content_detection_magic_file: str = Field(default="/usr/share/file/magic.mgc", env="CONTENT_DETECTION_MAGIC_FILE")
    content_max_file_size_mb: int = Field(default=100, env="CONTENT_MAX_FILE_SIZE_MB")
    content_processing_timeout_seconds: int = Field(default=300, env="CONTENT_PROCESSING_TIMEOUT_SECONDS")
    content_batch_processing_max_items: int = Field(default=50, env="CONTENT_BATCH_PROCESSING_MAX_ITEMS")

    # Content Connector Configuration
    content_connector_parallel_discovery: bool = Field(default=True, env="CONTENT_CONNECTOR_PARALLEL_DISCOVERY")
    content_connector_max_concurrent_discovery: int = Field(default=10, env="CONTENT_CONNECTOR_MAX_CONCURRENT_DISCOVERY")
    content_connector_default_timeout: int = Field(default=30, env="CONTENT_CONNECTOR_DEFAULT_TIMEOUT")
    content_connector_retry_attempts: int = Field(default=3, env="CONTENT_CONNECTOR_RETRY_ATTEMPTS")
    content_connector_retry_backoff: float = Field(default=1.0, env="CONTENT_CONNECTOR_RETRY_BACKOFF")

    # Web Connector Configuration
    web_connector_user_agent: str = Field(default="Agentic-Backend/1.0", env="WEB_CONNECTOR_USER_AGENT")
    web_connector_max_redirects: int = Field(default=5, env="WEB_CONNECTOR_MAX_REDIRECTS")
    web_connector_respect_robots_txt: bool = Field(default=True, env="WEB_CONNECTOR_RESPECT_ROBOTS_TXT")
    web_connector_scraping_delay: float = Field(default=1.0, env="WEB_CONNECTOR_SCRAPING_DELAY")

    # Social Media Connector Configuration
    social_connector_rate_limit_buffer: float = Field(default=0.1, env="SOCIAL_CONNECTOR_RATE_LIMIT_BUFFER")
    social_connector_max_retries: int = Field(default=5, env="SOCIAL_CONNECTOR_MAX_RETRIES")
    social_connector_backoff_multiplier: float = Field(default=2.0, env="SOCIAL_CONNECTOR_BACKOFF_MULTIPLIER")

    # Email Connector Configuration
    email_connector_imap_timeout: int = Field(default=60, env="EMAIL_CONNECTOR_IMAP_TIMEOUT")
    email_connector_batch_size: int = Field(default=50, env="EMAIL_CONNECTOR_BATCH_SIZE")
    email_connector_attachment_max_size_mb: int = Field(default=10, env="EMAIL_CONNECTOR_ATTACHMENT_MAX_SIZE_MB")

    # Email Workflow Configuration
    email_workflow_analysis_timeout: int = Field(default=120, env="EMAIL_WORKFLOW_ANALYSIS_TIMEOUT")  # seconds
    email_workflow_task_timeout: int = Field(default=60, env="EMAIL_WORKFLOW_TASK_TIMEOUT")  # seconds
    email_workflow_ollama_timeout: int = Field(default=60, env="EMAIL_WORKFLOW_OLLAMA_TIMEOUT")  # seconds for individual Ollama calls
    email_workflow_max_retries: int = Field(default=3, env="EMAIL_WORKFLOW_MAX_RETRIES")
    email_workflow_retry_delay: float = Field(default=1.0, env="EMAIL_WORKFLOW_RETRY_DELAY")  # seconds

    # File System Connector Configuration
    filesystem_connector_recursive_scan: bool = Field(default=True, env="FILESYSTEM_CONNECTOR_RECURSIVE_SCAN")
    filesystem_connector_follow_symlinks: bool = Field(default=False, env="FILESYSTEM_CONNECTOR_FOLLOW_SYMLINKS")
    filesystem_connector_exclude_patterns: str = Field(default="*.tmp,*.log,*.cache", env="FILESYSTEM_CONNECTOR_EXCLUDE_PATTERNS")

    # Cloud Storage Configuration
    cloud_storage_s3_region: str = Field(default="us-east-1", env="CLOUD_STORAGE_S3_REGION")
    cloud_storage_s3_max_concurrent: int = Field(default=10, env="CLOUD_STORAGE_S3_MAX_CONCURRENT")
    cloud_storage_gcs_project_id: str = Field(default="", env="CLOUD_STORAGE_GCS_PROJECT_ID")

    # API Connector Configuration
    api_connector_default_headers: str = Field(default='{"User-Agent": "Agentic-Backend/1.0"}', env="API_CONNECTOR_DEFAULT_HEADERS")
    api_connector_auth_retry_enabled: bool = Field(default=True, env="API_CONNECTOR_AUTH_RETRY_ENABLED")
    api_connector_pagination_auto_detect: bool = Field(default=True, env="API_CONNECTOR_PAGINATION_AUTO_DETECT")

    # Content Processing Pipeline Configuration
    content_pipeline_max_workers: int = Field(default=4, env="CONTENT_PIPELINE_MAX_WORKERS")
    content_pipeline_queue_size: int = Field(default=100, env="CONTENT_PIPELINE_QUEUE_SIZE")
    content_pipeline_enable_metrics: bool = Field(default=True, env="CONTENT_PIPELINE_ENABLE_METRICS")

    # Content Quality Configuration
    content_quality_min_score: float = Field(default=0.5, env="CONTENT_QUALITY_MIN_SCORE")
    content_quality_auto_filter: bool = Field(default=False, env="CONTENT_QUALITY_AUTO_FILTER")
    content_quality_scoring_enabled: bool = Field(default=True, env="CONTENT_QUALITY_SCORING_ENABLED")

    # Content Analytics Configuration
    content_analytics_enabled: bool = Field(default=True, env="CONTENT_ANALYTICS_ENABLED")
    content_analytics_update_interval: int = Field(default=3600, env="CONTENT_ANALYTICS_UPDATE_INTERVAL")  # seconds
    content_analytics_retention_days: int = Field(default=90, env="CONTENT_ANALYTICS_RETENTION_DAYS")

    # Content Discovery Scheduling
    content_discovery_scheduler_enabled: bool = Field(default=True, env="CONTENT_DISCOVERY_SCHEDULER_ENABLED")
    content_discovery_default_interval: int = Field(default=3600, env="CONTENT_DISCOVERY_DEFAULT_INTERVAL")  # seconds
    content_discovery_max_parallel_sources: int = Field(default=5, env="CONTENT_DISCOVERY_MAX_PARALLEL_SOURCES")

    # Content Database Configuration
    content_db_batch_insert_size: int = Field(default=100, env="CONTENT_DB_BATCH_INSERT_SIZE")
    content_db_connection_pool_size: int = Field(default=10, env="CONTENT_DB_CONNECTION_POOL_SIZE")
    content_db_query_timeout: int = Field(default=30, env="CONTENT_DB_QUERY_TIMEOUT")

    # Semantic Processing Configuration
    semantic_embedding_batch_size: int = Field(default=10, env="SEMANTIC_EMBEDDING_BATCH_SIZE")
    semantic_search_top_k_default: int = Field(default=5, env="SEMANTIC_SEARCH_TOP_K_DEFAULT")
    semantic_chunk_max_size: int = Field(default=512, env="SEMANTIC_CHUNK_MAX_SIZE")
    semantic_chunk_overlap: int = Field(default=50, env="SEMANTIC_CHUNK_OVERLAP")
    semantic_clustering_max_clusters: int = Field(default=10, env="SEMANTIC_CLUSTERING_MAX_CLUSTERS")
    semantic_quality_scoring_enabled: bool = Field(default=True, env="SEMANTIC_QUALITY_SCORING_ENABLED")
    semantic_usage_tracking_enabled: bool = Field(default=True, env="SEMANTIC_USAGE_TRACKING_ENABLED")

    # X API Configuration (formerly Twitter) - OAuth 2.0 + Playwright
    x_bearer_token: Optional[str] = Field(default=None, env="X_BEARER_TOKEN")
    x_api_key: Optional[str] = Field(default=None, env="X_API_KEY")
    x_api_secret: Optional[str] = Field(default=None, env="X_API_SECRET")
    x_username: Optional[str] = Field(default=None, env="X_USERNAME")  # For Playwright login
    x_password: Optional[str] = Field(default=None, env="X_PASSWORD")  # For Playwright login
    x_base_url: str = Field(default="https://api.x.com/2", env="X_BASE_URL")
    x_bookmark_url: Optional[str] = Field(default=None, env="X_BOOKMARK_URL")
    x_request_timeout: int = Field(default=30, env="X_REQUEST_TIMEOUT")
    x_max_retries: int = Field(default=3, env="X_MAX_RETRIES")
    x_rate_limit_buffer: int = Field(default=5, env="X_RATE_LIMIT_BUFFER")
    x_bookmarks_max_results: int = Field(default=100, env="X_BOOKMARKS_MAX_RESULTS")
    x_bookmarks_days_back: int = Field(default=30, env="X_BOOKMARKS_DAYS_BACK")
    x_thread_max_tweets: int = Field(default=50, env="X_THREAD_MAX_TWEETS")
    x_use_playwright: bool = Field(default=True, env="X_USE_PLAYWRIGHT")  # Default to Playwright

    # Database Configuration for New Services
    db_model_performance_retention_days: int = Field(default=90, env="DB_MODEL_PERFORMANCE_RETENTION_DAYS")
    db_http_request_log_retention_days: int = Field(default=30, env="DB_HTTP_REQUEST_LOG_RETENTION_DAYS")
    db_metrics_aggregation_interval_minutes: int = Field(default=60, env="DB_METRICS_AGGREGATION_INTERVAL_MINUTES")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # Allow extra environment variables
    }


settings = Settings()