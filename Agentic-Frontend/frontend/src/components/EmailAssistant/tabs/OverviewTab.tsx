import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  Divider,
  List,
  ListItem,
  Chip,
  LinearProgress,
  CircularProgress,
  useTheme,
  alpha,
  Card,
  CardContent,
} from '@mui/material';
import {
  Email as EmailIcon,
  Task as TaskIcon,
  Sync as SyncIcon,
  Search as SearchIcon,
  ChatBubble as ChatIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useEmail } from '../../../hooks/useEmail';
import { useTasks } from '../../../hooks/useTasks';
import { StatCard } from '../../common/StatCard';
import { ActivityFeedItem } from '../../common/ActivityFeedItem';
import { getDashboardMetrics, getRecentActivity, getAIInsights } from '../../../services/emailApi';
import { QuickChat } from './QuickChat';
import { SyncControl } from '../SyncControl';
import apiClient from '../../../services/api';

interface OverviewTabProps {
  onNavigate?: (tab: string, options?: any) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ onNavigate }) => {
  const theme = useTheme();
  const { accounts, syncEmails, isSyncing } = useEmail();
  const { tasks } = useTasks();

  // Fetch dashboard metrics (includes embedding stats)
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: getDashboardMetrics,
    refetchInterval: 30000,
  });

  // Fetch recent activity
  const { data: activities, isLoading: activitiesLoading } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => getRecentActivity(10),
    refetchInterval: 30000,
  });

  // Fetch AI insights
  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ['ai-insights'],
    queryFn: getAIInsights,
    refetchInterval: 60000,
  });

  const handleSyncAll = () => {
    syncEmails(accounts.map(a => a.account_id));
  };

  const quickActions = [
    {
      icon: <SearchIcon />,
      label: 'Semantic Search',
      onClick: () => onNavigate?.('inbox'),
      color: 'primary',
    },
    {
      icon: <EmailIcon />,
      label: 'View Inbox',
      onClick: () => onNavigate?.('inbox'),
      color: 'secondary',
    },
    {
      icon: <TaskIcon />,
      label: 'Manage Tasks',
      onClick: () => onNavigate?.('inbox'),
      color: 'warning',
    },
    {
      icon: <ChatIcon />,
      label: 'AI Assistant',
      onClick: () => onNavigate?.('assistant'),
      color: 'info',
    },
    {
      icon: <SyncIcon />,
      label: 'Sync Emails',
      onClick: handleSyncAll,
      color: 'success',
    },
    {
      icon: <SettingsIcon />,
      label: 'Settings',
      onClick: () => onNavigate?.('settings'),
      color: 'default',
    },
  ];

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Main 3-column layout with equal height columns */}
      <Box sx={{ flex: 1, display: 'flex', gap: 3, overflow: 'auto', minHeight: 0 }}>
        {/* Left Column - Fixed content */}
        <Box sx={{ width: '20%', minWidth: 250, display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Email Accounts Widget */}
          <Paper sx={{ p: 2, flexShrink: 0 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Email Accounts
              </Typography>
              <List sx={{ p: 0 }}>
                {accounts.map((account) => (
                  <ListItem
                    key={account.account_id}
                    sx={{
                      px: 0,
                      py: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'stretch',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {account.display_name}
                      </Typography>
                      <Chip
                        label={account.sync_status}
                        size="small"
                        color={
                          account.sync_status === 'active' ? 'success' :
                          account.sync_status === 'error' ? 'error' : 'default'
                        }
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                    </Box>
                    <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                      {account.email_address}
                    </Typography>
                    <Typography variant="caption" sx={{ color: theme.palette.text.secondary, mt: 0.5 }}>
                      {account.total_emails_synced} emails synced
                    </Typography>
                    {account.last_sync_at && (
                      <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                        Last sync: {new Date(account.last_sync_at).toLocaleString()}
                      </Typography>
                    )}
                  </ListItem>
                ))}
              </List>

              {/* Replace old button with new SyncControl component */}
              <Box sx={{ mt: 2 }}>
                <SyncControl accountIds={accounts.map(a => a.account_id)} />
              </Box>
            </Paper>

          {/* Quick Actions */}
          <Paper sx={{ p: 2, flexShrink: 0 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Quick Actions
              </Typography>
              <Grid container spacing={1}>
                {quickActions.map((action, index) => (
                  <Grid item xs={6} key={index}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={action.icon}
                      onClick={action.onClick}
                      sx={{
                        flexDirection: 'column',
                        gap: 0.5,
                        py: 1.5,
                        fontSize: '0.75rem',
                      }}
                    >
                      {action.label}
                    </Button>
                  </Grid>
                ))}
              </Grid>
          </Paper>
        </Box>

        {/* Center Column - Flexible content */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
          {/* System Status Banner */}
          {metrics?.sync_status && (
            <Card
              sx={{
                flexShrink: 0,
                bgcolor: alpha(theme.palette.success.main, 0.1),
                border: `1px solid ${theme.palette.success.main}`,
              }}
            >
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CheckCircleIcon sx={{ color: theme.palette.success.main }} />
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    All Systems Operational
                  </Typography>
                  <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                    {metrics.sync_status.active_accounts} active accounts • Last sync:{' '}
                    {metrics.sync_status.last_sync
                      ? new Date(metrics.sync_status.last_sync).toLocaleTimeString()
                      : 'Never'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Key Metrics */}
          <Grid container spacing={2} sx={{ flexShrink: 0 }}>
            <Grid item xs={6} md={4}>
              <StatCard
                title="Total Emails"
                value={metrics?.total_emails || 0}
                icon={<EmailIcon />}
                color="primary"
                loading={metricsLoading}
                onClick={() => onNavigate?.('inbox', { filter: 'all', view: 'emails' })}
              />
            </Grid>
            <Grid item xs={6} md={4}>
              <Paper
                sx={{
                  p: 2,
                  height: '100%',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  border: `1px solid ${theme.palette.divider}`,
                  '&:hover': {
                    boxShadow: 3,
                    borderColor: theme.palette.info.main,
                  },
                }}
                onClick={() => onNavigate?.('settings')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <SearchIcon sx={{ color: theme.palette.info.main, mr: 1 }} />
                    <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', color: 'text.secondary' }}>
                      Embeddings
                    </Typography>
                  </Box>
                  {/* Status indicator */}
                  {metrics?.embedding_stats?.is_generating && (
                    <CircularProgress size={14} thickness={5} sx={{ color: theme.palette.success.main }} />
                  )}
                </Box>
                {metricsLoading ? (
                  <CircularProgress size={20} />
                ) : metrics?.embedding_stats ? (
                  <>
                    <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 1 }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: theme.palette.info.main }}>
                        {metrics.embedding_stats.coverage_percent}%
                      </Typography>
                      <Typography variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                        coverage
                      </Typography>
                    </Box>
                    <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 0.5 }}>
                      {metrics.embedding_stats.emails_with_embeddings} / {metrics.embedding_stats.total_emails} emails
                    </Typography>

                    {/* Status chip with dynamic color and message */}
                    {metrics.embedding_stats.status_message && (
                      <Chip
                        label={metrics.embedding_stats.status_message}
                        size="small"
                        icon={metrics.embedding_stats.is_generating ? <CircularProgress size={12} sx={{ color: 'inherit !important' }} /> : undefined}
                        color={
                          metrics.embedding_stats.status === 'generating' ? 'success' :
                          metrics.embedding_stats.status === 'pending' ? 'warning' :
                          'default'
                        }
                        sx={{
                          height: 20,
                          fontSize: '0.65rem',
                          mt: 0.5,
                          '& .MuiChip-icon': {
                            marginLeft: '4px'
                          }
                        }}
                      />
                    )}

                    {/* Progress bar for active generation */}
                    {metrics.embedding_stats.is_generating && (
                      <Box sx={{ mt: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={metrics.embedding_stats.coverage_percent}
                          sx={{
                            height: 4,
                            borderRadius: 2,
                            backgroundColor: alpha(theme.palette.success.main, 0.1),
                            '& .MuiLinearProgress-bar': {
                              backgroundColor: theme.palette.success.main
                            }
                          }}
                        />
                      </Box>
                    )}
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Loading...
                  </Typography>
                )}
              </Paper>
            </Grid>
            <Grid item xs={6} md={4}>
              <StatCard
                title="Unread"
                value={metrics?.unread_emails || 0}
                subtitle="Needs attention"
                icon={<EmailIcon />}
                color="warning"
                loading={metricsLoading}
                onClick={() => onNavigate?.('inbox', { filter: 'unread', view: 'emails' })}
              />
            </Grid>
            <Grid item xs={6} md={4}>
              <StatCard
                title="Pending Tasks"
                value={metrics?.pending_tasks || 0}
                subtitle="Active items"
                icon={<TaskIcon />}
                color="secondary"
                loading={metricsLoading}
                onClick={() => onNavigate?.('inbox', { filter: 'pending_tasks', view: 'tasks' })}
              />
            </Grid>
            <Grid item xs={6} md={4}>
              <StatCard
                title="High Priority"
                value={metrics?.high_priority_tasks || 0}
                subtitle="Urgent tasks"
                icon={<WarningIcon />}
                color="error"
                loading={metricsLoading}
                onClick={() => onNavigate?.('inbox', { filter: 'high_priority', view: 'emails' })}
              />
            </Grid>
            <Grid item xs={6} md={4}>
              <StatCard
                title="Today"
                value={metrics?.emails_today || 0}
                subtitle="New emails"
                icon={<TrendingUpIcon />}
                color="info"
                loading={metricsLoading}
                onClick={() => onNavigate?.('inbox', { filter: 'today', view: 'emails' })}
              />
            </Grid>
            <Grid item xs={6} md={4}>
              <StatCard
                title="Completed"
                value={metrics?.tasks_completed_today || 0}
                subtitle="Tasks today"
                icon={<CheckCircleIcon />}
                color="success"
                loading={metricsLoading}
                onClick={() => onNavigate?.('inbox', { filter: 'completed', view: 'tasks' })}
              />
            </Grid>
          </Grid>

          {/* Recent Activity - Fills remaining space */}
          <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Recent Activity
              </Typography>
              <Button size="small" onClick={() => onNavigate?.('inbox')}>
                View All
              </Button>
            </Box>
            {activitiesLoading ? (
              <Box sx={{ py: 4 }}>
                <LinearProgress />
              </Box>
            ) : activities && activities.length > 0 ? (
              <List sx={{ p: 0, flex: 1, overflow: 'auto' }}>
                {activities.map((activity, index) => (
                  <React.Fragment key={activity.id}>
                    <ActivityFeedItem
                      type={activity.type}
                      title={activity.title}
                      description={activity.description}
                      timestamp={activity.timestamp}
                      status={activity.status}
                      metadata={activity.metadata}
                    />
                    {index < activities.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Typography variant="body2" sx={{ color: theme.palette.text.secondary, py: 2, textAlign: 'center' }}>
                No recent activity
              </Typography>
            )}
          </Paper>
        </Box>

        {/* Right Column - Two equal-height widgets */}
        <Box sx={{ width: '20%', minWidth: 250, display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* AI-Powered Insights - Takes 50% of column height */}
          <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, flexShrink: 0 }}>
              AI Insights
            </Typography>
            <Box sx={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
              {insightsLoading ? (
                <LinearProgress />
              ) : insights && insights.length > 0 ? (
                <List sx={{ p: 0 }}>
                {insights.map((insight, index) => (
                  <React.Fragment key={insight.id}>
                    <ListItem sx={{ px: 0, py: 2, flexDirection: 'column', alignItems: 'stretch' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Chip
                          label={insight.type.toUpperCase()}
                          size="small"
                          color={
                            insight.type === 'alert' ? 'error' :
                            insight.type === 'suggestion' ? 'info' :
                            'default'
                          }
                          sx={{ height: 20, fontSize: '0.7rem' }}
                        />
                        <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                          {Math.round(insight.confidence * 100)}% confident
                        </Typography>
                      </Box>
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                        {insight.title}
                      </Typography>
                      <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                        {insight.description}
                      </Typography>
                    </ListItem>
                    {index < insights.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
                </List>
              ) : (
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary, textAlign: 'center', py: 2 }}>
                  No insights available
                </Typography>
              )}
            </Box>
          </Paper>

          {/* Pending Actions - Takes 50% of column height */}
          <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, flexShrink: 0 }}>
              Pending Actions
            </Typography>
            <Box sx={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
              {tasks.filter(t => t.status === 'pending' || t.status === 'in_progress').length > 0 ? (
                <List sx={{ p: 0 }}>
                  {tasks
                    .filter(t => t.status === 'pending' || t.status === 'in_progress')
                    .slice(0, 5)
                    .map((task, index) => (
                      <React.Fragment key={task.id}>
                        <ListItem sx={{ px: 0, py: 1.5, flexDirection: 'column', alignItems: 'stretch' }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {task.title}
                            </Typography>
                            <Chip
                              label={task.priority}
                              size="small"
                              color={
                                task.priority === 'high' ? 'error' :
                                task.priority === 'medium' ? 'warning' :
                                'default'
                              }
                              sx={{ height: 18, fontSize: '0.65rem' }}
                            />
                          </Box>
                          <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                            {task.description}
                          </Typography>
                          {task.due_date && (
                            <Typography variant="caption" sx={{ color: theme.palette.text.secondary, mt: 0.5 }}>
                              Due: {new Date(task.due_date).toLocaleDateString()}
                            </Typography>
                          )}
                        </ListItem>
                        {index < 4 && <Divider />}
                      </React.Fragment>
                    ))}
                </List>
              ) : (
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary, textAlign: 'center', py: 2 }}>
                  No pending actions
                </Typography>
              )}
            </Box>
            <Button
              variant="outlined"
              fullWidth
              sx={{ mt: 2, flexShrink: 0 }}
              onClick={() => onNavigate?.('inbox')}
            >
              View All Tasks
            </Button>
          </Paper>
        </Box>
      </Box>

      {/* Quick Chat - Full Width Below All Columns */}
      <Box sx={{ flexShrink: 0, mt: 3 }}>
        <QuickChat />
      </Box>

      {/* Add spinning animation for sync icon */}
      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          .spinning {
            animation: spin 1s linear infinite;
          }
        `}
      </style>
    </Box>
  );
};

export default OverviewTab;
