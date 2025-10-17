import apiClient from './api';

export interface EmailAccount {
  account_id: string;
  email_address: string;
  display_name: string;
  account_type: string;
  sync_status: string;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  next_sync_at: string | null;
  total_emails_synced: number;
  embedding_model: string | null;
  last_error: string | null;
  sync_configuration?: {
    sync_days_back: number | null;
    max_emails_limit: number | null;
    folders_to_sync: string[];
    sync_attachments: boolean;
    include_spam: boolean;
    include_trash: boolean;
  };
}

export interface Email {
  id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  body_text: string;
  body_html: string;
  sent_at: string;
  received_at: string;
  is_read: boolean;
  is_important: boolean;
  has_attachments: boolean;
  category?: string;
  importance_score?: number;
  thread_id?: string;
}

export interface Task {
  id: string;
  email_id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed';
  priority: 'low' | 'medium' | 'high';
  due_date: string | null;
  estimated_time: string | null;
  sender_email: string;
  sender_name: string;
  email_subject: string;
  importance_score: number;
  suggested_actions: string[];
  created_at: string;
  completed_at: string | null;
}

export interface DashboardMetrics {
  total_emails: number;
  unread_emails: number;
  pending_tasks: number;
  high_priority_tasks: number;
  emails_today: number;
  tasks_completed_today: number;
  avg_response_time: number;
  sync_status: {
    active_accounts: number;
    last_sync: string | null;
    next_sync: string | null;
  };
}

export interface RecentActivity {
  id: string;
  type: 'email' | 'task' | 'chat' | 'sync' | 'system';
  title: string;
  description: string;
  timestamp: string;
  status?: 'success' | 'error' | 'pending' | 'info';
  metadata?: any;
}

export interface AIInsight {
  id: string;
  type: 'pattern' | 'suggestion' | 'alert' | 'summary';
  title: string;
  description: string;
  confidence: number;
  created_at: string;
  metadata?: any;
}

// Email Account Management
export const getEmailAccounts = async (): Promise<EmailAccount[]> => {
  const response = await apiClient.get('/api/v1/email-sync/accounts');
  return response.data.accounts;
};

export const getEmailAccount = async (accountId: string): Promise<EmailAccount> => {
  const response = await apiClient.get(`/api/v1/email-sync/accounts/${accountId}`);
  return response.data;
};

export const createEmailAccount = async (accountData: any): Promise<EmailAccount> => {
  const response = await apiClient.post('/api/v1/email-sync/accounts', accountData);
  return response.data;
};

export const updateEmailAccount = async (accountId: string, data: any): Promise<EmailAccount> => {
  const response = await apiClient.put(`/api/v1/email-sync/accounts/${accountId}`, data);
  return response.data;
};

export const deleteEmailAccount = async (accountId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/email-sync/accounts/${accountId}`);
};

// Email Operations
export const getEmails = async (params?: any): Promise<Email[]> => {
  const response = await apiClient.get('/api/v1/email-sync/emails', { params });
  return response.data.emails;
};

export const getEmail = async (emailId: string): Promise<Email> => {
  const response = await apiClient.get(`/api/v1/email-sync/emails/${emailId}`);
  return response.data;
};

export const updateEmail = async (emailId: string, data: any): Promise<Email> => {
  const response = await apiClient.patch(`/api/v1/email-sync/emails/${emailId}`, data);
  return response.data;
};

export const deleteEmail = async (emailId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/email-sync/emails/${emailId}`);
};

export const bulkUpdateEmails = async (emailIds: string[], data: any): Promise<void> => {
  await apiClient.post('/api/v1/email-sync/emails/bulk-update', {
    email_ids: emailIds,
    ...data,
  });
};

// Email Sync - V2 UID-based sync (no more incremental/full distinction)
export const syncEmails = async (accountIds?: string[], forceFullSync = false): Promise<any> => {
  const response = await apiClient.post('/api/v1/email-sync/v2/sync', {
    account_ids: accountIds,
    force_full_sync: forceFullSync,
  });
  return response.data;
};

export const getSyncStatus = async (): Promise<any> => {
  const response = await apiClient.get('/api/v1/email-sync/status');
  return response.data;
};

// Semantic Search
export const semanticSearch = async (query: string, accountId?: string, limit = 50): Promise<Email[]> => {
  const params: any = { query, limit };
  if (accountId) {
    params.account_id = accountId;
  }
  const response = await apiClient.get('/api/v1/email-sync/search', { params });
  return response.data.results;
};

// Task Management
export const getTasks = async (params?: any): Promise<Task[]> => {
  const response = await apiClient.get('/api/v1/email-sync/tasks', { params });
  return response.data.tasks;
};

export const getTask = async (taskId: string): Promise<Task> => {
  const response = await apiClient.get(`/api/v1/email-sync/tasks/${taskId}`);
  return response.data;
};

export const createTask = async (emailId: string, taskData: any): Promise<Task> => {
  const response = await apiClient.post(`/api/v1/email-sync/emails/${emailId}/tasks`, taskData);
  return response.data;
};

export const updateTask = async (taskId: string, data: any): Promise<Task> => {
  const response = await apiClient.patch(`/api/v1/email-sync/tasks/${taskId}`, data);
  return response.data;
};

export const deleteTask = async (taskId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/email-sync/tasks/${taskId}`);
};

export const bulkUpdateTasks = async (taskIds: string[], data: any): Promise<void> => {
  await apiClient.post('/api/v1/email-sync/tasks/bulk-update', {
    task_ids: taskIds,
    ...data,
  });
};

// Dashboard & Analytics
export const getDashboardMetrics = async (): Promise<DashboardMetrics> => {
  const response = await apiClient.get('/api/v1/email-sync/dashboard');
  return response.data;
};

export const getRecentActivity = async (limit = 20): Promise<RecentActivity[]> => {
  const response = await apiClient.get('/api/v1/email-sync/activity', {
    params: { limit },
  });
  return response.data.activities;
};

export const getAIInsights = async (accountId?: string): Promise<AIInsight[]> => {
  const params = accountId ? { account_id: accountId } : {};
  const response = await apiClient.get('/api/v1/email-sync/insights', { params });
  return response.data.insights;
};

// Embedding Management
export const getEmbeddingStats = async (accountId?: string): Promise<any> => {
  const params = accountId ? { account_id: accountId } : {};
  const response = await apiClient.get('/api/v1/email-sync/embeddings/stats', { params });
  return response.data;
};

export const regenerateEmbeddings = async (params: {
  accountId?: string;
  sourceModel?: string;
  emailIds?: string[];
  embeddingTypes?: string[];
  deleteExisting?: boolean;
}): Promise<any> => {
  const requestData: any = {};

  if (params.accountId) {
    requestData.account_id = params.accountId;
  }
  if (params.sourceModel) {
    requestData.source_model = params.sourceModel;
  }
  if (params.emailIds) {
    requestData.email_ids = params.emailIds;
  }
  if (params.embeddingTypes) {
    requestData.embedding_types = params.embeddingTypes;
  }
  if (params.deleteExisting !== undefined) {
    requestData.delete_existing = params.deleteExisting;
  }

  const response = await apiClient.post('/api/v1/email-sync/embeddings/regenerate', requestData);
  return response.data;
};

export const getAvailableModels = async (): Promise<string[]> => {
  const response = await apiClient.get('/api/v1/email-sync/embeddings/models');
  return response.data.models;
};

// Email Thread Management
export const getEmailThread = async (threadId: string): Promise<Email[]> => {
  const response = await apiClient.get(`/api/v1/email-sync/threads/${threadId}`);
  return response.data.emails;
};

// Email Categories
export const getEmailCategories = async (accountId?: string): Promise<string[]> => {
  const params = accountId ? { account_id: accountId } : {};
  const response = await apiClient.get('/api/v1/email-sync/categories', { params });
  return response.data.categories;
};

// Email Analytics
export const getEmailAnalytics = async (params?: {
  accountId?: string;
  startDate?: string;
  endDate?: string;
  groupBy?: 'day' | 'week' | 'month';
}): Promise<any> => {
  const response = await apiClient.get('/api/v1/email-sync/analytics', { params });
  return response.data;
};

export default {
  // Account management
  getEmailAccounts,
  getEmailAccount,
  createEmailAccount,
  updateEmailAccount,
  deleteEmailAccount,

  // Email operations
  getEmails,
  getEmail,
  updateEmail,
  deleteEmail,
  bulkUpdateEmails,

  // Sync operations
  syncEmails,
  getSyncStatus,

  // Search
  semanticSearch,

  // Tasks
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  bulkUpdateTasks,

  // Dashboard
  getDashboardMetrics,
  getRecentActivity,
  getAIInsights,

  // Embeddings
  getEmbeddingStats,
  regenerateEmbeddings,
  getAvailableModels,

  // Threads
  getEmailThread,

  // Categories
  getEmailCategories,

  // Analytics
  getEmailAnalytics,
};
