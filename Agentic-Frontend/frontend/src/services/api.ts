import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import type { Agent, Task, ApiError, LogEntry, ChatSession, ChatMessage, ChatSessionStats, CreateChatSessionRequest, SendChatMessageRequest, ChatMessageResponse, ChatModelsResponse, ChatTemplatesResponse } from '../types';

class ApiClient {
  private client: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
    if (!apiBaseUrl) {
      throw new Error('VITE_API_BASE_URL environment variable is not defined. Please check your .env file.');
    }

    this.client = axios.create({
      baseURL: apiBaseUrl,
      timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '300000'), // Configurable timeout with fallback
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
    this.loadAuthToken();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearAuthToken();
          window.location.href = '/login';
        }
        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private handleApiError(error: AxiosError): ApiError {
    // Handle CORS/network errors
    if (!error.response) {
      if (error.code === 'ERR_NETWORK') {
        return {
          detail: 'Network error: Unable to connect to the server. Please check your internet connection and server status.',
          status_code: 0,
        };
      }
      return {
        detail: `Connection error: ${error.message}`,
        status_code: 0,
      };
    }

    // Handle CORS preflight errors
    if (error.response.status === 0) {
      return {
        detail: 'CORS error: The server is not configured to accept requests from this origin. Please check the server CORS configuration.',
        status_code: 0,
      };
    }

    if (error.response?.data) {
      return error.response.data as ApiError;
    }

    return {
      detail: error.message || 'An unexpected error occurred',
      status_code: error.response?.status || 500,
    };
  }

  private loadAuthToken() {
    this.authToken = localStorage.getItem('auth_token');
  }

  setAuthToken(token: string) {
    this.authToken = token;
    localStorage.setItem('auth_token', token);
  }

  clearAuthToken() {
    this.authToken = null;
    localStorage.removeItem('auth_token');
  }

  getAuthToken() {
    return this.authToken;
  }

  // Health endpoints
  async getHealth() {
    const response = await this.client.get('/api/v1/health');
    return response.data;
  }

  async getReadiness() {
    const response = await this.client.get('/api/v1/ready');
    return response.data;
  }

  async getMetrics() {
    const response = await this.client.get('/api/v1/metrics');
    return response.data;
  }

  // Authentication
  async login(username: string, password: string) {
    // Use JSON login endpoint as recommended for frontend
    const response = await this.client.post('/api/v1/auth/login-json', {
      username,
      password,
    });

    if (response.data.access_token) {
      this.setAuthToken(response.data.access_token);
    }

    return response.data;
  }

  async logout() {
    try {
      await this.client.post('/api/v1/auth/logout');
    } finally {
      this.clearAuthToken();
    }
  }

  async createUser(userData: {
    username: string;
    email: string;
    password: string;
    is_active?: boolean;
    is_superuser?: boolean;
  }) {
    const response = await this.client.post('/api/v1/auth/users', userData);
    return response.data;
  }

  async getUsers() {
    const response = await this.client.get('/api/v1/auth/users');
    return response.data;
  }

  async getUser(userId: string) {
    const response = await this.client.get(`/api/v1/auth/users/${userId}`);
    return response.data;
  }

  async updateUser(userId: string, userData: Partial<{
    username: string;
    email: string;
    is_active: boolean;
    is_superuser: boolean;
  }>) {
    const response = await this.client.put(`/api/v1/auth/users/${userId}`, userData);
    return response.data;
  }

  async deleteUser(userId: string) {
    await this.client.delete(`/api/v1/auth/users/${userId}`);
  }

  async changePassword(currentPassword: string, newPassword: string) {
    const response = await this.client.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  }

  // Agent management
  async getAgents(): Promise<Agent[]> {
    const response = await this.client.get('/api/v1/agents');
    return response.data;
  }

  async getAgent(agentId: string): Promise<Agent> {
    const response = await this.client.get(`/api/v1/agents/${agentId}`);
    return response.data;
  }

  async createAgent(agentData: Partial<Agent>): Promise<Agent> {
    const response = await this.client.post('/api/v1/agents/create', agentData);
    return response.data;
  }

  async updateAgent(agentId: string, agentData: Partial<Agent>): Promise<Agent> {
    const response = await this.client.put(`/api/v1/agents/${agentId}`, agentData);
    return response.data;
  }

  async deleteAgent(agentId: string): Promise<void> {
    await this.client.delete(`/api/v1/agents/${agentId}`);
  }

  // Task management
  async getTasks(): Promise<Task[]> {
    const response = await this.client.get('/api/v1/tasks');
    return response.data;
  }

  async getTask(taskId: string): Promise<Task> {
    const response = await this.client.get(`/api/v1/tasks/${taskId}/status`);
    return response.data;
  }

  async runTask(taskData: { agent_id: string; input: Record<string, any> }): Promise<Task> {
    const response = await this.client.post('/api/v1/tasks/run', taskData);
    return response.data;
  }

  async cancelTask(taskId: string): Promise<void> {
    await this.client.delete(`/api/v1/tasks/${taskId}`);
  }

  // Logging
  async getTaskLogs(taskId: string): Promise<LogEntry[]> {
    const response = await this.client.get(`/api/v1/logs/${taskId}`);
    return response.data;
  }

  async getHistoricalLogs(params?: {
    agent_id?: string;
    level?: string;
    search?: string;
    limit?: number;
  }): Promise<LogEntry[]> {
    const response = await this.client.get('/api/v1/logs/history', { params });
    return response.data;
  }

  // Security endpoints
  async getSecurityStatus() {
    const response = await this.client.get('/api/v1/security/status');
    return response.data;
  }

  async getSecurityHealth() {
    const response = await this.client.get('/api/v1/security/health');
    return response.data;
  }

  async getSecurityIncidents(params?: {
    limit?: number;
    severity?: string;
    resolved?: boolean;
    agent_id?: string;
  }) {
    const response = await this.client.get('/api/v1/security/incidents', { params });
    return response.data;
  }

  async resolveSecurityIncident(incidentId: string, resolutionNotes: string) {
    const response = await this.client.post(`/api/v1/security/incidents/${incidentId}/resolve`, {
      resolution_notes: resolutionNotes,
    });
    return response.data;
  }


  async validateToolExecution(validationData: {
    agent_id: string;
    tool_name: string;
    input_data: Record<string, any>;
  }) {
    const response = await this.client.post('/api/v1/security/validate-tool-execution', validationData);
    return response.data;
  }

  async getAgentSecurityReport(agentId: string) {
    const response = await this.client.get(`/api/v1/security/agents/${agentId}/report`);
    return response.data;
  }

  // System metrics endpoints
  async getSystemMetrics() {
    const response = await this.client.get('/api/v1/system/metrics');
    return response.data;
  }

  async getSystemMetricsCpu() {
    const response = await this.client.get('/api/v1/system/metrics/cpu');
    return response.data;
  }

  async getSystemMetricsMemory() {
    const response = await this.client.get('/api/v1/system/metrics/memory');
    return response.data;
  }

  async getSystemMetricsDisk() {
    const response = await this.client.get('/api/v1/system/metrics/disk');
    return response.data;
  }

  async getSystemMetricsNetwork() {
    const response = await this.client.get('/api/v1/system/metrics/network');
    return response.data;
  }

  async getSystemMetricsGpu() {
    const response = await this.client.get('/api/v1/system/metrics/gpu');
    return response.data;
  }

  async getSystemMetricsLoad() {
    const response = await this.client.get('/api/v1/system/metrics/load');
    return response.data;
  }

  async getSystemMetricsSwap() {
    const response = await this.client.get('/api/v1/system/metrics/swap');
    return response.data;
  }

  async getSystemInfo() {
    const response = await this.client.get('/api/v1/system/info');
    return response.data;
  }

  // Ollama model management endpoints
  async getOllamaModels() {
    const response = await this.client.get('/api/v1/ollama/models');
    return response.data;
  }

  async getOllamaModelNames() {
    const response = await this.client.get('/api/v1/ollama/models/names');
    return response.data;
  }

  async getOllamaHealth() {
    const response = await this.client.get('/api/v1/ollama/health');
    return response.data;
  }

  async pullOllamaModel(modelName: string) {
    const response = await this.client.post(`/api/v1/ollama/models/pull/${modelName}`);
    return response.data;
  }

  // Dashboard data
  async getDashboardSummary() {
    const response = await this.client.get('/api/v1/dashboard/summary');
    return response.data;
  }

  // Chat system endpoints
  async createChatSession(sessionData: CreateChatSessionRequest): Promise<ChatSession> {
    const response = await this.client.post('/api/v1/chat/sessions', sessionData);
    return response.data;
  }

  async getChatSessions(): Promise<ChatSession[]> {
    const response = await this.client.get('/api/v1/chat/sessions');
    return response.data;
  }

  async getChatSession(sessionId: string): Promise<ChatSession> {
    const response = await this.client.get(`/api/v1/chat/sessions/${sessionId}`);
    return response.data;
  }

  async getChatSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const response = await this.client.get(`/api/v1/chat/sessions/${sessionId}/messages`);
    return response.data;
  }

  async sendChatMessage(sessionId: string, messageData: SendChatMessageRequest): Promise<ChatMessageResponse> {
    const response = await this.client.post(`/api/v1/chat/sessions/${sessionId}/messages`, messageData);
    return response.data;
  }

  async updateChatSessionStatus(sessionId: string, status: string): Promise<ChatSession> {
    const response = await this.client.put(`/api/v1/chat/sessions/${sessionId}/status`, { status });
    return response.data;
  }

  async getChatSessionStats(sessionId: string): Promise<ChatSessionStats> {
    const response = await this.client.get(`/api/v1/chat/sessions/${sessionId}/stats`);
    return response.data;
  }

  async deleteChatSession(sessionId: string): Promise<void> {
    await this.client.delete(`/api/v1/chat/sessions/${sessionId}`);
  }

  async getChatTemplates(): Promise<ChatTemplatesResponse> {
    const response = await this.client.get('/api/v1/chat/templates');
    return response.data;
  }

  async getChatModels(): Promise<ChatModelsResponse> {
    const response = await this.client.get('/api/v1/chat/models');
    return response.data;
  }

  // ==========================================
  // PHASE 1: FOUNDATION ENHANCEMENT
  // ==========================================

  // Agentic HTTP Client Framework (Phase 1.2)
  async makeAgenticHttpRequest(requestData: {
    method: string;
    url: string;
    headers?: Record<string, string>;
    data?: any;
    json_data?: any;
    auth?: any;
    timeout?: number;
    retry_config?: any;
    rate_limit?: any;
  }) {
    const response = await this.client.post('/api/v1/http/request', requestData);
    return response.data;
  }

  async getHttpClientMetrics() {
    const response = await this.client.get('/api/v1/http/metrics');
    return response.data;
  }

  async getHttpRequestDetails(requestId: string) {
    const response = await this.client.get(`/api/v1/http/requests/${requestId}`);
    return response.data;
  }

  async getHttpClientHealth() {
    const response = await this.client.get('/api/v1/http/health');
    return response.data;
  }

  async streamDownload(downloadData: {
    url: string;
    destination_path: string;
    progress_callback_url?: string;
  }) {
    const response = await this.client.post('/api/v1/http/stream-download', downloadData);
    return response.data;
  }

  // Dynamic Model Selection System (Phase 1.3)
  async getAvailableModels() {
    const response = await this.client.get('/api/v1/models/available');
    return response.data;
  }

  async selectOptimalModel(selectionData: {
    task_type: string;
    content_type: string;
    priority?: string;
    max_tokens?: number;
    requirements?: any;
  }) {
    const response = await this.client.post('/api/v1/models/select', selectionData);
    return response.data;
  }

  async getModelPerformanceMetrics(params?: {
    task_type?: string;
    limit?: number;
  }) {
    const response = await this.client.get('/api/v1/models/performance', { params });
    return response.data;
  }

  async getModelStats(modelName: string) {
    const response = await this.client.get(`/api/v1/models/${modelName}/stats`);
    return response.data;
  }

  async refreshModelRegistry() {
    const response = await this.client.post('/api/v1/models/refresh');
    return response.data;
  }

  // Multi-Modal Content Framework (Phase 1.4)
  async processContent(contentData: {
    content: any;
    content_type?: string;
    operations?: string[];
    metadata?: any;
  }) {
    const response = await this.client.post('/api/v1/content/process', contentData);
    return response.data;
  }

  async getProcessedContent(contentId: string) {
    const response = await this.client.get(`/api/v1/content/${contentId}`);
    return response.data;
  }

  async batchProcessContent(batchData: {
    items: any[];
    operations?: string[];
    parallel?: boolean;
  }) {
    const response = await this.client.post('/api/v1/content/batch', batchData);
    return response.data;
  }

  async getContentCacheStats() {
    const response = await this.client.get('/api/v1/content/cache/stats');
    return response.data;
  }

  // Semantic Processing (Phase 1.5)
  async generateEmbeddings(embeddingData: {
    text: string;
    model?: string;
    dimensions?: number;
  }) {
    const response = await this.client.post('/api/v1/semantic/embed', embeddingData);
    return response.data;
  }

  async performSemanticSearch(searchData: {
    query: string;
    limit?: number;
    threshold?: number;
    filters?: any;
  }) {
    const response = await this.client.post('/api/v1/semantic/search', searchData);
    return response.data;
  }

  async clusterEmbeddings(clusterData: {
    embeddings: number[][];
    method?: string;
    n_clusters?: number;
  }) {
    const response = await this.client.post('/api/v1/semantic/cluster', clusterData);
    return response.data;
  }

  async getContentQualityScore(contentId: string) {
    const response = await this.client.get(`/api/v1/semantic/quality/${contentId}`);
    return response.data;
  }

  async intelligentTextChunking(chunkData: {
    text: string;
    strategy?: string;
    chunk_size?: number;
    overlap?: number;
  }) {
    const response = await this.client.post('/api/v1/semantic/chunk', chunkData);
    return response.data;
  }

  // ==========================================
  // PHASE 2: CONTENT INGESTION & PROCESSING
  // ==========================================

  // Universal Content Connectors (Phase 2)
  async discoverContent(discoveryData: {
    sources: Array<{
      type: string;
      config: any;
    }>;
  }) {
    const response = await this.client.post('/api/v1/content/discover', discoveryData);
    return response.data;
  }

  async discoverWebContent(webConfig: {
    feed_url?: string;
    url?: string;
    selectors?: any;
    max_items?: number;
  }) {
    const response = await this.client.post('/api/v1/content/connectors/web', webConfig);
    return response.data;
  }

  async discoverSocialContent(socialConfig: {
    platform: string;
    query?: string;
    username?: string;
    max_items?: number;
  }) {
    const response = await this.client.post('/api/v1/content/connectors/social', socialConfig);
    return response.data;
  }

  async discoverCommunicationContent(commConfig: {
    platform: string;
    channel?: string;
    token?: string;
    max_messages?: number;
  }) {
    const response = await this.client.post('/api/v1/content/connectors/communication', commConfig);
    return response.data;
  }

  async discoverFilesystemContent(fsConfig: {
    directory?: string;
    bucket_name?: string;
    prefix?: string;
    file_patterns?: string[];
    recursive?: boolean;
    max_keys?: number;
  }) {
    const response = await this.client.post('/api/v1/content/connectors/filesystem', fsConfig);
    return response.data;
  }

  // ==========================================
  // PHASE 3: INTELLIGENCE & LEARNING
  // ==========================================

  // Vision AI Integration (Phase 3.1)
  async analyzeImage(analysisData: {
    image_url?: string;
    image_data?: string;
    tasks: string[];
    model?: string;
    options?: any;
  }) {
    const response = await this.client.post('/api/v1/vision/analyze', analysisData);
    return response.data;
  }

  async detectObjectsInImage(detectionData: {
    image_url?: string;
    image_data?: string;
    confidence_threshold?: number;
    max_objects?: number;
  }) {
    const response = await this.client.post('/api/v1/vision/detect-objects', detectionData);
    return response.data;
  }

  async generateImageCaption(captionData: {
    image_url?: string;
    image_data?: string;
    model?: string;
  }) {
    const response = await this.client.post('/api/v1/vision/caption', captionData);
    return response.data;
  }

  async findSimilarImages(searchData: {
    image_url?: string;
    image_data?: string;
    limit?: number;
    threshold?: number;
  }) {
    const response = await this.client.post('/api/v1/vision/search', searchData);
    return response.data;
  }

  async extractTextFromImage(ocrData: {
    image_url?: string;
    image_data?: string;
    language?: string;
  }) {
    const response = await this.client.post('/api/v1/vision/ocr', ocrData);
    return response.data;
  }

  async getVisionModels() {
    const response = await this.client.get('/api/v1/vision/models');
    return response.data;
  }

  // Audio AI Integration (Phase 3.1)
  async transcribeAudio(transcriptionData: {
    audio_url?: string;
    audio_data?: string;
    language?: string;
    model?: string;
    options?: any;
  }) {
    const response = await this.client.post('/api/v1/audio/transcribe', transcriptionData);
    return response.data;
  }

  async identifySpeakersInAudio(identificationData: {
    audio_url?: string;
    audio_data?: string;
    max_speakers?: number;
  }) {
    const response = await this.client.post('/api/v1/audio/identify-speaker', identificationData);
    return response.data;
  }

  async analyzeEmotionInSpeech(emotionData: {
    audio_url?: string;
    audio_data?: string;
    model?: string;
  }) {
    const response = await this.client.post('/api/v1/audio/analyze-emotion', emotionData);
    return response.data;
  }

  async classifyAudioContent(classificationData: {
    audio_url?: string;
    audio_data?: string;
    categories?: string[];
  }) {
    const response = await this.client.post('/api/v1/audio/classify', classificationData);
    return response.data;
  }

  async analyzeMusicFeatures(musicData: {
    audio_url?: string;
    audio_data?: string;
    features?: string[];
  }) {
    const response = await this.client.post('/api/v1/audio/analyze-music', musicData);
    return response.data;
  }

  async getAudioModels() {
    const response = await this.client.get('/api/v1/audio/models');
    return response.data;
  }

  // Cross-Modal Processing (Phase 3.1)
  async alignTextWithImages(alignmentData: {
    text: string;
    images: string[];
    model?: string;
  }) {
    const response = await this.client.post('/api/v1/crossmodal/align', alignmentData);
    return response.data;
  }

  async correlateAudioWithVisual(correlateData: {
    audio_url?: string;
    image_url?: string;
    correlation_type?: string;
  }) {
    const response = await this.client.post('/api/v1/crossmodal/correlate', correlateData);
    return response.data;
  }

  async performCrossModalSearch(searchData: {
    query: string;
    modalities: string[];
    search_type?: string;
    limit?: number;
  }) {
    const response = await this.client.post('/api/v1/crossmodal/search', searchData);
    return response.data;
  }

  async fuseModalities(fusionData: {
    modalities: Array<{
      type: string;
      data: any;
    }>;
    fusion_method?: string;
  }) {
    const response = await this.client.post('/api/v1/crossmodal/fuse', fusionData);
    return response.data;
  }

  async getCrossModalModels() {
    const response = await this.client.get('/api/v1/crossmodal/models');
    return response.data;
  }

  // Quality Enhancement (Phase 3.1)
  async enhanceContent(enhancementData: {
    content: any;
    content_type: string;
    enhancement_type?: string;
  }) {
    const response = await this.client.post('/api/v1/quality/enhance', enhancementData);
    return response.data;
  }

  async correctContent(correctionData: {
    content: any;
    content_type: string;
    correction_rules?: any;
  }) {
    const response = await this.client.post('/api/v1/quality/correct', correctionData);
    return response.data;
  }

  async getQualityMetrics() {
    const response = await this.client.get('/api/v1/quality/metrics');
    return response.data;
  }

  // Semantic Understanding Engine (Phase 3.2)
  async classifyContent(classificationData: {
    content: string;
    categories?: string[];
    confidence_threshold?: number;
  }) {
    const response = await this.client.post('/api/v1/semantic/classify', classificationData);
    return response.data;
  }

  async extractRelations(extractionData: {
    content: string;
    entity_types?: string[];
    relation_types?: string[];
  }) {
    const response = await this.client.post('/api/v1/semantic/extract-relations', extractionData);
    return response.data;
  }

  async scoreContentImportance(scoringData: {
    content: string;
    context?: any;
    scoring_method?: string;
  }) {
    const response = await this.client.post('/api/v1/semantic/score-importance', scoringData);
    return response.data;
  }

  async detectDuplicates(detectionData: {
    content: string;
    candidate_pool?: string[];
    similarity_threshold?: number;
  }) {
    const response = await this.client.post('/api/v1/semantic/detect-duplicates', detectionData);
    return response.data;
  }

  async buildKnowledgeGraph(kgData: {
    content: string;
    entities?: any[];
    relations?: any[];
  }) {
    const response = await this.client.post('/api/v1/semantic/build-knowledge-graph', kgData);
    return response.data;
  }

  // Learning & Adaptation (Phase 3.3)
  async submitFeedback(feedbackData: {
    content_id: string;
    feedback_type: string;
    original_prediction?: any;
    user_correction?: any;
    confidence_rating?: number;
    additional_context?: any;
  }) {
    const response = await this.client.post('/api/v1/feedback/submit', feedbackData);
    return response.data;
  }

  async getFeedbackStats() {
    const response = await this.client.get('/api/v1/feedback/stats');
    return response.data;
  }

  async selectActiveLearningSamples(selectionData: {
    candidate_content: any[];
    selection_strategy?: string;
    sample_size?: number;
    model_name?: string;
  }) {
    const response = await this.client.post('/api/v1/active-learning/select-samples', selectionData);
    return response.data;
  }

  async startFineTuningJob(jobData: {
    base_model: string;
    target_model: string;
    training_data: any[];
    task_type?: string;
    fine_tuning_config?: any;
  }) {
    const response = await this.client.post('/api/v1/fine-tuning/start', jobData);
    return response.data;
  }

  async getFineTuningJobStatus(jobId: string) {
    const response = await this.client.get(`/api/v1/fine-tuning/${jobId}/status`);
    return response.data;
  }

  async optimizePerformance(optimizationData: {
    task_type: string;
    content_data: any;
    constraints?: any;
  }) {
    const response = await this.client.post('/api/v1/performance/optimize', optimizationData);
    return response.data;
  }

  async getPerformanceMetrics() {
    const response = await this.client.get('/api/v1/performance/metrics');
    return response.data;
  }

  // ==========================================
  // PHASE 4: SEARCH & DISCOVERY
  // ==========================================

  // Analytics Dashboard
  async getAnalyticsDashboard(dashboardParams: {
    time_period_days?: number;
    metrics?: string[];
    filters?: any;
  }) {
    const response = await this.client.post('/api/v1/analytics/dashboard', dashboardParams);
    return response.data;
  }


  async getContentInsights(contentId?: string, params?: any) {
    const endpoint = contentId
      ? `/api/v1/analytics/insights/content/${contentId}`
      : '/api/v1/analytics/insights/content';
    const response = await this.client.post(endpoint, params);
    return response.data;
  }

  async analyzeTrends(trendParams: {
    time_period_days?: number;
    metrics?: string[];
    trend_types?: string[];
  }) {
    const response = await this.client.post('/api/v1/analytics/trends', trendParams);
    return response.data;
  }

  async getTrendingContent() {
    const response = await this.client.get('/api/v1/analytics/trends/trending');
    return response.data;
  }

  async getPerformanceAnalytics(performanceParams: {
    time_period_days?: number;
    metrics?: string[];
  }) {
    const response = await this.client.post('/api/v1/analytics/performance', performanceParams);
    return response.data;
  }

  async getAnalyticsHealth() {
    const response = await this.client.get('/api/v1/analytics/health/quick');
    return response.data;
  }

  async exportAnalyticsReport(exportParams: {
    format?: string;
    time_period_days?: number;
    include_charts?: boolean;
  }) {
    const response = await this.client.get('/api/v1/analytics/export/report', {
      params: exportParams,
      responseType: 'blob'
    });
    return response.data;
  }

  async getAnalyticsCapabilities() {
    const response = await this.client.get('/api/v1/analytics/capabilities');
    return response.data;
  }

  // Personalization
  async getPersonalizedRecommendations(recommendationParams: {
    user_id: string;
    limit?: number;
    context?: any;
  }) {
    const response = await this.client.post('/api/v1/personalization/recommend', recommendationParams);
    return response.data;
  }

  async trackInteraction(interactionData: {
    user_id: string;
    content_id: string;
    interaction_type: string;
    metadata?: any;
  }) {
    const response = await this.client.post('/api/v1/personalization/track-interaction', interactionData);
    return response.data;
  }

  async getUserInsights(userId: string) {
    const response = await this.client.get(`/api/v1/personalization/insights/${userId}`);
    return response.data;
  }

  async resetUserProfile(userId: string) {
    const response = await this.client.post('/api/v1/personalization/reset-profile', { user_id: userId });
    return response.data;
  }

  async getPersonalizationHealth() {
    const response = await this.client.get('/api/v1/personalization/health');
    return response.data;
  }

  async getPersonalizationCapabilities() {
    const response = await this.client.get('/api/v1/personalization/capabilities');
    return response.data;
  }

  async getPersonalizationStats() {
    const response = await this.client.get('/api/v1/personalization/stats');
    return response.data;
  }

  async bulkTrackInteractions(interactions: Array<{
    user_id: string;
    content_id: string;
    interaction_type: string;
    metadata?: any;
  }>) {
    const response = await this.client.post('/api/v1/personalization/bulk-track', { interactions });
    return response.data;
  }

  async getTrendingPersonalizedContent(userId: string) {
    const response = await this.client.get('/api/v1/personalization/recommend/trending', {
      params: { user_id: userId }
    });
    return response.data;
  }

  // Trend Detection
  async analyzeTrendsAdvanced(analysisParams: {
    metric: string;
    time_period_days?: number;
    analysis_type?: string;
  }) {
    const response = await this.client.post('/api/v1/trends/analyze', analysisParams);
    return response.data;
  }

  async getPredictiveInsights(insightParams: {
    metrics: string[];
    prediction_horizon?: number;
  }) {
    const response = await this.client.post('/api/v1/trends/predictive-insights', insightParams);
    return response.data;
  }

  async detectAnomalies(anomalyParams: {
    metric: string;
    time_period_days?: number;
    sensitivity?: number;
  }) {
    const response = await this.client.post('/api/v1/trends/anomalies', anomalyParams);
    return response.data;
  }

  async getDetectedTrends() {
    const response = await this.client.get('/api/v1/trends');
    return response.data;
  }

  async getTrendDetails(trendId: string) {
    const response = await this.client.get(`/api/v1/trends/${trendId}`);
    return response.data;
  }

  async getMetricForecast(metric: string, params?: any) {
    const response = await this.client.get(`/api/v1/trends/forecast/${metric}`, { params });
    return response.data;
  }

  async getTrendsHealth() {
    const response = await this.client.get('/api/v1/trends/health');
    return response.data;
  }

  async getTrendsCapabilities() {
    const response = await this.client.get('/api/v1/trends/capabilities');
    return response.data;
  }

  async getTrendsByPattern(patternType: string) {
    const response = await this.client.get(`/api/v1/trends/patterns/${patternType}`);
    return response.data;
  }

  async analyzeSpecificMetric(metric: string, analysisParams: any) {
    const response = await this.client.post('/api/v1/trends/analyze-metric', {
      metric,
      ...analysisParams
    });
    return response.data;
  }

  async getTrendAlerts() {
    const response = await this.client.get('/api/v1/trends/alerts');
    return response.data;
  }

  // Search Analytics
  async generateSearchAnalyticsReport(reportParams: {
    time_period_days?: number;
    include_performance?: boolean;
    include_user_behavior?: boolean;
  }) {
    const response = await this.client.post('/api/v1/search-analytics/report', reportParams);
    return response.data;
  }

  async trackSearchEvent(eventData: {
    query: string;
    results_count: number;
    response_time_ms: number;
    user_id?: string;
    session_id?: string;
  }) {
    const response = await this.client.post('/api/v1/search-analytics/track-event', eventData);
    return response.data;
  }

  async getSearchSuggestions(suggestionParams: {
    query: string;
    limit?: number;
    context?: any;
  }) {
    const response = await this.client.post('/api/v1/search-analytics/suggestions', suggestionParams);
    return response.data;
  }

  async getSearchInsights(insightParams: {
    time_period_days?: number;
    query_patterns?: boolean;
    performance_metrics?: boolean;
  }) {
    const response = await this.client.post('/api/v1/search-analytics/insights', insightParams);
    return response.data;
  }

  async getSearchPerformance() {
    const response = await this.client.get('/api/v1/search-analytics/performance');
    return response.data;
  }

  async getSearchQueries(params?: {
    limit?: number;
    time_period_days?: number;
  }) {
    const response = await this.client.get('/api/v1/search-analytics/queries', { params });
    return response.data;
  }

  async getUserSearchBehavior(userId?: string) {
    const response = await this.client.get('/api/v1/search-analytics/user-behavior', {
      params: userId ? { user_id: userId } : undefined
    });
    return response.data;
  }

  async getSearchOptimizationInsights() {
    const response = await this.client.get('/api/v1/search-analytics/optimization');
    return response.data;
  }

  async exportSearchData(exportParams: {
    format?: string;
    time_period_days?: number;
    include_raw_queries?: boolean;
  }) {
    const response = await this.client.post('/api/v1/search-analytics/export', exportParams);
    return response.data;
  }

  async getSearchAnalyticsHealth() {
    const response = await this.client.get('/api/v1/search-analytics/health');
    return response.data;
  }

  async getSearchAnalyticsCapabilities() {
    const response = await this.client.get('/api/v1/search-analytics/capabilities');
    return response.data;
  }

  async getSearchTrends() {
    const response = await this.client.get('/api/v1/search-analytics/trends');
    return response.data;
  }

  async getPopularQueries(params?: {
    limit?: number;
    time_period_days?: number;
  }) {
    const response = await this.client.get('/api/v1/search-analytics/popular-queries', { params });
    return response.data;
  }

  async getSearchPerformanceSummary() {
    const response = await this.client.get('/api/v1/search-analytics/performance-summary');
    return response.data;
  }

  async bulkTrackSearchEvents(events: Array<{
    query: string;
    results_count: number;
    response_time_ms: number;
    user_id?: string;
    session_id?: string;
  }>) {
    const response = await this.client.post('/api/v1/search-analytics/bulk-track', { events });
    return response.data;
  }

  async getRealTimeSearchMetrics() {
    const response = await this.client.get('/api/v1/search-analytics/real-time');
    return response.data;
  }

  // ==========================================
  // PHASE 5: ORCHESTRATION & AUTOMATION
  // ==========================================

  // Workflow Automation
  async getWorkflowDefinitions(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }) {
    const response = await this.client.get('/api/v1/workflows/definitions', { params });
    return response.data;
  }

  async getWorkflowDefinition(workflowId: string) {
    const response = await this.client.get(`/api/v1/workflows/definitions/${workflowId}`);
    return response.data;
  }

  async createWorkflowDefinition(workflowData: {
    name: string;
    description: string;
    steps: any;
    priority?: string;
    max_execution_time?: number;
    resource_requirements?: any;
  }) {
    const response = await this.client.post('/api/v1/workflows/definitions', workflowData);
    return response.data;
  }

  async updateWorkflowDefinition(workflowId: string, workflowData: any) {
    const response = await this.client.put(`/api/v1/workflows/definitions/${workflowId}`, workflowData);
    return response.data;
  }

  async deleteWorkflowDefinition(workflowId: string) {
    await this.client.delete(`/api/v1/workflows/definitions/${workflowId}`);
  }

  async executeWorkflow(workflowId: string, executionParams?: any) {
    const response = await this.client.post('/api/v1/workflows/execute', {
      workflow_id: workflowId,
      ...executionParams
    });
    return response.data;
  }

  async getWorkflowExecutions(params?: {
    workflow_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) {
    const response = await this.client.get('/api/v1/workflows/executions', { params });
    return response.data;
  }

  async getWorkflowExecution(executionId: string) {
    const response = await this.client.get(`/api/v1/workflows/executions/${executionId}`);
    return response.data;
  }

  async cancelWorkflowExecution(executionId: string) {
    await this.client.delete(`/api/v1/workflows/executions/${executionId}`);
  }

  async scheduleWorkflow(scheduleData: {
    workflow_id: string;
    trigger_type: string;
    cron_expression?: string;
    parameters?: any;
  }) {
    const response = await this.client.post('/api/v1/workflows/schedule', scheduleData);
    return response.data;
  }

  async getWorkflowSchedules(workflowId?: string) {
    const response = await this.client.get('/api/v1/workflows/schedules', {
      params: workflowId ? { workflow_id: workflowId } : undefined
    });
    return response.data;
  }

  async evaluateConditionalLogic(logicData: {
    workflow_id: string;
    step_id: string;
    conditions: any[];
    context: any;
  }) {
    const response = await this.client.post('/api/v1/workflows/conditional-logic', logicData);
    return response.data;
  }

  async getWorkflowHealth() {
    const response = await this.client.get('/api/v1/workflows/health');
    return response.data;
  }

  async getWorkflowCapabilities() {
    const response = await this.client.get('/api/v1/workflows/capabilities');
    return response.data;
  }

  async getWorkflowStats() {
    const response = await this.client.get('/api/v1/workflows/stats');
    return response.data;
  }

  // Integration Layer
  async getIntegrationHealth() {
    const response = await this.client.get('/api/v1/integration/health');
    return response.data;
  }

  async getIntegrationCapabilities() {
    const response = await this.client.get('/api/v1/integration/capabilities');
    return response.data;
  }

  // API Gateway
  async getApiGatewayStats() {
    const response = await this.client.get('/api/v1/integration/gateway/stats');
    return response.data;
  }

  async updateApiGatewayConfig(configData: any) {
    const response = await this.client.put('/api/v1/integration/gateway/config', configData);
    return response.data;
  }

  // Webhooks
  async getWebhooks() {
    const response = await this.client.get('/api/v1/integration/webhooks');
    return response.data;
  }

  async subscribeWebhook(subscriptionData: {
    url: string;
    events: string[];
    secret?: string;
    headers?: any;
  }) {
    const response = await this.client.post('/api/v1/integration/webhooks/subscribe', subscriptionData);
    return response.data;
  }

  async unsubscribeWebhook(webhookId: string) {
    await this.client.delete(`/api/v1/integration/webhooks/${webhookId}`);
  }

  async testWebhook(webhookId: string, testData?: any) {
    const response = await this.client.post(`/api/v1/integration/webhooks/${webhookId}/test`, testData);
    return response.data;
  }

  async getWebhookDeliveries(webhookId: string, params?: {
    limit?: number;
    status?: string;
  }) {
    const response = await this.client.get(`/api/v1/integration/webhooks/${webhookId}/deliveries`, { params });
    return response.data;
  }

  // Queues
  async getQueues() {
    const response = await this.client.get('/api/v1/integration/queues');
    return response.data;
  }

  async getQueueStats(queueName: string) {
    const response = await this.client.get(`/api/v1/integration/queues/${queueName}/stats`);
    return response.data;
  }

  async enqueueTask(queueName: string, taskData: {
    type: string;
    priority?: string;
    data: any;
    callback_url?: string;
  }) {
    const response = await this.client.post(`/api/v1/integration/queues/${queueName}/enqueue`, taskData);
    return response.data;
  }

  async dequeueTask(queueName: string) {
    const response = await this.client.get(`/api/v1/integration/queues/${queueName}/dequeue`);
    return response.data;
  }

  async updateQueueConfig(queueName: string, configData: any) {
    const response = await this.client.put(`/api/v1/integration/queues/${queueName}/config`, configData);
    return response.data;
  }

  // Load Balancing
  async getLoadBalancerStats() {
    const response = await this.client.get('/api/v1/integration/load-balancer/stats');
    return response.data;
  }

  async getBackendServices() {
    const response = await this.client.get('/api/v1/integration/backends');
    return response.data;
  }

  async registerBackendService(serviceData: {
    id: string;
    url: string;
    supported_request_types: string[];
    max_concurrent_requests?: number;
    health_check_url?: string;
  }) {
    const response = await this.client.post('/api/v1/integration/backends/register', serviceData);
    return response.data;
  }

  async unregisterBackendService(serviceId: string) {
    await this.client.delete(`/api/v1/integration/backends/${serviceId}`);
  }

  async routeRequest(requestData: {
    request_type: string;
    data: any;
    priority?: string;
  }) {
    const response = await this.client.post('/api/v1/integration/load-balance/route', requestData);
    return response.data;
  }

  async getLoadBalancerHealth() {
    const response = await this.client.get('/api/v1/integration/load-balancer/health');
    return response.data;
  }

  // ==========================================
  // KNOWLEDGE BASE - ENHANCED API INTEGRATION
  // ==========================================

  // Core Knowledge Item Management
  async createKnowledgeItem(itemData: {
    title: string;
    content: string;
    category?: string;
    tags?: string[];
    metadata?: any;
  }) {
    const response = await this.client.post('/api/v1/knowledge/items', itemData);
    return response.data;
  }

  async createTwitterBookmarkItem(bookmarkData: {
    bookmark_url: string;
    title: string;
    summary?: string;
    content?: string;
    bookmarked_at?: string;
    tags?: string[];
    metadata?: any;
  }) {
    const response = await this.client.post('/api/v1/knowledge/items/twitter-bookmark', bookmarkData);
    return response.data;
  }

  async getKnowledgeItems(params?: {
    category?: string;
    tags?: string[];
    limit?: number;
    offset?: number;
  }) {
    const response = await this.client.get('/api/v1/knowledge/items', { params });
    return response.data;
  }

  async getKnowledgeItem(itemId: string) {
    const response = await this.client.get(`/api/v1/knowledge/items/${itemId}`);
    return response.data;
  }

  async getKnowledgeItemDetails(itemId: string) {
    const response = await this.client.get(`/api/v1/knowledge/items/${itemId}/details`);
    return response.data;
  }

  async updateKnowledgeItem(itemId: string, itemData: {
    title?: string;
    content?: string;
    category?: string;
    tags?: string[];
    metadata?: any;
  }) {
    const response = await this.client.put(`/api/v1/knowledge/items/${itemId}/edit`, itemData);
    return response.data;
  }

  async deleteKnowledgeItem(itemId: string) {
    await this.client.delete(`/api/v1/knowledge/items/${itemId}`);
  }

  async reprocessKnowledgeItem(itemId: string, options?: {
    phases?: string[];
    workflow_settings_id?: string;
    reason?: string;
    start_immediately?: boolean;
  }) {
    const response = await this.client.post(`/api/v1/knowledge/items/${itemId}/reprocess`, options || {});
    return response.data;
  }

  // Twitter Bookmarks Integration
  async fetchTwitterBookmarks(fetchData: {
    bookmark_url: string;
    max_results?: number;
    process_items?: boolean;
    workflow_settings_id?: string;
  }) {
    const response = await this.client.post('/api/v1/knowledge/fetch-twitter-bookmarks', fetchData);
    return response.data;
  }

  // List Twitter Bookmarks - Now using real backend endpoint
  async getTwitterBookmarks(params?: {
    limit?: number;
    offset?: number;
    has_been_processed?: boolean;
    page?: number;
  }) {
    const queryParams: any = {};
    if (params?.limit) queryParams.limit = params.limit;
    if (params?.offset) queryParams.offset = params.offset;
    if (params?.has_been_processed !== undefined) queryParams.has_been_processed = params.has_been_processed;
    if (params?.page) queryParams.page = params.page;

    const response = await this.client.get('/api/v1/knowledge/bookmarks', { params: queryParams });
    return response.data;
  }

  // Get detailed bookmark information
  async getTwitterBookmark(bookmarkId: string) {
    const response = await this.client.get(`/api/v1/knowledge/bookmarks/${bookmarkId}`);
    return response.data;
  }

  // Process a bookmark into knowledge base item
  async processTwitterBookmark(bookmarkId: string) {
    const response = await this.client.post(`/api/v1/knowledge/bookmarks/${bookmarkId}/process`);
    return response.data;
  }

  // Workflow Cancellation
  async cancelKnowledgeItemProcessing(itemId: string) {
    const response = await this.client.delete(`/api/v1/knowledge/items/${itemId}/cancel`);
    return response.data;
  }

  // Workflow Settings Management
  async getWorkflowSettings() {
    const response = await this.client.get('/api/v1/knowledge/workflow-settings');
    return response.data;
  }

  async createWorkflowSettings(settingsData: {
    settings_name: string;
    is_default?: boolean;
    phase_models?: any;
    phase_settings?: any;
    global_settings?: any;
  }) {
    const response = await this.client.post('/api/v1/knowledge/workflow-settings', settingsData);
    return response.data;
  }

  async getWorkflowSettingsById(settingsId: string) {
    const response = await this.client.get(`/api/v1/knowledge/workflow-settings/${settingsId}`);
    return response.data;
  }

  async updateWorkflowSettings(settingsId: string, settingsData: any) {
    const response = await this.client.put(`/api/v1/knowledge/workflow-settings/${settingsId}`, settingsData);
    return response.data;
  }

  async deleteWorkflowSettings(settingsId: string) {
    await this.client.delete(`/api/v1/knowledge/workflow-settings/${settingsId}`);
  }

  async activateWorkflowSettings(settingsId: string) {
    const response = await this.client.post(`/api/v1/knowledge/workflow-settings/${settingsId}/activate`);
    return response.data;
  }

  async getWorkflowSettingsDefaults() {
    const response = await this.client.get('/api/v1/knowledge/workflow-settings/defaults');
    return response.data;
  }

  // Progress Monitoring
  async getKnowledgeItemProgress(itemId: string) {
    const response = await this.client.get(`/api/v1/knowledge/items/${itemId}/progress`);
    return response.data;
  }

  async getBatchProgress(itemIds: string[]) {
    const params = new URLSearchParams();
    itemIds.forEach(id => params.append('item_ids', id));
    const response = await this.client.get('/api/v1/knowledge/progress/batch', { params });
    return response.data;
  }

  async getActiveProgress(limit?: number) {
    const response = await this.client.get('/api/v1/knowledge/progress/active', {
      params: limit ? { limit } : undefined
    });
    return response.data;
  }

  async getProgressSummary() {
    const response = await this.client.get('/api/v1/knowledge/progress/summary');
    return response.data;
  }

  // Advanced Browsing and Search
  async browseKnowledgeBase(params?: {
    category?: string;
    subcategory?: string;
    tags?: string[];
    date_from?: string;
    date_to?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    limit?: number;
    offset?: number;
  }) {
    const response = await this.client.get('/api/v1/knowledge/browse', { params });
    return response.data;
  }

  async searchKnowledgeBase(searchData: {
    query: string;
    category?: string;
    tags?: string[];
    limit?: number;
    similarity_threshold?: number;
    search_type?: 'semantic' | 'keyword' | 'hybrid';
  }) {
    const response = await this.client.post('/api/v1/knowledge/search', searchData);
    return response.data;
  }

  async getKnowledgeCategories() {
    const response = await this.client.get('/api/v1/knowledge/categories');
    return response.data;
  }

  async getKnowledgeStats() {
    const response = await this.client.get('/api/v1/knowledge/stats');
    return response.data;
  }

  // AI Processing
  async generateKnowledgeEmbeddings(embeddingData: {
    content: string;
    model?: string;
    dimensions?: number;
  }) {
    const response = await this.client.post('/api/v1/knowledge/embeddings', embeddingData);
    return response.data;
  }

  async classifyKnowledgeContent(classificationData: {
    content: string;
    categories?: string[];
    confidence_threshold?: number;
  }) {
    const response = await this.client.post('/api/v1/knowledge/classify', classificationData);
    return response.data;
  }

  // ==========================================
  // SECRETS MANAGEMENT
  // ==========================================

  async createAgentSecret(agentId: string, secretData: {
    secret_key: string;
    secret_value: string;
    description?: string;
  }) {
    const response = await this.client.post(`/api/v1/agents/${agentId}/secrets`, secretData);
    return response.data;
  }

  async getAgentSecrets(agentId: string) {
    const response = await this.client.get(`/api/v1/agents/${agentId}/secrets`);
    return response.data;
  }

  async getAgentSecret(agentId: string, secretId: string, decrypt?: boolean) {
    const response = await this.client.get(`/api/v1/agents/${agentId}/secrets/${secretId}`, {
      params: decrypt ? { decrypt: true } : undefined
    });
    return response.data;
  }

  async updateAgentSecret(agentId: string, secretId: string, secretData: {
    secret_value?: string;
    description?: string;
  }) {
    const response = await this.client.put(`/api/v1/agents/${agentId}/secrets/${secretId}`, secretData);
    return response.data;
  }

  async deleteAgentSecret(agentId: string, secretId: string) {
    await this.client.delete(`/api/v1/agents/${agentId}/secrets/${secretId}`);
  }

  async getAgentSecretValue(agentId: string, secretKey: string) {
    const response = await this.client.get(`/api/v1/agents/${agentId}/secrets/${secretKey}/value`);
    return response.data;
  }

  // ==========================================
  // EMAIL WORKFLOW SYSTEM
  // ==========================================

  // Dashboard Statistics
  async getEmailDashboardStats() {
    const response = await this.client.get('/api/v1/email/dashboard/stats');
    return response.data;
  }

  async getEmailDashboardRecentActivity(limit?: number) {
    const response = await this.client.get('/api/v1/email/dashboard/recent-activity', {
      params: limit ? { limit } : undefined
    });
    return response.data;
  }

  async exportEmailDashboardData(format?: string, timePeriod?: string) {
    const response = await this.client.post('/api/v1/email/dashboard/export', {
      format: format || 'json',
      time_period: timePeriod || '30d'
    });
    return response.data;
  }

  // Workflow Management
  async startEmailWorkflow(workflowData: {
    mailbox_config: {
      server: string;
      port: number;
      username: string;
      password: string;
      mailbox?: string;
      use_ssl?: boolean;
    };
    processing_options?: {
      max_emails?: number;
      unread_only?: boolean;
      since_date?: string;
      importance_threshold?: number;
      spam_threshold?: number;
      create_tasks?: boolean;
      schedule_followups?: boolean;
    };
  }) {
    const response = await this.client.post('/api/v1/email/workflows/start', workflowData);
    return response.data;
  }

  async getEmailWorkflowHistory(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }) {
    const response = await this.client.get('/api/v1/email/workflows/history', { params });
    return response.data;
  }

  async getEmailWorkflow(workflowId: string) {
    const response = await this.client.get(`/api/v1/email/workflows/${workflowId}`);
    return response.data;
  }

  async getEmailWorkflowStatus(workflowId: string) {
    const response = await this.client.get(`/api/v1/email/workflows/${workflowId}/status`);
    return response.data;
  }

  async cancelEmailWorkflow(workflowId: string) {
    const response = await this.client.post(`/api/v1/email/workflows/${workflowId}/cancel`);
    return response.data;
  }

  async getEmailWorkflowProgress(workflowId: string) {
    const response = await this.client.get(`/api/v1/email/workflows/${workflowId}/progress`);
    return response.data;
  }

  async getActiveEmailWorkflows() {
    const response = await this.client.get('/api/v1/email/workflows/active');
    return response.data;
  }

  // Task Management
  async getEmailTasks(params?: {
    status?: string;
    priority?: string;
    email_id?: string;
    limit?: number;
    offset?: number;
  }) {
    const response = await this.client.get('/api/v1/email/tasks', { params });
    return response.data;
  }

  async getEmailTask(taskId: string) {
    const response = await this.client.get(`/api/v1/email/tasks/${taskId}`);
    return response.data;
  }

  async completeEmailTask(taskId: string) {
    const response = await this.client.post(`/api/v1/email/tasks/${taskId}/complete`);
    return response.data;
  }

  async scheduleEmailTaskFollowup(taskId: string, followupData: {
    followup_date: string;
    followup_notes?: string;
  }) {
    const response = await this.client.post(`/api/v1/email/tasks/${taskId}/followup`, followupData);
    return response.data;
  }

  async updateEmailTaskPriority(taskId: string, priority: string) {
    const response = await this.client.put(`/api/v1/email/tasks/${taskId}/priority`, { priority });
    return response.data;
  }

  async getEmailTaskStats() {
    const response = await this.client.get('/api/v1/email/tasks/stats');
    return response.data;
  }

  async getOverdueEmailTasks() {
    const response = await this.client.get('/api/v1/email/tasks/overdue');
    return response.data;
  }

  // Conversational Email Assistant
  async sendEmailChatMessage(messageData: {
    message: string;
    session_id?: string;
    context?: {
      timezone?: string;
      preferred_format?: string;
      include_threads?: boolean;
      max_results?: number;
    };
  }) {
    const response = await this.client.post('/api/v1/email/chat', messageData);
    return response.data;
  }

  async searchEmailsViaChat(searchData: {
    message: string;
    session_id?: string;
  }) {
    const response = await this.client.post('/api/v1/email/chat/search', searchData);
    return response.data;
  }

  async organizeEmailsViaChat(organizeData: {
    message: string;
    session_id?: string;
  }) {
    const response = await this.client.post('/api/v1/email/chat/organize', organizeData);
    return response.data;
  }

  async summarizeEmailsViaChat(summarizeData: {
    message: string;
    session_id?: string;
  }) {
    const response = await this.client.post('/api/v1/email/chat/summarize', summarizeData);
    return response.data;
  }

  async performEmailActionsViaChat(actionData: {
    message: string;
    session_id?: string;
  }) {
    const response = await this.client.post('/api/v1/email/chat/action', actionData);
    return response.data;
  }

  async getEmailChatSessions() {
    const response = await this.client.get('/api/v1/email/chat/sessions');
    return response.data;
  }

  async getEmailChatSession(sessionId: string) {
    const response = await this.client.get(`/api/v1/email/chat/sessions/${sessionId}`);
    return response.data;
  }

  async getEmailChatSuggestions() {
    const response = await this.client.get('/api/v1/email/chat/suggestions');
    return response.data;
  }

  // Advanced Email Search & Filtering
  async searchEmails(searchData: {
    query?: string;
    search_type?: 'semantic' | 'keyword' | 'hybrid';
    limit?: number;
    offset?: number;
    date_from?: string;
    date_to?: string;
    sender?: string;
    categories?: string[];
    min_importance?: number;
    has_attachments?: boolean;
    sort_by?: string;
    include_threads?: boolean;
  }) {
    const response = await this.client.get('/api/v1/email/search', { params: searchData });
    return response.data;
  }

  async getEmailSearchSuggestions(query: string, limit?: number) {
    const response = await this.client.get('/api/v1/email/search/suggestions', {
      params: { query, limit }
    });
    return response.data;
  }

  async getEmailSearchFilters() {
    const response = await this.client.get('/api/v1/email/search/filters');
    return response.data;
  }

  async saveEmailSearchQuery(searchData: {
    name: string;
    query: string;
    filters: any;
  }) {
    const response = await this.client.post('/api/v1/email/search/save', searchData);
    return response.data;
  }

  async getSavedEmailSearches() {
    const response = await this.client.get('/api/v1/email/search/saved');
    return response.data;
  }

  async exportEmailSearchResults(searchData: {
    query: string;
    format?: string;
    filters?: any;
  }) {
    const response = await this.client.post('/api/v1/email/search/export', searchData);
    return response.data;
  }

  // Real-time Progress & Monitoring
  async getEmailMonitoringWorkflowProgress() {
    const response = await this.client.get('/api/v1/email/monitoring/workflow-progress');
    return response.data;
  }

  async getEmailSystemHealth() {
    const response = await this.client.get('/api/v1/email/monitoring/system-health');
    return response.data;
  }

  async getEmailProcessingPerformance() {
    const response = await this.client.get('/api/v1/email/monitoring/performance');
    return response.data;
  }

  async getEmailProcessingQueueStatus() {
    const response = await this.client.get('/api/v1/email/monitoring/queue-status');
    return response.data;
  }

  // Notifications & Alerts
  async getEmailNotifications(params?: {
    limit?: number;
    unread_only?: boolean;
  }) {
    const response = await this.client.get('/api/v1/email/notifications', { params });
    return response.data;
  }

  async markEmailNotificationAsRead(notificationId: string) {
    const response = await this.client.post(`/api/v1/email/notifications/${notificationId}/read`);
    return response.data;
  }

  async updateEmailNotificationSettings(settings: {
    email_notifications?: boolean;
    push_notifications?: boolean;
    notification_types?: string[];
  }) {
    const response = await this.client.post('/api/v1/email/notifications/settings', settings);
    return response.data;
  }

  async getEmailAlerts(params?: {
    severity?: string;
    resolved?: boolean;
  }) {
    const response = await this.client.get('/api/v1/email/alerts', { params });
    return response.data;
  }

  // Analytics & Insights
  async getEmailAnalyticsOverview(params?: {
    period?: string;
    metrics?: string[];
  }) {
    const response = await this.client.get('/api/v1/email/analytics/overview', { params });
    return response.data;
  }

  async getEmailProductivityInsights(params?: {
    period?: string;
    user_id?: string;
  }) {
    const response = await this.client.get('/api/v1/email/analytics/productivity', { params });
    return response.data;
  }

  async getEmailCategorizationAnalytics(params?: {
    period?: string;
    categories?: string[];
  }) {
    const response = await this.client.get('/api/v1/email/analytics/categories', { params });
    return response.data;
  }

  async getEmailSenderAnalytics(params?: {
    period?: string;
    limit?: number;
  }) {
    const response = await this.client.get('/api/v1/email/analytics/senders', { params });
    return response.data;
  }

  async getEmailTimePatternAnalytics(params?: {
    period?: string;
    timezone?: string;
  }) {
    const response = await this.client.get('/api/v1/email/analytics/time-patterns', { params });
    return response.data;
  }

  // Configuration & Settings
  async getEmailSettings() {
    const response = await this.client.get('/api/v1/email/settings');
    return response.data;
  }

  async updateEmailSettings(settings: {
    processing_rules?: any;
    notification_settings?: any;
    automation_settings?: any;
  }) {
    const response = await this.client.put('/api/v1/email/settings', settings);
    return response.data;
  }

  async getEmailTaskTemplates() {
    const response = await this.client.get('/api/v1/email/settings/templates');
    return response.data;
  }

  async createEmailTaskTemplate(templateData: {
    name: string;
    description: string;
    template: any;
    conditions?: any;
  }) {
    const response = await this.client.post('/api/v1/email/settings/templates', templateData);
    return response.data;
  }

  async getEmailProcessingRules() {
    const response = await this.client.get('/api/v1/email/settings/rules');
    return response.data;
  }

  async createEmailProcessingRule(ruleData: {
    name: string;
    description: string;
    conditions: any;
    actions: any;
    priority?: number;
  }) {
    const response = await this.client.post('/api/v1/email/settings/rules', ruleData);
    return response.data;
  }

  // ==========================================
  // DOCUMENTATION ENDPOINTS
  // ==========================================

  async getAgentCreationGuide() {
    const response = await this.client.get('/api/v1/docs/agent-creation');
    return response.data;
  }

  async getFrontendIntegrationGuide() {
    const response = await this.client.get('/api/v1/docs/frontend-integration');
    return response.data;
  }

  async getExampleConfigurations() {
    const response = await this.client.get('/api/v1/docs/examples');
    return response.data;
  }

  async getAgentTypeDocumentation(agentType: string, format?: string) {
    const response = await this.client.get(`/api/v1/agent-types/${agentType}/documentation`, {
      params: format ? { format } : undefined
    });
    return response.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;