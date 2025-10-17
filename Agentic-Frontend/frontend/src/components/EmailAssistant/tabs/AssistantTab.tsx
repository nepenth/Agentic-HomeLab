import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  TextField,
  IconButton,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Chip,
  Avatar,
  Menu,
  MenuItem,
  useTheme,
  alpha,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  MoreVert as MoreIcon,
  ContentCopy as CopyIcon,
  Search as SearchIcon,
  Email as EmailIcon,
  Task as TaskIcon,
  Settings as SettingsIcon,
  MicNone as MicIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useAssistant } from '../../../hooks/useAssistant';
import ModelSelector from '../ModelSelector';
import { formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import { ConnectionStatusIndicator, useConnectionQuality } from '../ConnectionStatus';

interface AssistantTabProps {
  onNavigateToEmail?: (emailId: string) => void;
}

export const AssistantTab: React.FC<AssistantTabProps> = ({ onNavigateToEmail }) => {
  const theme = useTheme();
  const {
    currentSession,
    sessions,
    messages,
    selectedModel,
    isStreaming,
    streamingEnabled,
    quickActions,
    context,
    switchSession,
    createSession,
    deleteSession,
    sendMessage,
    updateModel,
    updateContext,
  } = useAssistant();

  const { status: connectionStatus, quality: connectionQuality, latency, retry: retryConnection } = useConnectionQuality();
  const [messageInput, setMessageInput] = useState('');
  const [sessionMenuAnchor, setSessionMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-create a session if none exists
  useEffect(() => {
    if (sessions.length === 0 && !currentSession) {
      handleNewSession();
    }
  }, [sessions.length, currentSession]);

  const handleSendMessage = async () => {
    if (!messageInput.trim() || isStreaming) return;

    // Auto-create session if none exists
    if (!currentSession) {
      await handleNewSession();
      // Wait a bit for session to be created
      setTimeout(() => {
        sendMessage({
          message: messageInput,
          context: {
            emailId: context.currentEmail,
            taskId: context.currentTask,
          },
        });
      }, 100);
    } else {
      sendMessage({
        message: messageInput,
        context: {
          emailId: context.currentEmail,
          taskId: context.currentTask,
        },
      });
    }

    setMessageInput('');
  };

  const handleNewSession = async () => {
    createSession({ title: 'New Chat', modelName: selectedModel });
  };

  const handleSessionMenuOpen = (event: React.MouseEvent<HTMLElement>, sessionId: string) => {
    event.stopPropagation();
    setSessionMenuAnchor(event.currentTarget);
    setSelectedSessionId(sessionId);
  };

  const handleSessionMenuClose = () => {
    setSessionMenuAnchor(null);
    setSelectedSessionId(null);
  };

  const handleDeleteSession = () => {
    if (selectedSessionId) {
      deleteSession(selectedSessionId);
    }
    handleSessionMenuClose();
  };

  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
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

  const formatThinkingContent = (thinkingData: any): string => {
    if (typeof thinkingData === 'string') {
      return thinkingData;
    }

    // Handle array of thinking objects
    if (Array.isArray(thinkingData)) {
      return thinkingData
        .map(item => {
          if (typeof item === 'string') return item;
          if (item.content) return item.content;
          return JSON.stringify(item);
        })
        .join('\n\n');
    }

    // Handle single thinking object
    if (thinkingData && typeof thinkingData === 'object') {
      if (thinkingData.content) return thinkingData.content;
      return JSON.stringify(thinkingData, null, 2);
    }

    return String(thinkingData);
  };

  const getMessageAvatar = (role: string) => {
    if (role === 'user') {
      return (
        <Avatar sx={{ bgcolor: theme.palette.primary.main, width: 32, height: 32 }}>
          <PersonIcon fontSize="small" />
        </Avatar>
      );
    }
    return (
      <Avatar sx={{ bgcolor: theme.palette.secondary.main, width: 32, height: 32 }}>
        <BotIcon fontSize="small" />
      </Avatar>
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ flex: 1, display: 'flex', gap: 2, overflow: 'hidden', minHeight: 0 }}>
        {/* Left Panel - Session List (25%) */}
        <Box sx={{ width: '25%', minWidth: 250, display: 'flex', flexDirection: 'column' }}>
          <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
              <Button
                variant="contained"
                fullWidth
                startIcon={<AddIcon />}
                onClick={handleNewSession}
              >
                New Chat
              </Button>
            </Box>

            <List sx={{ flex: 1, overflow: 'auto', p: 1 }}>
              {sessions.map((session) => (
                <React.Fragment key={session.id}>
                  <ListItemButton
                    selected={currentSession?.id === session.id}
                    onClick={() => switchSession(session.id)}
                    sx={{
                      borderRadius: 1,
                      mb: 0.5,
                    }}
                  >
                    <ListItemText
                      primary={session.title}
                      secondary={
                        <Box>
                          <Typography variant="caption" sx={{ display: 'block' }}>
                            {session.message_count} messages
                          </Typography>
                          <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                            {session.updated_at ? formatDistanceToNow(new Date(session.updated_at), { addSuffix: true }) : 'Just now'}
                          </Typography>
                        </Box>
                      }
                      primaryTypographyProps={{
                        variant: 'body2',
                        fontWeight: 600,
                        noWrap: true,
                      }}
                    />
                    <IconButton
                      size="small"
                      onClick={(e) => handleSessionMenuOpen(e, session.id)}
                    >
                      <MoreIcon fontSize="small" />
                    </IconButton>
                  </ListItemButton>
                </React.Fragment>
              ))}
              {sessions.length === 0 && (
                <Box sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                    No chat sessions yet. Start a new one!
                  </Typography>
                </Box>
              )}
            </List>
          </Paper>
        </Box>

        {/* Center Panel - Chat Messages (50%) */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Chat Header */}
            <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {currentSession?.title || 'AI Assistant'}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 0.5, flexWrap: 'wrap', alignItems: 'center' }}>
                    <ModelSelector selectedModel={selectedModel} onModelChange={updateModel} showStatus={false} />
                    {streamingEnabled && (
                      <Chip label="Streaming" size="small" color="success" sx={{ height: 20 }} />
                    )}
                    <ConnectionStatusIndicator
                      status={connectionStatus}
                      quality={connectionQuality}
                      latency={latency}
                      onRetry={retryConnection}
                    />
                  </Box>
                </Box>
              </Box>
            </Box>

            {/* Messages Area */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
              {currentSession ? (
                messages.length > 0 ? (
                  <>
                    {messages.map((message, index) => (
                      <Box
                        key={message.id}
                        sx={{
                          display: 'flex',
                          gap: 2,
                          mb: 3,
                          flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
                        }}
                      >
                        {getMessageAvatar(message.role)}
                        <Box
                          sx={{
                            flex: 1,
                            maxWidth: '80%',
                          }}
                        >
                          <Box
                            sx={{
                              bgcolor:
                                message.role === 'user'
                                  ? alpha(theme.palette.primary.main, 0.1)
                                  : alpha(theme.palette.grey[500], 0.05),
                              borderRadius: 2,
                              p: 2,
                              position: 'relative',
                            }}
                          >
                            {message.metadata?.thinking_content && (
                              <Box
                                sx={{
                                  bgcolor: alpha(theme.palette.info.main, 0.08),
                                  border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                                  borderRadius: 1,
                                  mb: 1.5,
                                  overflow: 'hidden',
                                }}
                              >
                                <Box
                                  onClick={() => toggleThinking(message.id)}
                                  sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 1,
                                    p: 1,
                                    cursor: 'pointer',
                                    bgcolor: alpha(theme.palette.info.main, 0.05),
                                    '&:hover': {
                                      bgcolor: alpha(theme.palette.info.main, 0.12),
                                    },
                                  }}
                                >
                                  {expandedThinking.has(message.id) ? (
                                    <ExpandLessIcon sx={{ fontSize: 18, color: theme.palette.info.main }} />
                                  ) : (
                                    <ExpandMoreIcon sx={{ fontSize: 18, color: theme.palette.info.main }} />
                                  )}
                                  <Typography
                                    variant="caption"
                                    sx={{
                                      fontWeight: 600,
                                      color: theme.palette.info.main,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 0.5,
                                    }}
                                  >
                                    💭 Thinking Process
                                    {!expandedThinking.has(message.id) && !isStreaming && (
                                      <CheckCircleIcon sx={{ fontSize: 14, ml: 0.5 }} />
                                    )}
                                  </Typography>
                                </Box>
                                {expandedThinking.has(message.id) && (
                                  <Box
                                    sx={{
                                      p: 1.5,
                                      maxHeight: '300px',
                                      overflowY: 'auto',
                                      fontSize: '0.8rem',
                                      fontFamily: 'monospace',
                                      whiteSpace: 'pre-wrap',
                                      color: theme.palette.text.secondary,
                                      lineHeight: 1.6,
                                    }}
                                  >
                                    {formatThinkingContent(message.metadata.thinking_content)}
                                  </Box>
                                )}
                              </Box>
                            )}

                            <Box sx={{ '& p:last-child': { mb: 0 } }}>
                              <ReactMarkdown>
                                {typeof message.content === 'string'
                                  ? message.content
                                  : JSON.stringify(message.content)
                                }
                              </ReactMarkdown>
                            </Box>

                            {message.metadata?.email_references && message.metadata.email_references.length > 0 && (
                              <Box sx={{ mt: 2 }}>
                                <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                  Referenced Emails ({message.metadata.email_references.length}):
                                </Typography>
                                {message.metadata.email_references.map((ref: any, i: number) => {
                                  let label = 'Email';
                                  if (typeof ref === 'string') {
                                    label = ref;
                                  } else if (ref && ref.subject) {
                                    label = typeof ref.subject === 'string' ? ref.subject : JSON.stringify(ref.subject);
                                  } else if (ref && ref.email_id) {
                                    label = `Email ${ref.email_id.substring(0, 8)}`;
                                  }
                                  return (
                                    <Chip
                                      key={i}
                                      label={label}
                                      size="small"
                                      icon={<EmailIcon />}
                                      clickable
                                      onClick={() => {
                                        if (onNavigateToEmail && ref.email_id) {
                                          onNavigateToEmail(ref.email_id);
                                        }
                                      }}
                                      sx={{
                                        mr: 0.5,
                                        mb: 0.5,
                                        cursor: 'pointer',
                                        '&:hover': {
                                          bgcolor: alpha(theme.palette.primary.main, 0.2),
                                        }
                                      }}
                                    />
                                  );
                                })}
                              </Box>
                            )}

                            {message.metadata?.task_suggestions && message.metadata.task_suggestions.length > 0 && (
                              <Box sx={{ mt: 2 }}>
                                <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                  Task Suggestions ({message.metadata.task_suggestions.length}):
                                </Typography>
                                {message.metadata.task_suggestions.map((suggestion: any, i: number) => {
                                  const label = typeof suggestion === 'string'
                                    ? suggestion
                                    : (suggestion.title || suggestion.description || 'Task suggestion');
                                  return (
                                    <Chip
                                      key={i}
                                      label={typeof label === 'string' ? label : JSON.stringify(label)}
                                      size="small"
                                      icon={<TaskIcon />}
                                      clickable
                                      onClick={() => {
                                        // TODO: Create task from suggestion
                                        console.log('Create task:', suggestion);
                                      }}
                                      sx={{
                                        mr: 0.5,
                                        mb: 0.5,
                                        '&:hover': {
                                          bgcolor: alpha(theme.palette.secondary.main, 0.2),
                                        }
                                      }}
                                    />
                                  );
                                })}
                              </Box>
                            )}

                            {message.metadata?.tasks_created && message.metadata.tasks_created.length > 0 && (
                              <Box sx={{ mt: 2 }}>
                                <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                  Tasks Created ({message.metadata.tasks_created.length}):
                                </Typography>
                                {message.metadata.tasks_created.map((task: any, i: number) => {
                                  const label = typeof task === 'string'
                                    ? task
                                    : (task.title || task.description || 'Task');
                                  return (
                                    <Chip
                                      key={i}
                                      label={typeof label === 'string' ? label : JSON.stringify(label)}
                                      size="small"
                                      icon={<CheckCircleIcon />}
                                      color="success"
                                      sx={{ mr: 0.5, mb: 0.5 }}
                                    />
                                  );
                                })}
                              </Box>
                            )}

                            <IconButton
                              size="small"
                              sx={{
                                position: 'absolute',
                                top: 8,
                                right: 8,
                              }}
                              onClick={() => handleCopyMessage(message.content)}
                            >
                              <CopyIcon fontSize="small" />
                            </IconButton>
                          </Box>

                          <Box
                            sx={{
                              display: 'flex',
                              gap: 1,
                              mt: 0.5,
                              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                            }}
                          >
                            <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                              {message.timestamp ? formatDistanceToNow(new Date(message.timestamp), { addSuffix: true }) : 'Just now'}
                            </Typography>
                            {message.metadata?.model && (
                              <Chip
                                label={message.metadata.model}
                                size="small"
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                            )}
                            {message.metadata?.generation_time && (
                              <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                                {typeof message.metadata.generation_time === 'number'
                                  ? `${message.metadata.generation_time.toFixed(2)}s`
                                  : String(message.metadata.generation_time)
                                }
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </Box>
                    ))}

                    {/* Typing Indicator */}
                    {isStreaming && (
                      <Box
                        sx={{
                          display: 'flex',
                          gap: 2,
                          mb: 3,
                        }}
                      >
                        <Avatar sx={{ bgcolor: theme.palette.secondary.main }}>
                          <BotIcon />
                        </Avatar>
                        <Box sx={{ flex: 1, maxWidth: '80%' }}>
                          <Box
                            sx={{
                              bgcolor: alpha(theme.palette.grey[500], 0.05),
                              borderRadius: 2,
                              p: 2,
                              display: 'flex',
                              alignItems: 'center',
                              gap: 1,
                            }}
                          >
                            <CircularProgress size={16} />
                            <Typography variant="body2" sx={{ fontStyle: 'italic', color: theme.palette.text.secondary }}>
                              AI is thinking...
                            </Typography>
                          </Box>
                        </Box>
                      </Box>
                    )}

                    <div ref={messagesEndRef} />
                  </>
                ) : (
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      gap: 2,
                    }}
                  >
                    <BotIcon sx={{ fontSize: 64, color: theme.palette.text.secondary }} />
                    <Typography variant="h6" sx={{ color: theme.palette.text.secondary }}>
                      Start a conversation
                    </Typography>
                    <Typography variant="body2" sx={{ color: theme.palette.text.secondary, textAlign: 'center' }}>
                      Ask me anything about your emails, tasks, or general questions
                    </Typography>
                  </Box>
                )
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                  }}
                >
                  <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                    Select or create a chat session to get started
                  </Typography>
                </Box>
              )}
            </Box>

            {/* Input Area - Always visible */}
            <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}`, flexShrink: 0 }}>
              {context.currentEmail && (
                <Chip
                  label={`Context: Email #${context.currentEmail.substring(0, 8)}`}
                  size="small"
                  onDelete={() => updateContext({ currentEmail: undefined })}
                  sx={{ mb: 1, mr: 1 }}
                />
              )}
              {context.currentTask && (
                <Chip
                  label={`Context: Task #${context.currentTask.substring(0, 8)}`}
                  size="small"
                  onDelete={() => updateContext({ currentTask: undefined })}
                  sx={{ mb: 1 }}
                />
              )}
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  placeholder={currentSession ? "Type your message..." : "Type your message to start a new chat..."}
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  disabled={isStreaming}
                />
                <Tooltip title="Voice input (coming soon)">
                  <IconButton disabled>
                    <MicIcon />
                  </IconButton>
                </Tooltip>
                <IconButton
                  color="primary"
                  onClick={handleSendMessage}
                  disabled={!messageInput.trim() || isStreaming}
                >
                  {isStreaming ? <CircularProgress size={24} /> : <SendIcon />}
                </IconButton>
              </Box>
            </Box>
          </Paper>
        </Box>

        {/* Right Panel - Quick Actions & Context (25%) */}
        <Box sx={{ width: '25%', minWidth: 250, display: 'flex', flexDirection: 'column' }}>
          <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Quick Actions
              </Typography>
            </Box>

            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
              {quickActions && quickActions.length > 0 ? (
                <List dense sx={{ p: 0 }}>
                  {quickActions.map((action, index) => (
                    <ListItem key={index} disablePadding sx={{ mb: 1 }}>
                      <Button
                        variant="outlined"
                        fullWidth
                        sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                        onClick={() => setMessageInput(action.prompt)}
                      >
                        {action.label}
                      </Button>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <>
                  <Typography variant="body2" sx={{ mb: 2, fontWeight: 600 }}>
                    Suggested Prompts:
                  </Typography>
                  <List dense sx={{ p: 0 }}>
                    {[
                      'Summarize my unread emails',
                      'Show me high priority tasks',
                      'Find emails about [topic]',
                      'Create a task from the latest email',
                      'What are my pending actions?',
                      'Analyze email patterns',
                    ].map((prompt, index) => (
                      <ListItem key={index} disablePadding sx={{ mb: 1 }}>
                        <Button
                          variant="outlined"
                          fullWidth
                          size="small"
                          sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                          onClick={() => setMessageInput(prompt)}
                        >
                          {prompt}
                        </Button>
                      </ListItem>
                    ))}
                  </List>
                </>
              )}

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
                Session Info:
              </Typography>
              {currentSession && (
                <Box sx={{ p: 1.5, bgcolor: alpha(theme.palette.grey[500], 0.05), borderRadius: 1 }}>
                  <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>
                    Messages: {currentSession.message_count}
                  </Typography>
                  <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>
                    Model: {currentSession.model_name}
                  </Typography>
                  <Typography variant="caption" sx={{ display: 'block' }}>
                    Created: {new Date(currentSession.created_at).toLocaleDateString()}
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Box>
      </Box>

      {/* Session Menu */}
      <Menu
        anchorEl={sessionMenuAnchor}
        open={Boolean(sessionMenuAnchor)}
        onClose={handleSessionMenuClose}
      >
        <MenuItem onClick={handleDeleteSession}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete Session
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default AssistantTab;
