import type { LogEntry } from '../types';
import apiClient from './api';

interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string; // For pong messages
  message?: string; // For error messages
  retry_after?: number; // For rate limiting errors
}

class WebSocketService {
  private socket: WebSocket | null = null;
  private url: string;
  private currentEndpoint: string = 'logs';
  private reconnectAttempts: number = 0;
  private readonly maxReconnectAttempts: number = parseInt(import.meta.env.VITE_WS_MAX_RECONNECT_ATTEMPTS || '5');
  private readonly reconnectDelay: number = parseInt(import.meta.env.VITE_WS_RECONNECT_DELAY || '1000');
  private messageHandlers: Map<string, ((data: any) => void)[]> = new Map();
  private connectionStatusCallbacks: ((status: 'connecting' | 'connected' | 'disconnected' | 'error', error?: string) => void)[] = [];

  // Heartbeat mechanism (30-second ping/pong)
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private lastPongTime: number = Date.now();
  private connectionTimeout: NodeJS.Timeout | null = null;

  // Rate limiting (configurable via environment variables)
  private messageCount: number = 0;
  private rateLimitResetTime: number = Date.now();
  private readonly MAX_MESSAGES_PER_MINUTE = parseInt(import.meta.env.VITE_WS_MAX_MESSAGES_PER_MINUTE || '100');
  private readonly RATE_LIMIT_WINDOW_MS = parseInt(import.meta.env.VITE_WS_RATE_LIMIT_WINDOW_MS || '60000'); // 1 minute

  constructor() {
    const wsUrl = import.meta.env.VITE_WS_URL;
    if (!wsUrl) {
      throw new Error('VITE_WS_URL environment variable is not defined. Please check your .env file.');
    }
    this.url = wsUrl;
  }

  // Heartbeat mechanism methods
  private startHeartbeat() {
    this.stopHeartbeat(); // Clear any existing heartbeat

    const heartbeatInterval = parseInt(import.meta.env.VITE_WS_HEARTBEAT_INTERVAL || '30000'); // 30 seconds default
    const connectionTimeout = parseInt(import.meta.env.VITE_WS_CONNECTION_TIMEOUT || '90000'); // 90 seconds default

    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.sendPing();
      }
    }, heartbeatInterval);

    // Set connection timeout
    this.connectionTimeout = setTimeout(() => {
      console.warn(`WebSocket connection timeout - no pong received for ${connectionTimeout / 1000} seconds`);
      this.disconnect();
    }, connectionTimeout);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
  }

  private sendPing() {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'ping' }));
    }
  }

  private handlePong(timestamp: string) {
    this.lastPongTime = Date.now();

    // Reset connection timeout
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
    }

    const connectionTimeout = parseInt(import.meta.env.VITE_WS_CONNECTION_TIMEOUT || '90000');
    this.connectionTimeout = setTimeout(() => {
      console.warn(`WebSocket connection timeout - no pong received for ${connectionTimeout / 1000} seconds`);
      this.disconnect();
    }, connectionTimeout);

    console.log('Heartbeat received:', timestamp, `(last pong: ${this.lastPongTime})`);
  }

  // Rate limiting methods
  private checkRateLimit(): boolean {
    const now = Date.now();

    // Reset counter if window has passed
    if (now - this.rateLimitResetTime >= this.RATE_LIMIT_WINDOW_MS) {
      this.messageCount = 0;
      this.rateLimitResetTime = now;
    }

    // Check if we're approaching the limit (leave buffer for ping messages)
    if (this.messageCount >= this.MAX_MESSAGES_PER_MINUTE - 10) {
      console.warn('Approaching WebSocket rate limit, slowing down...');
      return false;
    }

    return true;
  }

  private incrementMessageCount() {
    this.messageCount++;
  }

  connect(endpoint: string = 'logs', token?: string) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected, returning existing connection');
      return this.socket;
    }

    // Store current endpoint for reconnection
    this.currentEndpoint = endpoint;

    // Build URL with specific endpoint and token if provided
    const baseUrl = this.url.replace('/ws', ''); // Remove trailing /ws if present
    const wsUrl = token ? `${baseUrl}/ws/${endpoint}?token=${token}` : `${baseUrl}/ws/${endpoint}`;

    console.log('Attempting WebSocket connection:', wsUrl);
    console.log('Token provided:', !!token);

    this.notifyConnectionStatus('connecting');
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.notifyConnectionStatus('connected');
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.notifyConnectionStatus('disconnected');
      this.attemptReconnect(token);
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket connection error:', error);
      this.notifyConnectionStatus('error', 'WebSocket connection failed');
    };

    this.socket.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        // Handle heartbeat pong messages
        if (message.type === 'pong' && message.timestamp) {
          this.handlePong(message.timestamp);
          return;
        }

        // Handle rate limiting errors
        if (message.type === 'error' && message.retry_after) {
          console.error('WebSocket rate limited:', message.message);
          console.log(`Retry after ${message.retry_after} seconds`);
          return;
        }

        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    return this.socket;
  }

  private attemptReconnect(token?: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.connect(this.currentEndpoint, token);
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  private handleMessage(message: WebSocketMessage) {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.data);
        } catch (error) {
          console.error(`Error in message handler for ${message.type}:`, error);
        }
      });
    }
  }

  disconnect() {
    // Stop heartbeat before disconnecting
    this.stopHeartbeat();

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.messageHandlers.clear();

    // Reset rate limiting counters
    this.messageCount = 0;
    this.rateLimitResetTime = Date.now();
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  // Connection status management
  private notifyConnectionStatus(status: 'connecting' | 'connected' | 'disconnected' | 'error', error?: string) {
    this.connectionStatusCallbacks.forEach(callback => {
      try {
        callback(status, error);
      } catch (err) {
        console.error('Error in connection status callback:', err);
      }
    });
  }

  onConnectionStatus(callback: (status: 'connecting' | 'connected' | 'disconnected' | 'error', error?: string) => void) {
    this.connectionStatusCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.connectionStatusCallbacks.indexOf(callback);
      if (index > -1) {
        this.connectionStatusCallbacks.splice(index, 1);
      }
    };
  }

  // Subscribe to real-time logs
  subscribeToLogs(
    callback: (logEntry: LogEntry) => void,
    filters?: {
      agent_id?: string;
      task_id?: string;
      level?: string;
    }
  ) {
    // Connect to logs endpoint with filters as query parameters
    const queryParams = new URLSearchParams();
    if (filters?.agent_id) queryParams.append('agent_id', filters.agent_id);
    if (filters?.task_id) queryParams.append('task_id', filters.task_id);
    if (filters?.level) queryParams.append('level', filters.level);

    const endpoint = `logs${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect to the logs endpoint with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handler for log_entry messages
    this.addMessageHandler('log_entry', callback);

    return () => {
      this.removeMessageHandler('log_entry', callback);
    };
  }

  // Subscribe to task updates
  subscribeToTaskUpdates(
    taskId: string,
    callback: (update: any) => void
  ) {
    // Connect to task-specific endpoint
    const endpoint = `tasks/${taskId}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handler for task messages
    this.addMessageHandler('task_status', callback);
    this.addMessageHandler('task_progress', callback);
    this.addMessageHandler('task_complete', callback);

    return () => {
      this.removeMessageHandler('task_status', callback);
      this.removeMessageHandler('task_progress', callback);
      this.removeMessageHandler('task_complete', callback);
    };
  }

  // Subscribe to general notifications
  subscribeToNotifications(callback: (notification: any) => void) {
    this.addMessageHandler('notification', callback);

    return () => {
      this.removeMessageHandler('notification', callback);
    };
  }

  // ==========================================
  // PHASE 5: ORCHESTRATION & AUTOMATION
  // ==========================================

  // Subscribe to workflow updates
  subscribeToWorkflowUpdates(
    callback: (update: any) => void,
    filters?: {
      workflow_id?: string;
      status?: string;
    }
  ) {
    // Connect to workflows endpoint with filters
    const queryParams = new URLSearchParams();
    if (filters?.workflow_id) queryParams.append('workflow_id', filters.workflow_id);
    if (filters?.status) queryParams.append('status', filters.status);

    const endpoint = `workflows${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handlers for workflow messages
    this.addMessageHandler('workflow_status', callback);
    this.addMessageHandler('workflow_progress', callback);
    this.addMessageHandler('workflow_complete', callback);
    this.addMessageHandler('workflow_failed', callback);

    return () => {
      this.removeMessageHandler('workflow_status', callback);
      this.removeMessageHandler('workflow_progress', callback);
      this.removeMessageHandler('workflow_complete', callback);
      this.removeMessageHandler('workflow_failed', callback);
    };
  }

  // Subscribe to integration events
  subscribeToIntegrationEvents(
    callback: (event: any) => void,
    filters?: {
      event_type?: string;
      source?: string;
    }
  ) {
    // Connect to integration endpoint with filters
    const queryParams = new URLSearchParams();
    if (filters?.event_type) queryParams.append('event_type', filters.event_type);
    if (filters?.source) queryParams.append('source', filters.source);

    const endpoint = `integration${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handlers for integration messages
    this.addMessageHandler('integration_event', callback);
    this.addMessageHandler('webhook_delivery', callback);
    this.addMessageHandler('queue_update', callback);
    this.addMessageHandler('backend_health', callback);

    return () => {
      this.removeMessageHandler('integration_event', callback);
      this.removeMessageHandler('webhook_delivery', callback);
      this.removeMessageHandler('queue_update', callback);
      this.removeMessageHandler('backend_health', callback);
    };
  }

  // Subscribe to load balancing metrics
  subscribeToLoadBalancingMetrics(
    callback: (metrics: any) => void,
    filters?: {
      backend_id?: string;
      metric_type?: string;
    }
  ) {
    // Connect to load-balancing endpoint with filters
    const queryParams = new URLSearchParams();
    if (filters?.backend_id) queryParams.append('backend_id', filters.backend_id);
    if (filters?.metric_type) queryParams.append('metric_type', filters.metric_type);

    const endpoint = `load-balancing${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handlers for load balancing messages
    this.addMessageHandler('backend_metrics', callback);
    this.addMessageHandler('load_distribution', callback);
    this.addMessageHandler('health_check', callback);

    return () => {
      this.removeMessageHandler('backend_metrics', callback);
      this.removeMessageHandler('load_distribution', callback);
      this.removeMessageHandler('health_check', callback);
    };
  }

  // ==========================================
  // KNOWLEDGE BASE WORKFLOW UPDATES
  // ==========================================

  // Subscribe to Knowledge Base workflow progress updates
  subscribeToKnowledgeBaseProgress(
    callback: (update: any) => void,
    filters?: {
      item_id?: string;
      workflow_id?: string;
      phase?: string;
    }
  ) {
    // Connect to knowledge base progress endpoint with filters
    const queryParams = new URLSearchParams();
    if (filters?.item_id) queryParams.append('item_id', filters.item_id);
    if (filters?.workflow_id) queryParams.append('workflow_id', filters.workflow_id);
    if (filters?.phase) queryParams.append('phase', filters.phase);

    const endpoint = `knowledge/progress${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handlers for Knowledge Base progress messages
    this.addMessageHandler('knowledge_progress', callback);
    this.addMessageHandler('phase_complete', callback);
    this.addMessageHandler('workflow_complete', callback);
    this.addMessageHandler('workflow_failed', callback);
    this.addMessageHandler('item_processed', callback);

    return () => {
      this.removeMessageHandler('knowledge_progress', callback);
      this.removeMessageHandler('phase_complete', callback);
      this.removeMessageHandler('workflow_complete', callback);
      this.removeMessageHandler('workflow_failed', callback);
      this.removeMessageHandler('item_processed', callback);
    };
  }

  // Subscribe to Knowledge Base item updates
  subscribeToKnowledgeBaseItems(
    callback: (update: any) => void,
    filters?: {
      category?: string;
      status?: string;
    }
  ) {
    // Connect to knowledge base items endpoint with filters
    const queryParams = new URLSearchParams();
    if (filters?.category) queryParams.append('category', filters.category);
    if (filters?.status) queryParams.append('status', filters.status);

    const endpoint = `knowledge/items${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handlers for Knowledge Base item messages
    this.addMessageHandler('item_created', callback);
    this.addMessageHandler('item_updated', callback);
    this.addMessageHandler('item_deleted', callback);
    this.addMessageHandler('item_reprocessed', callback);

    return () => {
      this.removeMessageHandler('item_created', callback);
      this.removeMessageHandler('item_updated', callback);
      this.removeMessageHandler('item_deleted', callback);
      this.removeMessageHandler('item_reprocessed', callback);
    };
  }

  // Subscribe to Knowledge Base search updates
  subscribeToKnowledgeBaseSearch(
    callback: (results: any) => void,
    filters?: {
      query?: string;
      category?: string;
      search_type?: string;
    }
  ) {
    // Connect to knowledge base search endpoint with filters
    const queryParams = new URLSearchParams();
    if (filters?.query) queryParams.append('query', filters.query);
    if (filters?.category) queryParams.append('category', filters.category);
    if (filters?.search_type) queryParams.append('search_type', filters.search_type);

    const endpoint = `knowledge/search${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Connect with authentication token
    const token = apiClient.getAuthToken();
    this.connect(endpoint, token || undefined);

    // Add handlers for Knowledge Base search messages
    this.addMessageHandler('search_results', callback);
    this.addMessageHandler('search_suggestions', callback);

    return () => {
      this.removeMessageHandler('search_results', callback);
      this.removeMessageHandler('search_suggestions', callback);
    };
  }

  private addMessageHandler(type: string, callback: (data: any) => void) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(callback);
  }

  private removeMessageHandler(type: string, callback: (data: any) => void) {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(callback);
      if (index > -1) {
        handlers.splice(index, 1);
      }
      if (handlers.length === 0) {
        this.messageHandlers.delete(type);
      }
    }
  }

  // Send custom messages with rate limiting
  send(type: string, data?: any) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected. Call connect() first.');
    }

    // Check rate limiting (skip for ping messages)
    if (type !== 'ping' && !this.checkRateLimit()) {
      console.warn('Message not sent due to rate limiting');
      return false;
    }

    const message = {
      type,
      ...(data && { data })
    };

    this.socket.send(JSON.stringify(message));
    if (type !== 'ping') {
      this.incrementMessageCount();
    }
    return true;
  }

  // Listen to custom message types
  on(type: string, callback: (data: any) => void) {
    this.addMessageHandler(type, callback);
  }

  // Remove message listener
  off(type: string, callback: (data: any) => void) {
    this.removeMessageHandler(type, callback);
  }
}

export const webSocketService = new WebSocketService();
export default webSocketService;