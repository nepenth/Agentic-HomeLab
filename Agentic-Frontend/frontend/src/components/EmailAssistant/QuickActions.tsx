import React from 'react';
import {
  Box,
  Button,
  Chip,
  Paper,
  Typography,
  Grid,
  IconButton,
  Tooltip,
  Fade,
  Badge,
  Stack
} from '@mui/material';
import {
  Assignment,
  Search,
  PriorityHigh,
  Timeline,
  Email,
  Schedule,
  CheckCircle,
  Refresh,
  TrendingUp,
  Insights,
  FilterList,
  Add
} from '@mui/icons-material';

interface QuickAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  description?: string;
  badge?: number;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'default';
  category: 'tasks' | 'emails' | 'workflows' | 'insights';
}

interface QuickActionsProps {
  onActionClick: (actionId: string, message: string) => void;
  taskStats?: {
    pending: number;
    completed: number;
    overdue: number;
  };
  workflowStats?: {
    active: number;
    completed: number;
    failed: number;
  };
  disabled?: boolean;
  compact?: boolean;
}

const getColorValue = (color?: string) => {
  const colorMap: Record<string, string> = {
    primary: '#007AFF',
    secondary: '#5856D6',
    success: '#34C759',
    warning: '#FF9500',
    error: '#FF3B30',
    default: '#8E8E93'
  };
  return colorMap[color || 'default'] || colorMap.default;
};

const QuickActions: React.FC<QuickActionsProps> = ({
  onActionClick,
  taskStats,
  workflowStats,
  disabled = false,
  compact = false
}) => {
  const quickActions: QuickAction[] = [
    // Task Management
    {
      id: 'show_pending_tasks',
      label: 'Pending',
      icon: <Assignment />,
      description: 'Show all pending tasks from emails',
      badge: taskStats?.pending,
      color: taskStats?.pending && taskStats.pending > 0 ? 'warning' : 'default',
      category: 'tasks'
    },
    {
      id: 'show_completed_tasks',
      label: 'Completed',
      icon: <CheckCircle />,
      description: 'Show completed tasks',
      badge: taskStats?.completed,
      color: 'success',
      category: 'tasks'
    },
    {
      id: 'show_overdue_tasks',
      label: 'Overdue',
      icon: <Schedule />,
      description: 'Show overdue or urgent tasks',
      badge: taskStats?.overdue,
      color: taskStats?.overdue && taskStats.overdue > 0 ? 'error' : 'default',
      category: 'tasks'
    },

    // Email Search & Management
    {
      id: 'search_emails',
      label: 'Search',
      icon: <Search />,
      description: 'Search your inbox intelligently',
      category: 'emails'
    },
    {
      id: 'show_urgent_emails',
      label: 'Urgent',
      icon: <PriorityHigh />,
      description: 'Find urgent emails needing attention',
      color: 'error',
      category: 'emails'
    },
    {
      id: 'recent_emails',
      label: 'Recent',
      icon: <Email />,
      description: 'Show emails from today',
      category: 'emails'
    },

    // Workflow Status
    {
      id: 'workflow_status',
      label: 'Status',
      icon: <Timeline />,
      description: 'Check email workflow status',
      badge: workflowStats?.active,
      color: workflowStats?.active && workflowStats.active > 0 ? 'primary' : 'default',
      category: 'workflows'
    },
    {
      id: 'refresh_workflows',
      label: 'Refresh',
      icon: <Refresh />,
      description: 'Refresh workflow data',
      category: 'workflows'
    },

    // Analytics & Insights
    {
      id: 'show_analytics',
      label: 'Analytics',
      icon: <TrendingUp />,
      description: 'View email processing analytics',
      category: 'insights'
    },
    {
      id: 'show_insights',
      label: 'Insights',
      icon: <Insights />,
      description: 'Get email workflow insights',
      category: 'insights'
    }
  ];

  const getActionMessage = (actionId: string): string => {
    const messages: Record<string, string> = {
      show_pending_tasks: "Show me all my pending tasks from email workflows",
      show_completed_tasks: "Show me my completed tasks",
      show_overdue_tasks: "Show me overdue or urgent tasks that need attention",
      search_emails: "Help me search my emails",
      show_urgent_emails: "Find urgent emails that need my attention",
      recent_emails: "Show me emails from today",
      workflow_status: "What's the current status of my email workflows?",
      refresh_workflows: "Refresh and update my workflow data",
      show_analytics: "Show me email processing analytics and statistics",
      show_insights: "Give me insights about my email patterns and productivity"
    };

    return messages[actionId] || actionId.replace('_', ' ');
  };

  const getCategoryTitle = (category: string): string => {
    const titles: Record<string, string> = {
      tasks: "Tasks",
      emails: "Emails",
      workflows: "Workflows",
      insights: "Analytics"
    };
    return titles[category] || category;
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      tasks: '#1976d2',
      emails: '#388e3c',
      workflows: '#f57c00',
      insights: '#7b1fa2'
    };
    return colors[category] || '#666';
  };

  const groupedActions = quickActions.reduce((groups, action) => {
    const category = action.category;
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(action);
    return groups;
  }, {} as Record<string, QuickAction[]>);

  const handleActionClick = (action: QuickAction) => {
    if (disabled) return;
    onActionClick(action.id, getActionMessage(action.id));
  };

  if (compact) {
    // Compact view - show only high priority actions in a single row
    const priorityActions = quickActions.filter(action =>
      ['show_pending_tasks', 'search_emails', 'show_urgent_emails', 'workflow_status'].includes(action.id)
    );

    return (
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {priorityActions.map((action) => (
          <Tooltip key={action.id} title={action.description} placement="top">
            <Button
              variant="outlined"
              size="small"
              startIcon={action.badge ? (
                <Badge
                  badgeContent={action.badge}
                  sx={{
                    '& .MuiBadge-badge': {
                      backgroundColor: getColorValue(action.color),
                      color: 'white'
                    }
                  }}
                >
                  {action.icon}
                </Badge>
              ) : action.icon}
              onClick={() => handleActionClick(action)}
              disabled={disabled}
              sx={{ minWidth: 'auto' }}
            >
              {action.label}
            </Button>
          </Tooltip>
        ))}
      </Box>
    );
  }

  return (
    <Paper
      elevation={2}
      sx={{
        p: 2,
        bgcolor: 'background.paper',
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider'
      }}
    >
      <Typography
        variant="h6"
        sx={{
          mb: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          fontWeight: 600,
          color: 'text.primary',
          fontSize: '1rem'
        }}
      >
        <FilterList sx={{ color: '#007AFF', fontSize: '1.2rem' }} />
        Quick Actions
      </Typography>

      <Stack spacing={2}>
        {Object.entries(groupedActions).map(([category, actions]) => (
          <Box key={category}>
            {/* Category Header */}
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                mb: 1,
                color: getCategoryColor(category),
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                fontSize: '0.7rem'
              }}
            >
              {getCategoryTitle(category)}
            </Typography>

            {/* Action Buttons Grid */}
            <Grid container spacing={1}>
              {actions.map((action) => (
                <Grid item xs={6} key={action.id}>
                  <Tooltip title={action.description} placement="top">
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => handleActionClick(action)}
                      disabled={disabled}
                      sx={{
                        width: '100%',
                        minHeight: '48px',
                        p: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 0.5,
                        borderColor: `${getColorValue(action.color)}30`,
                        backgroundColor: `${getColorValue(action.color)}05`,
                        color: getColorValue(action.color),
                        '&:hover': {
                          transform: 'translateY(-1px)',
                          boxShadow: `0 2px 8px ${getColorValue(action.color)}20`,
                          backgroundColor: `${getColorValue(action.color)}10`,
                          borderColor: `${getColorValue(action.color)}50`
                        },
                        '&:disabled': {
                          backgroundColor: '#f5f5f5',
                          color: '#bbb'
                        },
                        transition: 'all 0.2s ease-in-out',
                        borderRadius: 1.5
                      }}
                    >
                      {/* Icon with Badge */}
                      <Box sx={{ position: 'relative' }}>
                        {action.badge ? (
                          <Badge
                            badgeContent={action.badge}
                            max={99}
                            sx={{
                              '& .MuiBadge-badge': {
                                backgroundColor: getColorValue(action.color),
                                color: 'white',
                                fontSize: '0.6rem',
                                minWidth: '14px',
                                height: '14px'
                              }
                            }}
                          >
                            {React.cloneElement(action.icon as React.ReactElement, {
                              sx: { fontSize: '1.1rem' }
                            })}
                          </Badge>
                        ) : (
                          React.cloneElement(action.icon as React.ReactElement, {
                            sx: { fontSize: '1.1rem' }
                          })
                        )}
                      </Box>

                      {/* Label */}
                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 500,
                          lineHeight: 1,
                          fontSize: '0.7rem',
                          textAlign: 'center'
                        }}
                      >
                        {action.label}
                      </Typography>
                    </Button>
                  </Tooltip>
                </Grid>
              ))}
            </Grid>
          </Box>
        ))}
      </Stack>

      {/* Custom Action */}
      <Box sx={{ mt: 2, pt: 1.5, borderTop: 1, borderColor: 'divider' }}>
        <Tooltip title="Ask anything else about your emails" placement="top">
          <Button
            variant="text"
            size="small"
            startIcon={<Add />}
            onClick={() => onActionClick('custom', 'How can I help you today?')}
            disabled={disabled}
            sx={{
              fontSize: '0.75rem',
              color: 'text.secondary',
              '&:hover': {
                backgroundColor: '#f5f5f5'
              }
            }}
            fullWidth
          >
            Ask something else...
          </Button>
        </Tooltip>
      </Box>
    </Paper>
  );
};

export default QuickActions;