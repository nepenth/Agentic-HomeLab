import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Avatar,
  IconButton,
  Collapse,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Button,
  Tooltip,
  Fade
} from '@mui/material';
import {
  Person,
  SmartToy,
  ExpandMore,
  ExpandLess,
  ThumbUp,
  ThumbDown,
  ContentCopy,
  Email,
  Assignment,
  Search,
  CheckCircle,
  Schedule,
  PriorityHigh,
  Info
} from '@mui/icons-material';
import EmailReferences from './EmailReferences';

interface TaskData {
  id: string;
  description: string;
  status: string;
  priority: string;
  created_at?: string;
  email_sender?: string;
  email_subject?: string;
}

interface EmailData {
  id: string;
  subject: string;
  sender: string;
  date: string;
  snippet: string;
  importance_score?: number;
  has_attachments?: boolean;
}

interface ThinkingContent {
  id: string;
  content: string;
}

interface ChatMessageProps {
  id: string;
  content: string;
  messageType: 'user' | 'assistant' | 'system' | 'action';
  timestamp: string;
  modelUsed?: string;
  generationTimeMs?: number;
  richContent?: {
    tasks?: TaskData[];
    search_results?: EmailData[];
    task_stats?: any;
    workflow_stats?: any;
    email_references?: any[];
    tasks_created?: any[];
    metadata?: any;
    [key: string]: any;
  };
  suggestedActions?: string[];
  actionsPerformed?: Array<{ type: string; [key: string]: any }>;
  onActionClick?: (action: string) => void;
  onFeedback?: (messageId: string, type: 'positive' | 'negative') => void;
  onTaskComplete?: (taskId: string) => void;
  thinkingContent?: ThinkingContent[];
  isStreaming?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  id,
  content,
  messageType,
  timestamp,
  modelUsed,
  generationTimeMs,
  richContent,
  suggestedActions = [],
  actionsPerformed = [],
  onActionClick,
  onFeedback,
  onTaskComplete,
  thinkingContent = [],
  isStreaming = false
}) => {
  const [expanded, setExpanded] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
  const [thinkingExpanded, setThinkingExpanded] = useState(false);

  const isUser = messageType === 'user';
  const isSystem = messageType === 'system';
  const isAction = messageType === 'action';

  const handleFeedback = (type: 'positive' | 'negative') => {
    if (feedbackGiven) return;

    setFeedbackGiven(type);
    onFeedback?.(id, type);
  };

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(content);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high': return <PriorityHigh />;
      case 'medium': return <Schedule />;
      case 'low': return <Info />;
      default: return <Assignment />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <Fade in={true} timeout={300}>
      <Box
        sx={{
          display: 'flex',
          flexDirection: isUser ? 'row-reverse' : 'row',
          alignItems: 'flex-start',
          gap: 1,
          mb: 2,
          opacity: isSystem ? 0.7 : 1
        }}
      >
        <Avatar
          sx={{
            bgcolor: isUser ? 'primary.main' : isSystem ? 'grey.500' : 'secondary.main',
            width: 36,
            height: 36
          }}
        >
          {isUser ? <Person /> : <SmartToy />}
        </Avatar>

        <Paper
          elevation={1}
          sx={{
            maxWidth: '80%',
            minWidth: '200px',
            bgcolor: isUser ? 'primary.light' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
            p: 2,
            borderRadius: 2,
            position: 'relative'
          }}
        >
          {/* Message Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {isUser ? 'You' : isAction ? 'Action' : 'Assistant'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatTimestamp(timestamp)}
            </Typography>
            {modelUsed && !isUser && (
              <Chip
                label={modelUsed}
                size="small"
                variant="outlined"
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            )}
            {generationTimeMs && !isUser && (
              <Typography variant="caption" color="text.secondary">
                ({Math.round(generationTimeMs)}ms)
              </Typography>
            )}
          </Box>

          {/* Main Content */}
          <Typography variant="body1" sx={{ mb: richContent || suggestedActions.length > 0 || thinkingContent.length > 0 ? 1 : 0 }}>
            {content}
            {isStreaming && (
              <Box
                component="span"
                sx={{
                  animation: 'blink 1s linear infinite',
                  '@keyframes blink': {
                    '0%': { opacity: 1 },
                    '50%': { opacity: 0 },
                    '100%': { opacity: 1 },
                  }
                }}
              >
                ▋
              </Box>
            )}
          </Typography>

          {/* Thinking Content */}
          {thinkingContent.length > 0 && (
            <Card
              variant="outlined"
              sx={{
                mt: 1,
                mb: 1,
                bgcolor: 'rgba(156, 39, 176, 0.04)',
                borderColor: 'rgba(156, 39, 176, 0.23)'
              }}
            >
              <Box
                sx={{
                  p: 1,
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'rgba(156, 39, 176, 0.08)' }
                }}
                onClick={() => setThinkingExpanded(!thinkingExpanded)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
                  <Box
                    sx={{
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      bgcolor: 'rgba(156, 39, 176, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    🧠
                  </Box>
                  <Typography variant="caption" sx={{ color: '#9C27B0', fontWeight: 'medium' }}>
                    Thinking Process ({thinkingContent.length} section{thinkingContent.length > 1 ? 's' : ''})
                  </Typography>
                </Box>
                <IconButton size="small" sx={{ color: '#9C27B0' }}>
                  {thinkingExpanded ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>

              <Collapse in={thinkingExpanded}>
                <CardContent sx={{ pt: 0, pb: 1 }}>
                  {thinkingContent.map((thinking) => (
                    <Box
                      key={thinking.id}
                      sx={{
                        p: 1.5,
                        mb: 1,
                        bgcolor: 'rgba(156, 39, 176, 0.05)',
                        borderRadius: 1,
                        border: '1px solid rgba(156, 39, 176, 0.12)',
                        '&:last-child': { mb: 0 }
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: 'monospace',
                          whiteSpace: 'pre-wrap',
                          color: 'text.secondary',
                          fontSize: '0.85rem',
                          lineHeight: 1.4
                        }}
                      >
                        {thinking.content}
                      </Typography>
                    </Box>
                  ))}
                </CardContent>
              </Collapse>
            </Card>
          )}

          {/* Task Suggestions */}
          {richContent?.task_suggestions && richContent.task_suggestions.length > 0 && (
            <Card
              variant="outlined"
              sx={{
                mt: 1,
                mb: 1,
                bgcolor: 'rgba(25, 118, 210, 0.04)',
                borderColor: 'rgba(25, 118, 210, 0.23)'
              }}
            >
              <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, color: '#1976d2' }}>
                  <Assignment /> Suggested Tasks ({richContent.task_suggestions.length})
                </Typography>
                {richContent.task_suggestions.map((task: any, index: number) => (
                  <Card
                    key={index}
                    variant="outlined"
                    sx={{
                      mb: 1.5,
                      bgcolor: 'background.paper',
                      borderColor: 'rgba(25, 118, 210, 0.12)',
                      '&:last-child': { mb: 0 }
                    }}
                  >
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
                          {task.title}
                        </Typography>
                        <Chip
                          label={`Priority: ${task.priority}`}
                          size="small"
                          color={task.priority >= 4 ? 'error' : task.priority >= 3 ? 'warning' : 'default'}
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                        {task.description}
                      </Typography>

                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Schedule fontSize="small" color="disabled" />
                          <Typography variant="caption" color="text.secondary">
                            Est. {task.estimated_duration} min
                          </Typography>
                        </Box>

                        {task.due_date && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Schedule fontSize="small" color="disabled" />
                            <Typography variant="caption" color="text.secondary">
                              Due: {new Date(task.due_date).toLocaleDateString()}
                            </Typography>
                          </Box>
                        )}
                      </Box>

                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<Assignment />}
                        sx={{
                          textTransform: 'none',
                          fontSize: '0.75rem',
                          py: 0.5,
                          bgcolor: '#1976d2',
                          '&:hover': { bgcolor: '#1565c0' }
                        }}
                        onClick={() => {
                          // TODO: Implement task creation
                          console.log('Create task:', task);
                        }}
                      >
                        Create Task
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Actions Performed */}
          {actionsPerformed.length > 0 && (
            <Box sx={{ mb: 1 }}>
              {actionsPerformed.map((action, index) => (
                <Chip
                  key={index}
                  icon={<CheckCircle />}
                  label={`${action.type}: ${action.count || 1} item(s)`}
                  size="small"
                  variant="outlined"
                  sx={{
                    mr: 0.5,
                    mb: 0.5,
                    borderColor: '#34C759',
                    color: '#34C759'
                  }}
                />
              ))}
            </Box>
          )}

          {/* Rich Content - Tasks */}
          {richContent?.tasks && richContent.tasks.length > 0 && (
            <Card variant="outlined" sx={{ mt: 1, mb: 1 }}>
              <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Assignment /> Tasks ({richContent.tasks.length})
                </Typography>
                <List dense>
                  {richContent.tasks.slice(0, expanded ? undefined : 3).map((task: TaskData) => (
                    <ListItem
                      key={task.id}
                      sx={{
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 0.5,
                        bgcolor: 'background.default'
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        {getPriorityIcon(task.priority)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" sx={{ flexGrow: 1 }}>
                              {task.description}
                            </Typography>
                            <Chip
                              label={task.status}
                              size="small"
                              color={task.status === 'completed' ? 'success' : 'default'}
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                            <Chip
                              label={task.priority}
                              size="small"
                              color={getPriorityColor(task.priority)}
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                          </Box>
                        }
                        secondary={
                          task.email_sender && (
                            <Typography variant="caption" color="text.secondary">
                              📧 From: {task.email_sender}
                            </Typography>
                          )
                        }
                      />
                      {task.status === 'pending' && onTaskComplete && (
                        <IconButton
                          size="small"
                          onClick={() => onTaskComplete(task.id)}
                          sx={{ color: '#34C759' }}
                        >
                          <CheckCircle />
                        </IconButton>
                      )}
                    </ListItem>
                  ))}
                </List>
                {richContent.tasks.length > 3 && (
                  <Button
                    size="small"
                    onClick={() => setExpanded(!expanded)}
                    endIcon={expanded ? <ExpandLess /> : <ExpandMore />}
                  >
                    {expanded ? 'Show Less' : `Show ${richContent.tasks.length - 3} More`}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* Rich Content - Email Search Results */}
          {richContent?.search_results && richContent.search_results.length > 0 && (
            <Card variant="outlined" sx={{ mt: 1, mb: 1 }}>
              <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Email /> Email Results ({richContent.search_results.length})
                </Typography>
                <List dense>
                  {richContent.search_results.slice(0, expanded ? undefined : 2).map((email: EmailData) => (
                    <ListItem
                      key={email.id}
                      sx={{
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 0.5,
                        bgcolor: 'background.default'
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        <Email color={email.importance_score && email.importance_score > 0.8 ? 'error' : 'primary'} />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {email.subject}
                          </Typography>
                        }
                        secondary={
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              From: {email.sender} • {new Date(email.date).toLocaleDateString()}
                              {email.has_attachments && ' • 📎'}
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 0.5 }}>
                              {email.snippet}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
                {richContent.search_results.length > 2 && (
                  <Button
                    size="small"
                    onClick={() => setExpanded(!expanded)}
                    endIcon={expanded ? <ExpandLess /> : <ExpandMore />}
                  >
                    {expanded ? 'Show Less' : `Show ${richContent.search_results.length - 2} More`}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* Email References and Tasks */}
          {richContent && (richContent.email_references?.length > 0 || richContent.tasks_created?.length > 0) && (
            <EmailReferences
              emailReferences={richContent.email_references || []}
              tasksCreated={richContent.tasks_created || []}
              metadata={richContent.metadata}
            />
          )}

          {/* Suggested Actions */}
          {suggestedActions.length > 0 && !isUser && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                Suggested actions:
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {suggestedActions.map((action, index) => (
                  <Button
                    key={index}
                    variant="outlined"
                    size="small"
                    onClick={() => onActionClick?.(action)}
                    sx={{ fontSize: '0.7rem', height: 28 }}
                  >
                    {action}
                  </Button>
                ))}
              </Box>
            </Box>
          )}

          {/* Message Actions */}
          {!isUser && !isSystem && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' }}>
              <Tooltip title="Copy message">
                <IconButton size="small" onClick={handleCopyMessage}>
                  <ContentCopy fontSize="small" />
                </IconButton>
              </Tooltip>

              <Box sx={{ flexGrow: 1 }} />

              <Tooltip title="Good response">
                <IconButton
                  size="small"
                  onClick={() => handleFeedback('positive')}
                  color={feedbackGiven === 'positive' ? 'success' : 'default'}
                  disabled={!!feedbackGiven}
                >
                  <ThumbUp fontSize="small" />
                </IconButton>
              </Tooltip>

              <Tooltip title="Poor response">
                <IconButton
                  size="small"
                  onClick={() => handleFeedback('negative')}
                  color={feedbackGiven === 'negative' ? 'error' : 'default'}
                  disabled={!!feedbackGiven}
                >
                  <ThumbDown fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </Paper>
      </Box>
    </Fade>
  );
};

export default ChatMessage;