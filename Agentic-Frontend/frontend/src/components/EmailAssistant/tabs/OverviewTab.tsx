import React, { useState } from 'react';
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
  Stack,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Email as EmailIcon,
  Task as TaskIcon,
  Sync as SyncIcon,
  Search as SearchIcon,
  ChatBubble as ChatIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  AutoAwesome as AutoAwesomeIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useEmail } from '../../../hooks/useEmail';
import { useTasks } from '../../../hooks/useTasks';
import { StatCard } from '../../common/StatCard';
import { getDashboardMetrics, getAIInsights, AIInsight } from '../../../services/emailApi';
import { QuickChat } from './QuickChat';

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
    refetchInterval: 5000, // Poll more frequently for real-time status
  });

  // Fetch AI insights
  const { data: insights, isLoading: insightsLoading } = useQuery<AIInsight[]>({
    queryKey: ['ai-insights'],
    queryFn: () => getAIInsights(),
    refetchInterval: 60000,
  });

  const handleSyncAll = () => {
    syncEmails({ accountIds: accounts.map(a => a.account_id) });
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
      icon: <SettingsIcon />,
      label: 'Settings',
      onClick: () => onNavigate?.('settings'),
      color: 'inherit',
    },
  ];

  // Helper to format duration
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', gap: 3 }}>

      {/* Top Row: Key Metrics */}
      <Grid container spacing={2} sx={{ flexShrink: 0 }}>
        <Grid item xs={6} md={2}>
          <StatCard
            title="Total Emails"
            value={metrics?.total_emails || 0}
            icon={<EmailIcon />}
            color="primary"
            loading={metricsLoading}
            onClick={() => onNavigate?.('inbox', { filter: 'all', view: 'emails' })}
          />
        </Grid>
        <Grid item xs={6} md={2}>
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
        <Grid item xs={6} md={2}>
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
        <Grid item xs={6} md={2}>
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
        <Grid item xs={6} md={2}>
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
        <Grid item xs={6} md={2}>
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

      {/* Main Content Area - 2 Column Layout */}
      <Box sx={{ flex: 1, display: 'flex', gap: 3, minHeight: 0, overflow: 'hidden' }}>

        {/* Left Column: Sync & Accounts */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3, overflow: 'hidden' }}>

          {/* Sync Status Widget - Takes available space */}
          <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexShrink: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SyncIcon color="primary" />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Sync Status
                </Typography>
              </Box>
              <Button
                variant="contained"
                size="small"
                startIcon={isSyncing ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon />}
                onClick={handleSyncAll}
                disabled={isSyncing}
              >
                {isSyncing ? 'Syncing...' : 'Sync All'}
              </Button>
            </Box>

            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {/* Active Syncs Details */}
              {metrics?.sync_status?.active_sync_details && metrics.sync_status.active_sync_details.length > 0 ? (
                <Stack spacing={2} sx={{ mb: 3 }}>
                  {metrics.sync_status.active_sync_details.map((sync, index) => {
                    const account = accounts.find(a => a.account_id === sync.account_id);
                    return (
                      <Card key={index} variant="outlined" sx={{ bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
                        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="subtitle2" fontWeight="bold">
                              Syncing {account?.display_name || 'Account'}...
                            </Typography>
                            <Chip label="Running" size="small" color="primary" sx={{ height: 20, fontSize: '0.7rem' }} />
                          </Box>
                          <LinearProgress sx={{ mb: 1, height: 6, borderRadius: 3 }} />
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="caption" color="text.secondary">
                              Duration: {formatDuration(sync.duration_seconds)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {sync.emails_processed} processed • {sync.emails_added} new
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    );
                  })}
                </Stack>
              ) : (
                <Card variant="outlined" sx={{ mb: 3, bgcolor: alpha(theme.palette.success.main, 0.05), borderColor: alpha(theme.palette.success.main, 0.3) }}>
                  <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 }, display: 'flex', alignItems: 'center', gap: 2 }}>
                    <CheckCircleIcon color="success" />
                    <Box>
                      <Typography variant="subtitle2" fontWeight="bold">All Systems Operational</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Last sync: {metrics?.sync_status?.last_sync ? new Date(metrics.sync_status.last_sync).toLocaleTimeString() : 'Never'}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              )}

              <Divider sx={{ my: 2 }} />

              {/* Account List */}
              <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Connected Accounts
              </Typography>
              <List disablePadding>
                {accounts.map((account) => (
                  <ListItem
                    key={account.account_id}
                    sx={{
                      px: 0,
                      py: 1,
                      display: 'flex',
                      justifyContent: 'space-between',
                      borderBottom: `1px solid ${theme.palette.divider}`,
                      '&:last-child': { borderBottom: 'none' }
                    }}
                  >
                    <Box>
                      <Typography variant="body2" fontWeight={600}>{account.display_name}</Typography>
                      <Typography variant="caption" color="text.secondary">{account.email_address}</Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Chip
                        label={account.sync_status}
                        size="small"
                        color={account.sync_status === 'active' ? 'success' : account.sync_status === 'error' ? 'error' : 'default'}
                        sx={{ height: 20, fontSize: '0.7rem', mb: 0.5 }}
                      />
                      <Typography variant="caption" display="block" color="text.secondary">
                        {account.total_emails_synced.toLocaleString()} emails
                      </Typography>
                    </Box>
                  </ListItem>
                ))}
              </List>
            </Box>
          </Paper>

          {/* Quick Actions Grid - Fixed at bottom */}
          <Paper sx={{ p: 2, flexShrink: 0 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              Quick Actions
            </Typography>
            <Grid container spacing={2}>
              {quickActions.map((action, index) => (
                <Grid item xs={6} sm={4} key={index}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={action.icon}
                    onClick={action.onClick}
                    color={action.color as any}
                    sx={{
                      justifyContent: 'flex-start',
                      py: 1.5,
                      px: 2,
                      textAlign: 'left'
                    }}
                  >
                    {action.label}
                  </Button>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Box>

        {/* Right Column: Intelligence & Tasks */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3, overflow: 'hidden' }}>

          {/* Embedding Status Widget */}
          <Paper sx={{ p: 2, flexShrink: 0 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <MemoryIcon color="info" />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Semantic Embeddings
                </Typography>
              </Box>
              {metrics?.embedding_stats?.is_generating && (
                <Chip label="Processing" color="info" size="small" icon={<CircularProgress size={12} color="inherit" />} />
              )}
            </Box>

            {metrics?.embedding_stats ? (
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', mb: 1 }}>
                  <Box>
                    <Typography variant="h4" color="info.main" fontWeight={700}>
                      {metrics.embedding_stats.coverage_percent}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Coverage</Typography>
                  </Box>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="body2" fontWeight={600}>
                      {metrics.embedding_stats.emails_with_embeddings.toLocaleString()} / {metrics.embedding_stats.total_emails.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Emails Embedded</Typography>
                  </Box>
                </Box>

                <LinearProgress
                  variant="determinate"
                  value={metrics.embedding_stats.coverage_percent}
                  sx={{ height: 8, borderRadius: 4, mb: 2, bgcolor: alpha(theme.palette.info.main, 0.1) }}
                />

                {metrics.embedding_stats.is_generating ? (
                  <Card variant="outlined" sx={{ bgcolor: alpha(theme.palette.info.main, 0.05), borderColor: alpha(theme.palette.info.main, 0.3) }}>
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <SpeedIcon color="info" />
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {metrics.embedding_stats.status_message}
                          </Typography>
                          {metrics.embedding_stats.estimated_time_remaining && (
                            <Typography variant="caption" color="text.secondary">
                              Est. time remaining: {metrics.embedding_stats.estimated_time_remaining}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                ) : metrics.embedding_stats.pending_embeddings > 0 ? (
                  <Card variant="outlined" sx={{ bgcolor: alpha(theme.palette.warning.main, 0.05), borderColor: alpha(theme.palette.warning.main, 0.3) }}>
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 }, display: 'flex', gap: 2, alignItems: 'center' }}>
                      <WarningIcon color="warning" />
                      <Box>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {metrics.embedding_stats.pending_embeddings} emails pending
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Scheduled for next processing cycle
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CheckCircleIcon fontSize="small" color="success" /> All emails indexed and ready for semantic search.
                  </Typography>
                )}
              </Box>
            ) : (
              <LinearProgress />
            )}
          </Paper>

          {/* AI Insights & Tasks */}
          <Paper sx={{ p: 2, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, flexShrink: 0 }}>
              AI Insights & Pending Actions
            </Typography>

            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {/* Insights Section */}
              {insights && insights.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem' }}>
                    Insights
                  </Typography>
                  <List disablePadding>
                    {insights.map((insight) => (
                      <ListItem key={insight.id} sx={{ px: 0, py: 1.5, borderBottom: `1px solid ${theme.palette.divider}` }}>
                        <Box sx={{ display: 'flex', gap: 2 }}>
                          <AutoAwesomeIcon color="primary" sx={{ mt: 0.5 }} />
                          <Box>
                            <Typography variant="subtitle2" fontWeight={600}>{insight.title}</Typography>
                            <Typography variant="body2" color="text.secondary">{insight.description}</Typography>
                          </Box>
                        </Box>
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {/* Tasks Section */}
              <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem' }}>
                Top Priority Tasks
              </Typography>
              {tasks.filter(t => t.status === 'pending' || t.status === 'in_progress').length > 0 ? (
                <List disablePadding>
                  {tasks
                    .filter(t => t.status === 'pending' || t.status === 'in_progress')
                    .sort((a, b) => (a.priority === 'high' ? -1 : 1))
                    .slice(0, 5)
                    .map((task) => (
                      <ListItem key={task.id} sx={{ px: 0, py: 1.5, borderBottom: `1px solid ${theme.palette.divider}` }}>
                        <Box sx={{ width: '100%' }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="subtitle2" fontWeight={600}>{task.title}</Typography>
                            <Chip
                              label={task.priority}
                              size="small"
                              color={task.priority === 'high' ? 'error' : 'warning'}
                              sx={{ height: 20, fontSize: '0.65rem' }}
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary" noWrap>{task.description}</Typography>
                        </Box>
                      </ListItem>
                    ))}
                </List>
              ) : (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <CheckCircleIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
                  <Typography variant="body2" color="text.secondary">No pending tasks</Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Box>
      </Box>

      {/* Footer: Quick Chat */}
      <Box sx={{ flexShrink: 0 }}>
        <QuickChat />
      </Box>
    </Box>
  );
};

export default OverviewTab;
