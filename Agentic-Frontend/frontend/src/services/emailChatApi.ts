import apiClient from './api';

/**
 * Email Chat API
 *
 * Provides conversational operations for emails including
 * summarization, search, organization, and action execution.
 */

export interface EmailSummary {
  summary: string;
  key_points: string[];
  sentiment: string;
  urgency_level: string;
  suggested_actions: string[];
  processing_time_ms: number;
}

export interface ChatSearchResult {
  emails: any[];
  query_interpretation: string;
  filters_applied: Record<string, any>;
  total_found: number;
}

export interface ChatActionResult {
  success: boolean;
  action_performed: string;
  affected_emails: number;
  message: string;
}

/**
 * Summarize an email using AI
 */
export const summarizeEmail = async (emailId: string): Promise<EmailSummary> => {
  const response = await apiClient.post('/api/v1/chat/summarize', {
    email_id: emailId,
  });
  return response.data;
};

/**
 * Search emails using natural language
 */
export const conversationalSearch = async (query: string): Promise<ChatSearchResult> => {
  const response = await apiClient.post('/api/v1/chat/search', {
    query,
  });
  return response.data;
};

/**
 * Organize emails via conversational command
 */
export const organizeEmails = async (
  emailIds: string[],
  instruction: string
): Promise<ChatActionResult> => {
  const response = await apiClient.post('/api/v1/chat/organize', {
    email_ids: emailIds,
    instruction,
  });
  return response.data;
};

/**
 * Execute action via conversational command
 */
export const executeChatAction = async (
  action: string,
  context?: Record<string, any>
): Promise<ChatActionResult> => {
  const response = await apiClient.post('/api/v1/chat/action', {
    action,
    context,
  });
  return response.data;
};

/**
 * Get chat usage statistics
 */
export const getChatStats = async (): Promise<any> => {
  const response = await apiClient.get('/api/v1/chat/stats');
  return response.data;
};

/**
 * Create task via chat
 */
export const createTaskViaChat = async (params: {
  email_id?: string;
  description: string;
  context?: Record<string, any>;
}): Promise<any> => {
  const response = await apiClient.post('/api/v1/tasks/create', params);
  return response.data;
};

/**
 * Get example chat queries
 */
export const getChatExamples = async (): Promise<string[]> => {
  const response = await apiClient.get('/api/v1/chat/examples');
  return response.data.examples;
};

export default {
  summarizeEmail,
  conversational Search,
  organizeEmails,
  executeChatAction,
  getChatStats,
  createTaskViaChat,
  getChatExamples,
};
