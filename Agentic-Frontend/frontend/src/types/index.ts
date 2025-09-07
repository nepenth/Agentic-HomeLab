export interface User {
  id: string;
  username: string;
  email?: string;
  isAuthenticated: boolean;
  is_superuser?: boolean;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  model_name: string;
  config: {
    temperature: number;
    max_tokens: number;
    system_prompt: string;
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  agent_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input: Record<string, any>;
  output?: Record<string, any>;
  created_at: string;
  completed_at?: string;
}

export interface DashboardWidget {
  id: string;
  title: string;
  type: 'summary' | 'chart' | 'list' | 'metric';
  data: any;
  position: { x: number; y: number; w: number; h: number };
}

export interface LogEntry {
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  task_id?: string;
  agent_id?: string;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface BackendEndpoint {
  service: string;
  url: string;
  description: string;
  icon: string;
}

// Security-related types
export interface SecurityStatus {
  active_agents: number;
  total_incidents: number;
  recent_incidents: SecurityIncident[];
  resource_limits: {
    max_concurrent_agents: number;
    max_memory_mb: number;
    max_execution_time: number;
  };
  current_usage: {
    active_agents: number;
    total_memory_mb: number;
  };
}

export interface SecurityIncident {
  incident_id: string;
  agent_id: string;
  agent_type?: string;
  violation_type: 'RESOURCE_EXCEEDED' | 'PERMISSION_DENIED' | 'MALICIOUS_CONTENT' | 'RATE_LIMIT_EXCEEDED' | 'SCHEMA_VIOLATION' | 'EXECUTION_TIMEOUT';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  timestamp: string;
  resolved: boolean;
  resolution_notes?: string;
}

export interface SecurityHealth {
  status: 'healthy' | 'warning' | 'error';
  message: string;
  metrics: {
    total_incidents: number;
    active_agents: number;
    unresolved_high_severity: number;
  };
  timestamp: string;
}

export interface SecurityLimits {
  concurrent_agents: {
    current: number;
    max: number;
  };
  memory_usage: {
    current_mb: number;
    max_mb: number;
  };
  rate_limits: {
    tool_execution_per_hour: number;
    agent_creation_per_hour: number;
    external_requests_per_hour: number;
  };
}

export interface AgentSecurityReport {
  agent_id: string;
  agent_type: string;
  start_time: string;
  resource_usage: {
    memory_peak_mb: number;
    cpu_time_seconds: number;
    execution_time: number;
  };
  security_events: Array<{
    type: string;
    description: string;
    timestamp: string;
  }>;
  incidents: SecurityIncident[];
  is_secure: boolean;
}

export interface ToolValidationRequest {
  agent_id: string;
  tool_name: string;
  input_data: Record<string, any>;
}

export interface ToolValidationResponse {
  allowed: boolean;
  agent_id: string;
  tool_name: string;
  validation_time: number;
  errors?: string[];
}

// System metrics types
export interface SystemMetrics {
  timestamp: string;
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  gpu: GpuMetrics[];
}

export interface CpuMetrics {
  usage_percent: number;
  frequency_mhz: {
    current: number;
    min: number;
    max: number;
  };
  count: {
    physical: number;
    logical: number;
  };
}

export interface MemoryMetrics {
  total_gb: number;
  used_gb: number;
  usage_percent: number;
}

export interface GpuMetrics {
  index: number;
  name: string;
  utilization: {
    gpu_percent: number;
    memory_percent: number;
  };
  memory: {
    used_mb: number;
    total_mb: number;
  };
  temperature_fahrenheit: number;
  power: {
    usage_watts: number;
    limit_watts: number;
  };
}

export interface DiskMetrics {
  total_gb: number;
  used_gb: number;
  usage_percent: number;
  read_speed_mbps: number;
  write_speed_mbps: number;
}

export interface NetworkMetrics {
  interfaces: NetworkInterface[];
  total_received_mb: number;
  total_transmitted_mb: number;
}

export interface NetworkInterface {
  name: string;
  received_mb: number;
  transmitted_mb: number;
  speed_mbps: number;
}

// Ollama model management types
export interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
  digest: string;
}

export interface OllamaModelsResponse {
  models: OllamaModel[];
}

export interface OllamaModelNamesResponse {
  models: string[];
}

export interface OllamaHealthResponse {
  status: string;
  models_available: number;
  default_model: string;
}

export interface OllamaPullResponse {
  status: string;
  message: string;
  model_name: string;
}

// Chat system types
export interface ChatSession {
  id: string;
  session_type: 'general' | 'agent_creation';
  model_name: string;
  user_id: string;
  title: string;
  status: 'active' | 'completed' | 'archived';
  created_at: string;
  updated_at: string;
  config?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ChatSessionStats {
  session_id: string;
  message_count: number;
  total_tokens: number;
  duration_seconds: number;
  last_activity: string;
}

export interface ChatTemplate {
  id: string;
  name: string;
  description: string;
  session_type: string;
  config: Record<string, any>;
}

export interface CreateChatSessionRequest {
  session_type: 'general' | 'agent_creation';
  model_name: string;
  user_id?: string;
  title: string;
  config?: Record<string, any>;
}

export interface SendChatMessageRequest {
  message: string;
  model_name?: string;
  metadata?: Record<string, any>;
}

export interface PerformanceMetrics {
  response_time_seconds: number;
  load_time_seconds: number;
  prompt_eval_time_seconds: number;
  generation_time_seconds: number;
  prompt_tokens: number;
  response_tokens: number;
  total_tokens: number;
  tokens_per_second: number;
  context_length_chars: number;
  model_name: string;
  timestamp: string;
}

export interface ChatMessageResponse {
  message: ChatMessage;
  session_id: string;
  response?: string;
  tokens_used?: number;
  performance_metrics?: PerformanceMetrics;
}

export interface ChatModelsResponse {
  models: string[];
  default_model: string;
}

export interface ChatTemplatesResponse {
  templates: ChatTemplate[];
}

// ==========================================
// PHASE 1: FOUNDATION ENHANCEMENT TYPES
// ==========================================

// Agentic HTTP Client Types
export interface HttpRequestData {
  method: string;
  url: string;
  headers?: Record<string, string>;
  data?: any;
  json_data?: any;
  auth?: any;
  timeout?: number;
  retry_config?: any;
  rate_limit?: any;
}

export interface HttpResponse {
  status_code: number;
  headers: Record<string, string>;
  content: any;
  response_time_ms: number;
  request_id: string;
}

export interface HttpClientMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time_ms: number;
  requests_per_minute: number;
  error_rate: number;
}

export interface StreamDownloadData {
  url: string;
  destination_path: string;
  progress_callback_url?: string;
}

export interface StreamDownloadResponse {
  download_id: string;
  status: 'started' | 'completed' | 'failed';
  total_size_bytes?: number;
  downloaded_bytes?: number;
  progress_percentage?: number;
}

// Dynamic Model Selection Types
export interface AvailableModel {
  name: string;
  capabilities: string[];
  performance_score: number;
  supported_tasks: string[];
  context_length: number;
  pricing?: any;
}

export interface ModelSelectionRequest {
  task_type: string;
  content_type: string;
  priority?: string;
  max_tokens?: number;
  requirements?: any;
}

export interface ModelSelectionResponse {
  selected_model: string;
  confidence_score: number;
  reasoning: string;
  alternatives: Array<{
    model: string;
    score: number;
    reason: string;
  }>;
}

export interface ModelPerformanceMetrics {
  model_name: string;
  task_type: string;
  average_response_time_ms: number;
  success_rate: number;
  average_tokens_used: number;
  cost_per_request?: number;
  last_updated: string;
}

export interface ModelStats {
  model_name: string;
  total_requests: number;
  successful_requests: number;
  average_response_time_ms: number;
  error_rate: number;
  last_used: string;
}

// Multi-Modal Content Framework Types
export interface ContentProcessingRequest {
  content: any;
  content_type?: string;
  operations?: string[];
  metadata?: any;
}

export interface ProcessedContent {
  id: string;
  original_content: any;
  processed_content: any;
  content_type: string;
  operations_applied: string[];
  metadata: any;
  processing_time_ms: number;
  created_at: string;
}

export interface BatchProcessingRequest {
  items: any[];
  operations?: string[];
  parallel?: boolean;
}

export interface BatchProcessingResponse {
  batch_id: string;
  total_items: number;
  processed_items: number;
  failed_items: number;
  results: ProcessedContent[];
  processing_time_ms: number;
}

export interface ContentCacheStats {
  total_entries: number;
  cache_hit_rate: number;
  cache_size_bytes: number;
  last_cleanup: string;
}

// Semantic Processing Types
export interface EmbeddingRequest {
  text: string;
  model?: string;
  dimensions?: number;
}

export interface EmbeddingResponse {
  embeddings: number[];
  model_used: string;
  dimensions: number;
  processing_time_ms: number;
}

export interface SemanticSearchRequest {
  query: string;
  limit?: number;
  threshold?: number;
  filters?: any;
}

export interface SemanticSearchResult {
  content_id: string;
  content: string;
  similarity_score: number;
  metadata?: any;
}

export interface SemanticSearchResponse {
  results: SemanticSearchResult[];
  total_results: number;
  search_time_ms: number;
}

export interface ClusteringRequest {
  embeddings: number[][];
  method?: string;
  n_clusters?: number;
}

export interface ClusteringResponse {
  clusters: Array<{
    cluster_id: number;
    embeddings: number[][];
    centroid: number[];
    size: number;
  }>;
  method_used: string;
  silhouette_score?: number;
}

export interface TextChunkingRequest {
  text: string;
  strategy?: string;
  chunk_size?: number;
  overlap?: number;
}

export interface TextChunk {
  text: string;
  start_position: number;
  end_position: number;
  metadata?: any;
}

export interface TextChunkingResponse {
  chunks: TextChunk[];
  total_chunks: number;
  strategy_used: string;
}

// ==========================================
// PHASE 2: CONTENT INGESTION & PROCESSING TYPES
// ==========================================

// Universal Content Connectors Types
export interface ContentDiscoveryRequest {
  sources: Array<{
    type: string;
    config: any;
  }>;
}

export interface DiscoveredContent {
  id: string;
  source: string;
  content: any;
  content_type: string;
  metadata: any;
  discovered_at: string;
}

export interface WebContentConfig {
  feed_url?: string;
  url?: string;
  selectors?: any;
  max_items?: number;
}

export interface SocialContentConfig {
  platform: string;
  query?: string;
  username?: string;
  max_items?: number;
}

export interface CommunicationContentConfig {
  platform: string;
  channel?: string;
  token?: string;
  max_messages?: number;
}

export interface FilesystemContentConfig {
  directory?: string;
  bucket_name?: string;
  prefix?: string;
  file_patterns?: string[];
  recursive?: boolean;
  max_keys?: number;
}

// ==========================================
// PHASE 3: INTELLIGENCE & LEARNING TYPES
// ==========================================

// Vision AI Types
export interface VisionAnalysisRequest {
  image_url?: string;
  image_data?: string;
  tasks: string[];
  model?: string;
  options?: any;
}

export interface VisionAnalysisResponse {
  results: Array<{
    task: string;
    result: any;
    confidence?: number;
  }>;
  model_used: string;
  processing_time_ms: number;
}

export interface ObjectDetectionRequest {
  image_url?: string;
  image_data?: string;
  confidence_threshold?: number;
  max_objects?: number;
}

export interface DetectedObject {
  label: string;
  confidence: number;
  bounding_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ObjectDetectionResponse {
  objects: DetectedObject[];
  total_objects: number;
  model_used: string;
}

export interface ImageCaptionRequest {
  image_url?: string;
  image_data?: string;
  model?: string;
}

export interface ImageCaptionResponse {
  caption: string;
  confidence?: number;
  model_used: string;
}

export interface SimilarImagesRequest {
  image_url?: string;
  image_data?: string;
  limit?: number;
  threshold?: number;
}

export interface SimilarImage {
  image_id: string;
  similarity_score: number;
  metadata?: any;
}

export interface SimilarImagesResponse {
  similar_images: SimilarImage[];
  search_time_ms: number;
}

export interface OCRRequest {
  image_url?: string;
  image_data?: string;
  language?: string;
}

export interface OCRResponse {
  text: string;
  confidence?: number;
  language: string;
  bounding_boxes?: any[];
}

export interface VisionModel {
  name: string;
  capabilities: string[];
  supported_tasks: string[];
  max_resolution?: string;
}

// Audio AI Types
export interface AudioTranscriptionRequest {
  audio_url?: string;
  audio_data?: string;
  language?: string;
  model?: string;
  options?: any;
}

export interface AudioTranscriptionResponse {
  transcription: string;
  confidence?: number;
  language: string;
  duration_seconds: number;
  model_used: string;
}

export interface SpeakerIdentificationRequest {
  audio_url?: string;
  audio_data?: string;
  max_speakers?: number;
}

export interface SpeakerSegment {
  speaker_id: string;
  start_time: number;
  end_time: number;
  confidence: number;
}

export interface SpeakerIdentificationResponse {
  speakers: SpeakerSegment[];
  total_speakers: number;
  model_used: string;
}

export interface EmotionAnalysisRequest {
  audio_url?: string;
  audio_data?: string;
  model?: string;
}

export interface EmotionResult {
  emotion: string;
  confidence: number;
  timestamp?: number;
}

export interface EmotionAnalysisResponse {
  emotions: EmotionResult[];
  dominant_emotion: string;
  model_used: string;
}

export interface AudioClassificationRequest {
  audio_url?: string;
  audio_data?: string;
  categories?: string[];
}

export interface AudioClassificationResult {
  category: string;
  confidence: number;
}

export interface AudioClassificationResponse {
  classifications: AudioClassificationResult[];
  model_used: string;
}

export interface MusicAnalysisRequest {
  audio_url?: string;
  audio_data?: string;
  features?: string[];
}

export interface MusicFeatures {
  tempo?: number;
  key?: string;
  genre?: string;
  mood?: string;
  instruments?: string[];
  energy?: number;
  danceability?: number;
}

export interface MusicAnalysisResponse {
  features: MusicFeatures;
  model_used: string;
}

export interface AudioModel {
  name: string;
  capabilities: string[];
  supported_languages: string[];
  max_duration_seconds?: number;
}

// Cross-Modal Processing Types
export interface TextImageAlignmentRequest {
  text: string;
  images: string[];
  model?: string;
}

export interface AlignmentResult {
  text_segment: string;
  image_url: string;
  alignment_score: number;
  reasoning?: string;
}

export interface TextImageAlignmentResponse {
  alignments: AlignmentResult[];
  model_used: string;
}

export interface AudioVisualCorrelationRequest {
  audio_url?: string;
  image_url?: string;
  correlation_type?: string;
}

export interface AudioVisualCorrelationResponse {
  correlation_score: number;
  correlation_type: string;
  features: any;
  model_used: string;
}

export interface CrossModalSearchRequest {
  query: string;
  modalities: string[];
  search_type?: string;
  limit?: number;
}

export interface CrossModalSearchResult {
  content_id: string;
  modality: string;
  content: any;
  relevance_score: number;
  metadata?: any;
}

export interface CrossModalSearchResponse {
  results: CrossModalSearchResult[];
  total_results: number;
  search_time_ms: number;
}

export interface ModalityFusionRequest {
  modalities: Array<{
    type: string;
    data: any;
  }>;
  fusion_method?: string;
}

export interface ModalityFusionResponse {
  fused_content: any;
  fusion_method: string;
  confidence?: number;
  model_used: string;
}

export interface CrossModalModel {
  name: string;
  supported_modalities: string[];
  fusion_methods: string[];
  capabilities: string[];
}

// Quality Enhancement Types
export interface ContentEnhancementRequest {
  content: any;
  content_type: string;
  enhancement_type?: string;
}

export interface ContentEnhancementResponse {
  original_content: any;
  enhanced_content: any;
  enhancement_type: string;
  improvements: string[];
  confidence?: number;
}

export interface ContentCorrectionRequest {
  content: any;
  content_type: string;
  correction_rules?: any;
}

export interface ContentCorrectionResponse {
  original_content: any;
  corrected_content: any;
  corrections_applied: Array<{
    type: string;
    description: string;
    confidence: number;
  }>;
}

export interface QualityMetrics {
  content_quality_score: number;
  readability_score?: number;
  coherence_score?: number;
  factual_accuracy_score?: number;
  metrics: Record<string, number>;
  last_updated: string;
}

// Semantic Understanding Engine Types
export interface ContentClassificationRequest {
  content: string;
  categories?: string[];
  confidence_threshold?: number;
}

export interface ClassificationResult {
  category: string;
  confidence: number;
  subcategories?: string[];
}

export interface ContentClassificationResponse {
  classifications: ClassificationResult[];
  dominant_category: string;
  model_used: string;
}

export interface RelationExtractionRequest {
  content: string;
  entity_types?: string[];
  relation_types?: string[];
}

export interface ExtractedEntity {
  text: string;
  type: string;
  start_position: number;
  end_position: number;
  confidence: number;
}

export interface ExtractedRelation {
  subject: ExtractedEntity;
  predicate: string;
  object: ExtractedEntity;
  confidence: number;
}

export interface RelationExtractionResponse {
  entities: ExtractedEntity[];
  relations: ExtractedRelation[];
  model_used: string;
}

export interface ImportanceScoringRequest {
  content: string;
  context?: any;
  scoring_method?: string;
}

export interface ImportanceScoringResponse {
  importance_score: number;
  scoring_method: string;
  factors: Record<string, number>;
  model_used: string;
}

export interface DuplicateDetectionRequest {
  content: string;
  candidate_pool?: string[];
  similarity_threshold?: number;
}

export interface DuplicateDetectionResult {
  is_duplicate: boolean;
  similarity_score: number;
  duplicate_of?: string;
  model_used: string;
}

export interface KnowledgeGraphConstructionRequest {
  content: string;
  entities?: any[];
  relations?: any[];
}

export interface KnowledgeGraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

export interface KnowledgeGraphEdge {
  source: string;
  target: string;
  label: string;
  properties: Record<string, any>;
}

export interface KnowledgeGraphConstructionResponse {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  model_used: string;
}

// Learning & Adaptation Types
export interface FeedbackSubmissionRequest {
  content_id: string;
  feedback_type: string;
  original_prediction?: any;
  user_correction?: any;
  confidence_rating?: number;
  additional_context?: any;
}

export interface FeedbackSubmissionResponse {
  feedback_id: string;
  status: string;
  message: string;
}

export interface FeedbackStats {
  total_feedback: number;
  feedback_by_type: Record<string, number>;
  average_confidence_rating?: number;
  feedback_trends: Array<{
    date: string;
    count: number;
  }>;
}

export interface ActiveLearningSampleSelectionRequest {
  candidate_content: any[];
  selection_strategy?: string;
  sample_size?: number;
  model_name?: string;
}

export interface ActiveLearningSample {
  content: any;
  selection_score: number;
  uncertainty_score?: number;
  diversity_score?: number;
}

export interface ActiveLearningSampleSelectionResponse {
  selected_samples: ActiveLearningSample[];
  selection_strategy: string;
  total_candidates: number;
}

export interface FineTuningJobRequest {
  base_model: string;
  target_model: string;
  training_data: any[];
  task_type?: string;
  fine_tuning_config?: any;
}

export interface FineTuningJobResponse {
  job_id: string;
  status: string;
  estimated_completion_time?: string;
  model_name: string;
}

export interface FineTuningJobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percentage?: number;
  current_epoch?: number;
  total_epochs?: number;
  loss?: number;
  validation_accuracy?: number;
  created_at: string;
  updated_at: string;
}

export interface PerformanceOptimizationRequest {
  task_type: string;
  content_data: any;
  constraints?: any;
}

export interface PerformanceOptimizationResponse {
  optimized_model: string;
  optimization_strategy: string;
  expected_improvement: number;
  reasoning: string;
}

export interface PerformanceMetricsResponse {
  metrics: Record<string, number>;
  trends: Array<{
    timestamp: string;
    metric: string;
    value: number;
  }>;
  recommendations: string[];
}

// ==========================================
// PHASE 4: SEARCH & DISCOVERY TYPES
// ==========================================

// Analytics Dashboard Types
export interface AnalyticsDashboardRequest {
  time_period_days?: number;
  metrics?: string[];
  filters?: any;
}

export interface AnalyticsDashboardResponse {
  summary: {
    total_content: number;
    total_users: number;
    total_interactions: number;
    average_session_duration: number;
  };
  metrics: Record<string, any>;
  charts: Array<{
    title: string;
    type: string;
    data: any;
  }>;
  insights: string[];
}

export interface ContentInsightsRequest {
  content_id?: string;
  time_period_days?: number;
  metrics?: string[];
}

export interface ContentInsightsResponse {
  content_id?: string;
  insights: Array<{
    type: string;
    title: string;
    description: string;
    value: any;
    trend?: string;
  }>;
  recommendations: string[];
}

export interface TrendAnalysisRequest {
  time_period_days?: number;
  metrics?: string[];
  trend_types?: string[];
}

export interface TrendAnalysisResponse {
  trends: Array<{
    metric: string;
    trend_type: string;
    direction: 'increasing' | 'decreasing' | 'stable';
    change_percentage: number;
    significance: number;
  }>;
  predictions: Array<{
    metric: string;
    predicted_value: number;
    confidence_interval: [number, number];
    time_horizon: string;
  }>;
}

export interface TrendingContentResponse {
  trending_items: Array<{
    content_id: string;
    content_type: string;
    trend_score: number;
    growth_rate: number;
    peak_time: string;
  }>;
}

export interface PerformanceAnalyticsRequest {
  time_period_days?: number;
  metrics?: string[];
}

export interface PerformanceAnalyticsResponse {
  performance_metrics: Record<string, number>;
  bottlenecks: Array<{
    component: string;
    metric: string;
    value: number;
    threshold: number;
    severity: string;
  }>;
  recommendations: string[];
}

export interface AnalyticsExportRequest {
  format?: string;
  time_period_days?: number;
  include_charts?: boolean;
}

export interface AnalyticsCapabilities {
  supported_metrics: string[];
  supported_formats: string[];
  max_time_period_days: number;
  real_time_available: boolean;
}

// Personalization Types
export interface PersonalizedRecommendationsRequest {
  user_id: string;
  limit?: number;
  context?: any;
}

export interface PersonalizedRecommendation {
  content_id: string;
  content_type: string;
  relevance_score: number;
  reasoning: string;
  metadata?: any;
}

export interface PersonalizedRecommendationsResponse {
  recommendations: PersonalizedRecommendation[];
  personalization_strategy: string;
  user_profile_summary?: any;
}

export interface InteractionTrackingRequest {
  user_id: string;
  content_id: string;
  interaction_type: string;
  metadata?: any;
}

export interface InteractionTrackingResponse {
  interaction_id: string;
  status: string;
  user_profile_updated: boolean;
}

export interface UserInsightsResponse {
  user_id: string;
  insights: Array<{
    type: string;
    title: string;
    description: string;
    value: any;
  }>;
  preferences: Record<string, any>;
  behavior_patterns: Array<{
    pattern: string;
    frequency: number;
    last_observed: string;
  }>;
}

export interface UserProfileResetResponse {
  user_id: string;
  status: string;
  message: string;
}

export interface PersonalizationCapabilities {
  supported_interaction_types: string[];
  personalization_strategies: string[];
  real_time_updates: boolean;
  privacy_features: string[];
}

export interface PersonalizationStats {
  total_users: number;
  total_interactions: number;
  average_recommendations_per_user: number;
  personalization_accuracy: number;
  last_updated: string;
}

export interface BulkInteractionTrackingRequest {
  interactions: Array<{
    user_id: string;
    content_id: string;
    interaction_type: string;
    metadata?: any;
  }>;
}

export interface BulkInteractionTrackingResponse {
  processed_interactions: number;
  failed_interactions: number;
  errors?: string[];
}

export interface TrendingPersonalizedContentResponse {
  user_id: string;
  trending_content: Array<{
    content_id: string;
    content_type: string;
    trend_score: number;
    personalized_score: number;
  }>;
}

// Trend Detection Types
export interface AdvancedTrendAnalysisRequest {
  metric: string;
  time_period_days?: number;
  analysis_type?: string;
}

export interface AdvancedTrendAnalysisResponse {
  metric: string;
  analysis_type: string;
  trend_direction: 'up' | 'down' | 'stable';
  trend_strength: number;
  seasonality_detected: boolean;
  anomalies: Array<{
    timestamp: string;
    value: number;
    expected_value: number;
    deviation: number;
  }>;
  forecast: Array<{
    timestamp: string;
    predicted_value: number;
    confidence_lower: number;
    confidence_upper: number;
  }>;
}

export interface PredictiveInsightsRequest {
  metrics: string[];
  prediction_horizon?: number;
}

export interface PredictiveInsight {
  metric: string;
  insight_type: string;
  description: string;
  confidence: number;
  impact: string;
  recommended_actions: string[];
}

export interface PredictiveInsightsResponse {
  insights: PredictiveInsight[];
  prediction_horizon: string;
  model_accuracy: number;
}

export interface AnomalyDetectionRequest {
  metric: string;
  time_period_days?: number;
  sensitivity?: number;
}

export interface DetectedAnomaly {
  timestamp: string;
  metric_value: number;
  expected_value: number;
  deviation: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
}

export interface AnomalyDetectionResponse {
  anomalies: DetectedAnomaly[];
  total_anomalies: number;
  detection_sensitivity: number;
  time_period_analyzed: string;
}

export interface DetectedTrendsResponse {
  trends: Array<{
    trend_id: string;
    metric: string;
    trend_type: string;
    start_date: string;
    end_date: string;
    strength: number;
    description: string;
  }>;
}

export interface TrendDetailsResponse {
  trend_id: string;
  metric: string;
  trend_type: string;
  start_date: string;
  end_date: string;
  strength: number;
  description: string;
  data_points: Array<{
    timestamp: string;
    value: number;
  }>;
  analysis: {
    slope: number;
    r_squared: number;
    seasonality: boolean;
    outliers: number;
  };
}

export interface MetricForecastRequest {
  metric: string;
  forecast_periods?: number;
  confidence_level?: number;
}

export interface MetricForecastResponse {
  metric: string;
  forecast: Array<{
    timestamp: string;
    predicted_value: number;
    confidence_lower: number;
    confidence_upper: number;
  }>;
  model_used: string;
  accuracy_metrics: {
    mape: number;
    rmse: number;
    r_squared: number;
  };
}

export interface TrendsCapabilities {
  supported_metrics: string[];
  supported_analysis_types: string[];
  max_time_period_days: number;
  real_time_detection: boolean;
}

export interface TrendsByPatternResponse {
  pattern_type: string;
  trends: Array<{
    trend_id: string;
    metric: string;
    pattern_score: number;
    description: string;
  }>;
}

export interface SpecificMetricAnalysisRequest {
  metric: string;
  analysis_type: string;
  parameters?: any;
}

export interface SpecificMetricAnalysisResponse {
  metric: string;
  analysis_type: string;
  results: any;
  confidence: number;
  interpretation: string;
}

export interface TrendAlertsResponse {
  alerts: Array<{
    alert_id: string;
    trend_id: string;
    alert_type: string;
    severity: string;
    message: string;
    triggered_at: string;
    acknowledged: boolean;
  }>;
}

// Search Analytics Types
export interface SearchAnalyticsReportRequest {
  time_period_days?: number;
  include_performance?: boolean;
  include_user_behavior?: boolean;
}

export interface SearchAnalyticsReportResponse {
  report_id: string;
  time_period: string;
  summary: {
    total_searches: number;
    unique_queries: number;
    average_results_per_search: number;
    average_response_time_ms: number;
  };
  performance_metrics: Record<string, number>;
  user_behavior: Record<string, any>;
  recommendations: string[];
}

export interface SearchEventTrackingRequest {
  query: string;
  results_count: number;
  response_time_ms: number;
  user_id?: string;
  session_id?: string;
}

export interface SearchEventTrackingResponse {
  event_id: string;
  status: string;
  query_analyzed: boolean;
}

export interface SearchSuggestionsRequest {
  query: string;
  limit?: number;
  context?: any;
}

export interface SearchSuggestion {
  suggestion: string;
  relevance_score: number;
  popularity_score: number;
  category?: string;
}

export interface SearchSuggestionsResponse {
  suggestions: SearchSuggestion[];
  query_analyzed: string;
  total_suggestions: number;
}

export interface SearchInsightsRequest {
  time_period_days?: number;
  query_patterns?: boolean;
  performance_metrics?: boolean;
}

export interface SearchInsightsResponse {
  insights: Array<{
    type: string;
    title: string;
    description: string;
    value: any;
    trend?: string;
  }>;
  query_patterns: Array<{
    pattern: string;
    frequency: number;
    average_performance: number;
  }>;
  performance_insights: Array<{
    metric: string;
    current_value: number;
    target_value: number;
    status: string;
  }>;
}

export interface SearchPerformanceResponse {
  performance_metrics: Record<string, number>;
  bottlenecks: Array<{
    component: string;
    metric: string;
    value: number;
    threshold: number;
  }>;
  optimization_opportunities: string[];
}

export interface SearchQueriesResponse {
  queries: Array<{
    query: string;
    frequency: number;
    average_results: number;
    average_response_time_ms: number;
    last_executed: string;
  }>;
  total_queries: number;
  time_period: string;
}

export interface UserSearchBehaviorResponse {
  user_id?: string;
  search_behavior: {
    total_searches: number;
    average_query_length: number;
    preferred_categories: string[];
    search_patterns: Array<{
      pattern: string;
      frequency: number;
    }>;
    performance_trends: Array<{
      date: string;
      average_response_time: number;
      satisfaction_score?: number;
    }>;
  };
}

export interface SearchOptimizationInsightsResponse {
  optimization_insights: Array<{
    type: string;
    title: string;
    description: string;
    impact: string;
    implementation_effort: string;
  }>;
  current_optimization_score: number;
  recommended_actions: string[];
}

export interface SearchDataExportRequest {
  format?: string;
  time_period_days?: number;
  include_raw_queries?: boolean;
}

export interface SearchAnalyticsCapabilities {
  supported_export_formats: string[];
  max_time_period_days: number;
  real_time_tracking: boolean;
  advanced_analytics: boolean;
}

export interface PopularQueriesResponse {
  popular_queries: Array<{
    query: string;
    search_count: number;
    average_results: number;
    trend: string;
  }>;
  time_period: string;
  total_unique_queries: number;
}

export interface SearchPerformanceSummaryResponse {
  summary: {
    total_searches: number;
    average_response_time_ms: number;
    success_rate: number;
    user_satisfaction_score?: number;
  };
  trends: Array<{
    date: string;
    searches: number;
    average_response_time: number;
  }>;
  top_performing_queries: Array<{
    query: string;
    response_time_ms: number;
    results_count: number;
  }>;
}

export interface BulkSearchEventTrackingRequest {
  events: Array<{
    query: string;
    results_count: number;
    response_time_ms: number;
    user_id?: string;
    session_id?: string;
  }>;
}

export interface BulkSearchEventTrackingResponse {
  processed_events: number;
  failed_events: number;
  errors?: string[];
}

export interface RealTimeSearchMetricsResponse {
  current_metrics: Record<string, number>;
  recent_trends: Array<{
    timestamp: string;
    metric: string;
    value: number;
  }>;
  active_users: number;
  queue_depth: number;
}

// ==========================================
// PHASE 5: ORCHESTRATION & AUTOMATION TYPES
// ==========================================

// Workflow Automation Types
export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  steps: any;
  priority?: string;
  max_execution_time?: number;
  resource_requirements?: any;
  created_at: string;
  updated_at: string;
  status: string;
}

export interface WorkflowDefinitionsResponse {
  definitions: WorkflowDefinition[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  execution_time_ms?: number;
  current_step?: string;
  progress_percentage?: number;
  results?: any;
  error_message?: string;
}

export interface WorkflowExecutionsResponse {
  executions: WorkflowExecution[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface WorkflowExecutionDetails {
  execution: WorkflowExecution;
  steps: Array<{
    step_id: string;
    name: string;
    status: string;
    started_at?: string;
    completed_at?: string;
    execution_time_ms?: number;
    output?: any;
    error_message?: string;
  }>;
  logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    step_id?: string;
  }>;
}

export interface WorkflowSchedule {
  id: string;
  workflow_id: string;
  trigger_type: string;
  cron_expression?: string;
  parameters?: any;
  is_active: boolean;
  next_run?: string;
  last_run?: string;
  created_at: string;
}

export interface WorkflowSchedulesResponse {
  schedules: WorkflowSchedule[];
  total_count: number;
}

export interface ConditionalLogicEvaluationRequest {
  workflow_id: string;
  step_id: string;
  conditions: any[];
  context: any;
}

export interface ConditionalLogicEvaluationResponse {
  evaluation_result: boolean;
  matched_conditions: string[];
  next_step?: string;
  reasoning: string;
}

export interface WorkflowHealthResponse {
  status: string;
  uptime_percentage: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_execution_time_ms: number;
  active_executions: number;
  queued_executions: number;
}

export interface WorkflowCapabilities {
  supported_step_types: string[];
  max_concurrent_executions: number;
  max_workflow_steps: number;
  supported_triggers: string[];
  scheduling_enabled: boolean;
}

export interface WorkflowStats {
  total_workflows: number;
  active_workflows: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_execution_time_ms: number;
  most_used_workflows: Array<{
    workflow_id: string;
    name: string;
    execution_count: number;
  }>;
}

// Integration Layer Types
export interface IntegrationHealthResponse {
  status: string;
  components: Record<string, {
    status: string;
    uptime_percentage: number;
    last_check: string;
  }>;
  overall_health_score: number;
}

export interface IntegrationCapabilities {
  supported_integrations: string[];
  webhook_support: boolean;
  queue_support: boolean;
  load_balancing: boolean;
  api_gateway: boolean;
}

// API Gateway Types
export interface ApiGatewayStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time_ms: number;
  requests_per_minute: number;
  error_rate: number;
  active_connections: number;
}

export interface ApiGatewayConfig {
  rate_limits: Record<string, number>;
  cors_settings: any;
  authentication_required: boolean;
  logging_level: string;
}

// Webhooks Types
export interface Webhook {
  id: string;
  url: string;
  events: string[];
  secret?: string;
  headers?: any;
  is_active: boolean;
  created_at: string;
  last_triggered?: string;
  failure_count: number;
}

export interface WebhooksResponse {
  webhooks: Webhook[];
  total_count: number;
}

export interface WebhookSubscriptionRequest {
  url: string;
  events: string[];
  secret?: string;
  headers?: any;
}

export interface WebhookSubscriptionResponse {
  webhook_id: string;
  status: string;
  message: string;
}

export interface WebhookTestResponse {
  success: boolean;
  response_status?: number;
  response_body?: any;
  error_message?: string;
}

export interface WebhookDeliveriesResponse {
  deliveries: Array<{
    id: string;
    webhook_id: string;
    event: string;
    status: string;
    attempted_at: string;
    response_status?: number;
    error_message?: string;
  }>;
  total_count: number;
}

// Queues Types
export interface Queue {
  name: string;
  type: string;
  max_size: number;
  current_size: number;
  processing_rate: number;
  error_rate: number;
  is_active: boolean;
}

export interface QueuesResponse {
  queues: Queue[];
  total_count: number;
}

export interface QueueStats {
  queue_name: string;
  total_messages: number;
  processed_messages: number;
  failed_messages: number;
  average_processing_time_ms: number;
  oldest_message_age_seconds: number;
  active_consumers: number;
}

export interface QueueTaskEnqueueRequest {
  type: string;
  priority?: string;
  data: any;
  callback_url?: string;
}

export interface QueueTaskEnqueueResponse {
  task_id: string;
  queue_name: string;
  position_in_queue: number;
  estimated_processing_time_seconds?: number;
}

export interface QueueTaskDequeueResponse {
  task_id: string;
  type: string;
  priority: string;
  data: any;
  enqueued_at: string;
  retry_count: number;
}

export interface QueueConfigUpdateRequest {
  max_size?: number;
  processing_timeout_seconds?: number;
  retry_policy?: any;
  dead_letter_queue?: string;
}

// Load Balancing Types
export interface LoadBalancerStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time_ms: number;
  active_backends: number;
  total_backends: number;
  load_distribution: Record<string, number>;
}

export interface BackendService {
  id: string;
  url: string;
  supported_request_types: string[];
  max_concurrent_requests?: number;
  health_check_url?: string;
  is_active: boolean;
  current_load: number;
  last_health_check: string;
  health_status: string;
}

export interface BackendServicesResponse {
  backends: BackendService[];
  total_count: number;
}

export interface BackendServiceRegistrationRequest {
  id: string;
  url: string;
  supported_request_types: string[];
  max_concurrent_requests?: number;
  health_check_url?: string;
}

export interface BackendServiceRegistrationResponse {
  backend_id: string;
  status: string;
  message: string;
}

export interface RequestRoutingRequest {
  request_type: string;
  data: any;
  priority?: string;
}

export interface RequestRoutingResponse {
  backend_id: string;
  backend_url: string;
  routing_reason: string;
  estimated_response_time_ms?: number;
}

export interface LoadBalancerHealthResponse {
  status: string;
  active_backends: number;
  total_backends: number;
  load_distribution_score: number;
  failover_ready: boolean;
}

// ==========================================
// SECRETS MANAGEMENT TYPES
// ==========================================

export interface AgentSecret {
  secret_id: string;
  secret_key: string;
  description?: string;
  created_at: string;
  updated_at: string;
  last_accessed?: string;
}

export interface AgentSecretsResponse {
  secrets: AgentSecret[];
  total_count: number;
}

export interface AgentSecretCreateRequest {
  secret_key: string;
  secret_value: string;
  description?: string;
}

export interface AgentSecretCreateResponse {
  secret_id: string;
  status: string;
  message: string;
}

export interface AgentSecretValueResponse {
  secret_key: string;
  secret_value: string;
  decrypted: boolean;
}

// ==========================================
// DOCUMENTATION TYPES
// ==========================================

export interface AgentCreationGuide {
  title: string;
  sections: Array<{
    title: string;
    content: string;
    examples?: any[];
  }>;
  best_practices: string[];
  troubleshooting: Array<{
    issue: string;
    solution: string;
  }>;
}

export interface FrontendIntegrationGuide {
  title: string;
  sections: Array<{
    title: string;
    content: string;
    code_examples?: Record<string, string>;
  }>;
  api_endpoints: Array<{
    endpoint: string;
    method: string;
    description: string;
    parameters?: any;
    response?: any;
  }>;
  integration_patterns: Array<{
    pattern: string;
    description: string;
    example: string;
  }>;
}

export interface ExampleConfiguration {
  title: string;
  description: string;
  category: string;
  configuration: any;
  use_cases: string[];
  prerequisites?: string[];
}

export interface AgentTypeDocumentation {
  agent_type: string;
  name: string;
  description: string;
  capabilities: string[];
  configuration_options: Record<string, any>;
  example_usage: any;
  best_practices: string[];
  limitations?: string[];
}