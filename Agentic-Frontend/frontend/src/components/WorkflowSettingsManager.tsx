import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  IconButton,
  Alert,
} from '@mui/material';
import {
  ExpandMore,
  Save,
  Refresh,
  Settings,
  PlayArrow,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

interface WorkflowSettings {
  id?: string;
  settings_name: string;
  is_default?: boolean;
  phase_models: {
    [phase: string]: {
      model: string;
      fallback_models?: string[];
      task_type?: string;
    };
  };
  phase_settings: {
    [phase: string]: {
      skip?: boolean;
      force_reprocess?: boolean;
      enabled?: boolean;
    };
  };
  global_settings: {
    max_concurrent_items?: number;
    retry_attempts?: number;
    auto_start_processing?: boolean;
    enable_progress_tracking?: boolean;
  };
}

interface WorkflowSettingsManagerProps {
  open: boolean;
  onClose: () => void;
  onSettingsActivated?: (settings: WorkflowSettings) => void;
}

const PHASE_NAMES = [
  'fetch_bookmarks',
  'cache_content',
  'cache_media',
  'interpret_media',
  'categorize_content',
  'holistic_understanding',
  'synthesized_learning',
  'embeddings'
];

// Phases that don't need model selection (they don't use LLM processing)
const NON_LLM_PHASES = ['fetch_bookmarks', 'cache_content', 'cache_media'];

const AVAILABLE_MODELS = [
  'llama2:7b',
  'llama2:13b',
  'llama2:70b',
  'codellama:7b',
  'codellama:13b',
  'mistral:7b',
  'qwen2:7b',
  'qwen2:72b',
  'gemma:7b',
  'phi3:14b'
];

const WorkflowSettingsManager: React.FC<WorkflowSettingsManagerProps> = ({
  open,
  onClose,
  onSettingsActivated,
}) => {
  const [settings, setSettings] = useState<WorkflowSettings>({
    settings_name: '',
    phase_models: {},
    phase_settings: {},
    global_settings: {
      max_concurrent_items: 3,
      retry_attempts: 3,
      auto_start_processing: true,
      enable_progress_tracking: true,
    },
  });
  const [selectedSettingsId, setSelectedSettingsId] = useState<string | null>(null);
  const [activeSettings, setActiveSettings] = useState<WorkflowSettings | null>(null);

  const queryClient = useQueryClient();

  // Fetch available models
  const { data: availableModels, error: modelsError } = useQuery({
    queryKey: ['ollama-models'],
    queryFn: () => apiClient.getOllamaModels(),
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Fetch workflow settings
  const { data: workflowSettingsList, error: settingsListError, refetch: refetchSettings } = useQuery({
    queryKey: ['workflow-settings'],
    queryFn: () => apiClient.getWorkflowSettings(),
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Fetch defaults
  const { data: defaults, error: defaultsError } = useQuery({
    queryKey: ['workflow-settings-defaults'],
    queryFn: () => apiClient.getWorkflowSettingsDefaults(),
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Fetch currently active settings
  const { data: currentActiveSettings, error: activeSettingsError } = useQuery({
    queryKey: ['workflow-settings-active'],
    queryFn: () => apiClient.getWorkflowSettingsDefaults(), // This should be a separate endpoint for active settings
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (settingsData: Partial<WorkflowSettings>) =>
      apiClient.createWorkflowSettings(settingsData),
    onSuccess: () => {
      refetchSettings();
      queryClient.invalidateQueries({ queryKey: ['workflow-settings'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<WorkflowSettings> }) =>
      apiClient.updateWorkflowSettings(id, data),
    onSuccess: () => {
      refetchSettings();
    },
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => apiClient.activateWorkflowSettings(id),
    onSuccess: (result) => {
      if (onSettingsActivated) {
        onSettingsActivated(result.current_settings);
      }
      onClose();
    },
  });

  // Initialize with defaults
  useEffect(() => {
    if (defaults && !settings.settings_name) {
      setSettings(prev => ({
        ...prev,
        phase_models: defaults.phase_models || {},
        phase_settings: defaults.phase_settings || {},
        global_settings: { ...prev.global_settings, ...defaults.global_settings },
      }));
    }
  }, [defaults]);

  const handleSave = () => {
    if (!settings.settings_name.trim()) {
      alert('Please provide a settings name');
      return;
    }

    if (selectedSettingsId) {
      updateMutation.mutate({
        id: selectedSettingsId,
        data: settings,
      });
    } else {
      createMutation.mutate({
        settings_name: settings.settings_name,
        is_default: settings.is_default,
        phase_models: settings.phase_models,
        phase_settings: settings.phase_settings,
        global_settings: settings.global_settings,
      });
    }
  };

  const handleLoadSettings = (settingsData: WorkflowSettings) => {
    setSettings(settingsData);
    setSelectedSettingsId(settingsData.id || null);
  };

  const handleActivateSettings = (settingsId: string) => {
    activateMutation.mutate(settingsId);
  };

  const handleModelChange = (phase: string, model: string) => {
    setSettings(prev => ({
      ...prev,
      phase_models: {
        ...prev.phase_models,
        [phase]: {
          ...prev.phase_models[phase],
          model,
        },
      },
    }));
  };

  const handlePhaseToggle = (phase: string, enabled: boolean) => {
    setSettings(prev => ({
      ...prev,
      phase_settings: {
        ...prev.phase_settings,
        [phase]: {
          ...prev.phase_settings[phase],
          enabled,
        },
      },
    }));
  };

  const handleGlobalSettingChange = (key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      global_settings: {
        ...prev.global_settings,
        [key]: value,
      },
    }));
  };

  const modelOptions = availableModels?.models?.map((m: any) => m.name) || AVAILABLE_MODELS;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Settings />
          <Typography variant="h6">Workflow Settings Manager</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 3 }}>
          {/* Currently Active Settings */}
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              <strong>System Default Settings:</strong>
            </Typography>
            {currentActiveSettings ? (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2">
                  <strong>Default Configuration:</strong> {Object.keys(currentActiveSettings.phase_models || {}).length} phases with default models
                </Typography>
                <Typography variant="body2">
                  <strong>Max Concurrent Items:</strong> {currentActiveSettings.global_settings?.max_concurrent_items || 3}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                  💡 Create and activate custom settings above to override these defaults for your current session.
                </Typography>
              </Box>
            ) : (
              <Typography variant="body2">
                Loading system defaults...
              </Typography>
            )}
          </Alert>

          <Grid container spacing={3}>
            {/* Settings List */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Saved Settings
                  </Typography>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      <strong>How Settings Work:</strong> Create custom configurations with specific models and settings for each processing phase.
                      Click "Activate" to apply a saved setting to your current session - this will override the system defaults for new workflows.
                    </Typography>
                  </Alert>
                  <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                    {workflowSettingsList?.settings?.map((setting: WorkflowSettings) => (
                      <Box
                        key={setting.id}
                        sx={{
                          p: 1,
                          mb: 1,
                          border: '1px solid #e0e0e0',
                          borderRadius: 1,
                          cursor: 'pointer',
                          '&:hover': { backgroundColor: '#f5f5f5' },
                        }}
                        onClick={() => handleLoadSettings(setting)}
                      >
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {setting.settings_name}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            {setting.is_default && (
                              <Chip label="Default" size="small" color="primary" variant="outlined" />
                            )}
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleActivateSettings(setting.id!);
                              }}
                              disabled={activateMutation.isPending}
                            >
                              <PlayArrow fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {Object.keys(setting.phase_models || {}).length} phases configured
                        </Typography>
                      </Box>
                    )) || (
                      <Typography variant="body2" color="text.secondary">
                        No saved settings found
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Settings Editor */}
            <Grid item xs={12} md={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Settings Configuration
                  </Typography>

                  {/* Basic Settings */}
                  <Box sx={{ mb: 3 }}>
                    <TextField
                      fullWidth
                      label="Settings Name"
                      value={settings.settings_name}
                      onChange={(e) => setSettings(prev => ({ ...prev, settings_name: e.target.value }))}
                      sx={{ mb: 2 }}
                    />
                  </Box>

                  {/* Phase Models */}
                  <Accordion defaultExpanded>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="subtitle1">Model Selection per Phase</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Note: Only phases that use AI processing require model selection. Data collection phases (Fetch Bookmarks, Cache Content, Cache Media) don't use LLM models.
                      </Typography>
                      <Grid container spacing={2}>
                        {PHASE_NAMES.filter(phase => !NON_LLM_PHASES.includes(phase)).map((phase) => (
                          <Grid item xs={12} sm={6} key={phase}>
                            <FormControl fullWidth size="small">
                              <InputLabel>
                                {phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </InputLabel>
                              <Select
                                value={settings.phase_models[phase]?.model || ''}
                                label={phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                onChange={(e) => handleModelChange(phase, e.target.value)}
                              >
                                {modelOptions.map((model) => (
                                  <MenuItem key={model} value={model}>
                                    {model}
                                  </MenuItem>
                                ))}
                              </Select>
                            </FormControl>
                          </Grid>
                        ))}
                      </Grid>
                    </AccordionDetails>
                  </Accordion>

                  {/* Phase Controls */}
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="subtitle1">Phase Controls</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        {PHASE_NAMES.map((phase) => (
                          <Grid item xs={12} sm={6} md={4} key={phase}>
                            <FormControlLabel
                              control={
                                <Switch
                                  checked={settings.phase_settings[phase]?.enabled !== false}
                                  onChange={(e) => handlePhaseToggle(phase, e.target.checked)}
                                />
                              }
                              label={phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            />
                          </Grid>
                        ))}
                      </Grid>
                    </AccordionDetails>
                  </Accordion>

                  {/* Global Settings */}
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="subtitle1">Global Settings</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            type="number"
                            label="Max Concurrent Items"
                            value={settings.global_settings.max_concurrent_items || 3}
                            onChange={(e) => handleGlobalSettingChange('max_concurrent_items', parseInt(e.target.value))}
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            type="number"
                            label="Retry Attempts"
                            value={settings.global_settings.retry_attempts || 3}
                            onChange={(e) => handleGlobalSettingChange('retry_attempts', parseInt(e.target.value))}
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={settings.global_settings.auto_start_processing !== false}
                                onChange={(e) => handleGlobalSettingChange('auto_start_processing', e.target.checked)}
                              />
                            }
                            label="Auto Start Processing"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={settings.global_settings.enable_progress_tracking !== false}
                                onChange={(e) => handleGlobalSettingChange('enable_progress_tracking', e.target.checked)}
                              />
                            }
                            label="Enable Progress Tracking"
                          />
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>

        {/* Status Messages */}
        {createMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to create settings. Please try again.
          </Alert>
        )}
        {updateMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to update settings. Please try again.
          </Alert>
        )}
        {activateMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to activate settings. Please try again.
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="outlined"
          startIcon={<Save />}
          disabled={createMutation.isPending || updateMutation.isPending}
          sx={{ mr: 1 }}
        >
          {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save Settings'}
        </Button>
        <Button
          onClick={() => {
            if (selectedSettingsId) {
              handleActivateSettings(selectedSettingsId);
            } else {
              // If no settings selected, try to activate the first available settings
              const firstSettings = workflowSettingsList?.settings?.[0];
              if (firstSettings) {
                handleActivateSettings(firstSettings.id);
              }
            }
          }}
          variant="contained"
          color="primary"
          disabled={activateMutation.isPending || !workflowSettingsList?.settings?.length}
        >
          {activateMutation.isPending ? 'Applying...' : 'Apply Settings'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default WorkflowSettingsManager;