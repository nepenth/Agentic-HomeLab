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
    [key: string]: any;
  };
  suggestedActions?: string[];
  actionsPerformed?: Array<{ type: string; [key: string]: any }>;
  onActionClick?: (action: string) => void;
  onFeedback?: (messageId: string, type: 'positive' | 'negative') => void;
  onTaskComplete?: (taskId: string) => void;
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
  onTaskComplete
}) => {
  const [expanded, setExpanded] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);

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
          <Typography variant="body1" sx={{ mb: richContent || suggestedActions.length > 0 ? 1 : 0 }}>
            {content}
          </Typography>

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