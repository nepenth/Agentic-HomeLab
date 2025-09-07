# Frontend API Flow Documentation

This document provides a comprehensive overview of all external API calls and WebSocket connections used throughout the frontend application. It serves as a source of truth for understanding current API usage patterns, facilitating backend API issue diagnosis and frontend API updates based on backend changes.

## Table of Contents

1. [API Service Overview](#api-service-overview)
2. [Authentication Flow](#authentication-flow)
3. [Page/Component API Usage](#pagecomponent-api-usage)
4. [WebSocket Connections](#websocket-connections)
5. [Error Handling Patterns](#error-handling-patterns)
6. [API Endpoints Reference](#api-endpoints-reference)

## API Service Overview

The frontend uses a centralized `ApiClient` class (`frontend/src/services/api.ts`) that handles all HTTP communication with the backend. Key features:

- **Base URL**: Configurable via `VITE_API_BASE_URL` environment variable
- **Authentication**: JWT token-based with automatic header injection
- **Error Handling**: Centralized error processing with CORS and network error handling
- **Interceptors**: Request/response interceptors for auth and error handling
- **Timeout**: 30-second timeout for all requests

## Recent Frontend Improvements

### Scroll Bar Fixes (✅ IMPLEMENTED)
**Issue:** Pages were not displaying scroll bars when content overflowed
**Root Cause:** Conflicting CSS with `display: flex` and `place-items: center` on body element
**Solution:**
- Removed `display: flex` and `place-items: center` from body element
- Added `overflow: auto` to both html and body elements
- Simplified #root container styling to allow proper height management
- **Files Modified:** `frontend/src/index.css`, `frontend/src/App.css`

### GPU Display Debugging (✅ IMPLEMENTED)
**Issue:** Only one GPU was displaying despite API returning data for multiple GPUs
**Root Cause:** Syntax error in GPU rendering code
**Solution:**
- Fixed syntax error with extra `);` in map function
- Added comprehensive console logging for GPU processing and rendering
- Improved React keys for proper component re-rendering: `key={`gpu-${gpu.id}-${_index}`}`
- **Files Modified:** `frontend/src/pages/SystemHealth.tsx`

### GPU Data Flow
**Backend Response Format:**
```json
[
  {
    "index": 0,
    "name": "Tesla P40",
    "utilization": {"gpu_percent": 0, "memory_percent": 0},
    "memory": {"total_mb": 24576, "used_mb": 139, "free_mb": 24436},
    "temperature_fahrenheit": 75.2,
    "clocks": {"graphics_mhz": 544, "memory_mhz": 405},
    "power": {"usage_watts": 9.82, "limit_watts": 250.0}
  },
  {
    "index": 1,
    "name": "Tesla P40",
    "utilization": {"gpu_percent": 0, "memory_percent": 0},
    "memory": {"total_mb": 24576, "used_mb": 139, "free_mb": 24436},
    "temperature_fahrenheit": 69.8,
    "clocks": {"graphics_mhz": 544, "memory_mhz": 405},
    "power": {"usage_watts": 9.82, "limit_watts": 250.0}
  }
]
```

**Frontend Processing:**
- Maps GPU array to display format with proper unit conversions (MB to GB)
- Handles missing data gracefully with fallbacks
- Provides debugging information for troubleshooting

### Authentication Implementation

```typescript
// Automatic token injection via request interceptor
this.client.interceptors.request.use(
  (config) => {
    if (this.authToken) {
      config.headers.Authorization = `Bearer ${this.authToken}`;
    }
    return config;
  }
);
```

## Authentication Flow

### Login Process
1. **Frontend**: `apiClient.login(username, password)`
2. **Backend**: `POST /api/v1/auth/login`
3. **Response**: Returns `access_token` which is stored in localStorage
4. **WebSocket**: Automatically connects to `/ws/logs` with token
5. **Redirect**: User redirected to dashboard on success

### Logout Process
1. **Frontend**: `apiClient.logout()`
2. **Backend**: `POST /api/v1/auth/logout`
3. **Cleanup**: Token removed from localStorage
4. **WebSocket**: Connection automatically disconnected
5. **Redirect**: User redirected to login page

### Token Management
- **Storage**: localStorage (`auth_token` key)
- **Validation**: Automatic on each request via interceptor
- **Expiration**: Handled by backend, frontend redirects to login on 401

## Page/Component API Usage

### Dashboard (`frontend/src/pages/Dashboard.tsx`)

**Primary APIs:**
- `getAgents()` - Fetches all agents for statistics and recent tasks
- `getTasks()` - Retrieves task list for recent activity display
- `getSecurityStatus()` - Security metrics and active agent count
- `getSystemMetrics()` - CPU, memory, GPU metrics for system health card
- `getOllamaHealth()` - Ollama service status and model information

**Usage Pattern:**
```typescript
const { data: agents, isLoading } = useQuery({
  queryKey: ['agents'],
  queryFn: () => apiClient.getAgents(),
  refetchInterval: 30000, // Refetch every 30 seconds
});
```

**Real-time Updates:** None currently implemented

### System Health (`frontend/src/pages/SystemHealth.tsx`)

**Primary APIs:**
- `getSystemMetricsCpu()` - CPU usage, temperature, frequency
- `getSystemMetricsMemory()` - Memory usage statistics
- `getSystemMetricsDisk()` - Disk I/O and usage metrics
- `getSystemMetricsNetwork()` - Network traffic and speed metrics
- `getSystemMetricsGpu()` - GPU utilization (NVIDIA Tesla P40 × 2)
- `getSystemMetricsLoad()` - System load averages
- `getSystemMetricsSwap()` - Swap memory usage
- `getSystemInfo()` - System uptime, processes, boot time
- `getOllamaHealth()` - Ollama service health status

**Usage Pattern:**
```typescript
const [cpuMetrics, memoryMetrics, ...] = await Promise.all([
  apiClient.getSystemMetricsCpu().catch(() => null),
  apiClient.getSystemMetricsMemory().catch(() => null),
  // ... other metrics
]);
```

**GPU Data Processing:**
```typescript
// Backend returns array of GPUs
// Example response: [{"index":0,"name":"Tesla P40",...},{"index":1,"name":"Tesla P40",...}]

// Frontend transforms to display format
gpus: Array.isArray(gpuMetrics) ? gpuMetrics.map((gpu: any) => ({
  id: gpu.index,
  name: gpu.name,
  usage: gpu.utilization?.gpu_percent || 0,
  memoryUsed: gpu.memory?.used_mb ? gpu.memory.used_mb / 1024 : 0,
  memoryTotal: gpu.memory?.total_mb ? gpu.memory.total_mb / 1024 : 0,
  temperature: gpu.temperature_fahrenheit || 'N/A',
  frequency: gpu.clocks?.graphics_mhz || 'N/A',
  memoryFrequency: gpu.clocks?.memory_mhz || 'N/A',
  power: gpu.power?.usage_watts || 'N/A',
})) : []
```

**Debugging Features:**
- Console logging for GPU processing: `console.log('Processing GPU data:', gpu)`
- Console logging for GPU rendering: `console.log('Rendering GPU:', gpu.id, gpu.name, 'Index in array:', _index)`
- Unique keys for React rendering: `key={`gpu-${gpu.id}-${_index}`}`

**Real-time Updates:** None currently implemented

### Agent Management (`frontend/src/pages/AgentManagement.tsx`)

**Primary APIs:**
- `getAgents()` - List all agents with filtering
- `getOllamaModelNames()` - Available Ollama models for agent creation
- `createAgent()` - Create new static/dynamic agents
- `updateAgent()` - Modify existing agent configuration
- `deleteAgent()` - Remove agents from system

**Enhanced Features APIs:**
- `getAvailableModels()` - Get models with capabilities for dynamic selection
- `getModelPerformanceMetrics()` - Model performance data for comparison
- `makeAgenticHttpRequest()` - Execute HTTP requests with agentic features
- `getHttpClientMetrics()` - HTTP client performance and usage metrics
- `processContent()` - Multi-modal content processing
- `getAgentSecrets()` - Retrieve agent secrets for configuration
- `createAgentSecret()` - Add new secrets to agents
- `deleteAgentSecret()` - Remove agent secrets

**CRUD Operations:**
```typescript
// Create
const createAgentMutation = useMutation({
  mutationFn: (agentData: Partial<Agent>) => apiClient.createAgent(agentData),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['agents'] });
  },
});

// Update
const updateAgentMutation = useMutation({
  mutationFn: ({ id, data }: { id: string; data: Partial<Agent> }) =>
    apiClient.updateAgent(id, data),
});

// Delete
const deleteAgentMutation = useMutation({
  mutationFn: (id: string) => apiClient.deleteAgent(id),
});
```

**Real-time Updates:** None currently implemented

### Security Center (`frontend/src/pages/Security.tsx`)

**Primary APIs:**
- `getSecurityStatus()` - Current security metrics, active agents, and resource limits
- `getSecurityHealth()` - Security service health status
- `getSecurityIncidents()` - List security incidents with filtering
- `resolveSecurityIncident()` - Resolve security incidents with notes

**Note:** Resource limits are included in the SecurityStatus response (`resource_limits` field) rather than a separate endpoint.

**Usage Pattern:**
```typescript
const {
  data: incidents,
  isLoading,
  refetch,
} = useQuery({
  queryKey: ['security-incidents', incidentFilters],
  queryFn: () => apiClient.getSecurityIncidents({
    limit: incidentFilters.limit,
    severity: incidentFilters.severity !== 'all' ? incidentFilters.severity : undefined,
    resolved: incidentFilters.resolved !== 'all' ? incidentFilters.resolved === 'true' : undefined,
  }),
  refetchInterval: 30000,
});
```

**Real-time Updates:** None currently implemented

### Content Processing Hub (`frontend/src/pages/ContentProcessing.tsx`)

**Primary APIs:**
- `discoverContent()` - Discover content from multiple sources simultaneously
- `discoverWebContent()` - Discover content from web sources (RSS, scraping)
- `discoverSocialContent()` - Discover content from social media platforms
- `discoverCommunicationContent()` - Discover content from communication channels
- `discoverFilesystemContent()` - Discover content from file systems and cloud storage
- `processContent()` - Process discovered content with AI operations
- `getContentCacheStats()` - Get content cache statistics and performance metrics

**Content Discovery Workflow:**
```typescript
// Multi-source content discovery
const discoverContentMutation = useMutation({
  mutationFn: (request: ContentDiscoveryRequest) => apiClient.discoverContent(request),
  onSuccess: (results) => {
    // Handle discovered content from multiple sources
    console.log('Discovered content:', results);
  },
});

// Source-specific discovery
const webDiscoveryMutation = useMutation({
  mutationFn: (config: WebContentConfig) => apiClient.discoverWebContent(config),
  onSuccess: (results) => {
    // Handle web content discovery results
  },
});
```

**Content Processing Pipeline:**
```typescript
// Process content with multiple operations
const processContentMutation = useMutation({
  mutationFn: (request: ContentProcessingRequest) => apiClient.processContent(request),
  onSuccess: (result) => {
    setProcessingResults(result);
    // Display processing results with summary, entities, and metadata
  },
});

// Cache management
const cacheStatsQuery = useQuery({
  queryKey: ['content-cache-stats'],
  queryFn: () => apiClient.getContentCacheStats(),
  refetchInterval: 30000, // Real-time cache monitoring
});
```

**Usage Pattern:**
- **Source Configuration**: Interactive forms for configuring different content sources (RSS feeds, social media, file systems)
- **Discovery Management**: Real-time progress tracking for content discovery operations
- **Processing Pipeline**: Visual pipeline builder with drag-and-drop operations and result visualization
- **Cache Monitoring**: Live cache statistics with performance metrics and optimization suggestions
- **Multi-Modal Support**: Support for text, image, audio, and structured data processing

**Real-time Updates:** Cache statistics updated every 30 seconds

### Analytics Command Center (`frontend/src/pages/Analytics.tsx`)

**Primary APIs:**
- `getAnalyticsDashboard()` - Get comprehensive analytics dashboard with metrics and KPIs
- `getContentInsights()` - Get AI-powered content performance insights and recommendations
- `analyzeTrends()` - Perform advanced trend analysis with predictive capabilities
- `getAnalyticsHealth()` - Get system health status and monitoring data
- `exportAnalyticsReport()` - Export analytics data in various formats (PDF, CSV, JSON, XLSX)

**Dashboard Data Flow:**
```typescript
// Comprehensive analytics dashboard
const dashboardQuery = useQuery({
  queryKey: ['analytics-dashboard', timePeriodDays, selectedMetrics],
  queryFn: () => apiClient.getAnalyticsDashboard({
    time_period_days: timePeriodDays,
    metrics: selectedMetrics,
  }),
  refetchInterval: 300000, // Auto-refresh every 5 minutes
});

// Content insights with AI recommendations
const insightsQuery = useQuery({
  queryKey: ['content-insights', timePeriodDays],
  queryFn: () => apiClient.getContentInsights(undefined, {
    time_period_days: timePeriodDays,
  }),
  refetchInterval: 300000,
});

// Trend analysis with predictive insights
const trendsQuery = useQuery({
  queryKey: ['trend-analysis', timePeriodDays],
  queryFn: () => apiClient.analyzeTrends({
    time_period_days: timePeriodDays,
    metrics: selectedMetrics,
    trend_types: ['emerging', 'declining', 'seasonal'],
  }),
  refetchInterval: 300000,
});

// System health monitoring
const healthQuery = useQuery({
  queryKey: ['analytics-health'],
  queryFn: () => apiClient.getAnalyticsHealth(),
  refetchInterval: 60000, // Health check every minute
});
```

**Export Functionality:**
```typescript
// Export analytics reports
const exportMutation = useMutation({
  mutationFn: (exportParams: any) => apiClient.exportAnalyticsReport(exportParams),
  onSuccess: (data) => {
    // Handle file download with automatic blob creation
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `analytics-report.${exportFormat}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },
});
```

**Usage Pattern:**
- **Real-time Monitoring**: Dashboard auto-refreshes every 5 minutes with latest metrics
- **Health Monitoring**: System health checked every minute with status indicators
- **Interactive Filtering**: Time period selection, metric filtering, and date range controls
- **Export Capabilities**: Multiple format support (PDF, CSV, JSON, XLSX) with customizable content
- **Tab-based Navigation**: Organized views for Dashboard, Trends, Insights, and Performance
- **Responsive Design**: Mobile-friendly layout with collapsible controls

**Real-time Updates:** Dashboard data refreshes every 5 minutes, health status every minute

### Personalization Studio (`frontend/src/pages/Personalization.tsx`)

**Primary APIs:**
- `getPersonalizedRecommendations()` - Get AI-powered personalized content recommendations
- `getUserInsights()` - Get detailed user insights and behavioral analysis
- `trackInteraction()` - Track user interactions for learning and personalization
- `resetUserProfile()` - Reset user profile and personalization data
- `getPersonalizationStats()` - Get personalization system statistics and metrics

**Personalization Data Flow:**
```typescript
// Get personalized recommendations for a user
const recommendationsQuery = useQuery({
  queryKey: ['personalization-recommendations', userId, limit],
  queryFn: () => apiClient.getPersonalizedRecommendations({
    user_id: userId,
    limit: limit,
    diversity_weight: diversityWeight,
  }),
  enabled: !!userId,
  refetchInterval: 300000, // Auto-refresh every 5 minutes
});

// Get detailed user insights and behavior analysis
const insightsQuery = useQuery({
  queryKey: ['user-insights', userId],
  queryFn: () => apiClient.getUserInsights(userId),
  enabled: !!userId,
  refetchInterval: 300000,
});

// Track user interactions for continuous learning
const trackInteractionMutation = useMutation({
  mutationFn: (interaction: InteractionData) => apiClient.trackInteraction(interaction),
  onSuccess: () => {
    // Invalidate and refetch recommendations and insights
    queryClient.invalidateQueries({ queryKey: ['personalization-recommendations'] });
    queryClient.invalidateQueries({ queryKey: ['user-insights'] });
  },
});

// Reset user profile for fresh personalization
const resetProfileMutation = useMutation({
  mutationFn: (userId: string) => apiClient.resetUserProfile(userId),
  onSuccess: () => {
    // Clear cached data and refetch
    queryClient.invalidateQueries({ queryKey: ['personalization-recommendations'] });
    queryClient.invalidateQueries({ queryKey: ['user-insights'] });
  },
});
```

**Recommendation Engine:**
```typescript
// Interactive recommendation feedback
const handleRecommendationFeedback = (contentId: string, feedback: 'like' | 'dislike') => {
  trackInteractionMutation.mutate({
    user_id: selectedUserId,
    content_id: contentId,
    interaction_type: feedback,
    timestamp: new Date().toISOString(),
    metadata: {
      source: 'personalization_studio',
      context: 'recommendation_feedback'
    }
  });
};
```

**Usage Pattern:**
- **User Selection**: Enter user ID to load personalized content and insights
- **Real-time Recommendations**: AI-powered recommendations with scoring and reasoning
- **Interactive Feedback**: Like/dislike buttons to improve personalization
- **Profile Management**: Reset user profiles for fresh personalization
- **Behavioral Insights**: Detailed analysis of user behavior patterns and preferences
- **Settings Configuration**: Adjustable personalization parameters (diversity, limits)
- **Performance Monitoring**: Real-time stats on personalization effectiveness

**Real-time Updates:** Recommendations and insights refresh every 5 minutes, stats every minute

### Trend Detection & Forecasting (`frontend/src/pages/Trends.tsx`)

**Primary APIs:**
- `analyzeTrends()` - Advanced trend analysis with multi-metric support
- `getTrendAlerts()` - Get configured trend alerts and notifications
- `configureTrendAlerts()` - Configure alerts for trend changes and anomalies

---

## Phase 5: Orchestration & Automation

### Workflow Orchestration Studio (`frontend/src/pages/WorkflowStudio.tsx`)

**Primary APIs:**
- `getWorkflowDefinitions()` - List all workflow definitions with filtering
- `getWorkflowExecutions()` - Get execution history for workflows
- `createWorkflowDefinition()` - Create new workflow with steps and triggers
- `executeWorkflow()` - Execute workflow with real-time monitoring
- `getWorkflowStats()` - Get workflow performance statistics

**WebSocket Connections:**
- `/ws/workflows` - Real-time workflow status updates
- **Message Types:** `workflow_status`, `workflow_progress`, `workflow_complete`, `workflow_failed`
- **Features:** Live execution monitoring, automatic UI updates, status notifications

**Usage Pattern:**
```typescript
// Real-time workflow monitoring
const workflowSubscription = webSocketService.subscribeToWorkflowUpdates(
  (update) => {
    console.log('Workflow update:', update);
    // Auto-refresh UI with latest status
    refetchExecutions();
  },
  { workflow_id: selectedWorkflow?.id }
);
```

### Integration Control Center (`frontend/src/pages/IntegrationHub.tsx`)

**Primary APIs:**
- `getApiGatewayStats()` - API gateway performance and route metrics
- `getWebhooks()` - List webhook subscriptions with delivery metrics
- `getQueues()` - Queue status and pending items
- `getBackendServices()` - Backend service health and metrics
- `subscribeWebhook()` - Create webhook subscriptions
- `registerBackendService()` - Register new backend services

**WebSocket Connections:**
- `/ws/integration` - Real-time integration events
- **Message Types:** `integration_event`, `webhook_delivery`, `queue_update`, `backend_health`
- **Features:** Live webhook delivery tracking, queue monitoring, backend health alerts

**Usage Pattern:**
```typescript
// Real-time integration monitoring
const integrationSubscription = webSocketService.subscribeToIntegrationEvents(
  (event) => {
    if (event.type === 'webhook_delivery') {
      // Update webhook delivery metrics
      refetchWebhooks();
    }
  }
);
```

### Load Balancing Dashboard (`frontend/src/pages/LoadBalancing.tsx`)

**Primary APIs:**
- `getLoadBalancerStats()` - Overall load balancing metrics
- `getBackendServices()` - Backend service status and load factors
- `registerBackendService()` - Register backend services for load balancing
- `getLoadBalancerHealth()` - Load balancer health status

**WebSocket Connections:**
- `/ws/load-balancing` - Real-time load balancing metrics
- **Message Types:** `backend_metrics`, `load_distribution`, `health_check`
- **Features:** Live backend monitoring, load distribution updates, health check alerts

**Usage Pattern:**
```typescript
// Real-time load balancing monitoring
const loadBalancingSubscription = webSocketService.subscribeToLoadBalancingMetrics(
  (metrics) => {
    if (metrics.type === 'backend_metrics') {
      // Update backend service metrics
      refetchBackends();
    }
  }
);
```

### Phase 5 WebSocket Architecture

**Connection Management:**
- **Authentication:** JWT token-based authentication for all Phase 5 WebSocket connections
- **Heartbeat:** 30-second ping/pong with 90-second timeout (backend specification)
- **Rate Limiting:** 100 messages/minute per connection with client-side enforcement
- **Auto-Reconnection:** Exponential backoff with max 5 retry attempts

**Message Format:**
```json
{
  "type": "workflow_status|integration_event|backend_metrics",
  "data": {
    "timestamp": "2024-01-01T12:00:00Z",
    "workflow_id|event_type|backend_id": "identifier",
    "status|details|metrics": "payload"
  }
}
```

**Real-time Features:**
- ✅ **Workflow Execution Monitoring:** Live status updates during workflow execution
- ✅ **Integration Event Streaming:** Real-time webhook deliveries and queue updates
- ✅ **Load Balancing Metrics:** Live backend health and performance monitoring
- ✅ **Automatic UI Updates:** Components refresh automatically on WebSocket events
- ✅ **Connection Resilience:** Robust reconnection and error handling

**Trend Analysis Data Flow:**
```typescript
// Comprehensive trend analysis across multiple metrics
const trendAnalysisQuery = useQuery({
  queryKey: ['trend-analysis', timePeriodDays, selectedMetrics],
  queryFn: () => apiClient.analyzeTrends({
    time_period_days: timePeriodDays,
    metrics: selectedMetrics,
    trend_types: ['emerging', 'declining', 'seasonal'],
  }),
  refetchInterval: autoRefresh ? 300000 : false, // Auto-refresh every 5 minutes
});

// Forecasting with configurable horizon
const forecastingQuery = useQuery({
  queryKey: ['forecasting', timePeriodDays, forecastHorizon, selectedMetrics],
  queryFn: () => apiClient.analyzeTrends({
    time_period_days: timePeriodDays,
    metrics: selectedMetrics,
    trend_types: ['emerging', 'declining', 'seasonal'],
  }),
  refetchInterval: autoRefresh ? 300000 : false,
});

// Anomaly detection with configurable sensitivity
const anomalyQuery = useQuery({
  queryKey: ['anomaly-detection', timePeriodDays, anomalyThreshold, selectedMetrics],
  queryFn: () => apiClient.analyzeTrends({
    time_period_days: timePeriodDays,
    metrics: selectedMetrics,
    trend_types: ['emerging', 'declining', 'seasonal'],
  }),
  refetchInterval: autoRefresh ? 300000 : false,
});
```

**Alert Configuration:**
```typescript
// Configure alerts for trend changes
const alertConfigMutation = useMutation({
  mutationFn: (config: any) => Promise.resolve(config), // Placeholder for actual API
  onSuccess: () => {
    // Handle alert configuration success
    console.log('Alert configured successfully');
  },
});

// Interactive alert setup
const handleConfigureAlert = (metric: string, threshold: number, trendType: string) => {
  alertConfigMutation.mutate({
    metric,
    threshold,
    trend_type: trendType,
    notification_channels: ['email', 'dashboard'],
    enabled: true,
  });
};
```

**Usage Pattern:**
- **Multi-Metric Analysis**: Analyze trends across usage, performance, content, and user metrics simultaneously
- **Interactive Forecasting**: Configure forecast horizon and view predictive insights
- **Anomaly Detection**: Real-time anomaly detection with configurable sensitivity thresholds
- **Alert Management**: Set up alerts for significant trend changes and anomalies
- **Auto-Refresh**: Optional auto-refresh every 5 minutes for real-time monitoring
- **Settings Configuration**: Adjustable parameters for trend detection sensitivity and forecasting accuracy

**Real-time Updates:** Trend analysis refreshes every 5 minutes when auto-refresh is enabled

### Search Intelligence Hub (`frontend/src/pages/SearchIntelligence.tsx`)

**Primary APIs:**
- `getAnalyticsDashboard()` - Get comprehensive search analytics and metrics
- `getContentInsights()` - Get search insights and optimization recommendations
- `trackInteraction()` - Track search events and user interactions

**Search Analytics Data Flow:**
```typescript
// Comprehensive search analytics dashboard
const searchAnalyticsQuery = useQuery({
  queryKey: ['search-analytics', timePeriodDays],
  queryFn: () => apiClient.getAnalyticsDashboard({
    time_period_days: timePeriodDays,
    metrics: ['search'],
  }),
  refetchInterval: autoRefresh ? 300000 : false, // Auto-refresh every 5 minutes
});

// Query-specific performance analysis
const queryPerformanceQuery = useQuery({
  queryKey: ['query-performance', searchQuery, timePeriodDays],
  queryFn: () => apiClient.getAnalyticsDashboard({
    time_period_days: timePeriodDays,
    metrics: ['search'],
  }),
  enabled: !!searchQuery,
  refetchInterval: autoRefresh ? 300000 : false,
});

// Search insights and optimization recommendations
const searchInsightsQuery = useQuery({
  queryKey: ['search-insights', timePeriodDays],
  queryFn: () => apiClient.getContentInsights(undefined, {
    time_period_days: timePeriodDays,
  }),
  refetchInterval: autoRefresh ? 300000 : false,
});
```

**Search Event Tracking:**
```typescript
// Track search events for analytics
const trackSearchMutation = useMutation({
  mutationFn: (searchEvent: any) => Promise.resolve(searchEvent), // Placeholder for actual API
  onSuccess: () => {
    // Invalidate and refetch analytics data
    queryClient.invalidateQueries({ queryKey: ['search-analytics'] });
    queryClient.invalidateQueries({ queryKey: ['query-performance'] });
  },
});

// Interactive search event tracking
const handleTrackSearch = (query: string, resultsCount: number, responseTime: number) => {
  trackSearchMutation.mutate({
    query,
    results_count: resultsCount,
    response_time_ms: responseTime,
    timestamp: new Date().toISOString(),
    user_id: 'current-user', // Would come from auth context
  });
};
```

**Usage Pattern:**
- **Query Analysis**: Enter specific search queries to analyze performance metrics
- **Real-time Monitoring**: Auto-refresh search analytics every 5 minutes
- **Performance Insights**: Detailed analysis of search success rates and response times
- **Optimization Recommendations**: AI-powered suggestions for search improvement
- **Interactive Feedback**: Track search events and user interactions
- **Multi-tab Interface**: Organized views for Analytics, Performance, Insights, and Trends

**Real-time Updates:** Search analytics refreshes every 5 minutes when auto-refresh is enabled

**HTTP Client Integration:**
```typescript
// HTTP Request Builder State
const [httpRequest, setHttpRequest] = useState({
  method: 'GET',
  url: '',
  headers: [{ key: '', value: '' }],
  data: '',
  timeout: 30,
  retry_config: { max_attempts: 3, backoff_factor: 2.0 },
  rate_limit: { requests_per_minute: 60 }
});

// Make Agentic HTTP Request
const makeHttpRequestMutation = useMutation({
  mutationFn: (requestData: any) => apiClient.makeAgenticHttpRequest(requestData),
  onSuccess: (response) => {
    setHttpResponse(response);
  },
});

// Get HTTP Client Metrics
const getHttpMetricsMutation = useMutation({
  mutationFn: () => apiClient.getHttpClientMetrics(),
  onSuccess: (metrics) => {
    setHttpMetrics(metrics);
  },
});
```

**Usage Pattern:**
- **Request Builder**: Interactive form for configuring HTTP requests with headers, body, timeout, and retry settings
- **Metrics Dashboard**: Real-time display of HTTP client performance (success rate, response times, request counts)
- **Response Viewer**: Formatted display of HTTP responses with status codes, headers, and body content
- **Rate Limiting**: Built-in rate limit controls and monitoring

### Real-Time Logs Viewer (`frontend/src/components/LogsViewer.tsx`)

**Primary WebSocket Connection:**
- `/ws/logs` - Real-time log streaming with JWT authentication

**Features:**
- **Multi-channel log management**: Create separate channels for different log streams
- **Advanced filtering**: Filter by agent_id, task_id, and log level
- **Real-time updates**: Live log streaming from backend agents
- **Auto-scroll**: Automatic scrolling to latest logs with manual override
- **Log persistence**: Configurable maximum log count per channel

**WebSocket Usage:**
```typescript
// Subscribe to logs with filters
const unsubscribe = webSocketService.subscribeToLogs(
  (logEntry) => {
    // Handle incoming log messages
    updateChannelLogs(logEntry);
  },
  {
    agent_id: 'specific-agent-id',
    level: 'info'
  }
);

// Cleanup on component unmount
unsubscribe();
```

**Channel Management:**
- **All Logs**: Default channel showing all incoming logs
- **Custom Channels**: User-created channels with specific filters
- **Channel Filters**: Agent-specific, task-specific, or level-specific log streams
- **Visual Indicators**: Color-coded channels with log count badges

**Real-time Updates:** ✅ **Fully implemented with WebSocket streaming**

## WebSocket Connections

### WebSocket Service (`frontend/src/services/websocket.ts`)

**Configuration:**
- **Base URL**: `VITE_WS_URL` environment variable
- **Authentication**: JWT token via query parameter (`?token=JWT_TOKEN`)
- **Reconnection**: Automatic with exponential backoff (max 5 attempts)
- **Message Handling**: Event-driven with typed message handlers

#### 📋 **CONFIRMED SPECIFICATIONS SUMMARY**

| Specification | Value | Implementation Status |
|---------------|-------|----------------------|
| **Heartbeat** | ✅ 30-second ping/pong | ✅ **Fully Implemented** |
| **Connection Limits** | ✅ 50 per user, 200 global | ✅ **Client Awareness** |
| **Rate Limiting** | ✅ 100 messages/minute | ✅ **Client-Side Limiting** |
| **Authentication** | ✅ JWT required | ✅ **Query Parameter** |
| **Protocol** | ✅ Raw WebSocket | ✅ **Native API** |
| **Connection Timeout** | ✅ 90 seconds | ✅ **Auto-Disconnect** |

### Available Endpoints

#### 1. Logs Stream (`/ws/logs`)
**Purpose:** Real-time log streaming for monitoring agent activities
**Authentication:** Required (JWT token)
**Parameters:**
- `agent_id` (optional): Filter logs by specific agent
- `task_id` (optional): Filter logs by specific task
- `level` (optional): Filter by log level (debug, info, warning, error)

**Message Format (Backend Specification):**
```json
{
  "type": "log_entry",
  "data": {
    "timestamp": "2024-01-01T12:00:00Z",
    "level": "info|warning|error|debug",
    "message": "Log message content",
    "agent_id": "optional-agent-uuid",
    "task_id": "optional-task-uuid",
    "source": "pipeline|agent|system"
  }
}
```

**Supported Log Levels:** `debug`, `info`, `warning`, `error`
**Supported Sources:** `pipeline`, `agent`, `system`

**Current Usage:**
- ✅ **Authentication flow**: Connected during login/logout in auth flow
- ✅ **Real-time logs viewer**: Used in LogsViewer component for live log streaming
- ✅ **Channel filtering**: Supports agent-specific, task-specific, and level-based filtering
- ✅ **Multi-channel management**: Multiple concurrent log streams with independent filters

#### 2. Task Monitoring (`/ws/tasks/{task_id}`)
**Purpose:** Real-time task progress and status updates
**Authentication:** Required (JWT token)
**Parameters:** Task ID in URL path

**Message Types:**
- `task_status`: Current task status
- `task_progress`: Progress percentage and messages
- `task_complete`: Task completion notification

**Message Format:**
```json
{
  "type": "task_status",
  "data": {
    "task_id": "task-uuid",
    "status": "running",
    "progress": 45,
    "message": "Processing step 3 of 5",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

**Current Usage:** Not currently used in frontend, but infrastructure ready.

### WebSocket Connection Flow

```typescript
// Connection with authentication
const token = apiClient.getAuthToken();
webSocketService.connect('logs', token || undefined);

// Subscription to logs
const unsubscribe = webSocketService.subscribeToLogs(
  (logEntry) => {
    console.log('New log:', logEntry);
  },
  {
    agent_id: 'specific-agent-id',
    level: 'info'
  }
);

// Cleanup
unsubscribe();
```

### Heartbeat Mechanism (✅ IMPLEMENTED)

The WebSocket service now includes automatic heartbeat management:

- **Ping Interval**: Sends ping messages every 30 seconds
- **Pong Response**: Handles pong messages with timestamps
- **Connection Timeout**: Automatically disconnects after 90 seconds of no pong response
- **Auto-Reconnection**: Triggers reconnection on heartbeat failure

### Rate Limiting (✅ IMPLEMENTED)

Client-side rate limiting prevents exceeding backend limits:

- **Message Limit**: Maximum 100 messages per minute per connection
- **Client-Side Tracking**: Monitors message count and enforces limits
- **Rate Limit Warnings**: Logs warnings when approaching limits
- **Error Handling**: Gracefully handles rate limit error responses from backend

### Server-Sent Events (SSE) Alternative

**Endpoint:** `GET /api/v1/logs/stream/{task_id}`
**Purpose:** Alternative to WebSocket for real-time log streaming
**Authentication:** JWT token in Authorization header
**Advantages:** Simpler to implement, better firewall compatibility
**Usage:**
```javascript
const eventSource = new EventSource('/api/v1/logs/stream/your-task-id', {
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
});

eventSource.onmessage = function(event) {
  const logData = JSON.parse(event.data);
  console.log('SSE Log:', logData);
};

eventSource.onerror = function(error) {
  console.error('SSE Error:', error);
};
```

## Error Handling Patterns

### Network Errors
```typescript
// Handled in ApiClient
if (error.code === 'ERR_NETWORK') {
  return {
    detail: 'Network error: Unable to connect to the server',
    status_code: 0,
  };
}
```

### CORS Errors
```typescript
if (error.response.status === 0) {
  return {
    detail: 'CORS error: Server not configured for this origin',
    status_code: 0,
  };
}
```

### Authentication Errors
```typescript
// Automatic redirect on 401
if (error.response?.status === 401) {
  this.clearAuthToken();
  window.location.href = '/login';
}
```

### Component-Level Error Handling
```typescript
const { data, error, refetch } = useQuery({
  queryKey: ['data'],
  queryFn: () => apiClient.getData(),
});

if (error) {
  return (
    <Alert severity="error" action={
      <Button onClick={() => refetch()}>Retry</Button>
    }>
      Failed to load data
    </Alert>
  );
}
```

## API Endpoints Reference

### Core Endpoints
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/health` | System health check | Auth validation |
| `GET` | `/api/v1/ready` | Readiness check | - |
| `GET` | `/api/v1/metrics` | Prometheus metrics | - |

### Authentication
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `POST` | `/api/v1/auth/login` | User login | Login page |
| `POST` | `/api/v1/auth/logout` | User logout | Auth flow |
| `POST` | `/api/v1/auth/change-password` | Password change | Settings page |

### Agent Management
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/agents` | List agents | Dashboard, AgentManagement |
| `GET` | `/api/v1/agents/{id}` | Get specific agent | - |
| `POST` | `/api/v1/agents/create` | Create agent | AgentManagement |
| `PUT` | `/api/v1/agents/{id}` | Update agent | AgentManagement |
| `DELETE` | `/api/v1/agents/{id}` | Delete agent | AgentManagement |

### Task Management
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/tasks` | List tasks | Dashboard |
| `GET` | `/api/v1/tasks/{id}/status` | Get task status | - |
| `POST` | `/api/v1/tasks/run` | Execute task | - |
| `DELETE` | `/api/v1/tasks/{id}` | Cancel task | - |

### System Monitoring
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/system/metrics` | All system metrics | Dashboard |
| `GET` | `/api/v1/system/metrics/cpu` | CPU metrics | SystemHealth |
| `GET` | `/api/v1/system/metrics/memory` | Memory metrics | SystemHealth |
| `GET` | `/api/v1/system/metrics/disk` | Disk metrics | SystemHealth |
| `GET` | `/api/v1/system/metrics/network` | Network metrics | SystemHealth |
| `GET` | `/api/v1/system/metrics/gpu` | GPU metrics | SystemHealth, Dashboard |
| `GET` | `/api/v1/system/metrics/load` | Load averages | SystemHealth |
| `GET` | `/api/v1/system/metrics/swap` | Swap metrics | SystemHealth |
| `GET` | `/api/v1/system/info` | System info | SystemHealth |

### Security
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/security/status` | Security status and resource limits | Dashboard, Security |
| `GET` | `/api/v1/security/health` | Security health | Security |
| `GET` | `/api/v1/security/incidents` | Security incidents | Security |
| `POST` | `/api/v1/security/incidents/{id}/resolve` | Resolve incident | Security |

### Ollama Integration
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/ollama/models` | Available models | - |
| `GET` | `/api/v1/ollama/models/names` | Model names only | AgentManagement |
| `GET` | `/api/v1/ollama/health` | Ollama health | Dashboard, SystemHealth |
| `POST` | `/api/v1/ollama/models/pull/{name}` | Pull model | - |

### Logging
| Method | Endpoint | Purpose | Used By |
|--------|----------|---------|---------|
| `GET` | `/api/v1/logs/{task_id}` | Task logs | - |
| `GET` | `/api/v1/logs/history` | Historical logs | - |
| `GET` | `/api/v1/logs/stream/{task_id}` | Server-Sent Events stream | Future: LogsViewer |

## Backend Integration Status ✅

The frontend implementation has been updated to fully align with the backend's expanded WebSocket and logging documentation. Key alignments:

- ✅ **WebSocket Authentication**: JWT token implementation matches backend requirements
- ✅ **Message Format**: Frontend parsing matches backend message schema exactly
- ✅ **Connection URLs**: Support for both development (`ws://`) and production (`wss://`) environments
- ✅ **Raw WebSocket Usage**: Correctly uses raw WebSockets (not Socket.IO) as specified
- ✅ **Query Parameters**: Proper implementation of `agent_id`, `task_id`, and `level` filtering
- ✅ **Error Handling**: Comprehensive error handling for connection failures and invalid tokens
- ✅ **Heartbeat Mechanism**: 30-second ping/pong with 90-second timeout implemented
- ✅ **Rate Limiting**: Client-side rate limiting (100 messages/minute) with backend error handling
- ✅ **Connection Limits**: Awareness of 50 per user, 200 global connection limits

## Backend Requirements for Full Functionality

### WebSocket Log Streaming
The real-time logs viewer requires the backend to send log messages via WebSocket with the following message format:

```json
{
  "type": "log_entry",
  "data": {
    "timestamp": "2024-01-01T12:00:00Z",
    "level": "info|warning|error|debug",
    "message": "Log message content",
    "agent_id": "optional-agent-uuid",
    "task_id": "optional-task-uuid",
    "source": "pipeline|agent|system"
  }
}
```

### Required Backend Information ✅
Based on the updated backend documentation, the following specifications are confirmed:

1. ✅ **Log Message Schema**: Complete specification provided (see message format above)
2. ✅ **Agent ID Format**: UUID format for agent identification
3. ✅ **Task ID Format**: UUID format for task identification
4. ✅ **Log Levels**: `debug`, `info`, `warning`, `error`
5. ✅ **WebSocket Heartbeat**: 30-second ping/pong mechanism implemented
6. ✅ **Connection Limits**: 50 per user, 200 global maximum concurrent connections
7. ✅ **Rate Limiting**: 100 messages per minute per WebSocket connection

### Backend Log Sources ✅
Based on backend documentation, the following log sources are supported:

- **Agent execution**: Logs from running agents (`source: "agent"`)
- **Task processing**: Task-specific execution logs (`source: "pipeline"`)
- **System events**: Backend system-level logs (`source: "system"`)
- **Security events**: Security-related log entries (integrated with security monitoring)

## Future Enhancements

### Implemented WebSocket Integration ✅
1. ✅ **Real-time Logs Streaming**: Full implementation with channel management and filtering
2. ✅ **Multi-channel Log Viewer**: Agent-specific and task-specific log streams
3. ✅ **Live Log Filtering**: Real-time filtering by agent, task, and log level
4. ✅ **WebSocket Authentication**: JWT token integration for secure connections

### Future WebSocket Enhancements
1. **Real-time Dashboard Updates**: Connect to `/ws/logs` for live metrics in dashboard
2. **Task Progress Monitoring**: Use `/ws/tasks/{id}` for task execution feedback
3. **Security Incident Alerts**: Real-time security notifications
4. **System Metrics Streaming**: Live system metrics via WebSocket

### Potential API Additions
1. **Bulk Operations**: Batch agent/task operations
2. **Advanced Filtering**: More sophisticated query parameters
3. **WebSocket Authentication**: Token refresh for long-running connections

## Maintenance Notes

### When Backend API Changes:
1. Update `ApiClient` methods in `frontend/src/services/api.ts`
2. Update component queries that use affected endpoints
3. Test error handling for new response formats
4. Update this documentation

### When Adding New Features:
1. Add new API methods to `ApiClient`
2. Create/update React Query hooks in components
3. Add error handling and loading states
4. Document in this file

### WebSocket Usage:
1. Always include JWT token in connection
2. Handle reconnection logic
3. Clean up subscriptions on component unmount
4. Parse messages safely with error handling

### Debugging Features Added:
1. **GPU Processing Logs**: Console logs for each GPU being processed from API response
2. **GPU Rendering Logs**: Console logs for each GPU being rendered in React components
3. **Unique React Keys**: Improved keys for proper component re-rendering: `gpu-${gpu.id}-${_index}`
4. **Error Boundary Ready**: Components prepared for error boundary implementation

### Recent Fixes Applied:
1. **Scroll Bar Visibility**: Fixed CSS conflicts preventing scroll bars from appearing
2. **GPU Display**: Fixed syntax error and added debugging for multi-GPU display
3. **Documentation Updates**: Updated both backend and frontend documentation to reflect changes

This document should be updated whenever new API calls or WebSocket connections are added to maintain it as the source of truth for frontend-backend integration.