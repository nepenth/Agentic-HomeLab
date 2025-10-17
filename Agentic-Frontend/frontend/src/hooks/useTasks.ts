import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RootState } from '../store';
import {
  setTasks,
  setSelectedTask,
  setFilters,
  setGroupBy,
  setSort,
  setLoading,
  setError,
  completeTask as completeTaskAction,
  dismissTask as dismissTaskAction,
} from '../store/taskSlice';
import apiClient from '../services/api';

export const useTasks = () => {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  const {
    tasks,
    selectedTask,
    filters,
    groupBy,
    sort,
    loading,
    error,
  } = useSelector((state: RootState) => state.task);

  // Fetch tasks with filters
  const { data: tasksData, isLoading: tasksLoading, refetch: refetchTasks } = useQuery({
    queryKey: ['tasks', filters, sort],
    queryFn: async () => {
      const params: any = {
        sort_by: sort.field,
        sort_order: sort.direction,
      };

      if (filters.status.length > 0) {
        params.status = filters.status.join(',');
      }

      if (filters.priority.length > 0) {
        params.priority = filters.priority.join(',');
      }

      if (filters.search) {
        params.search = filters.search;
      }

      const response = await apiClient.get('/api/v1/email-sync/tasks', { params });
      return response.data.tasks;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: false, // Temporarily disabled until backend endpoint is implemented
  });

  // Update Redux when tasks data changes
  React.useEffect(() => {
    if (tasksData) {
      dispatch(setTasks(tasksData));
    }
  }, [tasksData, dispatch]);

  // Create task from email mutation
  const createTaskMutation = useMutation({
    mutationFn: async ({ emailId, taskData }: { emailId: string; taskData: any }) => {
      const response = await apiClient.post(`/api/v1/email-sync/emails/${emailId}/tasks`, taskData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to create task'));
    },
  });

  // Update task mutation
  const updateTaskMutation = useMutation({
    mutationFn: async ({ taskId, data }: { taskId: string; data: any }) => {
      const response = await apiClient.patch(`/api/v1/email-sync/tasks/${taskId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to update task'));
    },
  });

  // Complete task mutation
  const completeTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      dispatch(completeTaskAction(taskId));
      const response = await apiClient.patch(`/api/v1/email-sync/tasks/${taskId}`, {
        status: 'completed',
        completed_at: new Date().toISOString(),
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to complete task'));
      queryClient.invalidateQueries({ queryKey: ['tasks'] }); // Revert optimistic update
    },
  });

  // Dismiss task mutation
  const dismissTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      dispatch(dismissTaskAction(taskId));
      const response = await apiClient.patch(`/api/v1/email-sync/tasks/${taskId}`, {
        status: 'dismissed',
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to dismiss task'));
      queryClient.invalidateQueries({ queryKey: ['tasks'] }); // Revert optimistic update
    },
  });

  // Delete task mutation
  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      await apiClient.delete(`/api/v1/email-sync/tasks/${taskId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to delete task'));
    },
  });

  // Bulk complete tasks mutation
  const bulkCompleteMutation = useMutation({
    mutationFn: async (taskIds: string[]) => {
      const response = await apiClient.post('/api/v1/email-sync/tasks/bulk-update', {
        task_ids: taskIds,
        status: 'completed',
        completed_at: new Date().toISOString(),
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to complete tasks'));
    },
  });

  // Bulk dismiss tasks mutation
  const bulkDismissMutation = useMutation({
    mutationFn: async (taskIds: string[]) => {
      const response = await apiClient.post('/api/v1/email-sync/tasks/bulk-update', {
        task_ids: taskIds,
        status: 'dismissed',
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to dismiss tasks'));
    },
  });

  // Group tasks by specified field
  const groupedTasks = () => {
    if (groupBy === 'none') {
      return { all: tasks };
    }

    const grouped: Record<string, any[]> = {};

    tasks.forEach((task) => {
      let key: string;

      if (groupBy === 'priority') {
        key = task.priority;
      } else if (groupBy === 'status') {
        key = task.status;
      } else if (groupBy === 'due_date') {
        if (!task.due_date) {
          key = 'No due date';
        } else {
          const dueDate = new Date(task.due_date);
          const today = new Date();
          const tomorrow = new Date(today);
          tomorrow.setDate(tomorrow.getDate() + 1);

          if (dueDate < today) {
            key = 'Overdue';
          } else if (dueDate.toDateString() === today.toDateString()) {
            key = 'Today';
          } else if (dueDate.toDateString() === tomorrow.toDateString()) {
            key = 'Tomorrow';
          } else if (dueDate < new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000)) {
            key = 'This week';
          } else {
            key = 'Later';
          }
        }
      } else {
        key = 'all';
      }

      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(task);
    });

    return grouped;
  };

  // Filter tasks
  const filteredTasks = tasks.filter((task) => {
    if (filters.status.length > 0 && !filters.status.includes(task.status)) {
      return false;
    }

    if (filters.priority.length > 0 && !filters.priority.includes(task.priority)) {
      return false;
    }

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        task.title.toLowerCase().includes(searchLower) ||
        task.description.toLowerCase().includes(searchLower) ||
        task.sender_email.toLowerCase().includes(searchLower) ||
        task.email_subject.toLowerCase().includes(searchLower)
      );
    }

    return true;
  });

  return {
    // State
    tasks: filteredTasks,
    allTasks: tasks,
    selectedTask,
    filters,
    groupBy,
    sort,
    loading: loading || tasksLoading,
    error,
    groupedTasks: groupedTasks(),

    // Actions
    setSelectedTask: (task: any) => dispatch(setSelectedTask(task)),
    setFilters: (newFilters: any) => dispatch(setFilters(newFilters)),
    setGroupBy: (newGroupBy: any) => dispatch(setGroupBy(newGroupBy)),
    setSort: (newSort: any) => dispatch(setSort(newSort)),

    // Mutations
    createTask: createTaskMutation.mutate,
    updateTask: updateTaskMutation.mutate,
    completeTask: completeTaskMutation.mutate,
    dismissTask: dismissTaskMutation.mutate,
    deleteTask: deleteTaskMutation.mutate,
    bulkComplete: bulkCompleteMutation.mutate,
    bulkDismiss: bulkDismissMutation.mutate,
    refetchTasks,

    // Loading states
    isCreating: createTaskMutation.isPending,
    isUpdating: updateTaskMutation.isPending,
    isCompleting: completeTaskMutation.isPending,
    isDismissing: dismissTaskMutation.isPending,
  };
};
