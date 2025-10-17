import apiClient from './api';

/**
 * Email Search API - Advanced Features
 *
 * Provides advanced search capabilities including semantic search,
 * thread detection, search suggestions, and dynamic filtering.
 */

export type SearchType = 'semantic' | 'keyword' | 'hybrid';
export type SortOrder = 'relevance' | 'date_desc' | 'date_asc' | 'importance_desc' | 'importance_asc';

export interface AdvancedSearchParams {
  query: string;
  search_type?: SearchType;
  limit?: number;
  offset?: number;
  include_threads?: boolean;

  // Filters
  date_from?: string;
  date_to?: string;
  sender?: string;
  categories?: string[];
  min_importance?: number;
  has_attachments?: boolean;
  thread_id?: string;

  // Sorting
  sort_by?: SortOrder;
}

export interface SearchResult {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  body_text: string;
  sent_at: string;
  relevance_score: number;
  importance_score: number;
  snippet: string;
  thread_id?: string;
  categories?: string[];
  has_attachments: boolean;
}

export interface SearchResponse {
  query: string;
  search_type: string;
  total_count: number;
  results: SearchResult[];
  facets: {
    categories?: Record<string, number>;
    senders?: Record<string, number>;
    date_ranges?: Record<string, number>;
    importance_levels?: Record<string, number>;
  };
  suggestions: string[];
  search_time_ms: number;
  timestamp: string;
}

export interface EmailThread {
  thread_id: string;
  subject: string;
  message_count: number;
  participants: string[];
  first_message_date: string;
  last_message_date: string;
  emails: Array<{
    email_id: string;
    subject: string;
    sender_email: string;
    sent_at: string;
    snippet: string;
  }>;
}

export interface ThreadDetectionResult {
  threads: EmailThread[];
  unthreaded_emails: any[];
  total_emails_processed: number;
  threads_created: number;
  average_thread_length: number;
  processing_time_ms: number;
  timestamp: string;
}

export interface SearchFilters {
  categories: Array<{ value: string; label: string }>;
  importance_levels: Array<{ value: string; label: string }>;
  date_ranges: Array<{ value: string; label: string }>;
  senders: string[];
}

/**
 * Perform advanced search with filters and options
 */
export const advancedSearch = async (params: AdvancedSearchParams): Promise<SearchResponse> => {
  const response = await apiClient.post(
    '/email-search/search',
    params,
    {
      params: { user_id: 'current' },
      headers: {
        'X-API-Key': localStorage.getItem('api_key') || '',
      },
    }
  );
  return response.data;
};

/**
 * Get search query suggestions based on partial input
 */
export const getSearchSuggestions = async (query: string, limit = 10): Promise<string[]> => {
  const response = await apiClient.get('/email-search/suggestions', {
    params: {
      query,
      user_id: 'current',
      limit,
    },
  });
  return response.data.suggestions;
};

/**
 * Get available filter options dynamically
 */
export const getSearchFilters = async (): Promise<SearchFilters> => {
  const response = await apiClient.get('/email-search/filters', {
    params: { user_id: 'current' },
  });
  return response.data.filters;
};

/**
 * Perform advanced search with complex boolean queries
 */
export const advancedComplexSearch = async (
  query: string,
  filters?: Record<string, any>
): Promise<SearchResponse> => {
  const response = await apiClient.post(
    '/email-search/advanced',
    null,
    {
      params: {
        query,
        filters: JSON.stringify(filters || {}),
        user_id: 'current',
      },
    }
  );
  return response.data;
};

/**
 * Detect and group emails into conversation threads
 */
export const detectThreads = async (emails: any[]): Promise<ThreadDetectionResult> => {
  const response = await apiClient.post(
    '/email-search/threads/detect',
    {
      emails,
      include_analysis: true,
    },
    {
      params: { user_id: 'current' },
    }
  );
  return response.data;
};

/**
 * Get detailed information about a specific thread
 */
export const getThread = async (threadId: string, includeRelated = false): Promise<EmailThread> => {
  const response = await apiClient.get(`/email-search/threads/${threadId}`, {
    params: {
      user_id: 'current',
      include_related: includeRelated,
    },
  });
  return response.data;
};

/**
 * Get search analytics and usage patterns
 */
export const getSearchAnalytics = async (periodDays = 30): Promise<any> => {
  const response = await apiClient.get('/email-search/analytics/search', {
    params: {
      user_id: 'current',
      period_days: periodDays,
    },
  });
  return response.data;
};

export default {
  advancedSearch,
  getSearchSuggestions,
  getSearchFilters,
  advancedComplexSearch,
  detectThreads,
  getThread,
  getSearchAnalytics,
};
