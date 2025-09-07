import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Avatar,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  Chip,
  Skeleton,
  Tooltip,
  Collapse,
  LinearProgress,
  Grid,
  Divider,
} from '@mui/material';
import {
  Send,
  SmartToy,
  Person,
  Add,
  Archive,
  Delete,
  Chat as ChatIcon,
  ExpandMore,
  ExpandLess,
  Monitor,
  Refresh,
  Timeline,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { ChatSession, ChatMessage, ChatModelsResponse, GpuMetrics, PerformanceMetrics } from '../types';

interface ChatPageProps {}

const Chat: React.FC<ChatPageProps> = () => {
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('llama2');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set());
  const [gpuMonitorOpen, setGpuMonitorOpen] = useState(false);
  const [performanceMetricsOpen, setPerformanceMetricsOpen] = useState(false);
  const [selectedPerformanceMetrics, setSelectedPerformanceMetrics] = useState<PerformanceMetrics | null>(null);

  // Fetch chat sessions
  const {
    data: sessions,
    isLoading: sessionsLoading,
  } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => apiClient.getChatSessions(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch available models
  const {
    data: modelsData,
    isLoading: modelsLoading,
  } = useQuery<ChatModelsResponse>({
    queryKey: ['chat-models'],
    queryFn: () => apiClient.getChatModels(),
  });

  // Fetch GPU metrics
  const {
    data: gpuData,
    isLoading: gpuLoading,
    refetch: refetchGpu,
  } = useQuery<GpuMetrics[]>({
    queryKey: ['gpu-metrics'],
    queryFn: () => apiClient.getSystemMetricsGpu(),
    enabled: gpuMonitorOpen,
    refetchInterval: gpuMonitorOpen ? 2000 : false, // Refresh every 2 seconds when open
  });

  // Fetch messages for selected session
  const {
    data: sessionMessages,
    isLoading: messagesLoading,
  } = useQuery({
    queryKey: ['chat-messages', selectedSession?.id],
    queryFn: () => selectedSession ? apiClient.getChatSessionMessages(selectedSession.id) : [],
    enabled: !!selectedSession,
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (data: { sessionId: string; message: string; model: string }) =>
      apiClient.sendChatMessage(data.sessionId, {
        message: data.message,
        model_name: data.model,
      }),
    onSuccess: (response) => {
      const currentTime = new Date().toISOString();
      const sessionId = response.session_id || selectedSession?.id || '';

      // Add user message
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: newMessage,
        timestamp: currentTime,
      };

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: response.response || 'I received your message.',
        timestamp: currentTime,
        metadata: response.performance_metrics ? {
          performance_metrics: response.performance_metrics
        } : undefined,
      };

      setMessages(prev => [...prev, userMessage, assistantMessage]);
      setNewMessage('');
      setIsTyping(false);

      // Refetch sessions to update last activity
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
    onError: () => {
      setIsTyping(false);
    },
  });

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: (data: { title: string; model: string }) =>
      apiClient.createChatSession({
        session_type: 'general',
        model_name: data.model,
        title: data.title,
        user_id: user?.id,
      }),
    onSuccess: (newSession) => {
      setSelectedSession(newSession);
      setCreateDialogOpen(false);
      setNewSessionTitle('');
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
  });

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => apiClient.deleteChatSession(sessionId),
    onSuccess: () => {
      if (selectedSession?.id === selectedSession?.id) {
        setSelectedSession(null);
        setMessages([]);
      }
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
  });

  // Update session status mutation
  const updateSessionStatusMutation = useMutation({
    mutationFn: ({ sessionId, status }: { sessionId: string; status: string }) =>
      apiClient.updateChatSessionStatus(sessionId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
  });

  // Update messages when session changes
  useEffect(() => {
    if (sessionMessages) {
      setMessages(sessionMessages);
    } else {
      setMessages([]);
    }
  }, [sessionMessages]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Set default model when models are loaded
  useEffect(() => {
    if (modelsData?.models && modelsData.models.length > 0 && !selectedModel) {
      setSelectedModel(modelsData.models[0]);
    }
  }, [modelsData, selectedModel]);

  const handleSendMessage = () => {
    if (!newMessage.trim() || !selectedSession) return;

    setIsTyping(true);
    sendMessageMutation.mutate({
      sessionId: selectedSession.id,
      message: newMessage,
      model: selectedModel,
    });
  };

  const handleCreateSession = () => {
    if (!newSessionTitle.trim()) return;

    createSessionMutation.mutate({
      title: newSessionTitle,
      model: selectedModel,
    });
  };

  const handleDeleteSession = (sessionId: string) => {
    if (window.confirm('Are you sure you want to delete this chat session?')) {
      deleteSessionMutation.mutate(sessionId);
    }
  };

  const handleArchiveSession = (sessionId: string) => {
    updateSessionStatusMutation.mutate({
      sessionId,
      status: 'archived',
    });
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        return 'Just now'; // Fallback for invalid dates
      }
      return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (error) {
      console.warn('Invalid timestamp:', timestamp);
      return 'Just now'; // Fallback for parsing errors
    }
  };

  const parseThinkingContent = (content: string) => {
    const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = thinkRegex.exec(content)) !== null) {
      // Add text before the thinking section
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex, match.index),
        });
      }

      // Add the thinking section
      parts.push({
        type: 'thinking',
        content: match[1].trim(),
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex),
      });
    }

    return parts;
  };

  const toggleThinking = (messageId: string) => {
    setExpandedThinking(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  const openPerformanceMetrics = (metrics: PerformanceMetrics) => {
    setSelectedPerformanceMetrics(metrics);
    setPerformanceMetricsOpen(true);
  };

  const MetricBar = ({ label, value, maxValue, unit = '%', color = 'primary' }: {
    label: string;
    value: number;
    maxValue?: number;
    unit?: string;
    color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';
  }) => {
    const percentage = maxValue ? (value / maxValue) * 100 : value;

    return (
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {label}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {value.toFixed(1)}{unit}
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={Math.min(percentage, 100)}
          color={color}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: 'grey.200',
            '& .MuiLinearProgress-bar': {
              borderRadius: 4,
            },
          }}
        />
      </Box>
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex' }}>
      {/* Sidebar with chat sessions */}
      <Box
        sx={{
          width: 300,
          borderRight: 1,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Chat Sessions
            </Typography>
            <Tooltip title="New Chat">
              <IconButton
                onClick={() => setCreateDialogOpen(true)}
                sx={{
                  bgcolor: 'primary.main',
                  color: 'white',
                  '&:hover': { bgcolor: 'primary.dark' },
                }}
              >
                <Add />
              </IconButton>
            </Tooltip>
          </Box>

          {/* Model Selector */}
          <FormControl fullWidth size="small">
            <InputLabel>Model</InputLabel>
            <Select
              value={selectedModel}
              label="Model"
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={modelsLoading}
            >
              {modelsLoading ? (
                <MenuItem disabled>Loading models...</MenuItem>
              ) : (
                modelsData?.models?.map((model) => (
                  <MenuItem key={model} value={model}>
                    {model}
                  </MenuItem>
                )) || (
                  <MenuItem value="llama2">Llama 2 (Default)</MenuItem>
                )
              )}
            </Select>
          </FormControl>
        </Box>

        {/* Sessions List */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {sessionsLoading ? (
            <Box sx={{ p: 2 }}>
              {[...Array(5)].map((_, index) => (
                <Skeleton key={index} variant="rectangular" height={70} sx={{ mb: 1, borderRadius: 2 }} />
              ))}
            </Box>
          ) : (
            <List sx={{ p: 1 }}>
              {sessions?.map((session) => (
                <Paper
                  key={session.id}
                  elevation={selectedSession?.id === session.id ? 2 : 0}
                  sx={{
                    mb: 1,
                    borderRadius: 2,
                    border: selectedSession?.id === session.id ? 2 : 1,
                    borderColor: selectedSession?.id === session.id ? 'primary.main' : 'divider',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      borderColor: 'primary.main',
                      bgcolor: 'action.hover',
                    },
                  }}
                  onClick={() => setSelectedSession(session)}
                >
                  <Box sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 600,
                          flex: 1,
                          mr: 1,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        {session.title}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="Archive">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleArchiveSession(session.id);
                            }}
                            sx={{ p: 0.5 }}
                          >
                            <Archive fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSession(session.id);
                            }}
                            color="error"
                            sx={{ p: 0.5 }}
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">
                        {formatTimestamp(session.updated_at)}
                      </Typography>
                      <Tooltip title={session.model_name} placement="top">
                        <Chip
                          label={session.model_name}
                          size="small"
                          variant="outlined"
                          sx={{
                            height: 18,
                            fontSize: '0.65rem',
                            borderRadius: 1,
                            '& .MuiChip-label': {
                              px: 1,
                              maxWidth: 80,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }
                          }}
                        />
                      </Tooltip>
                    </Box>
                  </Box>
                </Paper>
              )) || (
                <Box sx={{ p: 3, textAlign: 'center' }}>
                  <ChatIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    No chat sessions yet. Create your first chat!
                  </Typography>
                </Box>
              )}
            </List>
          )}
        </Box>
      </Box>

      {/* Main Chat Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {selectedSession ? (
          <>
            {/* Chat Header */}
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {selectedSession.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Using {selectedSession.model_name} • {selectedSession.status}
                  </Typography>
                </Box>
                <Tooltip title="GPU Monitor">
                  <IconButton
                    onClick={() => setGpuMonitorOpen(true)}
                    sx={{
                      bgcolor: 'primary.main',
                      color: 'white',
                      '&:hover': { bgcolor: 'primary.dark' },
                    }}
                  >
                    <Monitor />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>

            {/* Messages */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
              {messagesLoading ? (
                <Box>
                  {[...Array(3)].map((_, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 2 }} />
                    </Box>
                  ))}
                </Box>
              ) : (
                messages.map((message) => {
                  const hasThinking = message.role === 'assistant' && message.content.includes('<think>');
                  const thinkingParts = hasThinking ? parseThinkingContent(message.content) : [];

                  return (
                    <Box
                      key={message.id}
                      sx={{
                        display: 'flex',
                        mb: 2,
                        justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <Box
                        sx={{
                          display: 'flex',
                          maxWidth: '70%',
                          alignItems: 'flex-start',
                          gap: 1,
                        }}
                      >
                        {message.role === 'assistant' && (
                          <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                            <SmartToy fontSize="small" />
                          </Avatar>
                        )}
                        <Paper
                          elevation={1}
                          sx={{
                            p: 2,
                            bgcolor: message.role === 'user' ? 'primary.main' : 'background.paper',
                            color: message.role === 'user' ? 'white' : 'text.primary',
                            borderRadius: 2,
                            width: '100%',
                            position: 'relative',
                          }}
                        >
                          {hasThinking ? (
                            <Box>
                              {thinkingParts.map((part, index) => (
                                <Box key={index}>
                                  {part.type === 'text' && part.content && (
                                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', mb: part.content.trim() ? 1 : 0 }}>
                                      {part.content}
                                    </Typography>
                                  )}
                                  {part.type === 'thinking' && (
                                    <Box>
                                      <Button
                                        onClick={() => toggleThinking(message.id)}
                                        sx={{
                                          p: 0,
                                          minWidth: 'auto',
                                          textTransform: 'none',
                                          color: 'text.secondary',
                                          fontSize: '0.875rem',
                                          fontWeight: 500,
                                          mb: 1,
                                          '&:hover': { bgcolor: 'transparent' },
                                        }}
                                        startIcon={
                                          expandedThinking.has(message.id) ?
                                            <ExpandLess fontSize="small" /> :
                                            <ExpandMore fontSize="small" />
                                        }
                                      >
                                        {expandedThinking.has(message.id) ? 'Hide' : 'Show'} reasoning
                                      </Button>
                                      <Collapse in={expandedThinking.has(message.id)}>
                                        <Paper
                                          sx={{
                                            p: 2,
                                            bgcolor: 'grey.50',
                                            border: 1,
                                            borderColor: 'grey.200',
                                            borderRadius: 1,
                                            mb: 1,
                                          }}
                                        >
                                          <Typography
                                            variant="body2"
                                            sx={{
                                              fontFamily: 'monospace',
                                              whiteSpace: 'pre-wrap',
                                              color: 'text.secondary',
                                              fontSize: '0.8rem',
                                              lineHeight: 1.4,
                                            }}
                                          >
                                            {part.content}
                                          </Typography>
                                        </Paper>
                                      </Collapse>
                                    </Box>
                                  )}
                                </Box>
                              ))}
                            </Box>
                          ) : (
                            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                              {message.content}
                            </Typography>
                          )}

                          {/* Performance Metrics Toolbox */}
                          {message.role === 'assistant' && message.metadata?.performance_metrics && (
                            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, gap: 1 }}>
                              <Tooltip title="View Performance Metrics">
                                <IconButton
                                  size="small"
                                  onClick={() => openPerformanceMetrics(message.metadata!.performance_metrics)}
                                  sx={{
                                    color: 'text.secondary',
                                    '&:hover': { color: 'primary.main' },
                                    p: 0.5,
                                  }}
                                >
                                  <Timeline fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Typography variant="caption" color="text.secondary">
                                {message.metadata.performance_metrics.tokens_per_second.toFixed(1)} tokens/sec
                              </Typography>
                            </Box>
                          )}

                          <Typography
                            variant="caption"
                            sx={{
                              display: 'block',
                              mt: 1,
                              color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : 'text.secondary',
                            }}
                          >
                            {formatTimestamp(message.timestamp)}
                          </Typography>
                        </Paper>
                        {message.role === 'user' && (
                          <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
                            <Person fontSize="small" />
                          </Avatar>
                        )}
                      </Box>
                    </Box>
                  );
                })
              )}

              {isTyping && (
                <Box sx={{ display: 'flex', mb: 2, alignItems: 'flex-start', gap: 1 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                    <SmartToy fontSize="small" />
                  </Avatar>
                  <Paper elevation={1} sx={{ p: 2, borderRadius: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      AI is typing...
                    </Typography>
                  </Paper>
                </Box>
              )}

              <div ref={messagesEndRef} />
            </Box>

            {/* Message Input */}
            <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Type your message..."
                  disabled={sendMessageMutation.isPending}
                />
                <Button
                  variant="contained"
                  onClick={handleSendMessage}
                  disabled={!newMessage.trim() || sendMessageMutation.isPending}
                  sx={{ minWidth: 60 }}
                >
                  <Send />
                </Button>
              </Box>
            </Box>
          </>
        ) : (
          /* Welcome Screen */
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              p: 4,
            }}
          >
            <SmartToy sx={{ fontSize: 80, color: 'primary.main', mb: 3 }} />
            <Typography variant="h4" sx={{ fontWeight: 600, mb: 2 }}>
              Welcome to AI Chat
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 4, textAlign: 'center' }}>
              Start a conversation with our AI assistant. Select a model and create your first chat session.
            </Typography>
            <Button
              variant="contained"
              size="large"
              startIcon={<Add />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Start New Chat
            </Button>
          </Box>
        )}
      </Box>

      {/* Create Session Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>New Chat Session</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Session Title"
            fullWidth
            value={newSessionTitle}
            onChange={(e) => setNewSessionTitle(e.target.value)}
            placeholder="e.g., General Discussion, Code Help, etc."
          />
          <FormControl fullWidth margin="dense">
            <InputLabel>Model</InputLabel>
            <Select
              value={selectedModel}
              label="Model"
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {modelsData?.models?.map((model) => (
                <MenuItem key={model} value={model}>
                  {model}
                </MenuItem>
              )) || (
                <MenuItem value="llama2">Llama 2 (Default)</MenuItem>
              )}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateSession}
            variant="contained"
            disabled={createSessionMutation.isPending || !newSessionTitle.trim()}
          >
            {createSessionMutation.isPending ? 'Creating...' : 'Create Chat'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* GPU Monitor Dialog */}
      <Dialog
        open={gpuMonitorOpen}
        onClose={() => setGpuMonitorOpen(false)}
        maxWidth="md"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            height: '80vh',
            maxHeight: '600px',
          },
        }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Monitor />
            <Typography variant="h6">GPU Monitor</Typography>
          </Box>
          <IconButton onClick={() => refetchGpu()} disabled={gpuLoading}>
            <Refresh />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {gpuLoading ? (
            <Box sx={{ p: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Loading GPU metrics...
              </Typography>
              {[...Array(3)].map((_, index) => (
                <Skeleton key={index} variant="rectangular" height={80} sx={{ mb: 2, borderRadius: 1 }} />
              ))}
            </Box>
          ) : gpuData && gpuData.length > 0 ? (
            <Box>
              {gpuData.map((gpu) => (
                <Paper key={gpu.index} elevation={1} sx={{ p: 2, mb: 2, borderRadius: 2 }}>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                    GPU {gpu.index}: {gpu.name}
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 500 }}>
                        Utilization
                      </Typography>
                      <MetricBar
                        label="GPU Usage"
                        value={gpu.utilization.gpu_percent}
                        unit="%"
                        color="primary"
                      />
                      <MetricBar
                        label="Memory Usage"
                        value={gpu.utilization.memory_percent}
                        unit="%"
                        color="secondary"
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 500 }}>
                        Memory
                      </Typography>
                      <MetricBar
                        label="VRAM Used"
                        value={gpu.memory.used_mb / 1024}
                        maxValue={gpu.memory.total_mb / 1024}
                        unit="GB"
                        color="info"
                      />
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          {gpu.memory.used_mb} MB / {gpu.memory.total_mb} MB
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 500 }}>
                        Temperature
                      </Typography>
                      <MetricBar
                        label="GPU Temp"
                        value={gpu.temperature_fahrenheit}
                        maxValue={100}
                        unit="°F"
                        color={gpu.temperature_fahrenheit > 80 ? "error" : gpu.temperature_fahrenheit > 70 ? "warning" : "success"}
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 500 }}>
                        Power
                      </Typography>
                      <MetricBar
                        label="Power Usage"
                        value={gpu.power.usage_watts}
                        maxValue={gpu.power.limit_watts}
                        unit="W"
                        color="warning"
                      />
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          {gpu.power.usage_watts}W / {gpu.power.limit_watts}W
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Paper>
              ))}
            </Box>
          ) : (
            <Box sx={{ textAlign: 'center', p: 4 }}>
              <Monitor sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="body1" color="text.secondary">
                No GPU data available
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Make sure your system has GPU monitoring enabled
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGpuMonitorOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Performance Metrics Dialog */}
      <Dialog
        open={performanceMetricsOpen}
        onClose={() => setPerformanceMetricsOpen(false)}
        maxWidth="md"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            height: '80vh',
            maxHeight: '700px',
          },
        }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Timeline />
          <Typography variant="h6">LLM Performance Metrics</Typography>
        </DialogTitle>
        <DialogContent>
          {selectedPerformanceMetrics && (
            <Box>
              {/* Overview Cards */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'primary.light', color: 'white' }}>
                    <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                      {selectedPerformanceMetrics.tokens_per_second.toFixed(1)}
                    </Typography>
                    <Typography variant="body2">Tokens/Second</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light', color: 'white' }}>
                    <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                      {selectedPerformanceMetrics.total_tokens}
                    </Typography>
                    <Typography variant="body2">Total Tokens</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'warning.light', color: 'white' }}>
                    <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                      {selectedPerformanceMetrics.response_time_seconds.toFixed(2)}s
                    </Typography>
                    <Typography variant="body2">Response Time</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'info.light', color: 'white' }}>
                    <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                      {selectedPerformanceMetrics.model_name}
                    </Typography>
                    <Typography variant="body2">Model</Typography>
                  </Paper>
                </Grid>
              </Grid>

              {/* Detailed Metrics */}
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Detailed Performance Breakdown
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                      Response Times
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <MetricBar
                        label="Total Response Time"
                        value={selectedPerformanceMetrics.response_time_seconds}
                        maxValue={10}
                        unit="s"
                        color="primary"
                      />
                      <MetricBar
                        label="Model Load Time"
                        value={selectedPerformanceMetrics.load_time_seconds}
                        maxValue={selectedPerformanceMetrics.response_time_seconds}
                        unit="s"
                        color="warning"
                      />
                      <MetricBar
                        label="Prompt Evaluation"
                        value={selectedPerformanceMetrics.prompt_eval_time_seconds}
                        maxValue={selectedPerformanceMetrics.response_time_seconds}
                        unit="s"
                        color="info"
                      />
                      <MetricBar
                        label="Generation Time"
                        value={selectedPerformanceMetrics.generation_time_seconds}
                        maxValue={selectedPerformanceMetrics.response_time_seconds}
                        unit="s"
                        color="success"
                      />
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                      Token Usage
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="body2">Prompt Tokens</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {selectedPerformanceMetrics.prompt_tokens}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="body2">Response Tokens</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {selectedPerformanceMetrics.response_tokens}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2">Total Tokens</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {selectedPerformanceMetrics.total_tokens}
                          </Typography>
                        </Box>
                      </Box>

                      <Divider sx={{ my: 1 }} />

                      <Box>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          Context Length: {selectedPerformanceMetrics.context_length_chars} characters
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          Generation Speed: {selectedPerformanceMetrics.tokens_per_second.toFixed(2)} tokens/second
                        </Typography>
                        <Typography variant="body2">
                          Timestamp: {new Date(selectedPerformanceMetrics.timestamp).toLocaleString()}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>
                </Grid>
              </Grid>

              {/* Performance Insights */}
              <Paper sx={{ p: 2, mt: 3, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                  Performance Insights
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {selectedPerformanceMetrics.tokens_per_second > 50 && (
                    <Typography variant="body2" sx={{ color: 'success.main' }}>
                      ✅ Excellent generation speed! Model is performing optimally.
                    </Typography>
                  )}
                  {selectedPerformanceMetrics.tokens_per_second < 20 && (
                    <Typography variant="body2" sx={{ color: 'warning.main' }}>
                      ⚠️ Slower generation speed. Consider using a lighter model or optimizing prompts.
                    </Typography>
                  )}
                  {selectedPerformanceMetrics.load_time_seconds > 1 && (
                    <Typography variant="body2" sx={{ color: 'info.main' }}>
                      ℹ️ Model load time indicates first-time usage. Subsequent responses will be faster.
                    </Typography>
                  )}
                  {selectedPerformanceMetrics.response_time_seconds < 2 && (
                    <Typography variant="body2" sx={{ color: 'success.main' }}>
                      ✅ Fast response time! Excellent user experience.
                    </Typography>
                  )}
                  {selectedPerformanceMetrics.total_tokens > 1000 && (
                    <Typography variant="body2" sx={{ color: 'warning.main' }}>
                      ⚠️ High token usage. Consider breaking down complex queries.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPerformanceMetricsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Chat;