import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Divider,
  Chip,
  Tabs,
  Tab,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Snackbar,
  CircularProgress,
  LinearProgress,
  Badge,
  Avatar,
  Tooltip,
  Fab,
  Paper,
  InputAdornment,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Email,
  Send,
  Drafts,
  Archive,
  Star,
  PlayArrow,
  Pause,
  Stop,
  Search,
  FilterList,
  Settings,
  Analytics,
  Chat,
  Notifications,
  Refresh,
  Add,
  CheckCircle,
  Error,
  Warning,
  Info,
  Schedule,
  PriorityHigh,
  LowPriority,
  TrendingUp,
  GetApp,
  Save,
  Bookmark,
  Folder,
  Attachment,
  Security,
  Timeline,
  Assessment,
  Build,
  Rule,
  DateRange,
  AccessTime,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { apiClient } from '../../services/api';
import webSocketService from '../../services/websocket';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`email-assistant-tabpanel-${index}`}
      aria-labelledby={`email-assistant-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const EmailAssistant: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);

  // UI State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [startWorkflowDialog, setStartWorkflowDialog] = useState(false);
  const [chatDialog, setChatDialog] = useState(false);
  const [searchDialog, setSearchDialog] = useState(false);
  const [followupDialog, setFollowupDialog] = useState(false);
  const [exportDialog, setExportDialog] = useState(false);
  const [notificationSettingsDialog, setNotificationSettingsDialog] = useState(false);
  const [savedSearchesDialog, setSavedSearchesDialog] = useState(false);
  const [settingsDialog, setSettingsDialog] = useState(false);
  const [taskTemplatesDialog, setTaskTemplatesDialog] = useState(false);
  const [processingRulesDialog, setProcessingRulesDialog] = useState(false);

  // Form State
  const [workflowForm, setWorkflowForm] = useState({
    server: 'imap.gmail.com',
    port: 993,
    username: '',
    password: '',
    mailbox: 'INBOX',
    use_ssl: true,
    max_emails: 100,
    unread_only: false,
    importance_threshold: 0.7,
    spam_threshold: 0.8,
    create_tasks: true,
    schedule_followups: true,
  });

  const [searchForm, setSearchForm] = useState({
    query: '',
    search_type: 'semantic' as 'semantic' | 'keyword' | 'hybrid',
    date_from: null as string | null,
    date_to: null as string | null,
    sender: '',
    categories: [] as string[],
    min_importance: 0,
    has_attachments: false,
    limit: 20,
  });

  const [chatForm, setChatForm] = useState({
    message: '',
    session_id: '',
    context: {
      timezone: 'America/New_York',
      preferred_format: 'detailed',
      include_threads: true,
      max_results: 10,
    },
  });

  // Follow-up scheduling form
  const [followupForm, setFollowupForm] = useState({
    taskId: '',
    followup_date: '',
    followup_time: '',
    followup_notes: '',
  });

  // Export form
  const [exportForm, setExportForm] = useState({
    format: 'csv',
    data_type: 'dashboard_stats',
    date_range: {
      start: '',
      end: '',
    },
    include_charts: true,
  });

  // Notification settings form
  const [notificationSettings, setNotificationSettings] = useState({
    email_notifications: true,
    push_notifications: true,
    notification_types: ['task_created', 'workflow_completed', 'error_alerts'],
  });

  // Saved searches
  const [savedSearches, setSavedSearches] = useState<any[]>([]);
  const [currentSavedSearch, setCurrentSavedSearch] = useState<any>(null);

  // Settings and templates
  const [emailSettings, setEmailSettings] = useState<any>(null);
  const [taskTemplates, setTaskTemplates] = useState<any[]>([]);
  const [processingRules, setProcessingRules] = useState<any[]>([]);

  // Selected items for dialogs
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);

  // WebSocket for real-time updates
  const [wsConnected, setWsConnected] = useState(false);

  // Load initial data
  useEffect(() => {
    loadDashboardData();
    loadWorkflows();
    loadTasks();
    loadNotifications();

    // Connect to WebSocket for real-time updates
    const token = apiClient.getAuthToken();
    webSocketService.connect('email/progress', token || undefined);

    // Set up message handlers
    webSocketService.on('workflow_progress', updateWorkflowProgress);
    webSocketService.on('task_update', updateTaskStatus);
    webSocketService.on('notification', addNotification);

    // Connection status monitoring
    webSocketService.onConnectionStatus((status) => {
      setWsConnected(status === 'connected');
    });

    return () => {
      webSocketService.off('workflow_progress', updateWorkflowProgress);
      webSocketService.off('task_update', updateTaskStatus);
      webSocketService.off('notification', addNotification);
      webSocketService.disconnect();
    };
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [stats, analyticsData] = await Promise.all([
        apiClient.getEmailDashboardStats(),
        apiClient.getEmailAnalyticsOverview(),
      ]);
      setDashboardStats(stats);
      setAnalytics(analyticsData);
    } catch (err: any) {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const loadWorkflows = async () => {
    try {
      const data = await apiClient.getEmailWorkflowHistory({ limit: 20 });
      setWorkflows(data.workflows || []);
    } catch (err: any) {
      console.error('Failed to load workflows:', err);
    }
  };

  const loadTasks = async () => {
    try {
      const data = await apiClient.getEmailTasks({ limit: 20 });
      setTasks(data.tasks || []);
    } catch (err: any) {
      console.error('Failed to load tasks:', err);
    }
  };

  const loadNotifications = async () => {
    try {
      const data = await apiClient.getEmailNotifications({ limit: 10 });
      setNotifications(data.notifications || []);
    } catch (err: any) {
      console.error('Failed to load notifications:', err);
    }
  };

  const updateWorkflowProgress = (progressData: any) => {
    setWorkflows(prev =>
      prev.map(wf =>
        wf.id === progressData.workflow_id
          ? { ...wf, ...progressData }
          : wf
      )
    );
  };

  const updateTaskStatus = (taskData: any) => {
    setTasks(prev =>
      prev.map(task =>
        task.id === taskData.task_id
          ? { ...task, ...taskData }
          : task
      )
    );
  };

  const addNotification = (notification: any) => {
    setNotifications(prev => [notification, ...prev.slice(0, 9)]);
  };

  const handleStartWorkflow = async () => {
    try {
      setLoading(true);
      const result = await apiClient.startEmailWorkflow({
        mailbox_config: {
          server: workflowForm.server,
          port: workflowForm.port,
          username: workflowForm.username,
          password: workflowForm.password,
          mailbox: workflowForm.mailbox,
          use_ssl: workflowForm.use_ssl,
        },
        processing_options: {
          max_emails: workflowForm.max_emails,
          unread_only: workflowForm.unread_only,
          importance_threshold: workflowForm.importance_threshold,
          spam_threshold: workflowForm.spam_threshold,
          create_tasks: workflowForm.create_tasks,
          schedule_followups: workflowForm.schedule_followups,
        },
      });

      setSuccess('Email workflow started successfully!');
      setStartWorkflowDialog(false);
      loadWorkflows();
    } catch (err: any) {
      setError('Failed to start workflow');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelWorkflow = async (workflowId: string) => {
    try {
      await apiClient.cancelEmailWorkflow(workflowId);
      setSuccess('Workflow cancelled successfully');
      loadWorkflows();
    } catch (err: any) {
      setError('Failed to cancel workflow');
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    try {
      await apiClient.completeEmailTask(taskId);
      setSuccess('Task completed successfully');
      loadTasks();
    } catch (err: any) {
      setError('Failed to complete task');
    }
  };

  const handleSearchEmails = async () => {
    try {
      setLoading(true);
      const results = await apiClient.searchEmails(searchForm);
      setSearchResults(results.results || []);
      setSearchDialog(true);
    } catch (err: any) {
      setError('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSendChatMessage = async () => {
    if (!chatForm.message.trim()) return;

    try {
      const response = await apiClient.sendEmailChatMessage(chatForm);
      setChatMessages(prev => [...prev, {
        role: 'user',
        content: chatForm.message,
        timestamp: new Date(),
      }, {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        actions: response.actions,
        suggestions: response.suggestions,
      }]);
      setChatForm(prev => ({ ...prev, message: '' }));
    } catch (err: any) {
      setError('Failed to send message');
    }
  };

  const handleScheduleFollowup = async () => {
    try {
      const followupData = {
        followup_date: followupForm.followup_date + 'T' + (followupForm.followup_time || '09:00:00'),
        followup_notes: followupForm.followup_notes,
      };
      await apiClient.scheduleEmailTaskFollowup(followupForm.taskId, followupData);
      setSuccess('Follow-up scheduled successfully!');
      setFollowupDialog(false);
      setFollowupForm({ taskId: '', followup_date: '', followup_time: '', followup_notes: '' });
    } catch (err: any) {
      setError('Failed to schedule follow-up');
    }
  };

  const handleExportData = async () => {
    try {
      await apiClient.exportEmailDashboardData(exportForm.format, exportForm.date_range.start + ' to ' + exportForm.date_range.end);
      setSuccess('Export initiated successfully! Download will start shortly.');
      setExportDialog(false);
    } catch (err: any) {
      setError('Failed to export data');
    }
  };

  const handleUpdateNotificationSettings = async () => {
    try {
      await apiClient.updateEmailNotificationSettings(notificationSettings);
      setSuccess('Notification settings updated successfully!');
      setNotificationSettingsDialog(false);
    } catch (err: any) {
      setError('Failed to update notification settings');
    }
  };

  const handleSaveSearch = async (searchData: any) => {
    try {
      await apiClient.saveEmailSearchQuery(searchData);
      setSuccess('Search saved successfully!');
      setSavedSearchesDialog(false);
      // Refresh saved searches
      const saved = await apiClient.getSavedEmailSearches();
      setSavedSearches(saved);
    } catch (err: any) {
      setError('Failed to save search');
    }
  };

  const handleUpdateEmailSettings = async (settings: any) => {
    try {
      await apiClient.updateEmailSettings(settings);
      setSuccess('Email settings updated successfully!');
      setSettingsDialog(false);
    } catch (err: any) {
      setError('Failed to update settings');
    }
  };

  const handleCreateTaskTemplate = async (templateData: any) => {
    try {
      await apiClient.createEmailTaskTemplate(templateData);
      setSuccess('Task template created successfully!');
      setTaskTemplatesDialog(false);
      // Refresh templates
      const templates = await apiClient.getEmailTaskTemplates();
      setTaskTemplates(templates);
    } catch (err: any) {
      setError('Failed to create task template');
    }
  };

  const handleCreateProcessingRule = async (ruleData: any) => {
    try {
      await apiClient.createEmailProcessingRule(ruleData);
      setSuccess('Processing rule created successfully!');
      setProcessingRulesDialog(false);
      // Refresh rules
      const rules = await apiClient.getEmailProcessingRules();
      setProcessingRules(rules);
    } catch (err: any) {
      setError('Failed to create processing rule');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
      case 'urgent':
        return 'error';
      case 'medium':
      case 'normal':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
      case 'urgent':
        return <PriorityHigh />;
      case 'medium':
      case 'normal':
        return <TrendingUp />;
      case 'low':
        return <LowPriority />;
      default:
        return <Info />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
      case 'processing':
        return 'info';
      case 'failed':
      case 'error':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box sx={{ width: '100%', minHeight: '100vh', bgcolor: 'background.default' }}>
        {/* Header */}
        <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar sx={{ bgcolor: 'primary.main' }}>
                <Email />
              </Avatar>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 600 }}>
                  Email Assistant
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  AI-powered email management and automation
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Badge badgeContent={notifications.length} color="error">
                <IconButton onClick={() => setActiveTab(4)}>
                  <Notifications />
                </IconButton>
              </Badge>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={() => setStartWorkflowDialog(true)}
              >
                Start Workflow
              </Button>
            </Box>
          </Box>
        </Paper>

        {/* Main Content */}
        <Box sx={{ width: '100%' }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
              <Tab label="Dashboard" icon={<Analytics />} iconPosition="start" />
              <Tab label="Workflows" icon={<Settings />} iconPosition="start" />
              <Tab label="Tasks" icon={<CheckCircle />} iconPosition="start" />
              <Tab label="Search" icon={<Search />} iconPosition="start" />
              <Tab label="Chat" icon={<Chat />} iconPosition="start" />
              <Tab label="Analytics" icon={<Assessment />} iconPosition="start" />
              <Tab label="Settings" icon={<Build />} iconPosition="start" />
              <Tab label="Templates" icon={<Rule />} iconPosition="start" />
            </Tabs>
          </Box>

          {/* Dashboard Tab */}
          <TabPanel value={activeTab} index={0}>
            <Grid container spacing={3}>
              {/* Statistics Cards */}
              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Total Workflows
                    </Typography>
                    <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main' }}>
                      {dashboardStats?.total_workflows || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {dashboardStats?.active_workflows || 0} active
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Emails Processed
                    </Typography>
                    <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                      {dashboardStats?.total_emails_processed || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Today
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Active Tasks
                    </Typography>
                    <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main' }}>
                      {dashboardStats?.pending_tasks || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {dashboardStats?.completed_tasks || 0} completed
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Success Rate
                    </Typography>
                    <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                      {dashboardStats?.success_rate ? `${dashboardStats.success_rate.toFixed(1)}%` : '0%'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Avg: {dashboardStats?.avg_processing_time ? `${dashboardStats.avg_processing_time.toFixed(1)}s` : '0s'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              {/* Recent Activity */}
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Recent Activity
                    </Typography>
                    <List>
                      {workflows.slice(0, 5).map((workflow, index) => (
                        <ListItem key={workflow.id}>
                          <ListItemIcon>
                            {workflow.status === 'completed' ? (
                              <CheckCircle color="success" />
                            ) : workflow.status === 'running' ? (
                              <PlayArrow color="info" />
                            ) : (
                              <Error color="error" />
                            )}
                          </ListItemIcon>
                          <ListItemText
                            primary={`Workflow ${workflow.id}`}
                            secondary={`${workflow.status} - ${workflow.emails_processed || 0} emails processed`}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(workflow.created_at)}
                          </Typography>
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Workflows Tab */}
          <TabPanel value={activeTab} index={1}>
            <Box sx={{ mb: 2 }}>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => setStartWorkflowDialog(true)}
                sx={{ mr: 1 }}
              >
                Start New Workflow
              </Button>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={loadWorkflows}
                sx={{ mr: 1 }}
              >
                Refresh All
              </Button>
              <Button
                variant="outlined"
                startIcon={<GetApp />}
                onClick={() => setExportDialog(true)}
              >
                Export Workflows
              </Button>
            </Box>

            <Grid container spacing={2}>
              {workflows.map((workflow) => (
                <Grid item xs={12} md={6} lg={4} key={workflow.id}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6">
                          Workflow {workflow.id}
                        </Typography>
                        <Chip
                          label={workflow.status}
                          color={getStatusColor(workflow.status) as any}
                          size="small"
                        />
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {workflow.emails_processed || 0} emails processed • {workflow.tasks_created || 0} tasks created
                      </Typography>

                      {workflow.status === 'running' && (
                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="body2">Overall Progress</Typography>
                            <Typography variant="body2">{workflow.progress_percentage || 0}%</Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={workflow.progress_percentage || 0}
                            sx={{ mb: 1 }}
                          />
                          {workflow.current_phase && (
                            <Typography variant="caption" color="text.secondary">
                              Current: {workflow.current_phase.replace('_', ' ')}
                            </Typography>
                          )}
                        </Box>
                      )}

                      {/* Phase-by-phase progress */}
                      {workflow.phases && workflow.phases.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                            Processing Phases
                          </Typography>
                          {workflow.phases.slice(0, 4).map((phase: any, index: number) => (
                            <Box key={index} sx={{ mb: 0.5 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption">
                                  {phase.phase_name.replace('_', ' ')}
                                </Typography>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  <Typography variant="caption" color="text.secondary">
                                    {phase.status}
                                  </Typography>
                                  {phase.status === 'completed' && <CheckCircle fontSize="small" color="success" />}
                                </Box>
                              </Box>
                              {phase.status === 'running' && (
                                <LinearProgress
                                  variant="determinate"
                                  value={phase.progress_percentage || 0}
                                  size="small"
                                  sx={{ mt: 0.5 }}
                                />
                              )}
                            </Box>
                          ))}
                        </Box>
                      )}

                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Started: {formatDate(workflow.created_at)}
                        </Typography>
                        {workflow.completed_at && (
                          <Typography variant="caption" color="text.secondary">
                            Completed: {formatDate(workflow.completed_at)}
                          </Typography>
                        )}
                      </Box>

                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {workflow.status === 'running' && (
                          <Button
                            size="small"
                            startIcon={<Stop />}
                            onClick={() => handleCancelWorkflow(workflow.id)}
                            color="error"
                          >
                            Cancel
                          </Button>
                        )}
                        <Button
                          size="small"
                          startIcon={<Timeline />}
                          onClick={() => {
                            setSelectedWorkflow(workflow);
                            // Open detailed progress modal
                          }}
                        >
                          Details
                        </Button>
                        <Button
                          size="small"
                          startIcon={<Refresh />}
                          onClick={() => {/* Refresh single workflow */}}
                        >
                          Refresh
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </TabPanel>

          {/* Tasks Tab */}
          <TabPanel value={activeTab} index={2}>
            <Box sx={{ mb: 2 }}>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={loadTasks}
                sx={{ mr: 1 }}
              >
                Refresh Tasks
              </Button>
              <Button
                variant="outlined"
                startIcon={<GetApp />}
                onClick={() => setExportDialog(true)}
              >
                Export Tasks
              </Button>
            </Box>

            <Grid container spacing={2}>
              {tasks.map((task) => (
                <Grid item xs={12} md={6} key={task.id}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {task.description}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getPriorityIcon(task.priority)}
                          <Chip
                            label={task.priority}
                            color={getPriorityColor(task.priority) as any}
                            size="small"
                          />
                        </Box>
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        From: {task.email_sender}
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 2 }}>
                        {task.email_subject}
                      </Typography>

                      {/* Attachment Analysis */}
                      {task.attachments && task.attachments.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                            Attachments:
                          </Typography>
                          {task.attachments.map((attachment: any, index: number) => (
                            <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Attachment fontSize="small" />
                              <Typography variant="caption">
                                {attachment.filename} ({attachment.size_formatted})
                              </Typography>
                              <Chip
                                label={attachment.security_status || 'Safe'}
                                size="small"
                                color={attachment.security_status === 'suspicious' ? 'warning' : 'success'}
                              />
                            </Box>
                          ))}
                        </Box>
                      )}

                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Due: {formatDate(task.due_date)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Created: {formatDate(task.created_at)}
                        </Typography>
                      </Box>

                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleCompleteTask(task.id)}
                          disabled={task.status === 'completed'}
                        >
                          {task.status === 'completed' ? 'Completed' : 'Complete'}
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<Schedule />}
                          onClick={() => {
                            setSelectedTask(task);
                            setFollowupForm({ ...followupForm, taskId: task.id });
                            setFollowupDialog(true);
                          }}
                        >
                          Follow-up
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<PriorityHigh />}
                          onClick={() => {/* Update priority */}}
                        >
                          Priority
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </TabPanel>

          {/* Search Tab */}
          <TabPanel value={activeTab} index={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                  Advanced Email Search
                </Typography>

                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="Search Query"
                      value={searchForm.query}
                      onChange={(e) => setSearchForm(prev => ({ ...prev, query: e.target.value }))}
                      placeholder="e.g., urgent project deadlines"
                    />
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <FormControl fullWidth>
                      <InputLabel>Search Type</InputLabel>
                      <Select
                        value={searchForm.search_type}
                        onChange={(e) => setSearchForm(prev => ({ ...prev, search_type: e.target.value }))}
                      >
                        <MenuItem value="semantic">Semantic</MenuItem>
                        <MenuItem value="keyword">Keyword</MenuItem>
                        <MenuItem value="hybrid">Hybrid</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      label="Sender"
                      value={searchForm.sender}
                      onChange={(e) => setSearchForm(prev => ({ ...prev, sender: e.target.value }))}
                      placeholder="email@domain.com"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="From Date"
                      type="date"
                      value={searchForm.date_from ? dayjs(searchForm.date_from).format('YYYY-MM-DD') : ''}
                      onChange={(e) => setSearchForm(prev => ({ ...prev, date_from: e.target.value }))}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="To Date"
                      type="date"
                      value={searchForm.date_to ? dayjs(searchForm.date_to).format('YYYY-MM-DD') : ''}
                      onChange={(e) => setSearchForm(prev => ({ ...prev, date_to: e.target.value }))}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      <Button
                        variant="contained"
                        startIcon={<Search />}
                        onClick={handleSearchEmails}
                        disabled={loading}
                      >
                        {loading ? <CircularProgress size={20} /> : 'Search'}
                      </Button>
                      <Button
                        variant="outlined"
                        startIcon={<FilterList />}
                        onClick={() => setSearchDialog(true)}
                      >
                        Advanced Filters
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Chat Tab */}
          <TabPanel value={activeTab} index={4}>
            <Card sx={{ height: 600, display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Email Assistant Chat
                </Typography>

                <Box sx={{ flex: 1, overflow: 'auto', mb: 2, p: 1 }}>
                  {chatMessages.map((msg, index) => (
                    <Box
                      key={index}
                      sx={{
                        mb: 2,
                        p: 2,
                        borderRadius: 2,
                        bgcolor: msg.role === 'user' ? 'primary.light' : 'grey.100',
                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        maxWidth: '70%',
                        ml: msg.role === 'user' ? 'auto' : 0,
                      }}
                    >
                      <Typography variant="body1">{msg.content}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {msg.timestamp.toLocaleTimeString()}
                      </Typography>
                    </Box>
                  ))}
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    placeholder="Ask me about your emails..."
                    value={chatForm.message}
                    onChange={(e) => setChatForm(prev => ({ ...prev, message: e.target.value }))}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendChatMessage()}
                  />
                  <Button
                    variant="contained"
                    onClick={handleSendChatMessage}
                    disabled={!chatForm.message.trim()}
                  >
                    <Send />
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Analytics Tab */}
          <TabPanel value={activeTab} index={5}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Productivity Insights
                    </Typography>
                    {analytics?.insights?.map((insight: string, index: number) => (
                      <Typography key={index} variant="body2" sx={{ mb: 1 }}>
                        • {insight}
                      </Typography>
                    ))}
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Category Distribution
                    </Typography>
                    {analytics?.categories?.map((category: any, index: number) => (
                      <Box key={index} sx={{ mb: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2">{category.category}</Typography>
                          <Typography variant="body2">{category.count}</Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={(category.count / analytics.total_emails) * 100}
                          sx={{ mt: 0.5 }}
                        />
                      </Box>
                    ))}
                  </CardContent>
                </Card>
              </Grid>

              {/* Advanced Analytics */}
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Advanced Analytics
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={4}>
                        <Button
                          variant="outlined"
                          startIcon={<Timeline />}
                          onClick={() => {/* Load time pattern analytics */}}
                          fullWidth
                        >
                          Time Patterns
                        </Button>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <Button
                          variant="outlined"
                          startIcon={<Analytics />}
                          onClick={() => {/* Load sender analytics */}}
                          fullWidth
                        >
                          Sender Analysis
                        </Button>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <Button
                          variant="outlined"
                          startIcon={<TrendingUp />}
                          onClick={() => {/* Load performance metrics */}}
                          fullWidth
                        >
                          Performance
                        </Button>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Settings Tab */}
          <TabPanel value={activeTab} index={6}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Email Processing Settings
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Button
                        variant="outlined"
                        startIcon={<Settings />}
                        onClick={() => setSettingsDialog(true)}
                      >
                        Processing Settings
                      </Button>
                      <Button
                        variant="outlined"
                        startIcon={<Notifications />}
                        onClick={() => setNotificationSettingsDialog(true)}
                      >
                        Notification Settings
                      </Button>
                      <Button
                        variant="outlined"
                        startIcon={<Rule />}
                        onClick={() => setProcessingRulesDialog(true)}
                      >
                        Processing Rules
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Data Management
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Button
                        variant="outlined"
                        startIcon={<GetApp />}
                        onClick={() => setExportDialog(true)}
                      >
                        Export Data
                      </Button>
                      <Button
                        variant="outlined"
                        startIcon={<Bookmark />}
                        onClick={() => setSavedSearchesDialog(true)}
                      >
                        Saved Searches
                      </Button>
                      <Button
                        variant="outlined"
                        startIcon={<Folder />}
                        onClick={() => {/* Load templates */}}
                      >
                        Manage Templates
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Templates Tab */}
          <TabPanel value={activeTab} index={7}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Task Templates
                      </Typography>
                      <Button
                        variant="contained"
                        startIcon={<Add />}
                        onClick={() => setTaskTemplatesDialog(true)}
                      >
                        Create Template
                      </Button>
                    </Box>
                    <Grid container spacing={2}>
                      {taskTemplates.map((template: any, index: number) => (
                        <Grid item xs={12} md={6} lg={4} key={index}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                                {template.name}
                              </Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                {template.description}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button size="small" variant="outlined">
                                  Edit
                                </Button>
                                <Button size="small" variant="outlined" color="error">
                                  Delete
                                </Button>
                              </Box>
                            </CardContent>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>
        </Box>

        {/* Start Workflow Dialog */}
        <Dialog open={startWorkflowDialog} onClose={() => setStartWorkflowDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Start Email Workflow</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="IMAP Server"
                  value={workflowForm.server}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, server: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  label="Port"
                  type="number"
                  value={workflowForm.port}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, port: parseInt(e.target.value) }))}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={workflowForm.use_ssl}
                      onChange={(e) => setWorkflowForm(prev => ({ ...prev, use_ssl: e.target.checked }))}
                    />
                  }
                  label="Use SSL"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Username"
                  value={workflowForm.username}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, username: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Password"
                  type="password"
                  value={workflowForm.password}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, password: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Mailbox"
                  value={workflowForm.mailbox}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, mailbox: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Max Emails"
                  type="number"
                  value={workflowForm.max_emails}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, max_emails: parseInt(e.target.value) }))}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={workflowForm.unread_only}
                      onChange={(e) => setWorkflowForm(prev => ({ ...prev, unread_only: e.target.checked }))}
                    />
                  }
                  label="Unread Only"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={workflowForm.create_tasks}
                      onChange={(e) => setWorkflowForm(prev => ({ ...prev, create_tasks: e.target.checked }))}
                    />
                  }
                  label="Create Tasks"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={workflowForm.schedule_followups}
                      onChange={(e) => setWorkflowForm(prev => ({ ...prev, schedule_followups: e.target.checked }))}
                    />
                  }
                  label="Schedule Follow-ups"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setStartWorkflowDialog(false)}>Cancel</Button>
            <Button onClick={handleStartWorkflow} variant="contained" disabled={loading}>
              {loading ? <CircularProgress size={20} /> : 'Start Workflow'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Search Results Dialog */}
        <Dialog open={searchDialog} onClose={() => setSearchDialog(false)} maxWidth="lg" fullWidth>
          <DialogTitle>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Search Results</Typography>
              <Button
                variant="outlined"
                startIcon={<Save />}
                onClick={() => setSavedSearchesDialog(true)}
              >
                Save Search
              </Button>
            </Box>
          </DialogTitle>
          <DialogContent>
            <List>
              {searchResults.map((result, index) => (
                <ListItem key={index}>
                  <ListItemText
                    primary={result.subject}
                    secondary={
                      <Box>
                        <Typography variant="body2">From: {result.sender}</Typography>
                        <Typography variant="body2">Date: {formatDate(result.sent_date)}</Typography>
                        <Typography variant="body2">{result.content_preview}</Typography>
                        {result.attachments && result.attachments.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>
                              Attachments:
                            </Typography>
                            {result.attachments.map((attachment: any, idx: number) => (
                              <Chip
                                key={idx}
                                label={`${attachment.filename} (${attachment.security_status || 'Safe'})`}
                                size="small"
                                color={attachment.security_status === 'suspicious' ? 'warning' : 'default'}
                                sx={{ ml: 1, mt: 0.5 }}
                              />
                            ))}
                          </Box>
                        )}
                      </Box>
                    }
                  />
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip
                      label={`Score: ${result.relevance_score?.toFixed(2)}`}
                      size="small"
                      color="primary"
                    />
                    {result.thread_id && (
                      <Chip
                        label="Thread"
                        size="small"
                        variant="outlined"
                        icon={<Folder />}
                      />
                    )}
                  </Box>
                </ListItem>
              ))}
            </List>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSearchDialog(false)}>Close</Button>
            <Button
              variant="contained"
              startIcon={<GetApp />}
              onClick={() => setExportDialog(true)}
            >
              Export Results
            </Button>
          </DialogActions>
        </Dialog>

        {/* Follow-up Scheduling Dialog */}
        <Dialog open={followupDialog} onClose={() => setFollowupDialog(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Schedule Follow-up</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Schedule a follow-up reminder for this task
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Follow-up Date"
                  type="date"
                  value={followupForm.followup_date}
                  onChange={(e) => setFollowupForm(prev => ({ ...prev, followup_date: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Follow-up Time"
                  type="time"
                  value={followupForm.followup_time || ''}
                  onChange={(e) => setFollowupForm(prev => ({ ...prev, followup_time: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Follow-up Notes"
                  multiline
                  rows={3}
                  value={followupForm.followup_notes}
                  onChange={(e) => setFollowupForm(prev => ({ ...prev, followup_notes: e.target.value }))}
                  placeholder="What should be done in this follow-up?"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setFollowupDialog(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={() => {
                // Handle follow-up scheduling
                setSuccess('Follow-up scheduled successfully!');
                setFollowupDialog(false);
              }}
            >
              Schedule Follow-up
            </Button>
          </DialogActions>
        </Dialog>

        {/* Export Dialog */}
        <Dialog open={exportDialog} onClose={() => setExportDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Export Data</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Export Format</InputLabel>
                  <Select
                    value={exportForm.format}
                    onChange={(e) => setExportForm(prev => ({ ...prev, format: e.target.value }))}
                  >
                    <MenuItem value="csv">CSV</MenuItem>
                    <MenuItem value="json">JSON</MenuItem>
                    <MenuItem value="pdf">PDF</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Data Type</InputLabel>
                  <Select
                    value={exportForm.data_type}
                    onChange={(e) => setExportForm(prev => ({ ...prev, data_type: e.target.value }))}
                  >
                    <MenuItem value="dashboard_stats">Dashboard Statistics</MenuItem>
                    <MenuItem value="tasks">Tasks</MenuItem>
                    <MenuItem value="workflows">Workflows</MenuItem>
                    <MenuItem value="search_results">Search Results</MenuItem>
                    <MenuItem value="analytics">Analytics</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Start Date"
                  type="date"
                  value={exportForm.date_range.start}
                  onChange={(e) => setExportForm(prev => ({
                    ...prev,
                    date_range: { ...prev.date_range, start: e.target.value }
                  }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="End Date"
                  type="date"
                  value={exportForm.date_range.end}
                  onChange={(e) => setExportForm(prev => ({
                    ...prev,
                    date_range: { ...prev.date_range, end: e.target.value }
                  }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={exportForm.include_charts}
                      onChange={(e) => setExportForm(prev => ({ ...prev, include_charts: e.target.checked }))}
                    />
                  }
                  label="Include charts and visualizations (PDF only)"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setExportDialog(false)}>Cancel</Button>
            <Button
              variant="contained"
              startIcon={<GetApp />}
              onClick={() => {
                setSuccess('Export initiated successfully!');
                setExportDialog(false);
              }}
            >
              Export Data
            </Button>
          </DialogActions>
        </Dialog>

        {/* Notification Settings Dialog */}
        <Dialog open={notificationSettingsDialog} onClose={() => setNotificationSettingsDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Notification Settings</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Configure how you want to receive notifications about email processing activities.
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.email_notifications}
                      onChange={(e) => setNotificationSettings(prev => ({
                        ...prev,
                        email_notifications: e.target.checked
                      }))}
                    />
                  }
                  label="Email Notifications"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.push_notifications}
                      onChange={(e) => setNotificationSettings(prev => ({
                        ...prev,
                        push_notifications: e.target.checked
                      }))}
                    />
                  }
                  label="Push Notifications"
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Notification Types</Typography>
                <Grid container spacing={1}>
                  {[
                    { key: 'task_created', label: 'Task Created' },
                    { key: 'workflow_completed', label: 'Workflow Completed' },
                    { key: 'error_alerts', label: 'Error Alerts' },
                    { key: 'attachment_analysis', label: 'Attachment Analysis' },
                    { key: 'spam_detected', label: 'Spam Detected' },
                    { key: 'followup_reminders', label: 'Follow-up Reminders' }
                  ].map((type) => (
                    <Grid item xs={12} md={6} key={type.key}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={notificationSettings.notification_types.includes(type.key)}
                            onChange={(e) => {
                              const newTypes = e.target.checked
                                ? [...notificationSettings.notification_types, type.key]
                                : notificationSettings.notification_types.filter(t => t !== type.key);
                              setNotificationSettings(prev => ({
                                ...prev,
                                notification_types: newTypes
                              }));
                            }}
                          />
                        }
                        label={type.label}
                      />
                    </Grid>
                  ))}
                </Grid>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNotificationSettingsDialog(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={() => {
                setSuccess('Notification settings updated successfully!');
                setNotificationSettingsDialog(false);
              }}
            >
              Save Settings
            </Button>
          </DialogActions>
        </Dialog>

        {/* Saved Searches Dialog */}
        <Dialog open={savedSearchesDialog} onClose={() => setSavedSearchesDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Saved Searches</Typography>
              <Button variant="contained" startIcon={<Add />}>
                Save Current Search
              </Button>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2}>
              {savedSearches.map((search: any, index: number) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                        {search.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {search.description}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button size="small" variant="outlined">
                          Load Search
                        </Button>
                        <Button size="small" variant="outlined">
                          Edit
                        </Button>
                        <Button size="small" variant="outlined" color="error">
                          Delete
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSavedSearchesDialog(false)}>Close</Button>
          </DialogActions>
        </Dialog>

        {/* Settings Dialog */}
        <Dialog open={settingsDialog} onClose={() => setSettingsDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Email Processing Settings</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Configure email processing parameters and thresholds.
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Importance Threshold"
                  type="number"
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                  value={emailSettings?.importance_threshold || 0.7}
                  onChange={(e) => {/* Update settings */}}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Spam Threshold"
                  type="number"
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                  value={emailSettings?.spam_threshold || 0.8}
                  onChange={(e) => {/* Update settings */}}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={<Switch defaultChecked />}
                  label="Create Tasks Automatically"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={<Switch defaultChecked />}
                  label="Schedule Follow-ups"
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Processing Rules</Typography>
                <Button
                  variant="outlined"
                  startIcon={<Rule />}
                  onClick={() => setProcessingRulesDialog(true)}
                >
                  Manage Processing Rules
                </Button>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSettingsDialog(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={() => {
                setSuccess('Settings updated successfully!');
                setSettingsDialog(false);
              }}
            >
              Save Settings
            </Button>
          </DialogActions>
        </Dialog>

        {/* Task Templates Dialog */}
        <Dialog open={taskTemplatesDialog} onClose={() => setTaskTemplatesDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Create Task Template</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Template Name"
                  placeholder="e.g., Urgent Client Response"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description"
                  multiline
                  rows={2}
                  placeholder="Describe when to use this template"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Default Priority</InputLabel>
                  <Select defaultValue="medium">
                    <MenuItem value="low">Low</MenuItem>
                    <MenuItem value="medium">Medium</MenuItem>
                    <MenuItem value="high">High</MenuItem>
                    <MenuItem value="urgent">Urgent</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Default Due Date (hours from creation)"
                  type="number"
                  defaultValue={24}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Template Content"
                  multiline
                  rows={4}
                  placeholder="Describe the task requirements and steps"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={<Switch />}
                  label="Auto-assign based on email content"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTaskTemplatesDialog(false)}>Cancel</Button>
            <Button variant="contained">
              Create Template
            </Button>
          </DialogActions>
        </Dialog>

        {/* Processing Rules Dialog */}
        <Dialog open={processingRulesDialog} onClose={() => setProcessingRulesDialog(false)} maxWidth="lg" fullWidth>
          <DialogTitle>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Email Processing Rules</Typography>
              <Button variant="contained" startIcon={<Add />}>
                Add Rule
              </Button>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2}>
              {processingRules.map((rule: any, index: number) => (
                <Grid item xs={12} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {rule.name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Chip
                            label={rule.priority}
                            color={rule.priority === 'high' ? 'error' : 'default'}
                            size="small"
                          />
                          <Switch defaultChecked={rule.enabled} />
                        </Box>
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {rule.description}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button size="small" variant="outlined">
                          Edit
                        </Button>
                        <Button size="small" variant="outlined" color="error">
                          Delete
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setProcessingRulesDialog(false)}>Close</Button>
          </DialogActions>
        </Dialog>

        {/* Notifications */}
        <Snackbar
          open={!!error}
          autoHideDuration={6000}
          onClose={() => setError(null)}
        >
          <Alert onClose={() => setError(null)} severity="error">
            {error}
          </Alert>
        </Snackbar>

        <Snackbar
          open={!!success}
          autoHideDuration={6000}
          onClose={() => setSuccess(null)}
        >
          <Alert onClose={() => setSuccess(null)} severity="success">
            {success}
          </Alert>
        </Snackbar>
      </Box>
  );
};

export default EmailAssistant;