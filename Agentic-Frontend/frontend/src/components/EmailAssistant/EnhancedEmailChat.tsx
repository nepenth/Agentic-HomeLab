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
  const [selectedModel, setSelectedModel] = useState('llama2');
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // Fetch user preferences
  const { data: preferences } = useQuery({
    queryKey: ['email-assistant-preferences'],
    queryFn: async () => {
      // Note: This endpoint doesn't exist in API client yet, create placeholder response
      const response = { data: { default_model: 'llama2', enable_streaming: true } };
      return response.data;
    },
    onSuccess: (data) => {
      if (data.default_model) {
        setSelectedModel(data.default_model);
      }
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

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async ({ message, sessionId, modelName }: {
      message: string;
      sessionId?: string;
      modelName?: string;
    }) => {
      // Note: Using placeholder response since email assistant chat endpoints not available yet
      const response = {
        content: `I received your message: "${message}". The Email Assistant chat functionality is being implemented.`,
        message_type: 'assistant',
        rich_content: {},
        actions_performed: [],
        related_entities: {},
        suggested_actions: ['Show pending tasks', 'Search emails'],
        model_used: modelName || 'llama2',
        tokens_used: 50,
        generation_time_ms: 500,
        timestamp: new Date().toISOString()
      };
      return response;
    },
    onSuccess: (data) => {
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        content: data.content,
        messageType: data.message_type || 'assistant',
        timestamp: data.timestamp || new Date().toISOString(),
        modelUsed: data.model_used,
        generationTimeMs: data.generation_time_ms,
        richContent: data.rich_content,
        suggestedActions: data.suggested_actions,
        actionsPerformed: data.actions_performed
      };

      setMessages(prev => [...prev, assistantMessage]);
      setError(null);
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to send message');
      console.error('Send message error:', error);
    }
  });

  // Quick action mutation
  const quickActionMutation = useMutation({
    mutationFn: async (actionId: string) => {
      // Note: Using placeholder response since email assistant quick actions endpoints not available yet
      const actionMessages = {
        'show_pending_tasks': 'Here are your pending tasks...',
        'search_emails': 'I can help you search your emails...',
        'show_urgent': 'Here are your urgent emails...',
        'workflow_status': 'Your email workflows are running...'
      };

      const response = {
        action_id: actionId,
        response: {
          content: actionMessages[actionId as keyof typeof actionMessages] || 'Action executed successfully',
          rich_content: {},
          suggested_actions: ['View details', 'Mark as complete']
        }
      };
      return response;
    },
    onSuccess: (data) => {
      const actionMessage: ChatMessage = {
        id: Date.now().toString(),
        content: data.response.content,
        messageType: 'assistant',
        timestamp: new Date().toISOString(),
        richContent: data.response.rich_content,
        suggestedActions: data.response.suggested_actions
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
                    Model: <strong>{selectedModel}</strong>
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
                  endIcon={<Send />}
                >
                  Send
                </Button>
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