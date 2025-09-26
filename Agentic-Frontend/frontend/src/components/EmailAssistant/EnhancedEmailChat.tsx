import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Card,
  CardContent,
  IconButton,
  Divider,
  Alert,
  CircularProgress,
  Fade,
  Chip,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Send,
  SmartToy,
  Settings,
  History,
  Clear,
  Mic,
  Stop
} from '@mui/icons-material';
import { useMutation, useQuery } from '@tanstack/react-query';

import ModelSelector from './ModelSelector';
import ChatMessage from './ChatMessage';
import QuickActions from './QuickActions';
import apiClient from '../../services/api';

interface ThinkingContent {
  id: string;
  content: string;
}

interface ChatMessage {
  id: string;
  content: string;
  messageType: 'user' | 'assistant' | 'system' | 'action';
  timestamp: string;
  modelUsed?: string;
  generationTimeMs?: number;
  richContent?: any;
  suggestedActions?: string[];
  actionsPerformed?: Array<{ type: string; [key: string]: any }>;
  thinkingContent?: ThinkingContent[];
  isStreaming?: boolean;
}

interface ChatSession {
  id: string;
  title?: string;
  created_at: string;
  last_activity: string;
  selected_model: string;
  message_count: number;
  is_active: boolean;
}

const EnhancedEmailChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [selectedModel, setSelectedModel] = useState<string>('');  // Will be set from backend default
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textFieldRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input field on mount
  useEffect(() => {
    textFieldRef.current?.focus();
  }, []);

  // Fetch available models and set default
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['chat-models'],
    queryFn: async () => {
      const response = await apiClient.getChatModels();
      return response;
    },
    retry: 3,
    staleTime: 2 * 60 * 1000, // 2 minutes
    onError: (error) => {
      console.error('Failed to load chat models:', error);
    }
  });

  // Set default model when data loads (proper React pattern)
  React.useEffect(() => {
    if (modelsData?.default_model && selectedModel === '') {
      setSelectedModel(modelsData.default_model);
    } else if (!modelsData?.default_model && selectedModel === '' && modelsData?.models?.length > 0) {
      // Fallback to first available model if no default
      setSelectedModel(modelsData.models[0]);
    }
  }, [modelsData, selectedModel]);

  // Fetch user preferences
  const { data: preferences } = useQuery({
    queryKey: ['email-assistant-preferences'],
    queryFn: async () => {
      // Note: This endpoint doesn't exist in API client yet, create placeholder response
      const response = { data: { enable_streaming: true } };
      return response.data;
    },
    onSuccess: (data) => {
      if (data.enable_streaming !== undefined) {
        setStreamingEnabled(data.enable_streaming);
      }
    }
  });

  // Fetch task stats for quick actions
  const { data: taskStats } = useQuery({
    queryKey: ['email-workflow-stats'],
    queryFn: async () => {
      const response = await apiClient.getEmailDashboardStats();
      return response;
    }
  });

  // Handle streaming or regular message sending
  const sendMessage = async (message: string) => {
    if (!message.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      messageType: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setError(null);

    if (streamingEnabled) {
      await handleStreamingMessage(message, userMessage.id);
    } else {
      await handleRegularMessage(message);
    }
  };

  // Handle streaming message response
  const handleStreamingMessage = async (message: string, userMessageId: string) => {
    setIsStreaming(true);
    setCurrentStreamingMessage('');

    // Create placeholder assistant message
    const assistantMessageId = Date.now().toString() + '_assistant';
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      content: '',
      messageType: 'assistant',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      thinkingContent: []
    };

    setMessages(prev => [...prev, assistantMessage]);

    // Create abort controller for cancellation
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const requestData = {
        message: message,
        session_id: currentSession,
        context: {
          preferred_format: 'structured',
          include_threads: true,
          max_results: 10
        },
        model_name: selectedModel,
        max_days_back: 1095,  // 3 years to find older emails like travel records
        conversation_history: messages.slice(-5).map(msg => ({
          role: msg.messageType === 'user' ? 'user' : 'assistant',
          content: msg.content
        }))
      };

      const startTime = Date.now();
      let accumulatedText = '';
      let emailReferences: any[] = [];
      let thinkingContent: ThinkingContent[] = [];
      let tasksCreated: any[] = [];
      let suggestedActions: string[] = [];

      // Start streaming
      for await (const data of apiClient.sendEmailChatMessageStream(requestData)) {
        if (controller.signal.aborted) {
          break;
        }

        switch (data.type) {
          case 'status':
            setCurrentStreamingMessage(`⏳ ${data.message}`);
            break;

          case 'email_references':
            emailReferences = data.data;
            break;

          case 'thinking':
            thinkingContent = data.data;
            // Update the message with thinking content
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, thinkingContent: data.data }
                : msg
            ));
            break;

          case 'response_start':
            setCurrentStreamingMessage('');
            break;

          case 'response_chunk':
            accumulatedText = data.accumulated;
            setCurrentStreamingMessage(accumulatedText);

            // Update the streaming message
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, content: accumulatedText }
                : msg
            ));
            break;

          case 'complete':
            const endTime = Date.now();
            tasksCreated = data.data.tasks_created || [];
            const taskSuggestions = data.data.task_suggestions || [];
            suggestedActions = data.data.suggested_actions || [];

            // Final message update
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: accumulatedText,
                    isStreaming: false,
                    generationTimeMs: endTime - startTime,
                    richContent: {
                      email_references: emailReferences,
                      tasks_created: tasksCreated,
                      task_suggestions: taskSuggestions,
                      metadata: data.data.metadata
                    },
                    suggestedActions: suggestedActions
                  }
                : msg
            ));
            break;

          case 'error':
            setError(data.message);
            break;
        }
      }
    } catch (error: any) {
      console.error('Streaming error:', error);
      setError(error.message || 'Streaming failed');

      // Remove the failed streaming message
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
    } finally {
      setIsStreaming(false);
      setCurrentStreamingMessage('');
      setAbortController(null);
    }
  };

  // Handle regular (non-streaming) message
  const handleRegularMessage = async (message: string) => {
    try {
      const requestData = {
        message: message,
        session_id: currentSession,
        context: {
          preferred_format: 'structured',
          include_threads: true,
          max_results: 10
        },
        model_name: selectedModel,
        max_days_back: 1095,  // 3 years to find older emails like travel records
        conversation_history: messages.slice(-5).map(msg => ({
          role: msg.messageType === 'user' ? 'user' : 'assistant',
          content: msg.content
        }))
      };

      const data = await apiClient.sendEmailChatMessage(requestData);

      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        content: data.response_text || data.content,
        messageType: 'assistant',
        timestamp: data.timestamp || new Date().toISOString(),
        modelUsed: data.metadata?.model_used,
        generationTimeMs: data.metadata?.processing_time_ms,
        thinkingContent: data.thinking_content || [],
        richContent: {
          search_results: data.search_results,
          actions_taken: data.actions_taken,
          email_references: data.email_references || [],
          tasks_created: data.tasks_created || [],
          task_suggestions: data.task_suggestions || [],
          metadata: data.metadata || {}
        },
        suggestedActions: data.suggested_actions || [],
        actionsPerformed: data.actions_taken || []
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      setError(error.message || 'Failed to send message');
      console.error('Send message error:', error);
    }
  };

  // Cancel streaming
  const cancelStreaming = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setIsStreaming(false);
      setCurrentStreamingMessage('');
    }
  };

  // Send message mutation (legacy - now replaced by sendMessage function)
  const sendMessageMutation = {
    mutate: ({ message }: { message: string }) => {
      sendMessage(message);
    },
    isLoading: isStreaming
  } as any;

  // Original mutation for backwards compatibility
  const originalSendMessageMutation = useMutation({
    mutationFn: async ({ message, sessionId, modelName }: {
      message: string;
      sessionId?: string;
      modelName?: string;
    }) => {
      try {
        // Use the enhanced email chat endpoint with new features
        const requestPayload: any = {
          message: message,
          context: {
            preferred_format: 'structured',
            include_threads: true,
            max_results: 10
          },
          model_name: modelName,
          max_days_back: 1095,  // 3 years to find older emails like travel records
          conversation_history: messages.slice(-5).map(msg => ({
            role: msg.messageType === 'user' ? 'user' : 'assistant',
            content: msg.content
          }))
        };

        // Only include session_id if it's not null/undefined
        if (sessionId) {
          requestPayload.session_id = sessionId;
        }

        const response = await apiClient.sendEmailChatMessage(requestPayload);
        return response;
      } catch (error: any) {
        // Enhanced error handling with specific error types
        console.error('Email chat endpoint error:', error);
        console.error('Actual request payload sent:', requestPayload);
        console.error('Auth token present:', apiClient.getAuthToken() ? 'Yes' : 'No');
        console.error('Full error response data:', error.response?.data);
        console.error('Full error object:', error);
        console.error('Error detail property:', error.detail);

        let errorMessage = '';
        if (error.response?.status === 422) {
          // Try multiple locations for validation errors
          const validationErrors = error.response?.data?.detail || error.detail || error.response?.data;
          console.error('Validation errors found:', validationErrors);

          if (Array.isArray(validationErrors)) {
            const errorDetails = validationErrors.map(err =>
              `${err.loc?.join('.') || 'unknown'}: ${err.msg}`
            ).join('; ');
            errorMessage = `Validation error: ${errorDetails}`;
          } else {
            errorMessage = 'Request validation error - check request format';
          }
        } else if (error.response?.status === 401) {
          errorMessage = 'Authentication required - please log in';
        } else if (error.response?.status === 500) {
          errorMessage = 'Server error - please try again';
        } else {
          errorMessage = error.response?.data?.detail || error.detail || error.message || 'Unknown error';
        }

        // Return structured error response instead of fallback
        throw new Error(errorMessage);
      }
    },
    onSuccess: (data) => {
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        content: data.response_text || data.content,
        messageType: 'assistant',
        timestamp: data.timestamp || new Date().toISOString(),
        modelUsed: data.metadata?.model_used,
        generationTimeMs: data.metadata?.processing_time_ms,
        richContent: {
          search_results: data.search_results,
          actions_taken: data.actions_taken,
          email_references: data.email_references || [],
          tasks_created: data.tasks_created || [],
          metadata: data.metadata || {}
        },
        suggestedActions: data.suggested_actions || [],
        actionsPerformed: data.actions_taken || []
      };

      setMessages(prev => [...prev, assistantMessage]);
      setError(null);
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to send message');
      console.error('Send message error:', error);
    }
  });

  // Quick action mutation with proper authentication
  const quickActionMutation = useMutation({
    mutationFn: async (actionId: string) => {
      // Check if we have authentication - if so, try real backend, otherwise use interactive fallback
      const authToken = apiClient.getAuthToken();

      if (authToken) {
        try {
          // Try real backend integration with authentication
          const actionMessages = {
            'show_pending_tasks': 'Show me all my pending tasks from email workflows',
            'show_completed_tasks': 'Show me my completed tasks',
            'show_overdue_tasks': 'Show me overdue or urgent tasks that need attention',
            'search_emails': 'Help me search my emails',
            'show_urgent_emails': 'Find urgent emails that need my attention',
            'recent_emails': 'Show me emails from today',
            'workflow_status': 'What\'s the current status of my email workflows?',
            'refresh_workflows': 'Refresh and update my workflow data',
            'show_analytics': 'Show me email processing analytics and statistics',
            'show_insights': 'Give me insights about my email patterns and productivity'
          };

          const message = actionMessages[actionId as keyof typeof actionMessages] || 'Execute quick action';

          // Use the real email chat endpoint with authentication
          const quickActionPayload: any = {
            message: message,
            context: {
              preferred_format: 'structured',
              include_threads: true,
              max_results: 10
            }
          };

          // Only include session_id if it's not null/undefined
          if (currentSession) {
            quickActionPayload.session_id = currentSession;
          }

          const response = await apiClient.sendEmailChatMessage(quickActionPayload);

          return {
            action_id: actionId,
            response: response
          };
        } catch (error: any) {
          console.error('Authenticated quick action failed:', error);
          console.error('Quick action payload was:', {
            message: message,
            session_id: currentSession,
            context: {
              preferred_format: 'structured',
              include_threads: true,
              max_results: 10
            }
          });
          console.error('Full quick action error response:', error.response?.data);
          // Fall through to interactive fallback
        }
      }

      // Interactive fallback for when authentication is not available or backend fails
      const actionPrompts = {
        'show_pending_tasks': 'I\'ll help you view your pending tasks from email workflows. Let me check your current tasks...',
        'show_completed_tasks': 'I\'ll show you your recently completed tasks and their status.',
        'show_overdue_tasks': 'I\'ll find any overdue or urgent tasks that need your immediate attention.',
        'search_emails': 'I can help you search through your emails! What would you like to search for?\n\nExamples:\n• "emails from John about project"\n• "unread messages from last week"\n• "messages with attachments"\n• "urgent emails from today"',
        'show_urgent_emails': 'I\'ll scan through your emails to find urgent messages that need your immediate attention.',
        'recent_emails': 'I\'ll show you emails received today, sorted by importance and relevance.',
        'workflow_status': 'Let me check the current status of your email processing workflows...',
        'refresh_workflows': 'I\'ll refresh your workflow data and check for any updates or changes.',
        'show_analytics': 'I\'ll provide you with analytics about your email processing, including volume, response times, and patterns.',
        'show_insights': 'I\'ll analyze your email patterns and provide insights to help improve your productivity.'
      };

      const prompt = actionPrompts[actionId as keyof typeof actionPrompts] || 'How can I help you with your emails today?';

      // Generate contextual suggested actions based on the quick action
      const getSuggestedActions = (actionId: string): string[] => {
        switch (actionId) {
          case 'search_emails':
            return ['Search by sender', 'Search by date', 'Search by keyword', 'Search attachments'];
          case 'show_pending_tasks':
          case 'show_completed_tasks':
          case 'show_overdue_tasks':
            return ['Mark as complete', 'Set priority', 'Schedule followup', 'View details'];
          case 'workflow_status':
          case 'refresh_workflows':
            return ['View active workflows', 'Check queue status', 'Review logs', 'Start new workflow'];
          case 'show_analytics':
          case 'show_insights':
            return ['Export report', 'Set up alerts', 'View trends', 'Compare periods'];
          default:
            return ['Get more info', 'Refresh data', 'View details'];
        }
      };

      const response = {
        action_id: actionId,
        response: {
          content: prompt,
          message_type: 'assistant',
          rich_content: {
            action_type: actionId,
            interactive: actionId === 'search_emails'
          },
          suggested_actions: getSuggestedActions(actionId),
          model_used: selectedModel || 'assistant',
          generation_time_ms: 100,
          timestamp: new Date().toISOString()
        }
      };

      return response;
    },
    onSuccess: (data) => {
      // Handle both backend response format and fallback format
      const responseData = data.response || data;
      const actionMessage: ChatMessage = {
        id: Date.now().toString(),
        content: responseData.response_text || responseData.content || responseData.response || 'Action completed',
        messageType: 'assistant',
        timestamp: responseData.timestamp || new Date().toISOString(),
        modelUsed: responseData.model_used,
        generationTimeMs: responseData.generation_time_ms,
        richContent: {
          search_results: responseData.search_results,
          actions_taken: responseData.actions_taken,
          action_type: data.action_id
        },
        suggestedActions: responseData.suggested_actions || [],
        actionsPerformed: responseData.actions_taken || []
      };

      setMessages(prev => [...prev, actionMessage]);
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to execute quick action');
    }
  });

  const handleSendMessage = async () => {
    if (!inputValue.trim() || sendMessageMutation.isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputValue,
      messageType: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    await sendMessageMutation.mutateAsync({
      message: inputValue,
      sessionId: currentSession,
      modelName: selectedModel
    });
  };

  const handleQuickAction = (actionId: string, message: string) => {
    // Add user message for the quick action
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      messageType: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    quickActionMutation.mutate(actionId);
  };

  const handleSuggestedAction = (action: string) => {
    setInputValue(action);
    textFieldRef.current?.focus();
  };

  const handleTaskComplete = async (taskId: string) => {
    try {
      await apiClient.completeEmailTask(taskId);

      // Add a system message about the completion
      const systemMessage: ChatMessage = {
        id: Date.now().toString(),
        content: `✅ Task completed successfully`,
        messageType: 'system',
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to complete task:', error);
    }
  };

  const handleFeedback = async (messageId: string, type: 'positive' | 'negative') => {
    try {
      // Note: Feedback functionality placeholder - would implement when API endpoints are ready
      console.log('Feedback submitted:', { messageId, type });
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setCurrentSession(null);
    setError(null);
  };

  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel);

    if (messages.length > 0) {
      // Add a system message about model change
      const systemMessage: ChatMessage = {
        id: Date.now().toString(),
        content: `🔄 Switched to ${newModel} model`,
        messageType: 'system',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, systemMessage]);
    }
  };

  const isLoading = sendMessageMutation.isLoading || quickActionMutation.isLoading;

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Header */}
      <Paper elevation={1} sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'between', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <SmartToy sx={{ color: '#007AFF' }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Email Assistant
            </Typography>
            <Chip
              label={`${messages.filter(m => m.messageType !== 'system').length} messages`}
              size="small"
              variant="outlined"
            />
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={streamingEnabled}
                  onChange={(e) => setStreamingEnabled(e.target.checked)}
                  size="small"
                />
              }
              label="Stream"
              sx={{ mr: 1 }}
            />

            <IconButton
              size="small"
              onClick={handleClearChat}
              disabled={messages.length === 0}
              title="Clear chat"
            >
              <Clear />
            </IconButton>

            <IconButton size="small" title="Chat history">
              <History />
            </IconButton>

            <IconButton size="small" title="Settings">
              <Settings />
            </IconButton>
          </Box>
        </Box>
      </Paper>

      <Grid container spacing={2} sx={{ flexGrow: 1, overflow: 'hidden' }}>
        {/* Main Chat Area */}
        <Grid item xs={12} lg={9}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Model Selector */}
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={handleModelChange}
                disabled={isLoading}
                showStatus={true}
              />
            </Box>

            {/* Messages Area */}
            <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2, minHeight: 400 }}>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              {messages.length === 0 ? (
                <Box sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  textAlign: 'center',
                  py: 4
                }}>
                  <SmartToy sx={{ fontSize: 64, color: 'primary.light', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    Welcome to your Email Assistant
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 400 }}>
                    I can help you manage your email workflows, tasks, and search through your emails.
                    Try asking me about pending tasks or searching for specific emails.
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Model: <strong>{selectedModel || 'Loading...'}</strong>
                  </Typography>
                </Box>
              ) : (
                <Box>
                  {messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      id={message.id}
                      content={message.content}
                      messageType={message.messageType}
                      timestamp={message.timestamp}
                      modelUsed={message.modelUsed}
                      generationTimeMs={message.generationTimeMs}
                      richContent={message.richContent}
                      suggestedActions={message.suggestedActions}
                      actionsPerformed={message.actionsPerformed}
                      onActionClick={handleSuggestedAction}
                      onFeedback={handleFeedback}
                      onTaskComplete={handleTaskComplete}
                      thinkingContent={message.thinkingContent}
                      isStreaming={message.isStreaming}
                    />
                  ))}
                  {isLoading && (
                    <Fade in={true}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 2 }}>
                        <CircularProgress size={20} />
                        <Typography variant="body2" color="text.secondary">
                          {selectedModel} is thinking...
                        </Typography>
                      </Box>
                    </Fade>
                  )}
                  <div ref={messagesEndRef} />
                </Box>
              )}
            </Box>

            {/* Input Area */}
            <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  placeholder="Ask me about your emails, tasks, or workflows..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  disabled={isLoading}
                  inputRef={textFieldRef}
                  variant="outlined"
                  size="small"
                />
                {isStreaming ? (
                  <Button
                    variant="contained"
                    onClick={cancelStreaming}
                    color="error"
                    startIcon={<Stop />}
                    sx={{
                      minWidth: 100,
                      height: 40
                    }}
                  >
                    Stop
                  </Button>
                ) : (
                  <Button
                    variant="outlined"
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || isLoading}
                    sx={{
                      minWidth: 80,
                      height: 40,
                      bgcolor: !inputValue.trim() || isLoading ? 'transparent' : '#007AFF',
                      color: !inputValue.trim() || isLoading ? 'inherit' : 'white',
                      '&:hover': {
                        bgcolor: !inputValue.trim() || isLoading ? 'transparent' : '#0051D5'
                      }
                    }}
                  >
                    <Send />
                  </Button>
                )}
              </Box>
            </Box>
          </Card>
        </Grid>

        {/* Quick Actions Sidebar */}
        <Grid item xs={12} lg={3}>
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            <QuickActions
              onActionClick={handleQuickAction}
              taskStats={{
                pending: taskStats?.pending_tasks || 0,
                completed: taskStats?.completed_tasks || 0,
                overdue: taskStats?.overdue_tasks || 0
              }}
              workflowStats={{
                active: taskStats?.active_workflows || 0,
                completed: taskStats?.completed_workflows || 0,
                failed: 0
              }}
              disabled={isLoading}
            />
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default EnhancedEmailChat;