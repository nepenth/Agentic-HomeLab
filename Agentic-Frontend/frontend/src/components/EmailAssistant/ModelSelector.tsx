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
import { getEnhancedModelInfo, ModelInfo } from '../../utils/modelIntelligence';
import { HybridModelIntelligence } from '../../utils/dynamicModelIntelligence';

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
  showStatus?: boolean;
}

interface OllamaModel {
  name: string;
  size?: number;
  modified_at?: string;
  details?: {
    format?: string;
    family?: string;
    families?: string[];
    parameter_size?: string;
    quantization_level?: string;
  };
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

  // Fetch available models from chat endpoint which includes default model
  const {
    data: modelsData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['chat-models'],
    queryFn: async () => {
      const response = await apiClient.getChatModels();
      return response;
    },
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2
  });

  // Hybrid model intelligence system
  const hybridIntelligence = HybridModelIntelligence.getInstance();

  // Get current model info (enhanced if available, fallback to static)
  const getModelInfo = (modelName: string) => {
    if (enhancedModelInfo && enhancedModelInfo.name === modelName) {
      return enhancedModelInfo;
    }
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

  const availableModels = modelsData?.models || [];
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
            {availableModels.map((model: string) => {
              const modelInfo = getModelInfo(model);
              return (
                <MenuItem key={model} value={model}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <span>{getCategoryIcon(modelInfo.category)}</span>
                    <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                      {modelInfo.displayName}
                    </Typography>
                    {modelInfo.size && (
                      <Chip
                        label={modelInfo.size}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.65rem', height: 16 }}
                      />
                    )}
                    <Box sx={{ flexGrow: 1 }} />
                    {modelInfo.recommended && (
                      <CheckCircle
                        fontSize="small"
                        sx={{ color: '#34C759' }}
                      />
                    )}
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
    </Box>
  );
};

export default ModelSelector;