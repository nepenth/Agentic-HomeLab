import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Chip,
  LinearProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Skeleton,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Snackbar,
  Divider,
} from '@mui/material';
import {
  Email,
  PlayArrow,
  Stop,
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  ExpandMore,
  Description,
  Schedule,
  Assignment,
  BugReport,
  Settings,
  History,
  Delete,
  Done,
  Chat,
  Send,
  Timer,
  Sync,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import EnhancedEmailChat from '../components/EmailAssistant/EnhancedEmailChat';
import EmailSyncDashboard from '../components/EmailAssistant/EmailSyncDashboard';
import WorkflowLogsViewer from '../components/WorkflowLogsViewer';

interface EmailWorkflowStats {
  total_workflows: number;
  active_workflows: number;
  completed_workflows: number;
  total_emails_processed: number;
  total_tasks_created: number;
  pending_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  success_rate: number;
  avg_processing_time: number;
}

interface WorkflowSummary {
  workflows: {
    total: number;
    active: number;
    completed: number;
    failed: number;
    cancelled: number;
    stale: number;
  };
  tasks: {
    total: number;
    pending: number;
    completed: number;
    failed: number;
    running: number;
  };
  needs_cleanup: boolean;
}

interface EmailWorkflowLog {
  id: string;
  workflow_id?: string;
  task_id?: string;
  level: string;
  message: string;
  context: any;
  timestamp: string;
  workflow_phase?: string;
  email_count?: number;
}

interface EmailTask {
  id: string;
  status: string;
  description: string;
  priority: string;
  email_id?: string;
  email_sender?: string;
  email_subject?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  retry_count?: number;
  input: any;
  output?: any;
}

interface EmailContentSectionProps {
  taskId: string;
}

const EmailContentSection: React.FC<EmailContentSectionProps> = ({ taskId }) => {
  const [expanded, setExpanded] = useState(false);
  const [emailContent, setEmailContent] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchEmailContent = async () => {
    if (expanded && !emailContent) {
      setLoading(true);
      try {
        const content = await apiClient.getTaskEmailContent(taskId);
        setEmailContent(content);
      } catch (error) {
        console.error('Failed to fetch email content:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleToggle = () => {
    setExpanded(!expanded);
    if (!expanded) {
      fetchEmailContent();
    }
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Button
        variant="outlined"
        size="small"
        onClick={handleToggle}
        startIcon={expanded ? <ExpandMore sx={{ transform: 'rotate(180deg)' }} /> : <ExpandMore />}
        sx={{ mb: expanded ? 2 : 0 }}
      >
        {expanded ? 'Hide' : 'Show'} Full Email Content
      </Button>
      
      {expanded && (
        <Box sx={{ mt: 1 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
              <Typography variant="body2">Loading email content...</Typography>
            </Box>
          ) : emailContent ? (
            <Paper sx={{ p: 2, bgcolor: 'grey.50', border: '1px solid', borderColor: 'grey.200' }}>
              <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
                Full Email Content
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2"><strong>From:</strong> {emailContent.email_sender}</Typography>
                <Typography variant="body2"><strong>Subject:</strong> {emailContent.email_subject || 'No subject'}</Typography>
              </Box>
              <Box 
                sx={{ 
                  maxHeight: 400, 
                  overflow: 'auto', 
                  bgcolor: 'white', 
                  p: 2, 
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'grey.300',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  whiteSpace: 'pre-wrap'
                }}
              >
                {emailContent.email_content || 'No content available'}
              </Box>
            </Paper>
          ) : (
            <Alert severity="warning">
              Failed to load email content
            </Alert>
          )}
        </Box>
      )}
    </Box>
  );
};

const EmailAssistant: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);
  const [workflowConfigDialogOpen, setWorkflowConfigDialogOpen] = useState(false);
  const [emailSettingsDialogOpen, setEmailSettingsDialogOpen] = useState(false);
  const [timeoutSettingsDialogOpen, setTimeoutSettingsDialogOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [emailSettings, setEmailSettings] = useState<any>(null);
  const [workflowConfigForm, setWorkflowConfigForm] = useState({
    maxEmails: 50,
    importanceThreshold: 0.7,
    spamThreshold: 0.8,
    defaultPriority: 'medium',
    createTasksAutomatically: true,
    scheduleFollowups: true,
    processAttachments: true,
    server: '',
    port: 993,
    username: '',
    password: '',
    use_ssl: true,
    mailbox: 'INBOX',
    // Timeout settings
    analysisTimeout: 120,
    taskTimeout: 60,
    ollamaTimeout: 60,
    maxRetries: 3,
    retryDelay: 1,
  });
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [workflowProgress, setWorkflowProgress] = useState<any>(null);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' | 'warning' } | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch email workflow stats
  const {
    data: workflowStats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['email-workflow-stats'],
    queryFn: async () => {
      try {
        return await apiClient.getEmailDashboardStats() as EmailWorkflowStats;
      } catch (error) {
        console.error('Failed to fetch workflow stats:', error);
        return {
          pending_tasks: 0,
          completed_tasks: 0,
          overdue_tasks: 0,
          active_workflows: 0,
          completed_workflows: 0,
          total_emails_processed: 0
        } as EmailWorkflowStats;
      }
    },
    refetchInterval: 30000,
    retry: false,
    refetchOnWindowFocus: false
  });

  // Fetch email workflow logs
  const {
    data: workflowLogs,
    isLoading: logsLoading,
    error: logsError,
    refetch: refetchLogs,
  } = useQuery({
    queryKey: ['email-workflow-logs'],
    queryFn: async () => {
      try {
        const response = await apiClient.getEmailWorkflowLogs({ limit: 50 });
        return response as EmailWorkflowLog[];
      } catch (error) {
        console.error('Failed to fetch logs:', error);
        return [];
      }
    },
    refetchInterval: 10000,
    retry: false, // Don't retry on failure
    refetchOnWindowFocus: false, // Don't refetch when window gains focus
    enabled: false // Disable automatic fetching for now since endpoint is failing
  });

  // Fetch email tasks
  const {
    data: emailTasks,
    isLoading: tasksLoading,
    error: tasksError,
    refetch: refetchTasks,
  } = useQuery({
    queryKey: ['email-tasks'],
    queryFn: async () => {
      try {
        return await apiClient.getEmailTasks({ limit: 20 }) as EmailTask[];
      } catch (error) {
        console.error('Failed to fetch email tasks:', error);
        return [] as EmailTask[];
      }
    },
    refetchInterval: 15000,
    retry: false,
    refetchOnWindowFocus: false
  });

  // Start workflow mutation
  const startWorkflowMutation = useMutation({
    mutationFn: async (config: any) => {
      return await apiClient.startEmailWorkflowWithSavedSettings(config);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['email-workflow-logs'] });
    },
  });

  // Complete task mutation
  const completeTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      return await apiClient.completeEmailTask(taskId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
    },
  });

  // Mark not important mutation
  const markNotImportantMutation = useMutation({
    mutationFn: async (taskId: string) => {
      return await apiClient.markTaskNotImportant(taskId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      setSnackbar({ open: true, message: 'Task marked as not important. Feedback recorded for future improvements.', severity: 'info' });
    },
    onError: (error) => {
      console.error('Failed to mark task as not important:', error);
      setSnackbar({ open: true, message: 'Failed to mark task as not important', severity: 'error' });
    },
  });

  // Workflow summary query
  const {
    data: workflowSummary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['workflow-summary'],
    queryFn: async () => {
      try {
        return await apiClient.getWorkflowSummary() as WorkflowSummary;
      } catch (error) {
        console.error('Failed to fetch workflow summary:', error);
        return {
          total_workflows: 0,
          active_workflows: 0,
          completed_workflows: 0,
          failed_workflows: 0,
          total_emails_processed: 0,
          total_tasks_created: 0
        } as WorkflowSummary;
      }
    },
    refetchInterval: 30000,
    retry: false,
    refetchOnWindowFocus: false
  });

  // Cleanup mutations
  const cleanupStaleMutation = useMutation({
    mutationFn: async (maxAgeHours: number) => {
      return await apiClient.cleanupStaleWorkflows(maxAgeHours);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      refetchStats();
      refetchSummary();
    },
  });

  const clearAllMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.clearAllWorkflows(true);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      refetchStats();
      refetchSummary();
    },
  });

  const deleteWorkflowMutation = useMutation({
    mutationFn: async (workflowId: string) => {
      return await apiClient.deleteWorkflow(workflowId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      refetchStats();
      refetchSummary();
    },
  });

  const forceCompleteMutation = useMutation({
    mutationFn: async (workflowId: string) => {
      return await apiClient.forceCompleteWorkflow(workflowId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-workflow-stats'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      refetchStats();
      refetchSummary();
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleStartWorkflow = () => {
    startWorkflowMutation.mutate({});
  };

  const handleCompleteTask = (taskId: string) => {
    completeTaskMutation.mutate(taskId);
  };

  const handleMarkNotImportant = (taskId: string) => {
    markNotImportantMutation.mutate(taskId);
  };

  const handleCleanupStale = () => {
    cleanupStaleMutation.mutate(24);
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear ALL workflows? This action cannot be undone.')) {
      clearAllMutation.mutate();
    }
  };

  const handleDeleteWorkflow = (workflowId: string) => {
    if (window.confirm('Are you sure you want to delete this workflow?')) {
      deleteWorkflowMutation.mutate(workflowId);
    }
  };

  const handleForceComplete = (workflowId: string) => {
    forceCompleteMutation.mutate(workflowId);
  };

  const handleSendChatMessage = async () => {
    if (!chatInput.trim()) return;

    const userMessage = {
      role: 'user',
      content: chatInput,
      timestamp: new Date(),
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');

    try {
      // For now, simulate a response. In production, this would call the actual chat API
      const response = await new Promise(resolve =>
        setTimeout(() => resolve({
          role: 'assistant',
          content: `I understand you asked: "${userMessage.content}". I'm here to help with your email workflows and tasks. How can I assist you today?`,
          timestamp: new Date(),
        }), 1000)
      );

      setChatMessages(prev => [...prev, response]);
    } catch (error) {
      console.error('Chat error:', error);
    }
  };

  const handleQuickAction = (action: string) => {
    let message = '';
    switch (action) {
      case 'pending':
        message = 'Show me all my pending tasks from email workflows';
        break;
      case 'inbox':
        message = 'What\'s currently in my email inbox?';
        break;
      case 'urgent':
        message = 'Find all urgent emails that need attention';
        break;
      case 'status':
        message = 'What\'s the current status of my email workflows?';
        break;
      default:
        return;
    }
    setChatInput(message);
  };

  // Load email settings on component mount
  useEffect(() => {
    loadEmailSettings();
  }, []);

  // WebSocket connection management
  useEffect(() => {
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      disconnectWebSocket();
    };
  }, []);

  const loadEmailSettings = async () => {
    try {
      const settings = await apiClient.getEmailSettings();
      setEmailSettings(settings);
      // Populate workflow config form with current settings
      if (settings) {
        const formData = {
          server: settings.server || '',
          port: settings.port || 993,
          username: settings.username || '',
          password: '', // Don't populate password for security
          use_ssl: settings.use_ssl !== false, // Default to true
          mailbox: settings.mailbox || 'INBOX',
        };
        setWorkflowConfigForm(prev => ({ ...prev, ...formData }));
      }
    } catch (error) {
      console.error('Failed to load email settings:', error);
    }
  };


  const handleSaveWorkflowConfig = async () => {
    try {
      // Save email mailbox settings
      await apiClient.updateEmailSettings({
        server: workflowConfigForm.server,
        port: workflowConfigForm.port,
        username: workflowConfigForm.username,
        password: workflowConfigForm.password,
        use_ssl: workflowConfigForm.use_ssl,
        mailbox: workflowConfigForm.mailbox,
      });

      // Save workflow processing settings
      const workflowSettingsData = {
        settings_name: "Default Email Workflow Settings",
        description: "Default settings for email workflow processing",
        max_emails_per_workflow: workflowConfigForm.maxEmails,
        importance_threshold: workflowConfigForm.importanceThreshold,
        spam_threshold: workflowConfigForm.spamThreshold,
        default_task_priority: workflowConfigForm.defaultPriority,
        analysis_timeout_seconds: workflowConfigForm.analysisTimeout,
        task_conversion_timeout_seconds: workflowConfigForm.taskTimeout,
        ollama_request_timeout_seconds: workflowConfigForm.ollamaTimeout,
        max_retries: workflowConfigForm.maxRetries,
        retry_delay_seconds: workflowConfigForm.retryDelay,
        create_tasks_automatically: workflowConfigForm.createTasksAutomatically,
        schedule_followups: workflowConfigForm.scheduleFollowups,
        process_attachments: workflowConfigForm.processAttachments,
      };

      // Try to update existing default settings, or create new ones
      try {
        try {
          // Try to get existing default settings
          await apiClient.getDefaultEmailWorkflowSettings();
          // If successful, update them
          await apiClient.updateDefaultEmailWorkflowSettings(workflowSettingsData);
        } catch (error: any) {
          // If no default settings exist (404), create new ones
          if (error?.response?.status === 404) {
            await apiClient.createEmailWorkflowSettings(workflowSettingsData);
          } else {
            console.warn('Failed to save workflow settings:', error);
          }
        }
      } catch (workflowError) {
        console.warn('Failed to save workflow settings:', workflowError);
        // Continue with success message since email settings were saved
      }

      setSuccess('Email workflow configuration saved successfully!');
      setWorkflowConfigDialogOpen(false);
      setEmailSettingsDialogOpen(false);
      // Reload email settings to update both forms
      loadEmailSettings();
    } catch (error) {
      setError('Failed to save email configuration');
    }
  };

  const handleSaveTimeoutSettings = async () => {
    try {
      // Only save timeout and retry settings to workflow settings
      const timeoutSettingsData = {
        settings_name: "Default Email Workflow Settings",
        description: "Default settings for email workflow processing",
        analysis_timeout_seconds: workflowConfigForm.analysisTimeout,
        task_conversion_timeout_seconds: workflowConfigForm.taskTimeout,
        ollama_request_timeout_seconds: workflowConfigForm.ollamaTimeout,
        max_retries: workflowConfigForm.maxRetries,
        retry_delay_seconds: workflowConfigForm.retryDelay,
      };

      // Try to update existing default settings, or create new ones
      try {
        try {
          // Try to get existing default settings
          await apiClient.getDefaultEmailWorkflowSettings();
          // If successful, update them
          await apiClient.updateDefaultEmailWorkflowSettings(timeoutSettingsData);
        } catch (error: any) {
          // If no default settings exist (404), create new ones
          if (error?.response?.status === 404) {
            await apiClient.createEmailWorkflowSettings(timeoutSettingsData);
          } else {
            console.warn('Failed to save timeout settings:', error);
            setError('Failed to save timeout settings');
            return;
          }
        }
      } catch (workflowError) {
        console.warn('Failed to save timeout settings:', workflowError);
        setError('Failed to save timeout settings');
        return;
      }

      setSuccess('Timeout & Retry Settings saved successfully!');
      setTimeoutSettingsDialogOpen(false);
    } catch (error) {
      setError('Failed to save timeout settings');
    }
  };

  // WebSocket connection for real-time progress updates
  const connectWebSocket = () => {
    try {
      const token = apiClient.getAuthToken();
      if (!token) {
        console.error('No auth token available for WebSocket connection');
        return;
      }

      // Use dedicated WebSocket URL if available, otherwise construct from API URL
      const wsBaseUrl = import.meta.env.VITE_WS_URL || 
        (() => {
          const baseUrl = import.meta.env.VITE_API_BASE_URL || 'https://whyland-ai.nakedsun.xyz:8443/api/v1';
          const cleanUrl = baseUrl.replace(/\/api\/v1$/, '');
          const wsProtocol = cleanUrl.startsWith('https') ? 'wss' : 'ws';
          return `${wsProtocol}://${cleanUrl.replace(/^https?:\/\//, '')}/ws`;
        })();
      const wsUrl = `${wsBaseUrl}/email/progress?token=${encodeURIComponent(token)}`;

      console.log('Attempting WebSocket connection to:', wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected for email progress');
        setWsConnection(ws);
        setError(null); // Clear any previous connection errors
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnection(null);
        // Attempt to reconnect after a delay
        setTimeout(() => connectWebSocket(), 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection failed. Real-time updates may not be available.');
      };

      // Add connection timeout
      setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.warn('WebSocket connection timeout, closing...');
          ws.close();
        }
      }, 10000); // 10 second timeout
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  };

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'connected':
        console.log('WebSocket connected:', data.message);
        break;
      case 'workflow_progress':
        setWorkflowProgress(data);
        break;
      case 'workflow_status':
        // Update workflow status in progress
        setWorkflowProgress(prev => prev ? { ...prev, ...data } : data);
        break;
      case 'phase_update':
        // Update current phase
        setWorkflowProgress(prev => prev ? {
          ...prev,
          current_phase: data.phase,
          progress_percentage: data.progress_percentage,
          items_processed: data.items_processed,
          total_items: data.total_items
        } : data);
        break;
      case 'error':
        console.error('WebSocket error:', data.message);
        setError(data.message);
        break;
      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  };

  const disconnectWebSocket = () => {
    if (wsConnection) {
      wsConnection.close();
      setWsConnection(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'running':
      case 'processing':
        return <PlayArrow color="info" />;
      case 'failed':
        return <Error color="error" />;
      case 'pending':
        return <Schedule color="warning" />;
      default:
        return <Info color="disabled" />;
    }
  };

  const getLogIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return <Error color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'info':
        return <Info color="info" />;
      default:
        return <BugReport color="disabled" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Email Assistant
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI-powered email processing and task management
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => {
              refetchStats();
              refetchLogs();
              refetchTasks();
              refetchSummary();
            }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={handleStartWorkflow}
            disabled={startWorkflowMutation.isPending}
          >
            Start Workflow
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0}>
            <CardContent>
              {statsLoading ? (
                <Skeleton variant="rectangular" height={100} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Total Workflows
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>
                        {workflowStats?.total_workflows || 0}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <Email sx={{ fontSize: 32, color: 'primary.main' }} />
                      {(workflowSummary?.needs_cleanup || (workflowStats?.active_workflows || 0) > 10) && (
                        <Warning sx={{ fontSize: 16, color: 'warning.main', mt: 0.5 }} />
                      )}
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {workflowStats?.active_workflows || 0} active
                    {(workflowSummary?.needs_cleanup || (workflowStats?.active_workflows || 0) > 10) && (
                      <Chip
                        label="Cleanup needed"
                        size="small"
                        color="warning"
                        sx={{ ml: 1, fontSize: '0.7rem', height: 18 }}
                      />
                    )}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0}>
            <CardContent>
              {statsLoading ? (
                <Skeleton variant="rectangular" height={100} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Emails Processed
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                        {workflowStats?.total_emails_processed || 0}
                      </Typography>
                    </Box>
                    <Description sx={{ fontSize: 40, color: 'info.main' }} />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Success rate: {workflowStats?.success_rate?.toFixed(1) || 0}%
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0}>
            <CardContent>
              {statsLoading ? (
                <Skeleton variant="rectangular" height={100} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Tasks Created
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                        {workflowStats?.total_tasks_created || 0}
                      </Typography>
                    </Box>
                    <Assignment sx={{ fontSize: 40, color: 'success.main' }} />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {workflowStats?.pending_tasks || 0} pending
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0}>
            <CardContent>
              {statsLoading ? (
                <Skeleton variant="rectangular" height={100} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Overdue Tasks
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main' }}>
                        {workflowStats?.overdue_tasks || 0}
                      </Typography>
                    </Box>
                    <Warning sx={{ fontSize: 40, color: 'warning.main' }} />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Need attention
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Card elevation={0}>
        <CardContent>
          <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
            <Tab label="Dashboard" />
            <Tab label="Tasks" />
            <Tab label="Logs" />
            <Tab label="Chat" icon={<Chat />} iconPosition="start" />
            <Tab label="Email Sync" icon={<Sync />} iconPosition="start" />
            <Tab label="Management" />
            <Tab label="Workflow Settings" />
          </Tabs>

          {/* Dashboard Tab */}
          {activeTab === 0 && (
            <Box>
              {/* Email Configuration Status */}
              {/* Active Workflow Progress */}
              <Card elevation={2} sx={{ mb: 3, border: '2px solid', borderColor: 'primary.main' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <PlayArrow sx={{ mr: 1 }} />
                    Workflow Progress & Status
                  </Typography>

                  {workflowProgress ? (
                    <>
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          Current Phase: {workflowProgress.current_phase || 'Initializing'}
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={workflowProgress.progress_percentage || 0}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                        <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                          {workflowProgress.progress_percentage || 0}% Complete
                          {workflowProgress.items_processed !== undefined && workflowProgress.total_items !== undefined &&
                            ` • ${workflowProgress.items_processed}/${workflowProgress.total_items} items processed`
                          }
                        </Typography>
                      </Box>

                      <Grid container spacing={2}>
                        <Grid item xs={6} sm={3}>
                          <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="primary.main" sx={{ fontWeight: 700 }}>
                              {workflowProgress.emails_processed || 0}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Emails Processed
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="success.main" sx={{ fontWeight: 700 }}>
                              {workflowProgress.tasks_created || 0}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Tasks Created
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="info.main" sx={{ fontWeight: 700 }}>
                              {workflowProgress.workflow_id ? workflowProgress.workflow_id.slice(-8) : 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Workflow ID
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color={
                              workflowProgress.status === 'running' ? 'info.main' :
                              workflowProgress.status === 'completed' ? 'success.main' :
                              workflowProgress.status === 'failed' ? 'error.main' : 'warning.main'
                            } sx={{ fontWeight: 700 }}>
                              {workflowProgress.status || 'Unknown'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Status
                            </Typography>
                          </Box>
                        </Grid>
                      </Grid>
                    </>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                        No active workflow running
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Start an email workflow to see real-time progress updates here
                      </Typography>
                      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 1 }}>
                        <Chip
                          label={`WebSocket: ${wsConnection ? 'Connected' : 'Disconnected'}`}
                          size="small"
                          color={wsConnection ? 'success' : 'warning'}
                        />
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>

              {!emailSettings && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  <Typography variant="body2">
                    <strong>Email Not Configured:</strong> Configure your email settings to enable workflows.
                    <Button
                      size="small"
                      variant="outlined"
                      sx={{ ml: 2 }}
                      onClick={() => setWorkflowConfigDialogOpen(true)}
                    >
                      Configure Now
                    </Button>
                  </Typography>
                </Alert>
              )}

              {emailSettings && (
                <Alert severity="success" sx={{ mb: 3 }}>
                  <Typography variant="body2">
                    <strong>Email Configured:</strong> {emailSettings.username} @ {emailSettings.server}:{emailSettings.port}
                  </Typography>
                </Alert>
              )}

              {/* Primary action - cleaner and more focused */}
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center',
                py: 4,
                borderRadius: 3,
                bgcolor: 'grey.50',
                border: '1px solid',
                borderColor: 'grey.200'
              }}>
                <Box sx={{ textAlign: 'center', maxWidth: 400 }}>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                    {emailSettings ? 'Ready to Process Emails' : 'Email Configuration Required'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    {emailSettings 
                      ? 'Start an intelligent email workflow to automatically analyze emails and create actionable tasks.'
                      : 'Configure your email settings to begin processing emails with AI-powered analysis.'
                    }
                  </Typography>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={emailSettings ? <PlayArrow /> : <Settings />}
                    onClick={emailSettings ? handleStartWorkflow : () => setEmailSettingsDialogOpen(true)}
                    disabled={startWorkflowMutation.isPending}
                    sx={{ 
                      px: 4,
                      py: 1.5,
                      borderRadius: 2,
                      textTransform: 'none',
                      fontWeight: 600
                    }}
                  >
                    {emailSettings ? 'Start Email Workflow' : 'Configure Email Settings'}
                  </Button>
                </Box>
              </Box>
          </Box>
        )}

          {/* Tasks Tab - Modern Card Grid */}
          {activeTab === 1 && (
            <Box>
              {/* Header with Filters */}
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                mb: 4,
                pb: 2,
                borderBottom: '1px solid',
                borderColor: 'divider'
              }}>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
                    Email Tasks
                  </Typography>
                  {emailTasks && emailTasks.length > 0 && (
                    <Typography variant="body2" color="text.secondary">
                      {emailTasks.length} tasks • 
                      {emailTasks.filter(t => t.status === 'pending').length} pending • 
                      {emailTasks.filter(t => t.status === 'completed').length} completed
                    </Typography>
                  )}
                </Box>
                <Box sx={{ display: 'flex', gap: 1.5 }}>
                  <Select
                    size="small"
                    defaultValue="all"
                    displayEmpty
                    sx={{ 
                      minWidth: 120, 
                      borderRadius: 2,
                      '& .MuiSelect-select': { py: 1 }
                    }}
                  >
                    <MenuItem value="all">All Status</MenuItem>
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="completed">Completed</MenuItem>
                    <MenuItem value="failed">Failed</MenuItem>
                  </Select>
                  <Select
                    size="small"
                    defaultValue="all"
                    displayEmpty
                    sx={{ 
                      minWidth: 120,
                      borderRadius: 2,
                      '& .MuiSelect-select': { py: 1 }
                    }}
                  >
                    <MenuItem value="all">All Priority</MenuItem>
                    <MenuItem value="urgent">Urgent</MenuItem>
                    <MenuItem value="high">High</MenuItem>
                    <MenuItem value="medium">Medium</MenuItem>
                    <MenuItem value="low">Low</MenuItem>
                  </Select>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={refetchTasks}
                    startIcon={<Refresh />}
                    sx={{ 
                      borderRadius: 2,
                      px: 2,
                      py: 1,
                      textTransform: 'none',
                      fontWeight: 500
                    }}
                  >
                    Refresh
                  </Button>
                </Box>
              </Box>

              {/* Loading State */}
              {tasksLoading && (
                <Grid container spacing={3}>
                  {[...Array(6)].map((_, index) => (
                    <Grid item xs={12} sm={6} lg={4} key={index}>
                      <Card sx={{ 
                        height: 280,
                        borderRadius: 3,
                        border: '1px solid',
                        borderColor: 'grey.200'
                      }}>
                        <CardContent sx={{ p: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                            <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2 }} />
                            <Box sx={{ flex: 1 }}>
                              <Skeleton variant="text" width="60%" height={16} />
                              <Skeleton variant="text" width="40%" height={14} />
                            </Box>
                          </Box>
                          <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
                          <Skeleton variant="text" width="80%" height={20} sx={{ mb: 2 }} />
                          <Skeleton variant="rectangular" width="100%" height={60} sx={{ borderRadius: 1, mb: 2 }} />
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Skeleton variant="rectangular" width={80} height={32} sx={{ borderRadius: 2 }} />
                            <Skeleton variant="rectangular" width={60} height={32} sx={{ borderRadius: 2 }} />
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}

              {/* Empty State */}
              {!tasksLoading && (!emailTasks || emailTasks.length === 0) && (
                <Box sx={{ 
                  textAlign: 'center', 
                  py: 8,
                  px: 4,
                  borderRadius: 3,
                  bgcolor: 'grey.50',
                  border: '2px dashed',
                  borderColor: 'grey.300'
                }}>
                  <Assignment sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" sx={{ mb: 1, fontWeight: 600 }}>
                    No Email Tasks Yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 400, mx: 'auto' }}>
                    Start an email workflow to automatically generate intelligent tasks from your emails using AI analysis.
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<PlayArrow />}
                    onClick={handleStartWorkflow}
                    disabled={startWorkflowMutation.isPending || !emailSettings}
                    sx={{ 
                      borderRadius: 2,
                      px: 3,
                      py: 1.5,
                      textTransform: 'none',
                      fontWeight: 600
                    }}
                  >
                    {emailSettings ? 'Start Email Workflow' : 'Configure Email Settings First'}
                  </Button>
                </Box>
              )}

              {/* Task Cards Grid */}
              {!tasksLoading && emailTasks && emailTasks.length > 0 && (
                <Grid container spacing={3}>
                  {emailTasks.map((task) => {
                    const isExpanded = expandedTask === task.id;
                    
                    // Generate sender initials
                    const getSenderInitials = (sender: string) => {
                      if (!sender) return '?';
                      return sender.split(' ').map(word => word.charAt(0)).join('').toUpperCase().slice(0, 2);
                    };

                    // Get priority color
                    const getPriorityColor = (priority: string) => {
                      switch (priority) {
                        case 'urgent': return '#ff3b30';
                        case 'high': return '#ff9500';
                        case 'medium': return '#007aff';
                        case 'low': return '#34c759';
                        default: return '#8e8e93';
                      }
                    };

                    // Get status color
                    const getStatusColor = (status: string) => {
                      switch (status) {
                        case 'completed': return '#34c759';
                        case 'pending': return '#ff9500';
                        case 'failed': return '#ff3b30';
                        default: return '#8e8e93';
                      }
                    };

                    return (
                      <Grid item xs={12} sm={6} lg={4} key={task.id}>
                        <Card sx={{
                          height: isExpanded ? 'auto' : 320,
                          borderRadius: 3,
                          border: '1px solid',
                          borderColor: task.status === 'pending' ? 'primary.light' : 'grey.200',
                          boxShadow: task.status === 'pending' ? '0 4px 20px rgba(25, 118, 210, 0.08)' : '0 2px 12px rgba(0,0,0,0.04)',
                          transition: 'all 0.3s ease',
                          cursor: 'pointer',
                          position: 'relative',
                          overflow: 'visible',
                          '&:hover': {
                            transform: 'translateY(-2px)',
                            boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
                            borderColor: 'primary.main',
                          }
                        }}>
                          {/* Priority Indicator */}
                          <Box sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: 4,
                            bgcolor: getPriorityColor(task.priority),
                            borderRadius: '12px 12px 0 0'
                          }} />

                          <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                            {/* Header */}
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                              {/* Sender Avatar */}
                              <Box sx={{
                                width: 40,
                                height: 40,
                                borderRadius: '50%',
                                bgcolor: getPriorityColor(task.priority),
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                mr: 2,
                                color: 'white',
                                fontWeight: 700,
                                fontSize: '0.875rem'
                              }}>
                                {getSenderInitials(task.email_sender || 'Unknown')}
                              </Box>
                              
                              <Box sx={{ flex: 1, minWidth: 0 }}>
                                <Typography variant="body2" color="text.secondary" sx={{ 
                                  fontSize: '0.75rem',
                                  fontWeight: 500,
                                  textTransform: 'uppercase',
                                  letterSpacing: 0.5
                                }}>
                                  {task.input?.type?.replace('email_', '') || 'Task'}
                                </Typography>
                                <Typography variant="body2" sx={{ 
                                  fontWeight: 600,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}>
                                  {task.email_sender || 'Unknown Sender'}
                                </Typography>
                              </Box>

                              {/* Status Indicator */}
                              <Box sx={{
                                width: 12,
                                height: 12,
                                borderRadius: '50%',
                                bgcolor: getStatusColor(task.status),
                                flexShrink: 0
                              }} />
                            </Box>

                            {/* Task Description */}
                            <Typography variant="h6" sx={{ 
                              fontWeight: 600,
                              mb: 1,
                              fontSize: '1rem',
                              lineHeight: 1.3,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden'
                            }}>
                              {task.description}
                            </Typography>

                            {/* Email Subject */}
                            <Typography variant="body2" color="text.secondary" sx={{ 
                              mb: 2,
                              display: '-webkit-box',
                              WebkitLineClamp: 1,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden'
                            }}>
                              {task.email_subject || 'No subject'}
                            </Typography>

                            {/* Metadata */}
                            <Box sx={{ mb: 2, flex: 1 }}>
                              {task.input?.importance_score && (
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                  <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                                    Importance:
                                  </Typography>
                                  <Box sx={{ 
                                    flex: 1, 
                                    height: 4, 
                                    bgcolor: 'grey.200', 
                                    borderRadius: 2,
                                    overflow: 'hidden'
                                  }}>
                                    <Box sx={{
                                      width: `${task.input.importance_score * 100}%`,
                                      height: '100%',
                                      bgcolor: getPriorityColor(task.priority),
                                      transition: 'width 0.3s ease'
                                    }} />
                                  </Box>
                                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1, fontWeight: 600 }}>
                                    {(task.input.importance_score * 100).toFixed(0)}%
                                  </Typography>
                                </Box>
                              )}
                              
                              {task.created_at && (
                                <Typography variant="caption" color="text.secondary">
                                  {new Date(task.created_at).toLocaleDateString()} • {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </Typography>
                              )}
                            </Box>

                            {/* Suggested Actions Preview */}
                            {task.input?.suggested_actions && task.input.suggested_actions.length > 0 && !isExpanded && (
                              <Box sx={{ mb: 2 }}>
                                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                  {task.input.suggested_actions.slice(0, 2).map((action: string, index: number) => (
                                    <Chip 
                                      key={index} 
                                      label={action} 
                                      size="small" 
                                      variant="outlined"
                                      sx={{ 
                                        fontSize: '0.6875rem',
                                        height: 20,
                                        borderRadius: 1,
                                        '& .MuiChip-label': { px: 1 }
                                      }}
                                    />
                                  ))}
                                  {task.input.suggested_actions.length > 2 && (
                                    <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5, alignSelf: 'center' }}>
                                      +{task.input.suggested_actions.length - 2} more
                                    </Typography>
                                  )}
                                </Box>
                              </Box>
                            )}

                            {/* Expanded Content */}
                            {isExpanded && (
                              <Box sx={{ mb: 2 }}>
                                {/* All Suggested Actions */}
                                {task.input?.suggested_actions && task.input.suggested_actions.length > 0 && (
                                  <Box sx={{ mb: 2 }}>
                                    <Typography variant="subtitle2" color="primary" sx={{ mb: 1, fontWeight: 600 }}>
                                      Suggested Actions
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                      {task.input.suggested_actions.map((action: string, index: number) => (
                                        <Chip 
                                          key={index} 
                                          label={action} 
                                          size="small" 
                                          variant="outlined"
                                          sx={{ 
                                            fontSize: '0.75rem',
                                            borderRadius: 1.5
                                          }}
                                        />
                                      ))}
                                    </Box>
                                  </Box>
                                )}

                                {/* Email Content */}
                                <EmailContentSection taskId={task.id} />
                                
                                {/* Error Message */}
                                {task.error_message && (
                                  <Alert severity="error" sx={{ mt: 2 }}>
                                    {task.error_message}
                                  </Alert>
                                )}
                              </Box>
                            )}

                            {/* Actions */}
                            <Box sx={{ 
                              display: 'flex', 
                              gap: 1, 
                              mt: 'auto',
                              pt: 2,
                              borderTop: isExpanded ? '1px solid' : 'none',
                              borderColor: 'grey.200'
                            }}>
                              {/* Expand/Collapse */}
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedTask(isExpanded ? null : task.id);
                                }}
                                sx={{ 
                                  borderRadius: 2,
                                  textTransform: 'none',
                                  fontWeight: 500,
                                  px: 2,
                                  flex: 1
                                }}
                              >
                                {isExpanded ? 'Show Less' : 'Show More'}
                              </Button>

                              {/* Task Actions */}
                              {task.status === 'pending' && (
                                <>
                                  <Button
                                    size="small"
                                    variant="contained"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleCompleteTask(task.id);
                                    }}
                                    sx={{ 
                                      borderRadius: 2,
                                      textTransform: 'none',
                                      fontWeight: 600,
                                      px: 2,
                                      bgcolor: '#34c759',
                                      '&:hover': { bgcolor: '#30b754' }
                                    }}
                                  >
                                    Complete
                                  </Button>
                                  <IconButton
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleMarkNotImportant(task.id);
                                    }}
                                    sx={{ 
                                      bgcolor: 'grey.100',
                                      borderRadius: 2,
                                      '&:hover': { bgcolor: 'grey.200' }
                                    }}
                                  >
                                    <Delete sx={{ fontSize: 16 }} />
                                  </IconButton>
                                </>
                              )}

                              {task.status === 'completed' && (
                                <Chip
                                  label="Completed"
                                  size="small"
                                  sx={{ 
                                    bgcolor: '#34c759',
                                    color: 'white',
                                    fontWeight: 600,
                                    borderRadius: 2
                                  }}
                                />
                              )}
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    );
                  })}
                </Grid>
              )}
            </Box>
          )}

          {/* Logs Tab */}
          {activeTab === 2 && (
            <Box>
              <WorkflowLogsViewer
                workflowType="email_sync"
                title="Email Workflow Logs"
                height={650}
              />
            </Box>
          )}

          {/* Chat Tab */}
          {activeTab === 3 && (
            <EnhancedEmailChat />
          )}

          {/* Email Sync Tab */}
          {activeTab === 4 && (
            <EmailSyncDashboard />
          )}

          {/* Management Tab */}
          {activeTab === 5 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 3 }}>Workflow Management</Typography>

              {/* Workflow Summary */}
              <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={6} lg={3}>
                  <Card elevation={0}>
                    <CardContent>
                      {summaryLoading ? (
                        <Skeleton variant="rectangular" height={100} />
                      ) : (
                        <>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box>
                              <Typography color="text.secondary" gutterBottom variant="h6">
                                Total Workflows
                              </Typography>
                              <Typography variant="h3" sx={{ fontWeight: 700 }}>
                                {workflowSummary?.workflows.total || 0}
                              </Typography>
                            </Box>
                            <Email sx={{ fontSize: 40, color: 'primary.main' }} />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            {workflowSummary?.workflows.active || 0} active, {workflowSummary?.workflows.stale || 0} stale
                          </Typography>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} lg={3}>
                  <Card elevation={0}>
                    <CardContent>
                      {summaryLoading ? (
                        <Skeleton variant="rectangular" height={100} />
                      ) : (
                        <>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box>
                              <Typography color="text.secondary" gutterBottom variant="h6">
                                Total Tasks
                              </Typography>
                              <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                                {workflowSummary?.tasks.total || 0}
                              </Typography>
                            </Box>
                            <Assignment sx={{ fontSize: 40, color: 'info.main' }} />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            {workflowSummary?.tasks.pending || 0} pending, {workflowSummary?.tasks.running || 0} running
                          </Typography>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} lg={3}>
                  <Card elevation={0}>
                    <CardContent>
                      {summaryLoading ? (
                        <Skeleton variant="rectangular" height={100} />
                      ) : (
                        <>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box>
                              <Typography color="text.secondary" gutterBottom variant="h6">
                                Failed Workflows
                              </Typography>
                              <Typography variant="h3" sx={{ fontWeight: 700, color: 'error.main' }}>
                                {workflowSummary?.workflows.failed || 0}
                              </Typography>
                            </Box>
                            <Error sx={{ fontSize: 40, color: 'error.main' }} />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            Need attention
                          </Typography>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} lg={3}>
                  <Card elevation={0}>
                    <CardContent>
                      {summaryLoading ? (
                        <Skeleton variant="rectangular" height={100} />
                      ) : (
                        <>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Box>
                              <Typography color="text.secondary" gutterBottom variant="h6">
                                Cleanup Status
                              </Typography>
                              <Typography variant="h3" sx={{ fontWeight: 700, color: workflowSummary?.needs_cleanup ? 'warning.main' : 'success.main' }}>
                                {workflowSummary?.needs_cleanup ? 'Needed' : 'Clean'}
                              </Typography>
                            </Box>
                            <Warning sx={{ fontSize: 40, color: workflowSummary?.needs_cleanup ? 'warning.main' : 'success.main' }} />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            System health
                          </Typography>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Cleanup Actions */}
              <Card elevation={0} sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Cleanup Operations</Typography>
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Button
                      variant="outlined"
                      startIcon={<Refresh />}
                      onClick={handleCleanupStale}
                      disabled={cleanupStaleMutation.isPending}
                      color="warning"
                    >
                      Clean Stale Workflows
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<Error />}
                      onClick={handleClearAll}
                      disabled={clearAllMutation.isPending}
                      color="error"
                    >
                      Clear ALL Workflows
                    </Button>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Use "Clean Stale Workflows" to remove workflows that have been running for more than 24 hours.
                    Use "Clear ALL Workflows" only as a last resort - this will delete all workflow data.
                  </Typography>
                </CardContent>
              </Card>

              {/* Workflow Status Breakdown */}
              <Card elevation={0}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2 }}>Workflow Status Breakdown</Typography>
                  {summaryLoading ? (
                    <Skeleton variant="rectangular" height={200} />
                  ) : (
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle1" sx={{ mb: 1 }}>Workflows by Status</Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Active:</Typography>
                            <Chip label={workflowSummary?.workflows.active || 0} size="small" color="primary" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Completed:</Typography>
                            <Chip label={workflowSummary?.workflows.completed || 0} size="small" color="success" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Failed:</Typography>
                            <Chip label={workflowSummary?.workflows.failed || 0} size="small" color="error" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Cancelled:</Typography>
                            <Chip label={workflowSummary?.workflows.cancelled || 0} size="small" color="default" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Stale:</Typography>
                            <Chip label={workflowSummary?.workflows.stale || 0} size="small" color="warning" />
                          </Box>
                        </Box>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle1" sx={{ mb: 1 }}>Tasks by Status</Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Pending:</Typography>
                            <Chip label={workflowSummary?.tasks.pending || 0} size="small" color="warning" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Running:</Typography>
                            <Chip label={workflowSummary?.tasks.running || 0} size="small" color="info" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Completed:</Typography>
                            <Chip label={workflowSummary?.tasks.completed || 0} size="small" color="success" />
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Failed:</Typography>
                            <Chip label={workflowSummary?.tasks.failed || 0} size="small" color="error" />
                          </Box>
                        </Box>
                      </Grid>
                    </Grid>
                  )}
                </CardContent>
              </Card>

              {/* Cleanup Operations */}
              <Card elevation={0} sx={{ mb: 3, border: '2px solid', borderColor: 'warning.main' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'warning.main' }}>
                    🧹 Cleanup Operations
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    These operations help manage development and testing by clearing tasks and processing history.
                    Use with caution as these actions cannot be undone.
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6} lg={4}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
                            Delete All Tasks
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Removes all email tasks from the system. Email processing history remains intact.
                          </Typography>
                          <Button 
                            variant="contained" 
                            color="warning"
                            fullWidth
                            startIcon={<Delete />}
                            onClick={async () => {
                              if (window.confirm('Are you sure you want to delete all tasks? This action cannot be undone.')) {
                                try {
                                  const result = await apiClient.cleanupAllTasks();
                                  setSnackbar({
                                    open: true,
                                    message: result.message || 'All tasks deleted successfully',
                                    severity: 'success'
                                  });
                                  // Refresh data
                                  refetchSummary();
                                  refetchTasks();
                                } catch (error) {
                                  setSnackbar({
                                    open: true,
                                    message: 'Failed to delete tasks',
                                    severity: 'error'
                                  });
                                }
                              }
                            }}
                          >
                            Delete Tasks
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12} md={6} lg={4}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
                            Reset Processing History
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Clears workflow history and logs. Emails will be reprocessed as new on next run.
                          </Typography>
                          <Button 
                            variant="contained" 
                            color="warning"
                            fullWidth
                            startIcon={<Refresh />}
                            onClick={async () => {
                              if (window.confirm('Are you sure you want to reset processing history? Emails will be reprocessed on next workflow run.')) {
                                try {
                                  const result = await apiClient.cleanupProcessingHistory();
                                  setSnackbar({
                                    open: true,
                                    message: result.message || 'Processing history reset successfully',
                                    severity: 'success'
                                  });
                                  // Refresh data
                                  refetchSummary();
                                  refetchLogs();
                                } catch (error) {
                                  setSnackbar({
                                    open: true,
                                    message: 'Failed to reset processing history',
                                    severity: 'error'
                                  });
                                }
                              }
                            }}
                          >
                            Reset History
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12} md={12} lg={4}>
                      <Card variant="outlined" sx={{ border: '2px solid', borderColor: 'error.main' }}>
                        <CardContent>
                          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, color: 'error.main' }}>
                            Complete Reset
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Deletes ALL tasks and processing history. This is a complete fresh start.
                          </Typography>
                          <Button 
                            variant="contained" 
                            color="error"
                            fullWidth
                            startIcon={<Warning />}
                            onClick={async () => {
                              if (window.confirm('⚠️ DANGER: This will delete ALL tasks and processing history. Are you absolutely sure?')) {
                                if (window.confirm('This action cannot be undone. Type "CONFIRM" to proceed.') && 
                                    window.prompt('Type CONFIRM to proceed:') === 'CONFIRM') {
                                  try {
                                    const result = await apiClient.completeCleanupReset();
                                    setSnackbar({
                                      open: true,
                                      message: result.message || 'Complete reset successful',
                                      severity: 'success'
                                    });
                                    // Refresh all data
                                    refetchSummary();
                                    refetchTasks();
                                    refetchLogs();
                                    refetchStats();
                                  } catch (error) {
                                    setSnackbar({
                                      open: true,
                                      message: 'Failed to perform complete reset',
                                      severity: 'error'
                                    });
                                  }
                                }
                              }
                            }}
                          >
                            Complete Reset
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Box>
          )}

          {/* Workflow Settings Tab */}
          {activeTab === 6 && (
            <Box>
              <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
                Workflow Settings
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                Configure processing parameters, automation settings, and performance options for email workflows.
              </Typography>

              {/* Email Workflow Configuration */}
              <Card elevation={0} sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                    Email Workflow Configuration
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Configure processing parameters and automation settings for email workflows.
                  </Typography>

                  <Grid container spacing={3}>
                    {/* Workflow Processing Options */}
                    <Grid item xs={12}>
                      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                        Processing Parameters
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Max Emails per Workflow"
                        type="number"
                        value={workflowConfigForm.maxEmails}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, maxEmails: parseInt(e.target.value) || 50 }))}
                        helperText="Maximum number of emails to process in a single workflow"
                        size="small"
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Importance Threshold"
                        type="number"
                        inputProps={{ min: 0, max: 1, step: 0.1 }}
                        value={workflowConfigForm.importanceThreshold}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, importanceThreshold: parseFloat(e.target.value) || 0.7 }))}
                        helperText="Minimum importance score to create tasks (0-1)"
                        size="small"
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Spam Threshold"
                        type="number"
                        inputProps={{ min: 0, max: 1, step: 0.1 }}
                        value={workflowConfigForm.spamThreshold}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, spamThreshold: parseFloat(e.target.value) || 0.8 }))}
                        helperText="Spam detection threshold (0-1)"
                        size="small"
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Default Priority</InputLabel>
                        <Select
                          value={workflowConfigForm.defaultPriority}
                          onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, defaultPriority: e.target.value }))}
                          label="Default Priority"
                        >
                          <MenuItem value="low">Low</MenuItem>
                          <MenuItem value="medium">Medium</MenuItem>
                          <MenuItem value="high">High</MenuItem>
                          <MenuItem value="urgent">Urgent</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>

                    {/* Automation Settings */}
                    <Grid item xs={12}>
                      <Typography variant="subtitle1" sx={{ mb: 2, mt: 2, fontWeight: 600 }}>
                        Automation Settings
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={workflowConfigForm.createTasksAutomatically}
                            onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, createTasksAutomatically: e.target.checked }))}
                          />
                        }
                        label="Create Tasks Automatically"
                      />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={workflowConfigForm.scheduleFollowups}
                            onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, scheduleFollowups: e.target.checked }))}
                          />
                        }
                        label="Schedule Follow-ups"
                      />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={workflowConfigForm.processAttachments}
                            onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, processAttachments: e.target.checked }))}
                          />
                        }
                        label="Process Attachments"
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Timeout & Retry Settings */}
              <Card elevation={0} sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                    Timeout & Retry Settings
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Configure timeout and retry parameters for email processing operations.
                  </Typography>

                  <Grid container spacing={3}>
                    {/* Timeout Settings */}
                    <Grid item xs={12}>
                      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                        Timeout Settings
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Set maximum time limits for various email processing operations
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        label="Analysis Timeout"
                        type="number"
                        value={workflowConfigForm.analysisTimeout}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, analysisTimeout: parseInt(e.target.value) || 120 }))}
                        InputProps={{ endAdornment: 'seconds' }}
                        helperText="Maximum time to analyze each email"
                        size="small"
                      />
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        label="Task Conversion Timeout"
                        type="number"
                        value={workflowConfigForm.taskTimeout}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, taskTimeout: parseInt(e.target.value) || 60 }))}
                        InputProps={{ endAdornment: 'seconds' }}
                        helperText="Maximum time to convert analysis to tasks"
                        size="small"
                      />
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        label="Ollama Request Timeout"
                        type="number"
                        value={workflowConfigForm.ollamaTimeout}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, ollamaTimeout: parseInt(e.target.value) || 60 }))}
                        InputProps={{ endAdornment: 'seconds' }}
                        helperText="Maximum time for individual Ollama API calls"
                        size="small"
                      />
                    </Grid>

                    {/* Retry Settings */}
                    <Grid item xs={12}>
                      <Typography variant="subtitle1" sx={{ mb: 2, mt: 2, fontWeight: 600 }}>
                        Retry Settings
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Configure retry behavior for failed operations
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Maximum Retries"
                        type="number"
                        value={workflowConfigForm.maxRetries}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, maxRetries: parseInt(e.target.value) || 3 }))}
                        helperText="Number of retry attempts for failed operations"
                        size="small"
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Retry Delay"
                        type="number"
                        value={workflowConfigForm.retryDelay}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, retryDelay: parseInt(e.target.value) || 1 }))}
                        InputProps={{ endAdornment: 'seconds' }}
                        helperText="Delay between retry attempts"
                        size="small"
                      />
                    </Grid>

                    {/* Save Button */}
                    <Grid item xs={12}>
                      <Divider sx={{ my: 2 }} />
                      <Button
                        variant="contained"
                        startIcon={<Settings />}
                        onClick={handleSaveWorkflowConfig}
                        sx={{ mt: 1 }}
                      >
                        Save Workflow Settings
                      </Button>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* System Settings */}
              <Card elevation={0}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                    System Settings
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Access global system settings and preferences.
                  </Typography>

                  <Button
                    variant="outlined"
                    startIcon={<Settings />}
                    onClick={() => window.location.href = '/settings'}
                  >
                    Go to Main Settings
                  </Button>
                </CardContent>
              </Card>
            </Box>
          )}

          {/* Logs Dialog */}
      <Dialog
        open={logsDialogOpen}
        onClose={() => setLogsDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Email Workflow Logs</DialogTitle>
        <DialogContent>
          <Box sx={{ maxHeight: 500, overflow: 'auto' }}>
            {(workflowLogs || []).map((log) => (
              <Box key={log.id} sx={{ display: 'flex', alignItems: 'flex-start', py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {getLogIcon(log.level)}
                </ListItemIcon>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {log.message}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2, mt: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      {formatTimestamp(log.timestamp)}
                    </Typography>
                    {log.workflow_phase && (
                      <Chip label={log.workflow_phase} size="small" variant="outlined" />
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
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>


      {/* Email Settings Dialog */}
      <Dialog
        open={emailSettingsDialogOpen}
        onClose={() => setEmailSettingsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Configure Mailbox Settings</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure your email server connection settings for mailbox access.
              </Typography>
            </Grid>

            <Grid item xs={12} md={8}>
              <TextField
                fullWidth
                label="IMAP Server"
                value={workflowConfigForm.server}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, server: e.target.value }))}
                placeholder="e.g., imap.gmail.com"
                helperText="Your email provider's IMAP server address"
                required
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Port"
                type="number"
                value={workflowConfigForm.port}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, port: parseInt(e.target.value) || 993 }))}
                helperText="Usually 993 for SSL"
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Username"
                value={workflowConfigForm.username}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, username: e.target.value }))}
                placeholder="your-email@example.com"
                helperText="Your email address"
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={workflowConfigForm.password}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, password: e.target.value }))}
                helperText="Your email password or app password"
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Mailbox"
                value={workflowConfigForm.mailbox}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, mailbox: e.target.value }))}
                placeholder="INBOX"
                helperText="Mailbox folder to process (usually INBOX)"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={workflowConfigForm.use_ssl}
                    onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, use_ssl: e.target.checked }))}
                  />
                }
                label="Use SSL/TLS"
              />
            </Grid>

            {emailSettings && (
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Current saved settings:</strong> {emailSettings.username} @ {emailSettings.server}:{emailSettings.port}
                    {emailSettings.has_password && ' (Password saved)'}
                  </Typography>
                </Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              <Alert severity="warning">
                <Typography variant="body2">
                  <strong>Security Note:</strong> Your password will be encrypted before storage. Make sure to use an app password if your email provider requires 2FA.
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEmailSettingsDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveWorkflowConfig}
            disabled={!workflowConfigForm.server || !workflowConfigForm.username || !workflowConfigForm.password}
          >
            Save Mailbox Settings
          </Button>
        </DialogActions>
      </Dialog>

      {/* Workflow Configuration Dialog */}
      <Dialog
        open={workflowConfigDialogOpen}
        onClose={() => setWorkflowConfigDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Configure Workflow Settings</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure processing parameters and automation settings for email workflows.
              </Typography>
            </Grid>

            {/* Workflow Processing Options */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Email Workflow Configuration
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure processing parameters and automation settings
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Max Emails per Workflow"
                type="number"
                value={workflowConfigForm.maxEmails}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, maxEmails: parseInt(e.target.value) || 50 }))}
                helperText="Maximum number of emails to process in a single workflow"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Importance Threshold"
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={workflowConfigForm.importanceThreshold}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, importanceThreshold: parseFloat(e.target.value) || 0.7 }))}
                helperText="Minimum importance score to create tasks (0-1)"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Spam Threshold"
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={workflowConfigForm.spamThreshold}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, spamThreshold: parseFloat(e.target.value) || 0.8 }))}
                helperText="Spam detection threshold (0-1)"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Default Priority</InputLabel>
                <Select
                  value={workflowConfigForm.defaultPriority}
                  onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, defaultPriority: e.target.value }))}
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="urgent">Urgent</MenuItem>
                </Select>
              </FormControl>
            </Grid>


            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2, mt: 3 }}>Automation Settings</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={workflowConfigForm.createTasksAutomatically}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, createTasksAutomatically: e.target.checked }))}
                      />
                    }
                    label="Create Tasks Automatically"
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={workflowConfigForm.scheduleFollowups}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, scheduleFollowups: e.target.checked }))}
                      />
                    }
                    label="Schedule Follow-ups"
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={workflowConfigForm.processAttachments}
                        onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, processAttachments: e.target.checked }))}
                      />
                    }
                    label="Process Attachments"
                  />
                </Grid>
              </Grid>
            </Grid>

            {emailSettings && (
              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>Current saved settings:</strong> {emailSettings.username} @ {emailSettings.server}:{emailSettings.port}
                    {emailSettings.has_password && ' (Password saved)'}
                  </Typography>
                </Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              <Alert severity="warning">
                <Typography variant="body2">
                  <strong>Security Note:</strong> Your password will be encrypted before storage. Make sure to use an app password if your email provider requires 2FA.
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWorkflowConfigDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveWorkflowConfig}
          >
            Save Workflow Settings
          </Button>
        </DialogActions>
      </Dialog>

      {/* Timeout & Retry Settings Dialog */}
      <Dialog
        open={timeoutSettingsDialogOpen}
        onClose={() => setTimeoutSettingsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Timeout & Retry Settings</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure timeout and retry parameters for email processing operations.
              </Typography>
            </Grid>

            {/* Timeout Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Timeout Settings
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Set maximum time limits for various email processing operations
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Analysis Timeout"
                type="number"
                value={workflowConfigForm.analysisTimeout}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, analysisTimeout: parseInt(e.target.value) || 120 }))}
                InputProps={{ endAdornment: 'seconds' }}
                helperText="Maximum time to analyze each email"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Task Conversion Timeout"
                type="number"
                value={workflowConfigForm.taskTimeout}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, taskTimeout: parseInt(e.target.value) || 60 }))}
                InputProps={{ endAdornment: 'seconds' }}
                helperText="Maximum time to convert analysis to tasks"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Ollama Request Timeout"
                type="number"
                value={workflowConfigForm.ollamaTimeout}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, ollamaTimeout: parseInt(e.target.value) || 60 }))}
                InputProps={{ endAdornment: 'seconds' }}
                helperText="Maximum time for individual Ollama API calls"
              />
            </Grid>

            {/* Retry Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2, mt: 3, fontWeight: 600 }}>
                Retry Settings
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure retry behavior for failed operations
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Maximum Retries"
                type="number"
                value={workflowConfigForm.maxRetries}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, maxRetries: parseInt(e.target.value) || 3 }))}
                helperText="Number of retry attempts for failed operations"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Retry Delay"
                type="number"
                value={workflowConfigForm.retryDelay}
                onChange={(e) => setWorkflowConfigForm(prev => ({ ...prev, retryDelay: parseInt(e.target.value) || 1 }))}
                InputProps={{ endAdornment: 'seconds' }}
                helperText="Delay between retry attempts"
              />
            </Grid>

            <Grid item xs={12}>
              <Alert severity="info">
                <Typography variant="body2">
                  <strong>Note:</strong> These settings apply to all email workflow operations. Lower timeout values may cause operations to fail more frequently, while higher values may take longer to complete.
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTimeoutSettingsDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveTimeoutSettings}
          >
            Save Timeout & Retry Settings
          </Button>
        </DialogActions>
      </Dialog>
        </CardContent>
      </Card>

      {/* Success/Error Snackbars */}
      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setSuccess(null)} severity="success">
          {success}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setError(null)} severity="error">
          {error}
        </Alert>
      </Snackbar>

      {/* Feedback Snackbar */}
      {snackbar && (
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert onClose={() => setSnackbar(null)} severity={snackbar.severity}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      )}
    </Box>
  );
};

export default EmailAssistant;