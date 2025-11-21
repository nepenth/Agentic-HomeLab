import React, { useState, useEffect } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Box,
  Typography,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  LinearProgress,
  Button
} from '@mui/material';
import {
  Psychology,
  Refresh,
  Info,
  CheckCircle,
  Error,
  Speed,
  Memory,
  Code,
  QuestionAnswer,
  Search,
  CloudDownload,
  Update,
  ExpandMore,
  ExpandLess
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from '../../services/api';
import { getEnhancedModelInfo } from '../../utils/modelIntelligence';
import type { ModelInfo } from '../../utils/modelIntelligence';
import { HybridModelIntelligence } from '../../utils/dynamicModelIntelligence';

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
  showStatus?: boolean;
}

interface OllamaModel {
  name: string;
  display_name?: string;
  description?: string;
  category?: string;
  recommended?: boolean;
  size?: string;
  capabilities?: string[];
  performance?: {
    reasoning?: number;
    coding?: number;
    speed?: number;
    efficiency?: number;
  };
  use_cases?: string[];
  strengths?: string[];
  limitations?: string[];
  runtime_data?: {
    size_bytes?: number;
    family?: string;
    quantization?: string;
    parameter_count?: string;
    last_modified?: string;
  };
  benchmarks?: {
    average_score?: number;
    mmlu_score?: number;
    gpqa_score?: number;
    math_score?: number;
    humaneval_score?: number;
    bbh_score?: number;
    last_updated?: string;
  };
  ranking_score?: number;
}

interface ModelGroup {
  [familyName: string]: OllamaModel[];
}

interface GroupedModelsResponse {
  model_groups: ModelGroup;
  ungrouped_models: OllamaModel[];
  default_model: string;
  total_available: number;
  filtered_out: number;
  groups_count: number;
  ungrouped_count: number;
  last_updated: string;
}


const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  disabled = false,
  showStatus = true
}) => {
  const [modelStatus, setModelStatus] = useState<'idle' | 'switching' | 'error'>('idle');
  const [enhancedModelInfo, setEnhancedModelInfo] = useState<any>(null);
  const [webResearchEnabled, setWebResearchEnabled] = useState(false);
  const [detailsExpanded, setDetailsExpanded] = useState(false);
  const [autoCollapseTimer, setAutoCollapseTimer] = useState<NodeJS.Timeout | null>(null);
  const [runtimeModelInfo, setRuntimeModelInfo] = useState<Map<string, any>>(new Map());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['Qwen', 'DeepSeek'])); // Default expanded groups

  // Fetch available models with rich data
  const {
    data: modelsData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['chat-models-rich'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/api/v1/email-assistant/models/rich');
        return response.data; // Return the data, not the full response
      } catch (error) {
        console.warn('Rich models endpoint failed, falling back to basic models');
        // Fallback to basic models endpoint
        return await apiClient.getChatModels();
      }
    },
    refetchOnWindowFocus: false,
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 2
  });

  // Hybrid model intelligence system
  const hybridIntelligence = HybridModelIntelligence.getInstance();

  // Fetch runtime data for all models on mount with rate limiting
  useEffect(() => {
    const loadRuntimeModelData = async () => {
      if (!modelsData?.models) return;

      const modelInfoMap = new Map();

      // Rate limit: Process models sequentially with delay to avoid nginx rate limiting
      // nginx is configured with: limit_req_zone rate=10r/s burst=20
      // We'll use 150ms delay between requests to stay well under 10r/s (6.6r/s)
      for (const modelName of modelsData.models) {
        try {
          // Get runtime data (without web research to keep it fast)
          const info = await hybridIntelligence.getModelInfo(modelName, false);
          modelInfoMap.set(modelName, info);

          // Throttle requests to prevent nginx rate limiting (150ms = ~6.6 req/sec)
          await new Promise(resolve => setTimeout(resolve, 150));
        } catch (error) {
          console.warn(`Failed to load runtime data for ${modelName}:`, error);
        }
      }
      setRuntimeModelInfo(modelInfoMap);
    };

    loadRuntimeModelData();
  }, [modelsData?.models, hybridIntelligence]);

  // Get current model info from rich data
  const getModelInfo = (modelName: string) => {
    // Use rich data from API if available
    if (modelsData?.models) {
      const richModel = modelsData.models.find((m: any) => m.name === modelName);
      if (richModel) return richModel;
    }

    // Fallback to static info if rich data not available
    return getEnhancedModelInfo(modelName);
  };

  // Web research mutation
  const webResearchMutation = useMutation({
    mutationFn: async (modelName: string) => {
      setWebResearchEnabled(true);
      const enhancedInfo = await hybridIntelligence.getModelInfo(modelName, true);
      return enhancedInfo;
    },
    onSuccess: (data) => {
      setEnhancedModelInfo(data);
    },
    onError: (error) => {
      console.error('Web research failed:', error);
      // You could show a toast notification here
    },
    onSettled: () => {
      setWebResearchEnabled(false);
    }
  });

  const handleModelChange = async (newModel: string) => {
    if (newModel === selectedModel || disabled) return;

    setModelStatus('switching');

    try {
      // Simulate model switching delay (in real implementation, this might involve warming up the model)
      await new Promise(resolve => setTimeout(resolve, 1000));
      onModelChange(newModel);
      setModelStatus('idle');

      // Auto-expand details when model changes
      setDetailsExpanded(true);

      // Clear any existing timer
      if (autoCollapseTimer) {
        clearTimeout(autoCollapseTimer);
      }

      // Set auto-collapse timer for 5 seconds
      const timer = setTimeout(() => {
        setDetailsExpanded(false);
      }, 5000);
      setAutoCollapseTimer(timer);

    } catch (error) {
      console.error('Model switch error:', error);
      setModelStatus('error');
      setTimeout(() => setModelStatus('idle'), 3000);
    }
  };

  // Manual toggle for details (cancels auto-collapse)
  const handleDetailsToggle = () => {
    if (autoCollapseTimer) {
      clearTimeout(autoCollapseTimer);
      setAutoCollapseTimer(null);
    }
    setDetailsExpanded(!detailsExpanded);
  };

  // Toggle group expansion
  const toggleGroupExpansion = (groupName: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupName)) {
        newSet.delete(groupName);
      } else {
        newSet.add(groupName);
      }
      return newSet;
    });
  };

  // Cleanup timer on unmount
  React.useEffect(() => {
    return () => {
      if (autoCollapseTimer) {
        clearTimeout(autoCollapseTimer);
      }
    };
  }, [autoCollapseTimer]);

  const getCategoryColor = (category: ModelInfo['category']) => {
    const colors = {
      general: '#1976d2',
      code: '#f57c00',
      chat: '#388e3c',
      instruct: '#7b1fa2'
    };
    return colors[category];
  };

  const getCategoryIcon = (category: ModelInfo['category']) => {
    const icons = {
      general: '🧠',
      code: '💻',
      chat: '💬',
      instruct: '📝'
    };
    return icons[category];
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Loading models...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert
        severity="warning"
        action={
          <IconButton size="small" onClick={() => refetch()}>
            <Refresh />
          </IconButton>
        }
        sx={{ mb: 2 }}
      >
        Failed to load models. Using default model.
      </Alert>
    );
  }

  // Handle both grouped and flat responses for backward compatibility
  const modelGroups = modelsData?.model_groups || {};
  const ungroupedModels = modelsData?.ungrouped_models || [];
  const availableModels = modelsData?.models || modelsData?.data?.models || [];

  // Use grouped structure if available, otherwise fall back to flat list
  const hasGroupedData = Object.keys(modelGroups).length > 0 || ungroupedModels.length > 0;
  const allModels = hasGroupedData ? [
    ...Object.values(modelGroups).flat(),
    ...ungroupedModels
  ] : availableModels;

  const currentModelInfo = getModelInfo(selectedModel || '');

  return (
    <Box sx={{ minWidth: 200 }}>
      {/* Consolidated Model Selection with Inline Details */}
      <Box sx={{
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(20px)',
        borderRadius: 3,
        border: '1px solid rgba(0, 0, 0, 0.08)',
        overflow: 'hidden',
        transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
      }}>
        {/* Model Selection Row */}
        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          p: 1.5
        }}>
          <FormControl
            fullWidth
            size="small"
            disabled={disabled}
            sx={{
              flexGrow: 1,
              '& .MuiOutlinedInput-root': {
                '& fieldset': { border: 'none' },
                backgroundColor: 'transparent',
              },
              '& .MuiInputLabel-root': {
                transform: 'translate(8px, 9px) scale(1)',
                '&.Mui-focused, &.MuiFormLabel-filled': {
                  transform: 'translate(8px, -6px) scale(0.75)',
                }
              }
            }}
          >
            <InputLabel id="model-select-label" sx={{ fontSize: '0.85rem' }}>
              AI Model
            </InputLabel>
            <Select
              labelId="model-select-label"
              value={selectedModel || ''}
              onChange={(e) => handleModelChange(e.target.value)}
              startAdornment={
                <Box sx={{ display: 'flex', alignItems: 'center', mr: 1 }}>
                  {modelStatus === 'switching' ? (
                    <CircularProgress size={16} />
                  ) : modelStatus === 'error' ? (
                    <Error sx={{ color: '#FF3B30' }} fontSize="small" />
                  ) : (
                    <Psychology sx={{ color: '#007AFF' }} fontSize="small" />
                  )}
                </Box>
              }
              sx={{ fontSize: '0.9rem' }}
            >
            {/* Render grouped models */}
            {Object.entries(modelGroups).map(([familyName, models]) => (
              <Box key={familyName}>
                {/* Family header */}
                <MenuItem
                  onClick={() => toggleGroupExpansion(familyName)}
                  sx={{
                    backgroundColor: 'rgba(0, 122, 255, 0.05)',
                    borderBottom: '1px solid rgba(0, 122, 255, 0.2)',
                    '&:hover': { backgroundColor: 'rgba(0, 122, 255, 0.1)' }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    {expandedGroups.has(familyName) ? (
                      <ExpandLess sx={{ fontSize: '1rem', color: '#007AFF' }} />
                    ) : (
                      <ExpandMore sx={{ fontSize: '1rem', color: '#007AFF' }} />
                    )}
                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#007AFF' }}>
                      {familyName} ({(models as any[]).length})
                    </Typography>
                  </Box>
                </MenuItem>

                {/* Family models (only if expanded) */}
                {expandedGroups.has(familyName) && (models as any[]).map((model: any) => {
                  const modelInfo = getModelInfo(model.name);
                  return (
                    <MenuItem key={model.name} value={model.name} sx={{ pl: 4 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                        {/* Ranking indicator */}
                        <Box sx={{
                          width: 4,
                          height: 20,
                          backgroundColor: model.ranking_score > 80 ? '#34C759' :
                                          model.ranking_score > 60 ? '#FF9500' : '#FF3B30',
                          borderRadius: 1
                        }} />

                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 600 }}>
                              {model.display_name || modelInfo.displayName}
                            </Typography>
                            {model.recommended && (
                              <Chip label="★" size="small" color="primary" sx={{ height: 16, fontSize: '0.6rem' }} />
                            )}
                          </Box>

                          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.25, flexWrap: 'wrap' }}>
                            {model.size && (
                              <Chip label={model.size} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 16 }} />
                            )}
                            {model.runtime_data?.quantization && (
                              <Chip label={model.runtime_data.quantization} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 16 }} />
                            )}
                            {model.benchmarks?.average_score && (
                              <Chip
                                label={`Score: ${model.benchmarks.average_score.toFixed(1)}`}
                                size="small"
                                color="secondary"
                                sx={{ fontSize: '0.6rem', height: 16 }}
                              />
                            )}
                          </Box>

                          <Typography variant="caption" sx={{
                            color: 'text.secondary',
                            fontSize: '0.7rem',
                            display: 'block',
                            mt: 0.25
                          }}>
                            {model.description || modelInfo.description}
                          </Typography>
                        </Box>
                      </Box>
                    </MenuItem>
                  );
                })}
              </Box>
            ))}

            {/* Render ungrouped models */}
            {ungroupedModels.length > 0 && (
              <Box>
                <MenuItem
                  onClick={() => toggleGroupExpansion('Other')}
                  sx={{
                    backgroundColor: 'rgba(142, 142, 147, 0.05)',
                    borderBottom: '1px solid rgba(142, 142, 147, 0.2)',
                    '&:hover': { backgroundColor: 'rgba(142, 142, 147, 0.1)' }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    {expandedGroups.has('Other') ? (
                      <ExpandLess sx={{ fontSize: '1rem', color: '#8E8E93' }} />
                    ) : (
                      <ExpandMore sx={{ fontSize: '1rem', color: '#8E8E93' }} />
                    )}
                    <Typography variant="body2" sx={{ fontWeight: 600, color: '#8E8E93' }}>
                      Other ({ungroupedModels.length})
                    </Typography>
                  </Box>
                </MenuItem>

                {expandedGroups.has('Other') && ungroupedModels.map((model: any) => {
                  const modelInfo = getModelInfo(model.name);
                  return (
                    <MenuItem key={model.name} value={model.name} sx={{ pl: 4 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                        <Box sx={{
                          width: 4,
                          height: 20,
                          backgroundColor: model.ranking_score > 80 ? '#34C759' :
                                          model.ranking_score > 60 ? '#FF9500' : '#FF3B30',
                          borderRadius: 1
                        }} />

                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 600 }}>
                              {model.display_name || modelInfo.displayName}
                            </Typography>
                            {model.recommended && (
                              <Chip label="★" size="small" color="primary" sx={{ height: 16, fontSize: '0.6rem' }} />
                            )}
                          </Box>

                          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.25, flexWrap: 'wrap' }}>
                            {model.size && (
                              <Chip label={model.size} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 16 }} />
                            )}
                            {model.runtime_data?.quantization && (
                              <Chip label={model.runtime_data.quantization} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 16 }} />
                            )}
                            {model.benchmarks?.average_score && (
                              <Chip
                                label={`Score: ${model.benchmarks.average_score.toFixed(1)}`}
                                size="small"
                                color="secondary"
                                sx={{ fontSize: '0.6rem', height: 16 }}
                              />
                            )}
                          </Box>

                          <Typography variant="caption" sx={{
                            color: 'text.secondary',
                            fontSize: '0.7rem',
                            display: 'block',
                            mt: 0.25
                          }}>
                            {model.description || modelInfo.description}
                          </Typography>
                        </Box>
                      </Box>
                    </MenuItem>
                  );
                })}
              </Box>
            )}

            {/* Fallback for old flat structure */}
            {availableModels.length > 0 && Object.keys(modelGroups).length === 0 && ungroupedModels.length === 0 && availableModels.map((model: any) => {
              const modelInfo = getModelInfo(model.name || model);
              return (
                <MenuItem key={model.name || model} value={model.name || model}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <Box sx={{
                      width: 4,
                      height: 20,
                      backgroundColor: model.ranking_score > 80 ? '#34C759' :
                                      model.ranking_score > 60 ? '#FF9500' : '#FF3B30',
                      borderRadius: 1
                    }} />

                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 600 }}>
                          {model.display_name || modelInfo.displayName}
                        </Typography>
                        {model.recommended && (
                          <Chip label="★" size="small" color="primary" sx={{ height: 16, fontSize: '0.6rem' }} />
                        )}
                      </Box>

                      <Box sx={{ display: 'flex', gap: 0.5, mt: 0.25, flexWrap: 'wrap' }}>
                        {model.size && (
                          <Chip label={model.size} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 16 }} />
                        )}
                        {model.runtime_data?.quantization && (
                          <Chip label={model.runtime_data.quantization} size="small" variant="outlined" sx={{ fontSize: '0.6rem', height: 16 }} />
                        )}
                        {model.benchmarks?.average_score && (
                          <Chip
                            label={`Score: ${model.benchmarks.average_score.toFixed(1)}`}
                            size="small"
                            color="secondary"
                            sx={{ fontSize: '0.6rem', height: 16 }}
                          />
                        )}
                      </Box>

                      <Typography variant="caption" sx={{
                        color: 'text.secondary',
                        fontSize: '0.7rem',
                        display: 'block',
                        mt: 0.25
                      }}>
                        {model.description || modelInfo.description}
                      </Typography>
                    </Box>
                  </Box>
                </MenuItem>
              );
            })}
          </Select>
          </FormControl>

          {/* Action Buttons */}
          {showStatus && (
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Tooltip title="Expand model details">
                <IconButton
                  size="small"
                  onClick={handleDetailsToggle}
                  sx={{
                    width: 32,
                    height: 32,
                    color: detailsExpanded ? '#007AFF' : '#666',
                    '&:hover': { backgroundColor: 'rgba(0, 122, 255, 0.1)' }
                  }}
                >
                  <ExpandMore
                    sx={{
                      transform: detailsExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s ease',
                      fontSize: '1.2rem'
                    }}
                  />
                </IconButton>
              </Tooltip>
              <Tooltip title="Research this model online">
                <IconButton
                  size="small"
                  onClick={() => webResearchMutation.mutate(selectedModel)}
                  disabled={disabled || !selectedModel || webResearchMutation.isPending}
                  sx={{
                    width: 32,
                    height: 32,
                    color: enhancedModelInfo?.name === selectedModel ? '#007AFF' : '#666',
                    '&:hover': { backgroundColor: 'rgba(0, 122, 255, 0.1)' }
                  }}
                >
                  {webResearchMutation.isPending ? (
                    <CircularProgress size={14} />
                  ) : enhancedModelInfo?.name === selectedModel ? (
                    <CloudDownload fontSize="small" />
                  ) : (
                    <Search fontSize="small" />
                  )}
                </IconButton>
              </Tooltip>
              <Tooltip title="Refresh models">
                <IconButton
                  size="small"
                  onClick={() => refetch()}
                  disabled={disabled}
                  sx={{
                    width: 32,
                    height: 32,
                    color: '#666',
                    '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.05)' }
                  }}
                >
                  <Refresh fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </Box>

        {/* Abbreviated Model Info (when collapsed) */}
        {showStatus && !detailsExpanded && selectedModel && (
          <Box sx={{
            px: 1.5,
            pb: 1.5,
            borderTop: '1px solid rgba(0, 0, 0, 0.06)'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <span>{getCategoryIcon(currentModelInfo.category)}</span>
              <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.75rem' }}>
                {currentModelInfo.displayName}
              </Typography>
              {currentModelInfo.recommended && (
                <CheckCircle sx={{ color: '#34C759', fontSize: '0.8rem' }} />
              )}
              {enhancedModelInfo?.name === selectedModel && (
                <Chip
                  icon={<CloudDownload sx={{ fontSize: '0.6rem' }} />}
                  label="Enhanced"
                  size="small"
                  sx={{
                    backgroundColor: '#007AFF',
                    color: 'white',
                    fontSize: '0.6rem',
                    height: 14
                  }}
                />
              )}
            </Box>
            <Typography variant="caption" sx={{
              color: '#666',
              fontSize: '0.7rem',
              lineHeight: 1.2,
              display: 'block'
            }}>
              {currentModelInfo.description.length > 80
                ? currentModelInfo.description.substring(0, 80) + '...'
                : currentModelInfo.description
              }
            </Typography>
            {currentModelInfo.bestFor && (
              <Typography variant="caption" sx={{
                color: '#007AFF',
                fontSize: '0.65rem',
                fontWeight: 500,
                display: 'block',
                mt: 0.5
              }}>
                Best for: {currentModelInfo.bestFor.slice(0, 3).join(', ')}
              </Typography>
            )}
          </Box>
        )}
      </Box>

        {/* Expanded Model Details */}
        {detailsExpanded && (
          <Box sx={{
            borderTop: '1px solid rgba(0, 0, 0, 0.06)',
            p: 2,
            animation: 'slideDown 0.3s ease-out'
          }}>
            {/* Model Description */}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: '0.8rem', lineHeight: 1.4 }}>
              {currentModelInfo.description}
            </Typography>

            {/* Performance Metrics */}
            {currentModelInfo.performance && (
              <Box sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', mb: 1, display: 'block' }}>
                  Performance
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <QuestionAnswer sx={{ fontSize: '0.8rem', color: '#1976d2' }} />
                      <Typography variant="caption">Reasoning</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={currentModelInfo.performance.reasoning * 10}
                      sx={{ height: 4, borderRadius: 2 }}
                    />
                  </Box>
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <Code sx={{ fontSize: '0.8rem', color: '#f57c00' }} />
                      <Typography variant="caption">Coding</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={currentModelInfo.performance.coding * 10}
                      sx={{ height: 4, borderRadius: 2 }}
                    />
                  </Box>
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <Speed sx={{ fontSize: '0.8rem', color: '#388e3c' }} />
                      <Typography variant="caption">Speed</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={currentModelInfo.performance.speed * 10}
                      sx={{ height: 4, borderRadius: 2 }}
                    />
                  </Box>
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <Memory sx={{ fontSize: '0.8rem', color: '#7b1fa2' }} />
                      <Typography variant="caption">Efficiency</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={currentModelInfo.performance.efficiency * 10}
                      sx={{ height: 4, borderRadius: 2 }}
                    />
                  </Box>
                </Box>
              </Box>
            )}

            {/* Capabilities */}
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5, display: 'block' }}>
                Capabilities
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {currentModelInfo.capabilities.map((capability, index) => (
                  <Chip
                    key={index}
                    label={capability.replace('-', ' ')}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 18 }}
                  />
                ))}
              </Box>
            </Box>

            {/* Benchmark Scores */}
            {currentModelInfo.benchmarks && (
              <Box sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5, display: 'block' }}>
                  Benchmark Scores
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                  {currentModelInfo.benchmarks.average_score && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">Average:</Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{currentModelInfo.benchmarks.average_score.toFixed(1)}</Typography>
                    </Box>
                  )}
                  {currentModelInfo.benchmarks.mmlu_score && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">MMLU:</Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{currentModelInfo.benchmarks.mmlu_score.toFixed(1)}</Typography>
                    </Box>
                  )}
                  {currentModelInfo.benchmarks.gpqa_score && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">GPQA:</Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{currentModelInfo.benchmarks.gpqa_score.toFixed(1)}</Typography>
                    </Box>
                  )}
                  {currentModelInfo.benchmarks.math_score && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">Math:</Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{currentModelInfo.benchmarks.math_score.toFixed(1)}</Typography>
                    </Box>
                  )}
                  {currentModelInfo.benchmarks.humaneval_score && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">HumanEval:</Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{currentModelInfo.benchmarks.humaneval_score.toFixed(1)}</Typography>
                    </Box>
                  )}
                  {currentModelInfo.benchmarks.bbh_score && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">BBH:</Typography>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{currentModelInfo.benchmarks.bbh_score.toFixed(1)}</Typography>
                    </Box>
                  )}
                </Box>
              </Box>
            )}

            {/* Use Cases */}
            {currentModelInfo.useCases && currentModelInfo.useCases.length > 0 && (
              <Box sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5, display: 'block' }}>
                  Best For
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {currentModelInfo.useCases.join(' • ')}
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {/* Status Messages */}
        {modelStatus === 'switching' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mx: 2, mb: 2, p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <CircularProgress size={14} />
            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
              Switching to {currentModelInfo.displayName}...
            </Typography>
          </Box>
        )}

        {modelStatus === 'error' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mx: 2, mb: 2, p: 1, bgcolor: '#ffebee', borderRadius: 1 }}>
            <Error sx={{ color: '#FF3B30' }} fontSize="small" />
            <Typography variant="body2" sx={{ fontSize: '0.8rem', color: '#FF3B30' }}>
              Failed to switch model. Please try again.
            </Typography>
          </Box>
        )}
    </Box>
  );
};

export default ModelSelector;