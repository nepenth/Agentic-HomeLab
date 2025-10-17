import { useDispatch, useSelector } from 'react-redux';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RootState } from '../store';
import {
  setCurrentSession,
  setSessions,
  setMessages,
  addMessage,
  updateLastMessage,
  clearMessages,
  setSelectedModel,
  setIsStreaming,
  setStreamingEnabled,
  setContext,
  clearContext,
  setLoading,
  setError,
  addSession,
  removeSession,
} from '../store/assistantSlice';
import apiClient from '../services/api';
import { messageQueueService } from '../services/messageQueue';

interface SendMessageParams {
  message: string;
  sessionId?: string;
  context?: {
    emailId?: string;
    taskId?: string;
  };
}

export const useAssistant = () => {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  const {
    currentSession,
    sessions,
    messages,
    selectedModel,
    isStreaming,
    streamingEnabled,
    quickActions,
    context,
    loading,
    error,
  } = useSelector((state: RootState) => state.assistant);

  // Fetch chat sessions
  const { data: sessionsData, isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/email-assistant/sessions');
      return response.data.sessions;
    },
    onSuccess: (data) => {
      dispatch(setSessions(data));
    },
  });

  // Fetch messages for current session
  const { data: messagesData, isLoading: messagesLoading } = useQuery({
    queryKey: ['chat-messages', currentSession?.id],
    queryFn: async () => {
      if (!currentSession) return [];
      const response = await apiClient.get(`/api/v1/email-assistant/sessions/${currentSession.id}/messages`);
      return response.data.messages;
    },
    onSuccess: (data) => {
      dispatch(setMessages(data));
    },
    enabled: !!currentSession,
  });

  // Create new session mutation
  const createSessionMutation = useMutation({
    mutationFn: async ({ title, modelName }: { title?: string; modelName?: string }) => {
      const response = await apiClient.post('/api/v1/email-assistant/sessions', {
        title: title || 'New Chat',
        model_name: modelName || selectedModel,
      });
      return response.data;
    },
    onSuccess: (data) => {
      dispatch(addSession(data));
      dispatch(setCurrentSession(data));
      dispatch(clearMessages());
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to create session'));
    },
  });

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      await apiClient.delete(`/api/v1/email-assistant/sessions/${sessionId}`);
    },
    onSuccess: (_, sessionId) => {
      dispatch(removeSession(sessionId));
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to delete session'));
    },
  });

  // Send message with streaming support
  const sendMessageMutation = useMutation({
    mutationFn: async ({ message, sessionId, context: msgContext }: SendMessageParams) => {
      const useSessionId = sessionId || currentSession?.id;

      // Check if offline and queue message
      if (!navigator.onLine) {
        const queuedId = messageQueueService.enqueue(message, useSessionId, msgContext);
        dispatch(setError('You are offline. Message will be sent when connection is restored.'));

        // Add to UI with pending status
        const userMessage = {
          id: queuedId,
          role: 'user' as const,
          content: message,
          timestamp: new Date().toISOString(),
          metadata: { queued: true, status: 'pending' },
        };
        dispatch(addMessage(userMessage));

        return { queued: true, id: queuedId };
      }

      // Add user message optimistically
      const userMessage = {
        id: `temp-${Date.now()}`,
        role: 'user' as const,
        content: message,
        timestamp: new Date().toISOString(),
      };
      dispatch(addMessage(userMessage));

      // Add placeholder assistant message
      const assistantMessage = {
        id: `temp-assistant-${Date.now()}`,
        role: 'assistant' as const,
        content: '',
        timestamp: new Date().toISOString(),
      };
      dispatch(addMessage(assistantMessage));

      if (streamingEnabled) {
        // Use SSE for streaming responses
        dispatch(setIsStreaming(true));

        return new Promise((resolve, reject) => {
          // Get timeout settings from localStorage
          const savedSettings = localStorage.getItem('assistantSettings');
          const settings = savedSettings ? JSON.parse(savedSettings) : {
            connectionTimeout: 30000,
            responseTimeout: 120000,
          };

          let connectionTimeoutId: NodeJS.Timeout;
          let responseTimeoutId: NodeJS.Timeout;
          let accumulatedContent = '';
          let metadata: any = {};

          // Create EventSource for SSE
          const url = new URL(`${import.meta.env.VITE_API_BASE_URL}/api/v1/email/chat`);

          // Build query parameters for GET-style SSE or use POST with fetch
          // Since backend expects POST, we'll use fetch with streaming
          const controller = new AbortController();

          connectionTimeoutId = setTimeout(() => {
            controller.abort();
            dispatch(setIsStreaming(false));
            dispatch(setError('Connection timeout'));
            reject(new Error('Connection timeout'));
          }, settings.connectionTimeout);

          // Get auth token for streaming request
          const authToken = localStorage.getItem('auth_token') ||
                           localStorage.getItem('access_token') ||
                           sessionStorage.getItem('access_token');

          const headers: HeadersInit = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          };

          if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
          }

          fetch(url.toString(), {
            method: 'POST',
            headers,
            body: JSON.stringify({
              message,
              session_id: useSessionId,
              model_name: selectedModel,
              stream: true,
              context: {
                email_id: msgContext?.emailId,
                task_id: msgContext?.taskId,
              },
              max_days_back: 365,
            }),
            signal: controller.signal,
          })
          .then(response => {
            clearTimeout(connectionTimeoutId);

            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Set response timeout
            responseTimeoutId = setTimeout(() => {
              controller.abort();
              dispatch(setIsStreaming(false));
              dispatch(setError('Response timeout'));
              reject(new Error('Response timeout'));
            }, settings.responseTimeout);

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            function readStream(): Promise<void> {
              return reader!.read().then(({ done, value }) => {
                if (done) {
                  clearTimeout(responseTimeoutId);
                  dispatch(setIsStreaming(false));
                  resolve({ response_text: accumulatedContent, ...metadata });
                  return;
                }

                // Reset response timeout on each chunk
                clearTimeout(responseTimeoutId);
                responseTimeoutId = setTimeout(() => {
                  controller.abort();
                  dispatch(setIsStreaming(false));
                  dispatch(setError('Response timeout'));
                  reject(new Error('Response timeout'));
                }, settings.responseTimeout);

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    try {
                      const data = JSON.parse(line.slice(6));

                      if (data.type === 'response_chunk') {
                        accumulatedContent += data.text || '';
                        dispatch(updateLastMessage({ content: accumulatedContent }));
                      } else if (data.type === 'email_references') {
                        metadata.email_references = data.data;
                        dispatch(updateLastMessage({
                          content: accumulatedContent,
                          metadata: { ...metadata },
                        }));
                      } else if (data.type === 'thinking') {
                        metadata.thinking_content = data.data;
                        dispatch(updateLastMessage({
                          content: accumulatedContent,
                          metadata: { ...metadata },
                        }));
                      } else if (data.type === 'complete') {
                        metadata = { ...metadata, ...data.data };
                        dispatch(updateLastMessage({
                          content: accumulatedContent,
                          metadata: {
                            email_references: metadata.email_references,
                            task_suggestions: data.data.task_suggestions,
                            tasks_created: data.data.tasks_created,
                            thinking_content: metadata.thinking_content,
                            ...data.data.metadata,
                          },
                        }));
                      } else if (data.type === 'error') {
                        throw new Error(data.message || 'Stream error');
                      }
                    } catch (parseError) {
                      console.error('Failed to parse SSE data:', parseError);
                    }
                  }
                }

                return readStream();
              });
            }

            return readStream();
          })
          .catch(error => {
            clearTimeout(connectionTimeoutId);
            clearTimeout(responseTimeoutId);
            dispatch(setIsStreaming(false));
            dispatch(setError(error.message || 'Streaming failed'));
            reject(error);
          });
        });
      } else {
        // Non-streaming request using enhanced email chat
        const response = await apiClient.post(
          '/api/v1/email/chat',
          {
            message,
            session_id: useSessionId,
            model_name: selectedModel,
            stream: false,
            context: {
              email_id: msgContext?.emailId,
              task_id: msgContext?.taskId,
            },
            max_days_back: 365, // Search emails from last year
          }
        );

        // Update the last message with actual response
        dispatch(updateLastMessage({
          content: response.data.response_text,
          metadata: {
            email_references: response.data.email_references,
            task_suggestions: response.data.task_suggestions,
            tasks_created: response.data.tasks_created,
            thinking_content: response.data.thinking_content,
            ...response.data.metadata,
          },
        }));

        return response.data;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-messages', currentSession?.id] });
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to send message'));
      dispatch(setIsStreaming(false));
    },
  });

  // Semantic search with chat context
  const semanticSearchMutation = useMutation({
    mutationFn: async ({ query, limit = 10 }: { query: string; limit?: number }) => {
      const response = await apiClient.get('/api/v1/email-sync/search', {
        params: { query, limit },
      });
      return response.data.results;
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Search failed'));
    },
  });

  // Get quick actions for current context
  const { data: quickActionsData } = useQuery({
    queryKey: ['quick-actions', context.currentEmail, context.currentTask],
    queryFn: async () => {
      const params: any = {};

      if (context.currentEmail) {
        params.email_id = context.currentEmail;
      }

      if (context.currentTask) {
        params.task_id = context.currentTask;
      }

      const response = await apiClient.get('/api/v1/email-assistant/quick-actions', { params });
      return response.data.actions;
    },
    enabled: !!(context.currentEmail || context.currentTask),
  });

  // Execute quick action
  const executeQuickActionMutation = useMutation({
    mutationFn: async ({ action, emailId, taskId }: { action: string; emailId?: string; taskId?: string }) => {
      const response = await apiClient.post('/api/v1/email-assistant/execute-action', {
        action,
        email_id: emailId,
        task_id: taskId,
      });
      return response.data;
    },
    onSuccess: (data) => {
      // Add the action result as a message
      dispatch(addMessage({
        id: `action-${Date.now()}`,
        role: 'assistant',
        content: data.result,
        timestamp: new Date().toISOString(),
        metadata: {
          actions_performed: [data.action],
        },
      }));
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to execute action'));
    },
  });

  // Switch to a different session
  const switchSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      dispatch(setCurrentSession(session));
    }
  };

  // Update model selection
  const updateModel = (modelName: string) => {
    dispatch(setSelectedModel(modelName));
  };

  // Toggle streaming
  const toggleStreaming = () => {
    dispatch(setStreamingEnabled(!streamingEnabled));
  };

  // Update context
  const updateContext = (newContext: any) => {
    dispatch(setContext(newContext));
  };

  return {
    // State
    currentSession,
    sessions,
    messages,
    selectedModel,
    isStreaming,
    streamingEnabled,
    quickActions: quickActionsData || [],
    context,
    loading: loading || sessionsLoading || messagesLoading,
    error,

    // Actions
    switchSession,
    updateModel,
    toggleStreaming,
    updateContext,
    clearContext: () => dispatch(clearContext()),

    // Mutations
    createSession: createSessionMutation.mutate,
    deleteSession: deleteSessionMutation.mutate,
    sendMessage: sendMessageMutation.mutate,
    semanticSearch: semanticSearchMutation.mutate,
    executeQuickAction: executeQuickActionMutation.mutate,

    // Loading states
    isCreatingSession: createSessionMutation.isPending,
    isSendingMessage: sendMessageMutation.isPending,
    isExecutingAction: executeQuickActionMutation.isPending,
  };
};
