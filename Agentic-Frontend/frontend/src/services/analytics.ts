/**
 * Analytics Service for Assistant Performance Tracking
 *
 * Tracks timeout occurrences, connection quality, and response times
 * to optimize default values and improve user experience.
 */

interface AnalyticsEvent {
  type: 'timeout' | 'connection' | 'response' | 'error' | 'success';
  timestamp: number;
  data: any;
}

interface TimeoutEvent {
  type: 'connection' | 'response';
  configuredTimeout: number;
  actualDuration: number;
  model: string;
  messageLength: number;
}

interface ResponseMetrics {
  responseTime: number;
  model: string;
  messageLength: number;
  success: boolean;
  error?: string;
}

interface ConnectionMetrics {
  latency: number;
  quality: string;
  timestamp: number;
}

const ANALYTICS_STORAGE_KEY = 'assistant_analytics';
const MAX_EVENTS = 1000;

class AnalyticsService {
  private events: AnalyticsEvent[] = [];

  constructor() {
    this.loadEvents();
  }

  private loadEvents() {
    try {
      const stored = localStorage.getItem(ANALYTICS_STORAGE_KEY);
      if (stored) {
        this.events = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load analytics:', error);
      this.events = [];
    }
  }

  private saveEvents() {
    try {
      // Keep only last MAX_EVENTS
      if (this.events.length > MAX_EVENTS) {
        this.events = this.events.slice(-MAX_EVENTS);
      }
      localStorage.setItem(ANALYTICS_STORAGE_KEY, JSON.stringify(this.events));
    } catch (error) {
      console.error('Failed to save analytics:', error);
    }
  }

  private addEvent(type: AnalyticsEvent['type'], data: any) {
    this.events.push({
      type,
      timestamp: Date.now(),
      data,
    });
    this.saveEvents();
  }

  /**
   * Track a timeout event
   */
  trackTimeout(event: TimeoutEvent) {
    this.addEvent('timeout', event);
  }

  /**
   * Track connection metrics
   */
  trackConnection(metrics: ConnectionMetrics) {
    this.addEvent('connection', metrics);
  }

  /**
   * Track response metrics
   */
  trackResponse(metrics: ResponseMetrics) {
    this.addEvent(metrics.success ? 'success' : 'error', metrics);
  }

  /**
   * Get timeout statistics
   */
  getTimeoutStats(days = 30): {
    totalTimeouts: number;
    connectionTimeouts: number;
    responseTimeouts: number;
    avgConfiguredTimeout: number;
    avgActualDuration: number;
    timeoutsByModel: Record<string, number>;
  } {
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    const timeoutEvents = this.events.filter(
      e => e.type === 'timeout' && e.timestamp > cutoff
    );

    if (timeoutEvents.length === 0) {
      return {
        totalTimeouts: 0,
        connectionTimeouts: 0,
        responseTimeouts: 0,
        avgConfiguredTimeout: 0,
        avgActualDuration: 0,
        timeoutsByModel: {},
      };
    }

    const connectionTimeouts = timeoutEvents.filter(
      e => e.data.type === 'connection'
    ).length;

    const responseTimeouts = timeoutEvents.filter(
      e => e.data.type === 'response'
    ).length;

    const avgConfiguredTimeout =
      timeoutEvents.reduce((sum, e) => sum + e.data.configuredTimeout, 0) /
      timeoutEvents.length;

    const avgActualDuration =
      timeoutEvents.reduce((sum, e) => sum + e.data.actualDuration, 0) /
      timeoutEvents.length;

    const timeoutsByModel: Record<string, number> = {};
    timeoutEvents.forEach(e => {
      const model = e.data.model || 'unknown';
      timeoutsByModel[model] = (timeoutsByModel[model] || 0) + 1;
    });

    return {
      totalTimeouts: timeoutEvents.length,
      connectionTimeouts,
      responseTimeouts,
      avgConfiguredTimeout,
      avgActualDuration,
      timeoutsByModel,
    };
  }

  /**
   * Get response time statistics
   */
  getResponseTimeStats(days = 30): {
    avgResponseTime: number;
    medianResponseTime: number;
    p95ResponseTime: number;
    successRate: number;
    responsesByModel: Record<string, { avg: number; count: number }>;
  } {
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    const responseEvents = this.events.filter(
      e => (e.type === 'success' || e.type === 'error') && e.timestamp > cutoff
    );

    if (responseEvents.length === 0) {
      return {
        avgResponseTime: 0,
        medianResponseTime: 0,
        p95ResponseTime: 0,
        successRate: 0,
        responsesByModel: {},
      };
    }

    const responseTimes = responseEvents
      .map(e => e.data.responseTime)
      .filter(t => t !== undefined)
      .sort((a, b) => a - b);

    const avgResponseTime =
      responseTimes.reduce((sum, t) => sum + t, 0) / responseTimes.length;

    const medianResponseTime = responseTimes.length > 0
      ? responseTimes[Math.floor(responseTimes.length / 2)]
      : 0;

    const p95Index = Math.floor(responseTimes.length * 0.95);
    const p95ResponseTime = responseTimes.length > 0
      ? responseTimes[p95Index]
      : 0;

    const successCount = responseEvents.filter(e => e.type === 'success').length;
    const successRate = successCount / responseEvents.length;

    const responsesByModel: Record<string, { avg: number; count: number }> = {};
    responseEvents.forEach(e => {
      const model = e.data.model || 'unknown';
      if (!responsesByModel[model]) {
        responsesByModel[model] = { avg: 0, count: 0 };
      }
      responsesByModel[model].avg += e.data.responseTime;
      responsesByModel[model].count++;
    });

    Object.keys(responsesByModel).forEach(model => {
      responsesByModel[model].avg /= responsesByModel[model].count;
    });

    return {
      avgResponseTime,
      medianResponseTime,
      p95ResponseTime,
      successRate,
      responsesByModel,
    };
  }

  /**
   * Get connection quality statistics
   */
  getConnectionQualityStats(days = 30): {
    avgLatency: number;
    qualityDistribution: Record<string, number>;
    recentQuality: string;
  } {
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    const connectionEvents = this.events.filter(
      e => e.type === 'connection' && e.timestamp > cutoff
    );

    if (connectionEvents.length === 0) {
      return {
        avgLatency: 0,
        qualityDistribution: {},
        recentQuality: 'unknown',
      };
    }

    const avgLatency =
      connectionEvents.reduce((sum, e) => sum + e.data.latency, 0) /
      connectionEvents.length;

    const qualityDistribution: Record<string, number> = {};
    connectionEvents.forEach(e => {
      const quality = e.data.quality || 'unknown';
      qualityDistribution[quality] = (qualityDistribution[quality] || 0) + 1;
    });

    const recentQuality =
      connectionEvents.length > 0
        ? connectionEvents[connectionEvents.length - 1].data.quality
        : 'unknown';

    return {
      avgLatency,
      qualityDistribution,
      recentQuality,
    };
  }

  /**
   * Get recommended timeout values based on analytics
   */
  getRecommendedTimeouts(): {
    connectionTimeout: number;
    responseTimeout: number;
    confidence: number;
  } {
    const timeoutStats = this.getTimeoutStats(30);
    const responseStats = this.getResponseTimeStats(30);

    // If not enough data, return defaults
    if (this.events.length < 10) {
      return {
        connectionTimeout: 30000,
        responseTimeout: 120000,
        confidence: 0,
      };
    }

    // Calculate recommended connection timeout
    // Add 50% buffer to average actual duration for timeouts
    const recommendedConnection = Math.max(
      10000, // Minimum 10 seconds
      Math.min(
        60000, // Maximum 60 seconds
        timeoutStats.avgActualDuration * 1.5
      )
    );

    // Calculate recommended response timeout
    // Use p95 response time + 50% buffer
    const recommendedResponse = Math.max(
      30000, // Minimum 30 seconds
      Math.min(
        600000, // Maximum 10 minutes
        responseStats.p95ResponseTime * 1.5
      )
    );

    // Calculate confidence based on sample size
    const confidence = Math.min(1, this.events.length / 100);

    return {
      connectionTimeout: Math.round(recommendedConnection),
      responseTimeout: Math.round(recommendedResponse),
      confidence,
    };
  }

  /**
   * Clear all analytics data
   */
  clear() {
    this.events = [];
    this.saveEvents();
  }

  /**
   * Export analytics data
   */
  export(): string {
    return JSON.stringify(this.events, null, 2);
  }

  /**
   * Get summary report
   */
  getSummary(days = 30): string {
    const timeoutStats = this.getTimeoutStats(days);
    const responseStats = this.getResponseTimeStats(days);
    const connectionStats = this.getConnectionQualityStats(days);
    const recommended = this.getRecommendedTimeouts();

    return `
Analytics Summary (Last ${days} days)

Timeout Statistics:
- Total Timeouts: ${timeoutStats.totalTimeouts}
- Connection Timeouts: ${timeoutStats.connectionTimeouts}
- Response Timeouts: ${timeoutStats.responseTimeouts}
- Avg Configured Timeout: ${Math.round(timeoutStats.avgConfiguredTimeout / 1000)}s
- Avg Actual Duration: ${Math.round(timeoutStats.avgActualDuration / 1000)}s

Response Time Statistics:
- Average: ${Math.round(responseStats.avgResponseTime)}ms
- Median: ${Math.round(responseStats.medianResponseTime)}ms
- 95th Percentile: ${Math.round(responseStats.p95ResponseTime)}ms
- Success Rate: ${(responseStats.successRate * 100).toFixed(1)}%

Connection Quality:
- Average Latency: ${Math.round(connectionStats.avgLatency)}ms
- Recent Quality: ${connectionStats.recentQuality}

Recommended Settings:
- Connection Timeout: ${Math.round(recommended.connectionTimeout / 1000)}s
- Response Timeout: ${Math.round(recommended.responseTimeout / 1000)}s
- Confidence: ${(recommended.confidence * 100).toFixed(0)}%
`;
  }
}

export const analyticsService = new AnalyticsService();
