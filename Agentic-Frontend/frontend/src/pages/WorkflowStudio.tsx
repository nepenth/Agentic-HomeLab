import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  Alert,
  Skeleton,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Avatar,
  Divider,
  Tabs,
  Tab,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Fab,
  Tooltip,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Save,
  Add,
  Delete,
  Edit,
  Settings,
  Timeline,
  AccountTree,
  Schedule,
  Error,
  CheckCircle,
  Warning,
  Info,
  ExpandMore,
  Refresh,
  Assessment,
  Build,
  CallSplit,
  Loop,
  Timer,
  Webhook,
  Queue,
  CloudQueue,
  Storage,
  Api,
  Code,
  DataObject,
  Transform,
  Send,
  Email,
  Sms,
  NotificationImportant,
  TrendingUp,
  Memory,
  Speed,
  AccessTime,
  Psychology,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import webSocketService from '../services/websocket';

// Define workflow types locally for now
interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  triggers: WorkflowTrigger[];
  settings: WorkflowSettings;
  created_at: string;
  updated_at: string;
  version: number;
}

interface WorkflowStep {
  id: string;
  name: string;
  type: string;
  config: any;
  dependencies: string[];
  position: { x: number; y: number };
  status?: 'pending' | 'running' | 'completed' | 'failed';
  error?: string;
}

interface WorkflowTrigger {
  id: string;
  type: 'manual' | 'scheduled' | 'event' | 'webhook';
  config: any;
  enabled: boolean;
}

interface WorkflowSettings {
  max_execution_time: number;
  retry_policy: {
    max_attempts: number;
    backoff_factor: number;
  };
  resource_limits: {
    max_memory_mb: number;
    max_cpu_percent: number;
  };
  notifications: {
    on_success: boolean;
    on_failure: boolean;
    email_recipients: string[];
  };
}

interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  progress: number;
  current_step?: string;
  results: any;
  error?: string;
  metrics: {
    execution_time_ms: number;
    memory_used_mb: number;
    cpu_used_percent: number;
  };
}

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
      id={`workflow-tabpanel-${index}`}
      aria-labelledby={`workflow-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const WorkflowStudio: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDefinition | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [workflowForm, setWorkflowForm] = useState({
    name: '',
    description: '',
    steps: [] as WorkflowStep[],
    triggers: [] as WorkflowTrigger[],
    settings: {
      max_execution_time: 3600,
      retry_policy: { max_attempts: 3, backoff_factor: 2.0 },
      resource_limits: { max_memory_mb: 1024, max_cpu_percent: 80 },
      notifications: { on_success: true, on_failure: true, email_recipients: [] }
    } as WorkflowSettings
  });

  // Workflow Definitions Query
  const {
    data: workflows,
    isLoading: workflowsLoading,
    error: workflowsError,
    refetch: refetchWorkflows,
  } = useQuery<WorkflowDefinition[]>({
    queryKey: ['workflows'],
    queryFn: () => apiClient.getWorkflowDefinitions(),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Workflow Executions Query
  const {
    data: executions,
    isLoading: executionsLoading,
    error: executionsError,
    refetch: refetchExecutions,
  } = useQuery<WorkflowExecution[]>({
    queryKey: ['workflow-executions', selectedWorkflow?.id],
    queryFn: () => {
      if (!selectedWorkflow) return Promise.resolve([]);
      return apiClient.getWorkflowExecutions({ workflow_id: selectedWorkflow.id });
    },
    enabled: !!selectedWorkflow,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Create Workflow Mutation
  const createWorkflowMutation = useMutation({
    mutationFn: (workflow: Partial<WorkflowDefinition>) => apiClient.createWorkflowDefinition({
      name: workflow.name!,
      description: workflow.description!,
      steps: workflow.steps,
      priority: 'normal',
      max_execution_time: workflow.settings?.max_execution_time,
      resource_requirements: workflow.settings?.resource_limits
    }),
    onSuccess: () => {
      setShowCreateDialog(false);
      setWorkflowForm({
        name: '',
        description: '',
        steps: [],
        triggers: [],
        settings: {
          max_execution_time: 3600,
          retry_policy: { max_attempts: 3, backoff_factor: 2.0 },
          resource_limits: { max_memory_mb: 1024, max_cpu_percent: 80 },
          notifications: { on_success: true, on_failure: true, email_recipients: [] }
        }
      });
      refetchWorkflows();
    },
  });

  // Execute Workflow Mutation
  const executeWorkflowMutation = useMutation({
    mutationFn: (workflowId: string) => apiClient.executeWorkflow(workflowId),
    onSuccess: () => {
      refetchExecutions();
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCreateWorkflow = () => {
    createWorkflowMutation.mutate({
      name: workflowForm.name,
      description: workflowForm.description,
      steps: workflowForm.steps,
      triggers: workflowForm.triggers,
      settings: workflowForm.settings
    });
  };

  const handleExecuteWorkflow = (workflowId: string) => {
    executeWorkflowMutation.mutate(workflowId);
  };

  // WebSocket subscription for real-time workflow updates
  React.useEffect(() => {
    const unsubscribe = webSocketService.subscribeToWorkflowUpdates(
      (update) => {
        console.log('Workflow update received:', update);

        // Refresh workflow executions when we get updates
        if (selectedWorkflow && update.workflow_id === selectedWorkflow.id) {
          refetchExecutions();
        }

        // Refresh workflows list for any workflow updates
        refetchWorkflows();
      },
      {
        workflow_id: selectedWorkflow?.id,
        status: undefined // Listen to all status updates
      }
    );

    return unsubscribe;
  }, [selectedWorkflow, refetchExecutions, refetchWorkflows]);

  const handleAddStep = (stepType: string) => {
    const newStep: WorkflowStep = {
      id: `step_${Date.now()}`,
      name: `${stepType} Step`,
      type: stepType,
      config: {},
      dependencies: [],
      position: { x: Math.random() * 400, y: Math.random() * 300 }
    };

    setWorkflowForm(prev => ({
      ...prev,
      steps: [...prev.steps, newStep]
    }));
  };

  const handleUpdateStep = (stepId: string, updates: Partial<WorkflowStep>) => {
    setWorkflowForm(prev => ({
      ...prev,
      steps: prev.steps.map(step =>
        step.id === stepId ? { ...step, ...updates } : step
      )
    }));
  };

  const handleDeleteStep = (stepId: string) => {
    setWorkflowForm(prev => ({
      ...prev,
      steps: prev.steps.filter(step => step.id !== stepId)
    }));
  };

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'data_validation':
        return <Assessment />;
      case 'data_cleaning':
        return <Build />;
      case 'ai_processing':
        return <Psychology />;
      case 'api_call':
        return <Api />;
      case 'webhook':
        return <Webhook />;
      case 'email':
        return <Email />;
      case 'conditional':
        return <CallSplit />;
      case 'loop':
        return <Loop />;
      case 'delay':
        return <Timer />;
      default:
        return <DataObject />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      case 'pending':
        return 'warning';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle />;
      case 'running':
        return <PlayArrow />;
      case 'failed':
        return <Error />;
      case 'pending':
        return <Schedule />;
      case 'cancelled':
        return <Stop />;
      default:
        return <Info />;
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Workflow Orchestration Studio
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Design, build, and manage complex automated workflows with visual orchestration.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowCreateDialog(true)}
          >
            Create Workflow
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => {
              refetchWorkflows();
              refetchExecutions();
            }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="workflow tabs">
            <Tab icon={<AccountTree />} label="Workflows" />
            <Tab icon={<Timeline />} label="Executions" />
            <Tab icon={<Build />} label="Builder" />
            <Tab icon={<Assessment />} label="Analytics" />
          </Tabs>
        </CardContent>

        {/* Workflows Tab */}
        <TabPanel value={tabValue} index={0}>
          {workflowsError && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Failed to load workflows: {workflowsError.message}
              <Button size="small" onClick={() => refetchWorkflows()} sx={{ ml: 2 }}>
                Retry
              </Button>
            </Alert>
          )}
          {workflowsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : workflows ? (
            <Grid container spacing={3}>
              {workflows.map((workflow) => (
                <Grid item xs={12} md={6} lg={4} key={workflow.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box>
                          <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                            {workflow.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {workflow.description}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton size="small" onClick={() => setSelectedWorkflow(workflow)}>
                            <Edit />
                          </IconButton>
                          <IconButton size="small" color="error">
                            <Delete />
                          </IconButton>
                        </Box>
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Steps: {workflow.steps.length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Triggers: {workflow.triggers.length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Version: {workflow.version}
                        </Typography>
                      </Box>

                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                        {workflow.triggers.map((trigger) => (
                          <Chip
                            key={trigger.id}
                            label={trigger.type}
                            size="small"
                            variant="outlined"
                            color={trigger.enabled ? 'primary' : 'default'}
                          />
                        ))}
                      </Box>

                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<PlayArrow />}
                          onClick={() => handleExecuteWorkflow(workflow.id)}
                          disabled={executeWorkflowMutation.isPending}
                        >
                          Execute
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<Settings />}
                          onClick={() => {
                            setSelectedWorkflow(workflow);
                            setShowSettingsDialog(true);
                          }}
                        >
                          Settings
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {workflows.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <AccountTree sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No workflows created yet
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Create your first workflow to get started with automation
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No workflows available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Executions Tab */}
        <TabPanel value={tabValue} index={1}>
          {executionsError && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Failed to load workflow executions: {executionsError.message}
              <Button size="small" onClick={() => refetchExecutions()} sx={{ ml: 2 }}>
                Retry
              </Button>
            </Alert>
          )}
          {executionsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : executions ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Recent Executions
                </Typography>
              </Grid>

              {executions.map((execution) => (
                <Grid item xs={12} md={6} key={execution.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          Execution {execution.id.slice(-8)}
                        </Typography>
                        <Chip
                          label={execution.status}
                          color={getStatusColor(execution.status) as any}
                          icon={getStatusIcon(execution.status)}
                        />
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Progress: {execution.progress}%
                        </Typography>
                        <LinearProgress variant="determinate" value={execution.progress} sx={{ mb: 2 }} />

                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Started: {execution.started_at ? new Date(execution.started_at).toLocaleString() : 'N/A'}
                        </Typography>
                        {execution.completed_at && (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Completed: {new Date(execution.completed_at).toLocaleString()}
                          </Typography>
                        )}
                        {execution.current_step && (
                          <Typography variant="body2" color="text.secondary">
                            Current Step: {execution.current_step}
                          </Typography>
                        )}
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Performance Metrics:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Chip
                            label={`Time: ${(execution.metrics.execution_time_ms / 1000).toFixed(1)}s`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`Memory: ${execution.metrics.memory_used_mb}MB`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`CPU: ${execution.metrics.cpu_used_percent}%`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </Box>

                      {execution.error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                          {execution.error}
                        </Alert>
                      )}

                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button size="small" variant="outlined">
                          View Details
                        </Button>
                        <Button size="small" variant="outlined">
                          View Logs
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {executions.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      No executions found
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No executions available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Builder Tab */}
        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={3}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                    Step Library
                  </Typography>

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {[
                      { type: 'data_validation', label: 'Data Validation', icon: <Assessment /> },
                      { type: 'data_cleaning', label: 'Data Cleaning', icon: <Build /> },
                      { type: 'ai_processing', label: 'AI Processing', icon: <Psychology /> },
                      { type: 'api_call', label: 'API Call', icon: <Api /> },
                      { type: 'webhook', label: 'Webhook', icon: <Webhook /> },
                      { type: 'email', label: 'Send Email', icon: <Email /> },
                      { type: 'conditional', label: 'Conditional', icon: <CallSplit /> },
                      { type: 'loop', label: 'Loop', icon: <Loop /> },
                      { type: 'delay', label: 'Delay', icon: <Timer /> },
                    ].map((step) => (
                      <Button
                        key={step.type}
                        variant="outlined"
                        startIcon={step.icon}
                        onClick={() => handleAddStep(step.type)}
                        sx={{ justifyContent: 'flex-start' }}
                      >
                        {step.label}
                      </Button>
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={9}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                    Workflow Canvas
                  </Typography>

                  <Box
                    sx={{
                      height: 500,
                      border: '2px dashed',
                      borderColor: 'grey.300',
                      borderRadius: 1,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: 'relative',
                      overflow: 'hidden'
                    }}
                  >
                    {workflowForm.steps.length === 0 ? (
                      <Box sx={{ textAlign: 'center' }}>
                        <AccountTree sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                        <Typography variant="h6" color="text.secondary">
                          Add steps to build your workflow
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Drag and drop steps from the library to get started
                        </Typography>
                      </Box>
                    ) : (
                      <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
                        {workflowForm.steps.map((step) => (
                          <Card
                            key={step.id}
                            sx={{
                              position: 'absolute',
                              left: step.position.x,
                              top: step.position.y,
                              minWidth: 200,
                              cursor: 'move'
                            }}
                            elevation={2}
                          >
                            <CardContent sx={{ pb: 1 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {getStepIcon(step.type)}
                                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                    {step.name}
                                  </Typography>
                                </Box>
                                <IconButton size="small" onClick={() => handleDeleteStep(step.id)}>
                                  <Delete />
                                </IconButton>
                              </Box>
                              <Typography variant="body2" color="text.secondary">
                                {step.type}
                              </Typography>
                            </CardContent>
                          </Card>
                        ))}
                      </Box>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Workflow Performance Analytics
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Workflow analytics visualization would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Create Workflow Dialog */}
      <Dialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Add sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Create New Workflow</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Workflow Name"
                value={workflowForm.name}
                onChange={(e) => setWorkflowForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter workflow name"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                value={workflowForm.description}
                onChange={(e) => setWorkflowForm(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe what this workflow does"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Workflow Steps ({workflowForm.steps.length})
              </Typography>

              {workflowForm.steps.length === 0 ? (
                <Alert severity="info">
                  No steps added yet. Use the Builder tab to add steps to your workflow.
                </Alert>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {workflowForm.steps.map((step, index) => (
                    <Card key={step.id} variant="outlined">
                      <CardContent sx={{ pb: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getStepIcon(step.type)}
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                              {step.name}
                            </Typography>
                          </Box>
                          <IconButton size="small" onClick={() => handleDeleteStep(step.id)}>
                            <Delete />
                          </IconButton>
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          Type: {step.type}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)}>Cancel</Button>
          <Button
            onClick={handleCreateWorkflow}
            variant="contained"
            disabled={createWorkflowMutation.isPending || !workflowForm.name.trim()}
          >
            {createWorkflowMutation.isPending ? 'Creating...' : 'Create Workflow'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog
        open={showSettingsDialog}
        onClose={() => setShowSettingsDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Settings sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Workflow Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure workflow execution settings and resource limits.
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="Max Execution Time (seconds)"
                value={workflowForm.settings.max_execution_time}
                onChange={(e) => setWorkflowForm(prev => ({
                  ...prev,
                  settings: {
                    ...prev.settings,
                    max_execution_time: parseInt(e.target.value) || 3600
                  }
                }))}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Memory (MB)"
                value={workflowForm.settings.resource_limits.max_memory_mb}
                onChange={(e) => setWorkflowForm(prev => ({
                  ...prev,
                  settings: {
                    ...prev.settings,
                    resource_limits: {
                      ...prev.settings.resource_limits,
                      max_memory_mb: parseInt(e.target.value) || 1024
                    }
                  }
                }))}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max CPU (%)"
                value={workflowForm.settings.resource_limits.max_cpu_percent}
                onChange={(e) => setWorkflowForm(prev => ({
                  ...prev,
                  settings: {
                    ...prev.settings,
                    resource_limits: {
                      ...prev.settings.resource_limits,
                      max_cpu_percent: parseInt(e.target.value) || 80
                    }
                  }
                }))}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSettingsDialog(false)}>Cancel</Button>
          <Button
            onClick={() => setShowSettingsDialog(false)}
            variant="contained"
          >
            Save Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WorkflowStudio;