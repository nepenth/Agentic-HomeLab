import apiClient from './api';

/**
 * Email Workflow API
 *
 * Provides access to email workflow management including starting workflows,
 * tracking status, viewing history, and managing workflow configurations.
 */

export interface WorkflowConfig {
  mailbox_config: {
    server: string;
    port: number;
    username: string;
    password: string;
    use_ssl?: boolean;
  };
  processing_options?: Record<string, any>;
}

export interface Workflow {
  workflow_id: string;
  status: string;
  message: string;
  created_at: string;
}

export interface WorkflowStatus {
  workflow_id: string;
  status: string;
  emails_processed: number;
  tasks_created: number;
  started_at: string;
  completed_at: string | null;
  processing_time_ms: number | null;
}

export interface WorkflowLog {
  id: string;
  workflow_id: string | null;
  task_id: string | null;
  level: string;
  message: string;
  context: Record<string, any>;
  timestamp: string;
  workflow_phase: string | null;
  email_count: number | null;
}

export interface WorkflowSummary {
  workflows: {
    total: number;
    active: number;
    completed: number;
    failed: number;
    cancelled: number;
    stale: number;
  };
  tasks: {
    total: number;
    pending: number;
    completed: number;
    failed: number;
    running: number;
  };
  needs_cleanup: boolean;
}

export interface WorkflowDashboardStats {
  total_workflows: number;
  active_workflows: number;
  completed_workflows: number;
  total_emails_processed: number;
  total_tasks_created: number;
  pending_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  success_rate: number;
  avg_processing_time: number;
}

export interface WorkflowAnalytics {
  workflow_id: string;
  emails_processed: number;
  tasks_created: number;
  avg_importance_score: number;
  top_categories: Array<{ category: string; count: number }>;
  trend: Record<string, any>;
  alerts: Array<Record<string, any>>;
}

export interface WorkflowSettings {
  id: string;
  user_id: string;
  settings_name: string;
  description: string | null;
  max_emails_per_workflow: number;
  importance_threshold: number;
  spam_threshold: number;
  default_task_priority: string;
  analysis_timeout_seconds: number;
  task_conversion_timeout_seconds: number;
  ollama_request_timeout_seconds: number;
  max_retries: number;
  retry_delay_seconds: number;
  create_tasks_automatically: boolean;
  schedule_followups: boolean;
  process_attachments: boolean;
  is_default: boolean;
  is_active: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowSettingsRequest {
  settings_name: string;
  description?: string;
  max_emails_per_workflow?: number;
  importance_threshold?: number;
  spam_threshold?: number;
  default_task_priority?: string;
  analysis_timeout_seconds?: number;
  task_conversion_timeout_seconds?: number;
  ollama_request_timeout_seconds?: number;
  max_retries?: number;
  retry_delay_seconds?: number;
  create_tasks_automatically?: boolean;
  schedule_followups?: boolean;
  process_attachments?: boolean;
}

// Workflow Operations

/**
 * Start a new email workflow
 */
export const startWorkflow = async (config: WorkflowConfig): Promise<Workflow> => {
  const response = await apiClient.post('/workflows/start', config);
  return response.data;
};

/**
 * Get workflow status by ID
 */
export const getWorkflowStatus = async (workflowId: string): Promise<WorkflowStatus> => {
  const response = await apiClient.get(`/workflows/${workflowId}/status`);
  return response.data;
};

/**
 * Get workflow history
 */
export const getWorkflowHistory = async (limit = 50, offset = 0): Promise<WorkflowStatus[]> => {
  const response = await apiClient.get('/workflows/history', {
    params: { limit, offset },
  });
  return response.data;
};

/**
 * Cancel a running workflow
 */
export const cancelWorkflow = async (workflowId: string): Promise<{ message: string }> => {
  const response = await apiClient.post(`/workflows/${workflowId}/cancel`);
  return response.data;
};

/**
 * Get workflow logs
 */
export const getWorkflowLogs = async (workflowId: string): Promise<WorkflowLog[]> => {
  const response = await apiClient.get(`/workflows/${workflowId}/logs`);
  return response.data;
};

/**
 * Get workflow summary
 */
export const getWorkflowSummary = async (): Promise<WorkflowSummary> => {
  const response = await apiClient.get('/workflows/summary');
  return response.data;
};

/**
 * Cleanup stale workflows
 */
export const cleanupStaleWorkflows = async (): Promise<{ message: string; cleaned: number }> => {
  const response = await apiClient.post('/workflows/cleanup-stale');
  return response.data;
};

/**
 * Clear all workflows
 */
export const clearAllWorkflows = async (): Promise<{ message: string }> => {
  const response = await apiClient.delete('/workflows/clear-all');
  return response.data;
};

// Dashboard & Analytics

/**
 * Get workflow dashboard statistics
 */
export const getWorkflowDashboardStats = async (): Promise<WorkflowDashboardStats> => {
  const response = await apiClient.get('/dashboard/stats');
  return response.data;
};

/**
 * Get workflow analytics overview
 */
export const getWorkflowAnalytics = async (): Promise<WorkflowAnalytics> => {
  const response = await apiClient.get('/analytics/overview');
  return response.data;
};

/**
 * Get analytics for specific workflow
 */
export const getWorkflowAnalyticsById = async (workflowId: string): Promise<WorkflowAnalytics> => {
  const response = await apiClient.get(`/workflows/${workflowId}/analytics/overview`);
  return response.data;
};

// Workflow Settings

/**
 * Create new workflow settings
 */
export const createWorkflowSettings = async (settings: WorkflowSettingsRequest): Promise<WorkflowSettings> => {
  const response = await apiClient.post('/workflow-settings', settings);
  return response.data;
};

/**
 * Get all workflow settings
 */
export const getWorkflowSettings = async (): Promise<WorkflowSettings[]> => {
  const response = await apiClient.get('/workflow-settings');
  return response.data;
};

/**
 * Get default workflow settings
 */
export const getDefaultWorkflowSettings = async (): Promise<WorkflowSettings> => {
  const response = await apiClient.get('/workflow-settings/default');
  return response.data;
};

/**
 * Update default workflow settings
 */
export const updateDefaultWorkflowSettings = async (settingsId: string): Promise<WorkflowSettings> => {
  const response = await apiClient.put('/workflow-settings/default', { settings_id: settingsId });
  return response.data;
};

/**
 * Get specific workflow settings by ID
 */
export const getWorkflowSettingsById = async (settingsId: string): Promise<WorkflowSettings> => {
  const response = await apiClient.get(`/workflow-settings/${settingsId}`);
  return response.data;
};

/**
 * Update workflow settings
 */
export const updateWorkflowSettings = async (
  settingsId: string,
  updates: Partial<WorkflowSettingsRequest>
): Promise<WorkflowSettings> => {
  const response = await apiClient.put(`/workflow-settings/${settingsId}`, updates);
  return response.data;
};

/**
 * Delete workflow settings
 */
export const deleteWorkflowSettings = async (settingsId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/workflow-settings/${settingsId}`);
  return response.data;
};

export default {
  // Workflow operations
  startWorkflow,
  getWorkflowStatus,
  getWorkflowHistory,
  cancelWorkflow,
  getWorkflowLogs,
  getWorkflowSummary,
  cleanupStaleWorkflows,
  clearAllWorkflows,

  // Dashboard & Analytics
  getWorkflowDashboardStats,
  getWorkflowAnalytics,
  getWorkflowAnalyticsById,

  // Workflow settings
  createWorkflowSettings,
  getWorkflowSettings,
  getDefaultWorkflowSettings,
  updateDefaultWorkflowSettings,
  getWorkflowSettingsById,
  updateWorkflowSettings,
  deleteWorkflowSettings,
};
