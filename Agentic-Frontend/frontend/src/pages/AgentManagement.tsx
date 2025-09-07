import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  IconButton,
  Button,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Skeleton,
  Tooltip,
  Switch,
  FormControlLabel,
  Avatar,
  Divider,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  PlayArrow,
  Refresh,
  SmartToy,
  CheckCircle,
  Error,
  Settings,
  AutoAwesome,
  Send,
  Person,
  ModelTraining,
  Http,
  VpnKey,
  Memory,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/api';
import type {
  Agent,
  OllamaModelNamesResponse,
  ChatSession,
  ChatMessage,
  ProcessedContent,
  ContentProcessingRequest,
  AgentSecretsResponse
} from '../types';

interface CreateAgentForm {
  name: string;
  description: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  system_prompt: string;
}

const AgentManagement: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [wizardDialogOpen, setWizardDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [wizardSession, setWizardSession] = useState<ChatSession | null>(null);
  const [wizardMessages, setWizardMessages] = useState<ChatMessage[]>([]);
  const [wizardInput, setWizardInput] = useState('');
  const [isWizardTyping, setIsWizardTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // New state for enhanced features
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showContentProcessor, setShowContentProcessor] = useState(false);
  const [showSecretsManager, setShowSecretsManager] = useState(false);
  const [showHttpClient, setShowHttpClient] = useState(false);
  const [contentToProcess, setContentToProcess] = useState('');
  const [processingResults, setProcessingResults] = useState<ProcessedContent | null>(null);
  const [newSecret, setNewSecret] = useState({ key: '', value: '', description: '' });

  // HTTP Client state
  const [httpRequest, setHttpRequest] = useState({
    method: 'GET',
    url: '',
    headers: [{ key: '', value: '' }],
    data: '',
    timeout: 30,
    retry_config: { max_attempts: 3, backoff_factor: 2.0 },
    rate_limit: { requests_per_minute: 60 }
  });
  const [httpResponse, setHttpResponse] = useState<any>(null);
  const [httpMetrics, setHttpMetrics] = useState<any>(null);

  const [formData, setFormData] = useState<CreateAgentForm>({
    name: '',
    description: '',
    model_name: 'qwen3:30b-a3b-thinking-2507-q8_0',
    temperature: 0.7,
    max_tokens: 1000,
    system_prompt: 'You are a helpful AI assistant.',
  });

  // Fetch agents with enhanced filtering
  const {
    data: agents,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['agents', formData], // Include filters in query key
    queryFn: () => apiClient.getAgents(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch available Ollama models
  const {
    data: availableModels,
    isLoading: modelsLoading,
  } = useQuery<OllamaModelNamesResponse>({
    queryKey: ['ollama-models'],
    queryFn: () => apiClient.getOllamaModelNames(),
    refetchInterval: 60000, // Refetch every minute
  });

  // Fetch available models with capabilities (Phase 1.3)
  const {
    data: availableModelsWithCapabilities,
    isLoading: capabilitiesLoading,
  } = useQuery({
    queryKey: ['available-models'],
    queryFn: () => apiClient.getAvailableModels(),
    refetchInterval: 300000, // Refetch every 5 minutes
  });

  // Fetch model performance metrics
  const {
    data: modelPerformance,
  } = useQuery({
    queryKey: ['model-performance'],
    queryFn: () => apiClient.getModelPerformanceMetrics(),
    refetchInterval: 60000, // Refetch every minute
  });

  // Fetch agent secrets
  const {
    data: agentSecrets,
    isLoading: secretsLoading,
    refetch: refetchSecrets,
  } = useQuery<AgentSecretsResponse>({
    queryKey: ['agent-secrets', selectedAgent?.id],
    queryFn: () => selectedAgent ? apiClient.getAgentSecrets(selectedAgent.id) : Promise.resolve({ secrets: [], total_count: 0 }),
    enabled: !!selectedAgent && showSecretsManager,
  });

  // Create agent mutation
  const createAgentMutation = useMutation({
    mutationFn: (agentData: Partial<Agent>) => apiClient.createAgent(agentData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setCreateDialogOpen(false);
      resetForm();
    },
  });

  // Update agent mutation
  const updateAgentMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Agent> }) =>
      apiClient.updateAgent(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setEditingAgent(null);
      resetForm();
    },
  });

  // Delete agent mutation
  const deleteAgentMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteAgent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });

  // Wizard mutations
  const createWizardSessionMutation = useMutation({
    mutationFn: (description: string) =>
      apiClient.createChatSession({
        session_type: 'agent_creation',
        model_name: formData.model_name,
        title: `Agent Creation: ${description.slice(0, 50)}...`,
        user_id: 'current-user',
        config: { description },
      }),
    onSuccess: (session) => {
      setWizardSession(session);
      setWizardMessages([]);
    },
  });

  const sendWizardMessageMutation = useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      apiClient.sendChatMessage(sessionId, { message }),
    onSuccess: (response) => {
      if (response.message && response.response) {
        setWizardMessages(prev => [...prev, response.message, {
          id: `assistant-${Date.now()}`,
          session_id: response.session_id,
          role: 'assistant',
          content: response.response || 'I received your message.',
          timestamp: new Date().toISOString(),
        }]);
      }
      setWizardInput('');
      setIsWizardTyping(false);
    },
    onError: () => {
      setIsWizardTyping(false);
    },
  });


  const processContentMutation = useMutation({
    mutationFn: (contentData: ContentProcessingRequest) =>
      apiClient.processContent(contentData),
    onSuccess: (result) => {
      setProcessingResults(result);
    },
  });

  const createSecretMutation = useMutation({
    mutationFn: (secretData: { secret_key: string; secret_value: string; description?: string }) =>
      selectedAgent ? apiClient.createAgentSecret(selectedAgent.id, secretData) : Promise.reject('No agent selected'),
    onSuccess: () => {
      refetchSecrets();
      setNewSecret({ key: '', value: '', description: '' });
    },
  });

  const deleteSecretMutation = useMutation({
    mutationFn: (secretId: string) =>
      selectedAgent ? apiClient.deleteAgentSecret(selectedAgent.id, secretId) : Promise.reject('No agent selected'),
    onSuccess: () => {
      refetchSecrets();
    },
  });

  // HTTP Client mutations
  const makeHttpRequestMutation = useMutation({
    mutationFn: (requestData: any) => apiClient.makeAgenticHttpRequest(requestData),
    onSuccess: (response) => {
      setHttpResponse(response);
    },
  });

  const getHttpMetricsMutation = useMutation({
    mutationFn: () => apiClient.getHttpClientMetrics(),
    onSuccess: (metrics) => {
      setHttpMetrics(metrics);
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      model_name: 'qwen3:30b-a3b-thinking-2507-q8_0',
      temperature: 0.7,
      max_tokens: 1000,
      system_prompt: 'You are a helpful AI assistant.',
    });
  };

  const handleCreateAgent = () => {
    createAgentMutation.mutate(formData);
  };

  const handleEditAgent = (agent: Agent) => {
    setEditingAgent(agent);
    setFormData({
      name: agent.name,
      description: agent.description,
      model_name: agent.model_name,
      temperature: agent.config.temperature,
      max_tokens: agent.config.max_tokens,
      system_prompt: agent.config.system_prompt,
    });
  };

  const handleUpdateAgent = () => {
    if (editingAgent) {
      updateAgentMutation.mutate({
        id: editingAgent.id,
        data: formData,
      });
    }
  };

  const handleDeleteAgent = (id: string) => {
    if (window.confirm('Are you sure you want to delete this agent?')) {
      deleteAgentMutation.mutate(id);
    }
  };

  const handleToggleAgent = (agent: Agent) => {
    updateAgentMutation.mutate({
      id: agent.id,
      data: { is_active: !agent.is_active },
    });
  };

  const handleRunTask = (agentId: string) => {
    // Navigate to a task creation page or open a dialog
    navigate(`/workflows?agent=${agentId}`);
  };

  const handleStartWizard = () => {
    if (!formData.description.trim()) return;
    setIsWizardTyping(true);
    createWizardSessionMutation.mutate(formData.description);
    setWizardDialogOpen(true);
  };

  const handleSendWizardMessage = () => {
    if (!wizardInput.trim() || !wizardSession) return;
    setIsWizardTyping(true);

    // Add user message to the chat
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      session_id: wizardSession.id,
      role: 'user',
      content: wizardInput,
      timestamp: new Date().toISOString(),
    };

    setWizardMessages(prev => [...prev, userMessage]);
    sendWizardMessageMutation.mutate({
      sessionId: wizardSession.id,
      message: wizardInput,
    });
  };

  const handleCloseWizard = () => {
    setWizardDialogOpen(false);
    setWizardSession(null);
    setWizardMessages([]);
    setWizardInput('');
  };

  // New handler functions for enhanced features
  const handleOpenModelSelector = (agent: Agent) => {
    setSelectedAgent(agent);
    setShowModelSelector(true);
  };

  const handleOpenContentProcessor = (agent: Agent) => {
    setSelectedAgent(agent);
    setShowContentProcessor(true);
  };

  const handleOpenSecretsManager = (agent: Agent) => {
    setSelectedAgent(agent);
    setShowSecretsManager(true);
  };


  const handleProcessContent = () => {
    if (!contentToProcess.trim()) return;

    processContentMutation.mutate({
      content: contentToProcess,
      content_type: 'text',
      operations: ['summarize', 'extract_entities'],
    });
  };

  const handleCreateSecret = () => {
    if (!newSecret.key.trim() || !newSecret.value.trim()) return;

    createSecretMutation.mutate({
      secret_key: newSecret.key,
      secret_value: newSecret.value,
      description: newSecret.description,
    });
  };

  const handleDeleteSecret = (secretId: string) => {
    if (window.confirm('Are you sure you want to delete this secret?')) {
      deleteSecretMutation.mutate(secretId);
    }
  };

  // HTTP Client handlers
  const handleOpenHttpClient = () => {
    setShowHttpClient(true);
    getHttpMetricsMutation.mutate();
  };

  const handleAddHttpHeader = () => {
    setHttpRequest(prev => ({
      ...prev,
      headers: [...prev.headers, { key: '', value: '' }]
    }));
  };

  const handleUpdateHttpHeader = (index: number, field: 'key' | 'value', value: string) => {
    setHttpRequest(prev => ({
      ...prev,
      headers: prev.headers.map((header, i) =>
        i === index ? { ...header, [field]: value } : header
      )
    }));
  };

  const handleRemoveHttpHeader = (index: number) => {
    setHttpRequest(prev => ({
      ...prev,
      headers: prev.headers.filter((_, i) => i !== index)
    }));
  };

  const handleMakeHttpRequest = () => {
    const requestData = {
      method: httpRequest.method,
      url: httpRequest.url,
      headers: Object.fromEntries(
        httpRequest.headers
          .filter(h => h.key.trim() && h.value.trim())
          .map(h => [h.key, h.value])
      ),
      ...(httpRequest.data && { data: httpRequest.data }),
      timeout: httpRequest.timeout,
      retry_config: httpRequest.retry_config,
      rate_limit: httpRequest.rate_limit
    };

    makeHttpRequestMutation.mutate(requestData);
  };

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [wizardMessages]);

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? (
      <CheckCircle color="success" />
    ) : (
      <Error color="disabled" />
    );
  };


  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => refetch()}>
              Retry
            </Button>
          }
        >
          Failed to load agents. Please try again.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Agent Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Create, configure, and manage your AI agents dynamically.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetch()}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<ModelTraining />}
            onClick={() => setShowModelSelector(true)}
            disabled={!availableModelsWithCapabilities}
          >
            Model Performance
          </Button>
          <Button
            variant="outlined"
            startIcon={<Http />}
            onClick={handleOpenHttpClient}
          >
            HTTP Client
          </Button>
          <Button
            variant="outlined"
            startIcon={<AutoAwesome />}
            onClick={() => setWizardDialogOpen(true)}
          >
            AI Wizard
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Manual Create
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Total Agents
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    {isLoading ? '...' : agents?.length || 0}
                  </Typography>
                </Box>
                <SmartToy sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Active Agents
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                    {isLoading ? '...' : agents?.filter(a => a.is_active).length || 0}
                  </Typography>
                </Box>
                <CheckCircle sx={{ fontSize: 40, color: 'success.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Models Used
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                    {isLoading ? '...' : new Set(agents?.map(a => a.model_name)).size || 0}
                  </Typography>
                </Box>
                <Settings sx={{ fontSize: 40, color: 'info.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Recently Created
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main' }}>
                    {isLoading ? '...' : agents?.filter(a => {
                      const created = new Date(a.created_at);
                      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
                      return created > weekAgo;
                    }).length || 0}
                  </Typography>
                </Box>
                <Add sx={{ fontSize: 40, color: 'warning.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Agents Table */}
      <Card elevation={0}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Agent List
          </Typography>

          {isLoading ? (
            <Box>
              {[...Array(5)].map((_, index) => (
                <Box key={index} sx={{ mb: 2 }}>
                  <Skeleton variant="rectangular" width="100%" height={60} sx={{ borderRadius: 1 }} />
                </Box>
              ))}
            </Box>
          ) : (
            <TableContainer component={Paper} elevation={0}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Status</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell>Model</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {agents?.map((agent) => (
                    <TableRow key={agent.id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(agent.is_active)}
                          <FormControlLabel
                            control={
                              <Switch
                                checked={agent.is_active}
                                onChange={() => handleToggleAgent(agent)}
                                size="small"
                              />
                            }
                            label=""
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          {agent.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={agent.model_name}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: '0.75rem' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary" sx={{
                          maxWidth: 200,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {agent.description}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {new Date(agent.created_at).toLocaleDateString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Tooltip title="Run Task">
                            <IconButton
                              size="small"
                              onClick={() => handleRunTask(agent.id)}
                              disabled={!agent.is_active}
                            >
                              <PlayArrow />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Model Selection">
                            <IconButton
                              size="small"
                              onClick={() => handleOpenModelSelector(agent)}
                            >
                              <ModelTraining />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Content Processing">
                            <IconButton
                              size="small"
                              onClick={() => handleOpenContentProcessor(agent)}
                            >
                              <Memory />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Secrets Manager">
                            <IconButton
                              size="small"
                              onClick={() => handleOpenSecretsManager(agent)}
                            >
                              <VpnKey />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit Agent">
                            <IconButton
                              size="small"
                              onClick={() => handleEditAgent(agent)}
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete Agent">
                            <IconButton
                              size="small"
                              onClick={() => handleDeleteAgent(agent.id)}
                              color="error"
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  )) || (
                    <TableRow>
                      <TableCell colSpan={6} sx={{ textAlign: 'center', py: 4 }}>
                        <Typography variant="body2" color="text.secondary">
                          No agents found. Create your first agent to get started.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Create Agent Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Agent Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Model</InputLabel>
                <Select
                  value={formData.model_name}
                  label="Model"
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  disabled={modelsLoading}
                >
                  {modelsLoading ? (
                    <MenuItem disabled>Loading models...</MenuItem>
                  ) : (
                    availableModels?.models?.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    )) || (
                      <MenuItem value="qwen3:30b-a3b-thinking-2507-q8_0">
                        Qwen 3 30B (Thinking) - Default
                      </MenuItem>
                    )
                  )}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Temperature"
                type="number"
                value={formData.temperature}
                onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                inputProps={{ min: 0, max: 2, step: 0.1 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Max Tokens"
                type="number"
                value={formData.max_tokens}
                onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                inputProps={{ min: 1, max: 4096 }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="System Prompt"
                value={formData.system_prompt}
                onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                multiline
                rows={3}
                required
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateAgent}
            variant="contained"
            disabled={createAgentMutation.isPending || !formData.name || !formData.description}
          >
            {createAgentMutation.isPending ? 'Creating...' : 'Create Agent'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Agent Dialog */}
      <Dialog
        open={!!editingAgent}
        onClose={() => setEditingAgent(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Edit Agent</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Agent Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Model</InputLabel>
                <Select
                  value={formData.model_name}
                  label="Model"
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  disabled={modelsLoading}
                >
                  {modelsLoading ? (
                    <MenuItem disabled>Loading models...</MenuItem>
                  ) : (
                    availableModels?.models?.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    )) || (
                      <MenuItem value="qwen3:30b-a3b-thinking-2507-q8_0">
                        Qwen 3 30B (Thinking) - Default
                      </MenuItem>
                    )
                  )}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Temperature"
                type="number"
                value={formData.temperature}
                onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                inputProps={{ min: 0, max: 2, step: 0.1 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Max Tokens"
                type="number"
                value={formData.max_tokens}
                onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                inputProps={{ min: 1, max: 4096 }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="System Prompt"
                value={formData.system_prompt}
                onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                multiline
                rows={3}
                required
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditingAgent(null)}>Cancel</Button>
          <Button
            onClick={handleUpdateAgent}
            variant="contained"
            disabled={updateAgentMutation.isPending || !formData.name || !formData.description}
          >
            {updateAgentMutation.isPending ? 'Updating...' : 'Update Agent'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* AI-Assisted Agent Creation Wizard Dialog */}
      <Dialog
        open={wizardDialogOpen}
        onClose={handleCloseWizard}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { height: '80vh', maxHeight: '800px' },
        }}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <AutoAwesome sx={{ color: 'primary.main' }} />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                🤖 AI Agent Creation Wizard
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Describe your agent and let AI help you create it
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        <Divider />

        <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
          {!wizardSession ? (
            /* Initial Description Input */
            <Box sx={{ p: 3, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <Box sx={{ maxWidth: 600, mx: 'auto', textAlign: 'center' }}>
                <SmartToy sx={{ fontSize: 64, color: 'primary.main', mb: 3 }} />
                <Typography variant="h5" sx={{ mb: 2, fontWeight: 600 }}>
                  Describe Your Agent
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
                  Tell the AI assistant what kind of agent you want to create. Be as specific as possible about its purpose, capabilities, and requirements.
                </Typography>

                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="e.g., Create an agent that analyzes emails from my Gmail account, categorizes them by importance, and extracts key information like sender, subject, and urgency level."
                  sx={{ mb: 3 }}
                />

                <FormControl fullWidth sx={{ mb: 3 }}>
                  <InputLabel>AI Model</InputLabel>
                  <Select
                    value={formData.model_name}
                    label="AI Model"
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  >
                    {availableModels?.models?.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    )) || (
                      <MenuItem value="qwen3:30b-a3b-thinking-2507-q8_0">
                        Qwen 3 30B (Thinking) - Default
                      </MenuItem>
                    )}
                  </Select>
                </FormControl>

                <Button
                  variant="contained"
                  size="large"
                  startIcon={<AutoAwesome />}
                  onClick={handleStartWizard}
                  disabled={!formData.description.trim() || createWizardSessionMutation.isPending}
                  sx={{ minWidth: 200 }}
                >
                  {createWizardSessionMutation.isPending ? 'Starting Wizard...' : 'Start AI Creation'}
                </Button>
              </Box>
            </Box>
          ) : (
            /* Chat Interface */
            <>
              <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
                {wizardMessages.map((message) => (
                  <Box
                    key={message.id}
                    sx={{
                      display: 'flex',
                      mb: 2,
                      justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        maxWidth: '70%',
                        alignItems: 'flex-start',
                        gap: 1,
                      }}
                    >
                      {message.role === 'assistant' && (
                        <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                          <SmartToy fontSize="small" />
                        </Avatar>
                      )}
                      <Paper
                        elevation={1}
                        sx={{
                          p: 2,
                          bgcolor: message.role === 'user' ? 'primary.main' : 'background.paper',
                          color: message.role === 'user' ? 'white' : 'text.primary',
                          borderRadius: 2,
                        }}
                      >
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                          {message.content}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            display: 'block',
                            mt: 1,
                            color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : 'text.secondary',
                          }}
                        >
                          {new Date(message.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </Typography>
                      </Paper>
                      {message.role === 'user' && (
                        <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
                          <Person fontSize="small" />
                        </Avatar>
                      )}
                    </Box>
                  </Box>
                ))}

                {isWizardTyping && (
                  <Box sx={{ display: 'flex', mb: 2, alignItems: 'flex-start', gap: 1 }}>
                    <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                      <SmartToy fontSize="small" />
                    </Avatar>
                    <Paper elevation={1} sx={{ p: 2, borderRadius: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        AI is thinking...
                      </Typography>
                    </Paper>
                  </Box>
                )}

                <div ref={messagesEndRef} />
              </Box>

              <Divider />
              <Box sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    value={wizardInput}
                    onChange={(e) => setWizardInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendWizardMessage();
                      }
                    }}
                    placeholder="Ask questions or provide additional requirements..."
                    disabled={sendWizardMessageMutation.isPending}
                  />
                  <Button
                    variant="contained"
                    onClick={handleSendWizardMessage}
                    disabled={!wizardInput.trim() || sendWizardMessageMutation.isPending}
                    sx={{ minWidth: 60 }}
                  >
                    <Send />
                  </Button>
                </Box>
              </Box>
            </>
          )}
        </DialogContent>

        <DialogActions sx={{ p: 2, pt: 1 }}>
          <Button onClick={handleCloseWizard} variant="outlined">
            Close
          </Button>
          {wizardSession && (
            <Button
              variant="contained"
              startIcon={<CheckCircle />}
              onClick={() => {
                // Here you could add logic to finalize the agent creation
                // For now, just close the wizard
                handleCloseWizard();
              }}
            >
              Finalize Agent
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Model Performance Dialog */}
      <Dialog
        open={showModelSelector}
        onClose={() => setShowModelSelector(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <ModelTraining sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Model Performance & Selection</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {capabilitiesLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Skeleton variant="rectangular" width="100%" height={400} />
            </Box>
          ) : (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" sx={{ mb: 2 }}>Available Models</Typography>
                <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {availableModelsWithCapabilities?.map((model: any) => (
                    <Card key={model.name} sx={{ mb: 1 }}>
                      <CardContent sx={{ py: 2 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          {model.name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          {model.capabilities.map((cap: string) => (
                            <Chip key={cap} label={cap} size="small" variant="outlined" />
                          ))}
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          Performance Score: {model.performance_score.toFixed(2)}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" sx={{ mb: 2 }}>Performance Metrics</Typography>
                <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {modelPerformance?.map((metric: any) => (
                    <Card key={`${metric.model_name}-${metric.task_type}`} sx={{ mb: 1 }}>
                      <CardContent sx={{ py: 2 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          {metric.model_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Task: {metric.task_type}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                          <Typography variant="body2">
                            Success: {(metric.success_rate * 100).toFixed(1)}%
                          </Typography>
                          <Typography variant="body2">
                            Avg Time: {metric.average_response_time_ms}ms
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowModelSelector(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Content Processor Dialog */}
      <Dialog
        open={showContentProcessor}
        onClose={() => setShowContentProcessor(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Memory sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Content Processing</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Content to Process"
                value={contentToProcess}
                onChange={(e) => setContentToProcess(e.target.value)}
                placeholder="Enter text content to process..."
              />
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={handleProcessContent}
                  disabled={!contentToProcess.trim() || processContentMutation.isPending}
                  startIcon={<Memory />}
                >
                  {processContentMutation.isPending ? 'Processing...' : 'Process Content'}
                </Button>
              </Box>
            </Grid>
            {processingResults && (
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Processing Results</Typography>
                <Card>
                  <CardContent>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {processingResults.processed_content?.summary || 'No summary available'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Processing time: {processingResults.processing_time_ms}ms
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowContentProcessor(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Secrets Manager Dialog */}
      <Dialog
        open={showSecretsManager}
        onClose={() => setShowSecretsManager(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <VpnKey sx={{ color: 'primary.main' }} />
            <Typography variant="h6">
              Secrets Manager - {selectedAgent?.name}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2 }}>Add New Secret</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Secret Key"
                    value={newSecret.key}
                    onChange={(e) => setNewSecret({ ...newSecret, key: e.target.value })}
                    placeholder="e.g., api_key"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Secret Value"
                    type="password"
                    value={newSecret.value}
                    onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Description (Optional)"
                    value={newSecret.description}
                    onChange={(e) => setNewSecret({ ...newSecret, description: e.target.value })}
                  />
                </Grid>
              </Grid>
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  onClick={handleCreateSecret}
                  disabled={!newSecret.key.trim() || !newSecret.value.trim() || createSecretMutation.isPending}
                  startIcon={<VpnKey />}
                >
                  {createSecretMutation.isPending ? 'Adding...' : 'Add Secret'}
                </Button>
              </Box>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2 }}>Existing Secrets</Typography>
              {secretsLoading ? (
                <Skeleton variant="rectangular" width="100%" height={200} />
              ) : (
                <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {agentSecrets?.secrets?.map((secret) => (
                    <Card key={secret.secret_id} sx={{ mb: 1 }}>
                      <CardContent sx={{ py: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {secret.secret_key}
                            </Typography>
                            {secret.description && (
                              <Typography variant="body2" color="text.secondary">
                                {secret.description}
                              </Typography>
                            )}
                            <Typography variant="caption" color="text.secondary">
                              Created: {new Date(secret.created_at).toLocaleDateString()}
                            </Typography>
                          </Box>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteSecret(secret.secret_id)}
                            color="error"
                          >
                            <Delete />
                          </IconButton>
                        </Box>
                      </CardContent>
                    </Card>
                  )) || (
                    <Typography variant="body2" color="text.secondary">
                      No secrets found for this agent.
                    </Typography>
                  )}
                </Box>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSecretsManager(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* HTTP Client Dialog */}
      <Dialog
        open={showHttpClient}
        onClose={() => setShowHttpClient(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Http sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Agentic HTTP Client</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            {/* HTTP Metrics */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2 }}>HTTP Client Metrics</Typography>
              {httpMetrics ? (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card elevation={1}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {httpMetrics.total_requests || 0}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Total Requests
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card elevation={1}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {httpMetrics.successful_requests || 0}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Successful
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card elevation={1}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {((httpMetrics.successful_requests || 0) / (httpMetrics.total_requests || 1) * 100).toFixed(1)}%
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Success Rate
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card elevation={1}>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {httpMetrics.average_response_time_ms || 0}ms
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Avg Response Time
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    Loading metrics...
                  </Typography>
                </Box>
              )}
            </Grid>

            {/* Request Builder */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2 }}>Request Builder</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Method</InputLabel>
                    <Select
                      value={httpRequest.method}
                      label="Method"
                      onChange={(e) => setHttpRequest(prev => ({ ...prev, method: e.target.value }))}
                    >
                      <MenuItem value="GET">GET</MenuItem>
                      <MenuItem value="POST">POST</MenuItem>
                      <MenuItem value="PUT">PUT</MenuItem>
                      <MenuItem value="DELETE">DELETE</MenuItem>
                      <MenuItem value="PATCH">PATCH</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="URL"
                    value={httpRequest.url}
                    onChange={(e) => setHttpRequest(prev => ({ ...prev, url: e.target.value }))}
                    placeholder="https://api.example.com/endpoint"
                  />
                </Grid>
              </Grid>
            </Grid>

            {/* Headers */}
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Headers</Typography>
                <Button
                  size="small"
                  onClick={handleAddHttpHeader}
                  startIcon={<Add />}
                >
                  Add Header
                </Button>
              </Box>
              {httpRequest.headers.map((header, index) => (
                <Box key={index} sx={{ display: 'flex', gap: 1, mb: 1 }}>
                  <TextField
                    size="small"
                    placeholder="Header name"
                    value={header.key}
                    onChange={(e) => handleUpdateHttpHeader(index, 'key', e.target.value)}
                    sx={{ flex: 1 }}
                  />
                  <TextField
                    size="small"
                    placeholder="Header value"
                    value={header.value}
                    onChange={(e) => handleUpdateHttpHeader(index, 'value', e.target.value)}
                    sx={{ flex: 1 }}
                  />
                  <IconButton
                    size="small"
                    onClick={() => handleRemoveHttpHeader(index)}
                    color="error"
                  >
                    <Delete />
                  </IconButton>
                </Box>
              ))}
            </Grid>

            {/* Request Body */}
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Request Body (JSON)"
                value={httpRequest.data}
                onChange={(e) => setHttpRequest(prev => ({ ...prev, data: e.target.value }))}
                placeholder='{"key": "value"}'
              />
            </Grid>

            {/* Configuration */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mb: 2 }}>Configuration</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Timeout (seconds)"
                    value={httpRequest.timeout}
                    onChange={(e) => setHttpRequest(prev => ({ ...prev, timeout: parseInt(e.target.value) }))}
                    inputProps={{ min: 1, max: 300 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Rate Limit (req/min)"
                    value={httpRequest.rate_limit.requests_per_minute}
                    onChange={(e) => setHttpRequest(prev => ({
                      ...prev,
                      rate_limit: { ...prev.rate_limit, requests_per_minute: parseInt(e.target.value) }
                    }))}
                    inputProps={{ min: 1, max: 1000 }}
                  />
                </Grid>
              </Grid>
            </Grid>

            {/* Send Request Button */}
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={handleMakeHttpRequest}
                  disabled={!httpRequest.url.trim() || makeHttpRequestMutation.isPending}
                  startIcon={<Send />}
                  sx={{ minWidth: 150 }}
                >
                  {makeHttpRequestMutation.isPending ? 'Sending...' : 'Send Request'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => getHttpMetricsMutation.mutate()}
                  disabled={getHttpMetricsMutation.isPending}
                >
                  Refresh Metrics
                </Button>
              </Box>
            </Grid>

            {/* Response */}
            {httpResponse && (
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Response</Typography>
                <Card>
                  <CardContent>
                    <Box sx={{ mb: 2 }}>
                      <Chip
                        label={`Status: ${httpResponse.status_code}`}
                        color={httpResponse.status_code < 400 ? 'success' : 'error'}
                        sx={{ mr: 1 }}
                      />
                      <Chip
                        label={`Time: ${httpResponse.response_time_ms}ms`}
                        variant="outlined"
                      />
                    </Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Headers:</Typography>
                    <Box sx={{ mb: 2, p: 1, bgcolor: 'grey.50', borderRadius: 1, fontSize: '0.875rem' }}>
                      <pre>{JSON.stringify(httpResponse.headers, null, 2)}</pre>
                    </Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Body:</Typography>
                    <Box sx={{ p: 1, bgcolor: 'grey.50', borderRadius: 1, fontSize: '0.875rem', maxHeight: 200, overflow: 'auto' }}>
                      <pre>{typeof httpResponse.content === 'string' ? httpResponse.content : JSON.stringify(httpResponse.content, null, 2)}</pre>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHttpClient(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AgentManagement;