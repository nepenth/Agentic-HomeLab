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
  Skeleton,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  AlertTitle,
  Fade,
  Slide,
  Backdrop,
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
  BugReport,
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
  const [logs, setLogs] = useState<any[]>([]);
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
  const [emailSettingsDialog, setEmailSettingsDialog] = useState(false);
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
    // Timeout settings
    analysis_timeout: 120,
    task_timeout: 60,
    ollama_timeout: 60,
    max_retries: 3,
    retry_delay: 1,
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

  // Email settings
  const [savedEmailSettings, setSavedEmailSettings] = useState<any>(null);
  const [useSavedSettings, setUseSavedSettings] = useState(false);

  // Email settings form
  const [emailSettingsForm, setEmailSettingsForm] = useState({
    server: '',
    port: 993,
    username: '',
    password: '',
    use_ssl: true,
    mailbox: 'INBOX',
  });

  // WebSocket for real-time updates
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [useSSE, setUseSSE] = useState(false); // Fallback to SSE if WebSocket fails

  // Enhanced loading states
  const [loadingStates, setLoadingStates] = useState({
    dashboard: false,
    workflows: false,
    tasks: false,
    logs: false,
    notifications: false,
    emailSettings: false,
  });

  // Enhanced error states with recovery options
  const [errorStates, setErrorStates] = useState({
    dashboard: null as string | null,
    workflows: null as string | null,
    tasks: null as string | null,
    logs: null as string | null,
    notifications: null as string | null,
    emailSettings: null as string | null,
  });

  // Progress tracking
  const [workflowProgress, setWorkflowProgress] = useState<Map<string, any>>(new Map());
  const [taskProgress, setTaskProgress] = useState<Map<string, any>>(new Map());

  // Retry mechanisms
  const [retryCounts, setRetryCounts] = useState({
    dashboard: 0,
    workflows: 0,
    tasks: 0,
    logs: 0,
    notifications: 0,
    emailSettings: 0,
  });

  // Auto-refresh intervals
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [refreshIntervals, setRefreshIntervals] = useState({
    workflows: 5000, // 5 seconds for active workflows
    dashboard: 30000, // 30 seconds for dashboard
    tasks: 10000, // 10 seconds for tasks
  });

  // Enhanced connection management with SSE fallback
  useEffect(() => {
    initializeConnection();

    return () => {
      webSocketService.off('workflow_progress', updateWorkflowProgress);
      webSocketService.off('task_update', updateTaskStatus);
      webSocketService.off('notification', addNotification);
      webSocketService.disconnect();
      // Clean up SSE if active
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Auto-refresh workflows when there are active workflows
  useEffect(() => {
    if (!autoRefreshEnabled) return;

    const hasActiveWorkflows = workflows.some(wf => wf.status === 'running' || wf.status === 'processing');
    const hasActiveTasks = tasks.some(task => task.status === 'running' || task.status === 'pending');

    let workflowInterval: NodeJS.Timeout | null = null;
    let taskInterval: NodeJS.Timeout | null = null;

    if (hasActiveWorkflows) {
      workflowInterval = setInterval(() => {
        loadWorkflows();
      }, refreshIntervals.workflows);
    }

    if (hasActiveTasks) {
      taskInterval = setInterval(() => {
        loadTasks();
      }, refreshIntervals.tasks);
    }

    return () => {
      if (workflowInterval) clearInterval(workflowInterval);
      if (taskInterval) clearInterval(taskInterval);
    };
  }, [workflows, tasks, autoRefreshEnabled, refreshIntervals]);

  // Auto-refresh dashboard stats
  useEffect(() => {
    if (!autoRefreshEnabled) return;

    const dashboardInterval = setInterval(() => {
      loadDashboardData();
    }, refreshIntervals.dashboard);

    return () => clearInterval(dashboardInterval);
  }, [autoRefreshEnabled, refreshIntervals.dashboard]);

  // SSE fallback reference
  const eventSourceRef = React.useRef<EventSource | null>(null);

  const initializeConnection = async () => {
    const token = apiClient.getAuthToken();

    try {
      // Try WebSocket first
      webSocketService.connect('email/progress', token || undefined);

      // Set up message handlers
      webSocketService.on('workflow_progress', updateWorkflowProgress);
      webSocketService.on('task_update', updateTaskStatus);
      webSocketService.on('notification', addNotification);

      // Enhanced connection status monitoring
      webSocketService.onConnectionStatus((status, error) => {
        setConnectionStatus(status);
        setWsConnected(status === 'connected');

        if (status === 'error' && !useSSE) {
          console.warn('WebSocket failed, attempting SSE fallback:', error);
          setUseSSE(true);
          initializeSSE(token);
        }
      });

      // Load initial data
      await loadDashboardData();
      await loadWorkflows();
      await loadTasks();
      await loadLogs();
      await loadNotifications();
      await loadEmailSettings();

    } catch (error) {
      console.error('Failed to initialize connection:', error);
      setUseSSE(true);
      initializeSSE(token);
      // Still load data even if connection fails
      loadDashboardData();
      loadWorkflows();
      loadTasks();
      loadLogs();
      loadNotifications();
      loadEmailSettings();
    }
  };

  const initializeSSE = (token?: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace('/api/v1', '');
    const sseUrl = token ? `${baseUrl}/api/v1/logs/stream?token=${token}` : `${baseUrl}/api/v1/logs/stream`;

    eventSourceRef.current = new EventSource(sseUrl);

    eventSourceRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSSEMessage(data);
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    eventSourceRef.current.onerror = (error) => {
      console.error('SSE connection error:', error);
      setConnectionStatus('error');
    };

    eventSourceRef.current.onopen = () => {
      setConnectionStatus('connected');
    };
  };

  const handleSSEMessage = (data: any) => {
    if (data.type === 'workflow_progress') {
      updateWorkflowProgress(data);
    } else if (data.type === 'task_update') {
      updateTaskStatus(data);
    } else if (data.type === 'notification') {
      addNotification(data);
    }
  };

  const loadDashboardData = async (retryCount = 0) => {
    try {
      setLoadingStates(prev => ({ ...prev, dashboard: true }));
      setErrorStates(prev => ({ ...prev, dashboard: null }));

      const [stats, analyticsData] = await Promise.all([
        apiClient.getEmailDashboardStats(),
        apiClient.getEmailAnalyticsOverview(),
      ]);

      setDashboardStats(stats);
      setAnalytics(analyticsData);
      setRetryCounts(prev => ({ ...prev, dashboard: 0 })); // Reset retry count on success
    } catch (err: any) {
      console.error('Dashboard data load error:', err);

      const errorMessage = err.detail || err.message || 'Failed to load dashboard data';
      setErrorStates(prev => ({ ...prev, dashboard: errorMessage }));

      // Auto-retry logic for network errors
      if (retryCount < 3 && (err.code === 'NETWORK_ERROR' || err.status >= 500)) {
        const newRetryCount = retryCount + 1;
        setRetryCounts(prev => ({ ...prev, dashboard: newRetryCount }));

        setTimeout(() => {
          loadDashboardData(newRetryCount);
        }, Math.pow(2, newRetryCount) * 1000); // Exponential backoff
      }
    } finally {
      setLoadingStates(prev => ({ ...prev, dashboard: false }));
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

  const loadLogs = async () => {
    try {
      const data = await apiClient.getEmailWorkflowLogs({ limit: 50 });
      setLogs(data || []);
    } catch (err: any) {
      console.error('Failed to load logs:', err);
      setLogs([]);
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

  const loadEmailSettings = async () => {
    try {
      const settings = await apiClient.getEmailSettings();
      setSavedEmailSettings(settings);
      // Populate form with current settings
      if (settings) {
        setEmailSettingsForm({
          server: settings.server || '',
          port: settings.port || 993,
          username: settings.username || '',
          password: '', // Don't populate password for security
          use_ssl: settings.use_ssl !== false, // Default to true
          mailbox: settings.mailbox || 'INBOX',
        });
      }
      // If settings exist and have a password, enable the option to use saved settings
      if (settings && settings.has_password && settings.server) {
        setUseSavedSettings(true);
      }
    } catch (err: any) {
      console.error('Failed to load email settings:', err);
    }
  };

  const updateWorkflowProgress = (progressData: any) => {
    setWorkflows(prev =>
      prev.map(wf =>
        wf.id === progressData.workflow_id
          ? {
              ...wf,
              ...progressData,
              last_updated: new Date(),
              // Enhanced progress tracking
              progress_percentage: progressData.progress_percentage || wf.progress_percentage,
              current_phase: progressData.current_phase || wf.current_phase,
              phases: progressData.phases || wf.phases,
              estimated_completion: progressData.estimated_completion,
            }
          : wf
      )
    );

    // Update progress map for detailed tracking
    setWorkflowProgress(prev => {
      const newMap = new Map(prev);
      newMap.set(progressData.workflow_id, {
        ...progressData,
        timestamp: new Date(),
      });
      return newMap;
    });
  };

  const updateTaskStatus = (taskData: any) => {
    setTasks(prev =>
      prev.map(task =>
        task.id === taskData.task_id
          ? {
              ...task,
              ...taskData,
              last_updated: new Date(),
              // Enhanced task tracking
              progress_percentage: taskData.progress_percentage || task.progress_percentage,
              status: taskData.status || task.status,
              priority: taskData.priority || task.priority,
            }
          : task
      )
    );

    // Update task progress map
    setTaskProgress(prev => {
      const newMap = new Map(prev);
      newMap.set(taskData.task_id, {
        ...taskData,
        timestamp: new Date(),
      });
      return newMap;
    });
  };

  const addNotification = (notification: any) => {
    setNotifications(prev => [notification, ...prev.slice(0, 9)]);

    // Auto-dismiss non-critical notifications after 5 seconds
    if (notification.type !== 'error' && notification.type !== 'workflow_failed') {
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== notification.id));
      }, 5000);
    }
  };

  const handleStartWorkflow = async () => {
    try {
      setLoading(true);

      let result;
      if (useSavedSettings && savedEmailSettings) {
        // Use saved settings
        result = await apiClient.startEmailWorkflowWithSavedSettings({
          max_emails: workflowForm.max_emails,
          unread_only: workflowForm.unread_only,
          importance_threshold: workflowForm.importance_threshold,
          spam_threshold: workflowForm.spam_threshold,
          create_tasks: workflowForm.create_tasks,
          schedule_followups: workflowForm.schedule_followups,
        });
      } else {
        // Use form settings
        result = await apiClient.startEmailWorkflow({
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
            // Timeout settings
            analysis_timeout: workflowForm.analysis_timeout,
            task_timeout: workflowForm.task_timeout,
            ollama_timeout: workflowForm.ollama_timeout,
            max_retries: workflowForm.max_retries,
            retry_delay: workflowForm.retry_delay,
          },
        });
      }

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

  const handleUpdateEmailSettings = async () => {
    try {
      await apiClient.updateEmailSettings(emailSettingsForm);
      setSuccess('Email settings updated successfully!');
      setEmailSettingsDialog(false);
      // Reload email settings
      loadEmailSettings();
    } catch (err: any) {
      setError('Failed to update email settings');
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

  // Enhanced Workflow Progress Component
  const WorkflowProgressIndicator = ({ workflow }: { workflow: any }) => {
    const getPhaseIcon = (phase: any) => {
      if (phase.status === 'completed') return <CheckCircle color="success" fontSize="small" />;
      if (phase.status === 'running') return <CircularProgress size={16} />;
      if (phase.status === 'failed') return <Error color="error" fontSize="small" />;
      return <div style={{ width: 16, height: 16, borderRadius: '50%', backgroundColor: '#ccc' }} />;
    };

    const getPhaseColor = (phase: any) => {
      if (phase.status === 'completed') return 'success.main';
      if (phase.status === 'running') return 'info.main';
      if (phase.status === 'failed') return 'error.main';
      return 'grey.400';
    };

    return (
      <Box sx={{ mt: 2, p: 2, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Workflow Progress
        </Typography>

        {/* Overall Progress */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              Overall Progress
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {workflow.progress_percentage || 0}% Complete
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={workflow.progress_percentage || 0}
            sx={{
              height: 8,
              borderRadius: 4,
              '& .MuiLinearProgress-bar': {
                borderRadius: 4,
              },
            }}
          />
          {workflow.current_phase && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Current Phase: {workflow.current_phase.replace(/_/g, ' ')}
            </Typography>
          )}
        </Box>

        {/* Phase-by-phase Progress */}
        {workflow.phases && workflow.phases.length > 0 && (
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 2 }}>
              Processing Phases
            </Typography>
            <Stepper orientation="vertical" sx={{ mt: 1 }}>
              {workflow.phases.map((phase: any, index: number) => (
                <Step key={index} active={phase.status === 'running'} completed={phase.status === 'completed'}>
                  <StepLabel
                    StepIconComponent={() => getPhaseIcon(phase)}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                      <Typography variant="caption" sx={{ fontWeight: 500 }}>
                        {phase.phase_name.replace(/_/g, ' ')}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {phase.processing_duration_ms ? `${(phase.processing_duration_ms / 1000).toFixed(1)}s` : ''}
                      </Typography>
                    </Box>
                  </StepLabel>
                  <StepContent>
                    <Box sx={{ mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          Status: {phase.status}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {phase.progress_percentage || 0}%
                        </Typography>
                      </Box>
                      {phase.status === 'running' && (
                        <LinearProgress
                          variant="determinate"
                          value={phase.progress_percentage || 0}
                          size="small"
                          sx={{
                            height: 4,
                            borderRadius: 2,
                            '& .MuiLinearProgress-bar': {
                              borderRadius: 2,
                            }
                          }}
                        />
                      )}
                      {phase.model_used && phase.model_used !== 'n/a' && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                          Model: {phase.model_used}
                        </Typography>
                      )}
                      {phase.items_processed !== undefined && phase.total_items !== undefined && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                          Items: {phase.items_processed} / {phase.total_items}
                        </Typography>
                      )}
                    </Box>
                  </StepContent>
                </Step>
              ))}
            </Stepper>
          </Box>
        )}

        {/* Estimated completion time */}
        {workflow.status === 'running' && workflow.estimated_completion && (
          <Box sx={{ mt: 2, p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 500 }}>
              Estimated completion: {new Date(workflow.estimated_completion).toLocaleTimeString()}
            </Typography>
          </Box>
        )}
      </Box>
    );
  };

  return (
    <Box sx={{
      width: '100%',
      minHeight: '100vh',
      bgcolor: 'background.default',
      '@keyframes pulse': {
        '0%': { opacity: 1 },
        '50%': { opacity: 0.5 },
        '100%': { opacity: 1 },
      },
    }}>
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
                {/* Connection Status Indicator */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: connectionStatus === 'connected' ? 'success.main' :
                              connectionStatus === 'connecting' ? 'warning.main' :
                              connectionStatus === 'error' ? 'error.main' : 'grey.400',
                      animation: connectionStatus === 'connecting' ? 'pulse 2s infinite' : 'none',
                    }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {connectionStatus === 'connected' ? (useSSE ? 'SSE Connected' : 'WebSocket Connected') :
                     connectionStatus === 'connecting' ? 'Connecting...' :
                     connectionStatus === 'error' ? 'Connection Error' : 'Disconnected'}
                  </Typography>
                  {connectionStatus === 'error' && (
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={initializeConnection}
                      sx={{ ml: 1, fontSize: '0.7rem', py: 0.2 }}
                    >
                      Reconnect
                    </Button>
                  )}
                </Box>
                {/* Auto-refresh and active monitoring status */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                  <Box
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      bgcolor: autoRefreshEnabled ? 'info.main' : 'grey.400',
                      animation: autoRefreshEnabled ? 'pulse 3s infinite' : 'none',
                    }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Auto-refresh: {autoRefreshEnabled ? 'ON' : 'OFF'}
                  </Typography>
                  {workflows.some(wf => wf.status === 'running' || wf.status === 'processing') && (
                    <>
                      <Box
                        sx={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          bgcolor: 'warning.main',
                          animation: 'pulse 2s infinite',
                        }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        Monitoring {workflows.filter(wf => wf.status === 'running' || wf.status === 'processing').length} active workflow(s)
                      </Typography>
                    </>
                  )}
                </Box>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Badge badgeContent={notifications.length} color="error">
                <IconButton onClick={() => setActiveTab(9)}>
                  <Notifications />
                </IconButton>
              </Badge>
              <Tooltip title={autoRefreshEnabled ? "Disable auto-refresh" : "Enable auto-refresh"}>
                <IconButton
                  onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
                  color={autoRefreshEnabled ? "primary" : "default"}
                >
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={() => {
                  loadDashboardData();
                  loadWorkflows();
                  loadTasks();
                }}
                disabled={loadingStates.dashboard || loadingStates.workflows || loadingStates.tasks}
              >
                Refresh All
              </Button>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={() => setStartWorkflowDialog(true)}
                disabled={loadingStates.dashboard || connectionStatus === 'error'}
              >
                Start Workflow
              </Button>
            </Box>
          </Box>
        </Paper>

        {/* Enhanced Error Display */}
        {Object.entries(errorStates).some(([key, error]) => error && retryCounts[key as keyof typeof retryCounts] > 0) && (
          <Fade in={true}>
            <Alert
              severity="warning"
              sx={{ mb: 2 }}
              action={
                <Button
                  color="inherit"
                  size="small"
                  onClick={() => {
                    // Retry all failed operations
                    if (errorStates.dashboard) loadDashboardData();
                    if (errorStates.workflows) loadWorkflows();
                    if (errorStates.tasks) loadTasks();
                    if (errorStates.logs) loadLogs();
                    if (errorStates.notifications) loadNotifications();
                    if (errorStates.emailSettings) loadEmailSettings();
                  }}
                >
                  Retry All
                </Button>
              }
            >
              <AlertTitle>Connection Issues Detected</AlertTitle>
              Some data may be outdated. Click "Retry All" to refresh or individual sections will auto-retry.
            </Alert>
          </Fade>
        )}

        {/* Main Content */}
        <Box sx={{ width: '100%' }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
              <Tab label="Dashboard" icon={<Analytics />} iconPosition="start" />
              <Tab label="Workflows" icon={<Settings />} iconPosition="start" />
              <Tab label="Tasks" icon={<CheckCircle />} iconPosition="start" />
              <Tab label="Logs" icon={<BugReport />} iconPosition="start" />
              <Tab label="Search" icon={<Search />} iconPosition="start" />
              <Tab label="Chat" icon={<Chat />} iconPosition="start" />
              <Tab label="Analytics" icon={<Assessment />} iconPosition="start" />
              <Tab label="Settings" icon={<Build />} iconPosition="start" />
              <Tab label="Templates" icon={<Rule />} iconPosition="start" />
              <Tab label="Notifications" icon={<Notifications />} iconPosition="start" />
            </Tabs>
          </Box>

          {/* Dashboard Tab */}
          <TabPanel value={activeTab} index={0}>
            {loadingStates.dashboard ? (
              <Grid container spacing={3}>
                {[1, 2, 3, 4].map((i) => (
                  <Grid item xs={12} md={3} key={i}>
                    <Card>
                      <CardContent>
                        <Skeleton variant="text" width="60%" height={24} sx={{ mb: 2 }} />
                        <Skeleton variant="text" width="40%" height={36} />
                        <Skeleton variant="text" width="50%" height={16} />
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Skeleton variant="text" width="30%" height={24} sx={{ mb: 2 }} />
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Box key={i} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Skeleton variant="circular" width={24} height={24} sx={{ mr: 2 }} />
                          <Box sx={{ flex: 1 }}>
                            <Skeleton variant="text" width="40%" height={20} />
                            <Skeleton variant="text" width="60%" height={16} />
                          </Box>
                          <Skeleton variant="text" width="20%" height={16} />
                        </Box>
                      ))}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            ) : errorStates.dashboard ? (
              <Alert
                severity="error"
                sx={{ mb: 2 }}
                action={
                  <Button
                    color="inherit"
                    size="small"
                    onClick={() => loadDashboardData()}
                    disabled={loadingStates.dashboard}
                  >
                    {loadingStates.dashboard ? <CircularProgress size={16} /> : 'Retry'}
                  </Button>
                }
              >
                <AlertTitle>Failed to Load Dashboard</AlertTitle>
                {errorStates.dashboard}
                {retryCounts.dashboard > 0 && (
                  <Typography variant="caption" display="block">
                    Auto-retry attempt {retryCounts.dashboard}/3
                  </Typography>
                )}
              </Alert>
            ) : (
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

                {/* Active Workflow Progress */}
                {workflows.some(wf => wf.status === 'running' || wf.status === 'processing') && (
                  <Grid item xs={12}>
                    <Card sx={{ mb: 3 }}>
                      <CardContent>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                          Active Workflow Progress
                        </Typography>
                        {workflows
                          .filter(wf => wf.status === 'running' || wf.status === 'processing')
                          .map(workflow => (
                            <WorkflowProgressIndicator key={workflow.id} workflow={workflow} />
                          ))}
                      </CardContent>
                    </Card>
                  </Grid>
                )}

                {/* Recent Activity */}
                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          Recent Activity
                        </Typography>
                        <Button
                          size="small"
                          startIcon={<Refresh />}
                          onClick={() => loadWorkflows()}
                          disabled={loadingStates.workflows}
                        >
                          {loadingStates.workflows ? <CircularProgress size={16} /> : 'Refresh'}
                        </Button>
                      </Box>
                      {loadingStates.workflows ? (
                        <Box>
                          {[1, 2, 3, 4, 5].map((i) => (
                            <Box key={i} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              <Skeleton variant="circular" width={24} height={24} sx={{ mr: 2 }} />
                              <Box sx={{ flex: 1 }}>
                                <Skeleton variant="text" width="40%" height={20} />
                                <Skeleton variant="text" width="60%" height={16} />
                              </Box>
                              <Skeleton variant="text" width="20%" height={16} />
                            </Box>
                          ))}
                        </Box>
                      ) : (
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
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
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

                      {/* Enhanced Phase-by-phase progress */}
                      {workflow.phases && workflow.phases.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                            Processing Phases
                          </Typography>
                          <Stepper orientation="vertical" sx={{ mt: 1 }}>
                            {workflow.phases.map((phase: any, index: number) => (
                              <Step key={index} active={phase.status === 'running'} completed={phase.status === 'completed'}>
                                <StepLabel
                                  StepIconComponent={() => {
                                    if (phase.status === 'completed') return <CheckCircle color="success" fontSize="small" />;
                                    if (phase.status === 'running') return <CircularProgress size={16} />;
                                    if (phase.status === 'failed') return <Error color="error" fontSize="small" />;
                                    return <div style={{ width: 16, height: 16, borderRadius: '50%', backgroundColor: '#ccc' }} />;
                                  }}
                                >
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                    <Typography variant="caption" sx={{ fontWeight: 500 }}>
                                      {phase.phase_name.replace('_', ' ')}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {phase.processing_duration_ms ? `${(phase.processing_duration_ms / 1000).toFixed(1)}s` : ''}
                                    </Typography>
                                  </Box>
                                </StepLabel>
                                <StepContent>
                                  <Box sx={{ mb: 1 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                      <Typography variant="caption" color="text.secondary">
                                        {phase.status}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {phase.progress_percentage || 0}%
                                      </Typography>
                                    </Box>
                                    {phase.status === 'running' && (
                                      <LinearProgress
                                        variant="determinate"
                                        value={phase.progress_percentage || 0}
                                        sx={{
                                          height: 4,
                                          borderRadius: 2,
                                          '& .MuiLinearProgress-bar': {
                                            borderRadius: 2,
                                          }
                                        }}
                                      />
                                    )}
                                    {phase.model_used && phase.model_used !== 'n/a' && (
                                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                                        Model: {phase.model_used}
                                      </Typography>
                                    )}
                                  </Box>
                                </StepContent>
                              </Step>
                            ))}
                          </Stepper>
                        </Box>
                      )}

                      {/* Estimated completion time */}
                      {workflow.status === 'running' && workflow.estimated_completion && (
                        <Box sx={{ mb: 2, p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 500 }}>
                            Estimated completion: {new Date(workflow.estimated_completion).toLocaleTimeString()}
                          </Typography>
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

          {/* Logs Tab */}
          <TabPanel value={activeTab} index={3}>
            <Box sx={{ mb: 2 }}>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={loadLogs}
                sx={{ mr: 1 }}
              >
                Refresh Logs
              </Button>
              <Button
                variant="outlined"
                startIcon={<GetApp />}
                onClick={() => setExportDialog(true)}
              >
                Export Logs
              </Button>
            </Box>

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Email Workflow Logs
                </Typography>
                <Box sx={{ maxHeight: 600, overflow: 'auto' }}>
                  {logs.length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <BugReport sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography variant="h6" color="text.secondary">
                        No logs available
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Logs will appear here when workflows are running
                      </Typography>
                    </Box>
                  ) : (
                    logs.map((log) => (
                      <Box key={log.id} sx={{ display: 'flex', alignItems: 'flex-start', py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          {log.level === 'error' ? <Error color="error" /> :
                           log.level === 'warning' ? <Warning color="warning" /> :
                           log.level === 'info' ? <Info color="info" /> :
                           <BugReport color="disabled" />}
                        </ListItemIcon>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            {log.message}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 2, mt: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatDate(log.timestamp)}
                            </Typography>
                            {log.workflow_phase && (
                              <Chip label={log.workflow_phase} size="small" variant="outlined" />
                            )}
                            {log.email_count !== undefined && (
                              <Typography variant="caption" color="text.secondary">
                                Emails: {log.email_count}
                              </Typography>
                            )}
                          </Box>
                          {log.context && Object.keys(log.context).length > 0 && (
                            <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                              <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                                {JSON.stringify(log.context, null, 2)}
                              </Typography>
                            </Box>
                          )}
                        </Box>
                      </Box>
                    ))
                  )}
                </Box>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Search Tab */}
          <TabPanel value={activeTab} index={4}>
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
                        onChange={(e) => setSearchForm(prev => ({ ...prev, search_type: e.target.value as 'semantic' | 'keyword' | 'hybrid' }))}
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
          <TabPanel value={activeTab} index={5}>
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
          <TabPanel value={activeTab} index={6}>
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
          <TabPanel value={activeTab} index={7}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Email Settings
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Button
                        variant="outlined"
                        startIcon={<Email />}
                        onClick={() => setEmailSettingsDialog(true)}
                      >
                        Email Server Settings
                      </Button>
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
          <TabPanel value={activeTab} index={8}>
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

          {/* Notifications Tab */}
          <TabPanel value={activeTab} index={9}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Email Notifications
                      </Typography>
                      <Button
                        variant="outlined"
                        startIcon={<Settings />}
                        onClick={() => setNotificationSettingsDialog(true)}
                      >
                        Notification Settings
                      </Button>
                    </Box>
                    <Box sx={{ maxHeight: 600, overflow: 'auto' }}>
                      {notifications.length === 0 ? (
                        <Box sx={{ textAlign: 'center', py: 4 }}>
                          <Notifications sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                          <Typography variant="h6" color="text.secondary">
                            No notifications
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Notifications will appear here when workflows run or tasks are created
                          </Typography>
                        </Box>
                      ) : (
                        notifications.map((notification, index) => (
                          <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', py: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                            <ListItemIcon sx={{ minWidth: 40 }}>
                              {notification.type === 'task_created' ? <CheckCircle color="success" /> :
                               notification.type === 'workflow_completed' ? <PlayArrow color="info" /> :
                               notification.type === 'error' ? <Error color="error" /> :
                               <Info color="info" />}
                            </ListItemIcon>
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="body1" sx={{ fontWeight: 600, mb: 0.5 }}>
                                {notification.title}
                              </Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                {notification.message}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                <Typography variant="caption" color="text.secondary">
                                  {formatDate(notification.timestamp)}
                                </Typography>
                                <Chip
                                  label={notification.type.replace('_', ' ')}
                                  size="small"
                                  variant="outlined"
                                />
                              </Box>
                            </Box>
                          </Box>
                        ))
                      )}
                    </Box>
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
              {/* Saved Settings Toggle */}
              {savedEmailSettings && savedEmailSettings.has_password && (
                <Grid item xs={12}>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      You have saved email settings configured. You can use them or enter new ones.
                    </Typography>
                  </Alert>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={useSavedSettings}
                        onChange={(e) => setUseSavedSettings(e.target.checked)}
                      />
                    }
                    label="Use saved email settings"
                  />
                  {useSavedSettings && savedEmailSettings && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                        Using saved settings:
                      </Typography>
                      <Typography variant="body2">
                        Server: {savedEmailSettings.server}:{savedEmailSettings.port}
                      </Typography>
                      <Typography variant="body2">
                        Username: {savedEmailSettings.username}
                      </Typography>
                      <Typography variant="body2">
                        Mailbox: {savedEmailSettings.mailbox || 'INBOX'}
                      </Typography>
                    </Box>
                  )}
                </Grid>
              )}

              {/* Email Configuration Fields - Only show if not using saved settings */}
              {!useSavedSettings && (
                <>
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

              {/* Timeout Settings Section */}
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                  Timeout Settings
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Configure timeout values for email processing operations
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Analysis Timeout"
                  type="number"
                  value={workflowForm.analysis_timeout}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, analysis_timeout: parseInt(e.target.value) || 120 }))}
                  InputProps={{ endAdornment: 'seconds' }}
                  helperText="Maximum time to analyze each email"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Task Conversion Timeout"
                  type="number"
                  value={workflowForm.task_timeout}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, task_timeout: parseInt(e.target.value) || 60 }))}
                  InputProps={{ endAdornment: 'seconds' }}
                  helperText="Maximum time to convert analysis to tasks"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Ollama Request Timeout"
                  type="number"
                  value={workflowForm.ollama_timeout}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, ollama_timeout: parseInt(e.target.value) || 60 }))}
                  InputProps={{ endAdornment: 'seconds' }}
                  helperText="Maximum time for individual Ollama API calls"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Maximum Retries"
                  type="number"
                  value={workflowForm.max_retries}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, max_retries: parseInt(e.target.value) || 3 }))}
                  helperText="Number of retry attempts for failed operations"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Retry Delay"
                  type="number"
                  value={workflowForm.retry_delay}
                  onChange={(e) => setWorkflowForm(prev => ({ ...prev, retry_delay: parseInt(e.target.value) || 1 }))}
                  InputProps={{ endAdornment: 'seconds' }}
                  helperText="Delay between retry attempts"
                />
              </Grid>
                </>
              )}
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

        {/* Email Settings Dialog */}
        <Dialog open={emailSettingsDialog} onClose={() => setEmailSettingsDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Email Server Settings</DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Configure your email server settings to connect to your mailbox. These settings will be saved securely and used for future workflows.
                </Typography>
              </Grid>
              <Grid item xs={12} md={8}>
                <TextField
                  fullWidth
                  label="IMAP Server"
                  value={emailSettingsForm.server}
                  onChange={(e) => setEmailSettingsForm(prev => ({ ...prev, server: e.target.value }))}
                  placeholder="e.g., imap.gmail.com"
                  helperText="Your email provider's IMAP server address"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Port"
                  type="number"
                  value={emailSettingsForm.port}
                  onChange={(e) => setEmailSettingsForm(prev => ({ ...prev, port: parseInt(e.target.value) || 993 }))}
                  helperText="Usually 993 for SSL"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Username"
                  value={emailSettingsForm.username}
                  onChange={(e) => setEmailSettingsForm(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="your-email@example.com"
                  helperText="Your email address"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Password"
                  type="password"
                  value={emailSettingsForm.password}
                  onChange={(e) => setEmailSettingsForm(prev => ({ ...prev, password: e.target.value }))}
                  helperText="Your email password or app password"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Mailbox"
                  value={emailSettingsForm.mailbox}
                  onChange={(e) => setEmailSettingsForm(prev => ({ ...prev, mailbox: e.target.value }))}
                  placeholder="INBOX"
                  helperText="Mailbox folder to process (usually INBOX)"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={emailSettingsForm.use_ssl}
                      onChange={(e) => setEmailSettingsForm(prev => ({ ...prev, use_ssl: e.target.checked }))}
                    />
                  }
                  label="Use SSL/TLS"
                />
              </Grid>
              {savedEmailSettings && (
                <Grid item xs={12}>
                  <Alert severity="info">
                    <Typography variant="body2">
                      <strong>Current saved settings:</strong> {savedEmailSettings.username} @ {savedEmailSettings.server}:{savedEmailSettings.port}
                    </Typography>
                  </Alert>
                </Grid>
              )}
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEmailSettingsDialog(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleUpdateEmailSettings}
              disabled={!emailSettingsForm.server || !emailSettingsForm.username || !emailSettingsForm.password}
            >
              Save Email Settings
            </Button>
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