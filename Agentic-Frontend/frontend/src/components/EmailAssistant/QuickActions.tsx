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
  Badge
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
      label: 'Pending Tasks',
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
      label: 'Search Emails',
      icon: <Search />,
      description: 'Search your inbox intelligently',
      category: 'emails'
    },
    {
      id: 'show_urgent_emails',
      label: 'Urgent Emails',
      icon: <PriorityHigh />,
      description: 'Find urgent emails needing attention',
      color: 'error',
      category: 'emails'
    },
    {
      id: 'recent_emails',
      label: 'Recent Emails',
      icon: <Email />,
      description: 'Show emails from today',
      category: 'emails'
    },

    // Workflow Status
    {
      id: 'workflow_status',
      label: 'Workflow Status',
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
      tasks: "Task Management",
      emails: "Email Operations",
      workflows: "Workflow Control",
      insights: "Analytics & Insights"
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
          <Button
            key={action.id}
            variant="outlined"
            size="small"
            startIcon={action.badge ? (
              <Badge badgeContent={action.badge} color={action.color}>
                {action.icon}
              </Badge>
            ) : action.icon}
            onClick={() => handleActionClick(action)}
            disabled={disabled}
            sx={{ minWidth: 'auto' }}
          >
            {action.label}
          </Button>
        ))}
      </Box>
    );
  }

  return (
    <Paper elevation={1} sx={{ p: 2, bgcolor: 'background.paper' }}>
      <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <FilterList />
        Quick Actions
      </Typography>

      <Grid container spacing={2}>
        {Object.entries(groupedActions).map(([category, actions]) => (
          <Grid item xs={12} sm={6} md={3} key={category}>
            <Box>
              <Typography
                variant="subtitle2"
                sx={{
                  mb: 1,
                  color: getCategoryColor(category),
                  fontWeight: 600,
                  fontSize: '0.9rem'
                }}
              >
                {getCategoryTitle(category)}
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {actions.map((action) => (
                  <Fade key={action.id} in={true} timeout={300}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={
                        action.badge ? (
                          <Badge
                            badgeContent={action.badge}
                            color={action.color}
                            max={99}
                          >
                            {action.icon}
                          </Badge>
                        ) : action.icon
                      }
                      onClick={() => handleActionClick(action)}
                      disabled={disabled}
                      color={action.color}
                      sx={{
                        justifyContent: 'flex-start',
                        textAlign: 'left',
                        py: 1,
                        '&:hover': {
                          transform: 'translateY(-1px)',
                          boxShadow: 2
                        },
                        transition: 'all 0.2s ease-in-out'
                      }}
                      fullWidth
                    >
                      <Box sx={{ flexGrow: 1, textAlign: 'left' }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {action.label}
                        </Typography>
                        {action.description && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            {action.description}
                          </Typography>
                        )}
                      </Box>
                    </Button>
                  </Fade>
                ))}
              </Box>
            </Box>
          </Grid>
        ))}
      </Grid>

      {/* Custom Action */}
      <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
        <Button
          variant="text"
          size="small"
          startIcon={<Add />}
          onClick={() => onActionClick('custom', 'How can I help you today?')}
          disabled={disabled}
          sx={{ fontSize: '0.8rem' }}
        >
          Ask something else...
        </Button>
      </Box>
    </Paper>
  );
};

export default QuickActions;