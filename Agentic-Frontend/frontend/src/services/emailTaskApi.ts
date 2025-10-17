import apiClient from './api';

/**
 * Email Task API - Advanced Operations
 *
 * Provides advanced task management features including
 * email content linking, completion tracking, and priority adjustment.
 */

export interface TaskEmailContent {
  email_id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  body_text: string;
  body_html: string;
  sent_at: string;
  has_attachments: boolean;
  attachments: Array<{
    filename: string;
    size: number;
    content_type: string;
  }>;
}

/**
 * Get email content associated with a task
 */
export const getTaskEmailContent = async (taskId: string): Promise<TaskEmailContent> => {
  const response = await apiClient.get(`/tasks/${taskId}/email-content`);
  return response.data;
};

/**
 * Mark a task as complete
 */
export const completeTask = async (taskId: string, completionNotes?: string): Promise<any> => {
  const response = await apiClient.post(`/tasks/${taskId}/complete`, {
    completion_notes: completionNotes,
  });
  return response.data;
};

/**
 * Mark a task as not important (demote priority)
 */
export const markTaskNotImportant = async (taskId: string, reason?: string): Promise<any> => {
  const response = await apiClient.post(`/tasks/${taskId}/mark-not-important`, {
    reason,
  });
  return response.data;
};

export default {
  getTaskEmailContent,
  completeTask,
  markTaskNotImportant,
};
