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
  Alert
} from '@mui/material';
import {
  Psychology,
  Refresh,
  Info,
  CheckCircle,
  Error
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

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

interface ModelInfo {
  name: string;
  displayName: string;
  description: string;
  category: 'general' | 'code' | 'chat' | 'instruct';
  recommended: boolean;
  size?: string;
  capabilities: string[];
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  disabled = false,
  showStatus = true
}) => {
  const [modelStatus, setModelStatus] = useState<'idle' | 'switching' | 'error'>('idle');

  // Fetch available models
  const {
    data: modelsData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['ollama-models'],
    queryFn: async () => {
      const response = await apiClient.getOllamaModels();
      return response;
    },
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2
  });

  // Enhanced model information
  const getModelInfo = (modelName: string): ModelInfo => {
    const modelInfoMap: Record<string, Partial<ModelInfo>> = {
      'llama2': {
        displayName: 'Llama 2',
        description: 'Meta\'s general-purpose language model, excellent for conversations',
        category: 'general',
        recommended: true,
        capabilities: ['conversation', 'reasoning', 'general-knowledge']
      },
      'llama2:13b': {
        displayName: 'Llama 2 13B',
        description: 'Larger Llama 2 model with improved performance',
        category: 'general',
        recommended: false,
        size: '13B',
        capabilities: ['conversation', 'reasoning', 'analysis', 'general-knowledge']
      },
      'mistral': {
        displayName: 'Mistral 7B',
        description: 'Fast and efficient model optimized for instructions',
        category: 'instruct',
        recommended: true,
        capabilities: ['instruction-following', 'reasoning', 'conversation']
      },
      'codellama': {
        displayName: 'Code Llama',
        description: 'Specialized for code generation and understanding',
        category: 'code',
        recommended: false,
        capabilities: ['code-generation', 'debugging', 'code-explanation']
      },
      'neural-chat': {
        displayName: 'Neural Chat',
        description: 'Optimized for conversational AI applications',
        category: 'chat',
        recommended: true,
        capabilities: ['conversation', 'reasoning', 'task-assistance']
      }
    };

    const info = modelInfoMap[modelName] || {};
    return {
      name: modelName,
      displayName: info.displayName || modelName,
      description: info.description || 'AI language model',
      category: info.category || 'general',
      recommended: info.recommended || false,
      size: info.size,
      capabilities: info.capabilities || ['conversation']
    };
  };

  const handleModelChange = async (newModel: string) => {
    if (newModel === selectedModel || disabled) return;

    setModelStatus('switching');

    try {
      // Simulate model switching delay (in real implementation, this might involve warming up the model)
      await new Promise(resolve => setTimeout(resolve, 1000));
      onModelChange(newModel);
      setModelStatus('idle');
    } catch (error) {
      console.error('Model switch error:', error);
      setModelStatus('error');
      setTimeout(() => setModelStatus('idle'), 3000);
    }
  };

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

  const availableModels = modelsData?.models || ['llama2'];
  const currentModelInfo = getModelInfo(selectedModel);

  return (
    <Box sx={{ minWidth: 200 }}>
      <FormControl fullWidth size="small" disabled={disabled}>
        <InputLabel id="model-select-label">
          AI Model
        </InputLabel>
        <Select
          labelId="model-select-label"
          value={selectedModel}
          onChange={(e) => handleModelChange(e.target.value)}
          label="AI Model"
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
          endAdornment={
            showStatus && (
              <Tooltip title="Refresh models">
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    refetch();
                  }}
                  sx={{ mr: 1 }}
                >
                  <Refresh fontSize="small" />
                </IconButton>
              </Tooltip>
            )
          }
        >
          {availableModels.map((model: string) => {
            const modelInfo = getModelInfo(model);
            return (
              <MenuItem key={model} value={model}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <span>{getCategoryIcon(modelInfo.category)}</span>
                    <Typography variant="body2">
                      {modelInfo.displayName}
                    </Typography>
                    {modelInfo.size && (
                      <Chip
                        label={modelInfo.size}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem', height: 18 }}
                      />
                    )}
                  </Box>
                  <Box sx={{ flexGrow: 1 }} />
                  {modelInfo.recommended && (
                    <CheckCircle
                      fontSize="small"
                      sx={{ ml: 'auto', color: '#34C759' }}
                    />
                  )}
                </Box>
              </MenuItem>
            );
          })}
        </Select>
      </FormControl>

      {/* Model Information Display */}
      {showStatus && (
        <Box sx={{ mt: 1, p: 1, bgcolor: 'background.paper', borderRadius: 1, border: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <span>{getCategoryIcon(currentModelInfo.category)}</span>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {currentModelInfo.displayName}
            </Typography>
            <Chip
              label={currentModelInfo.category}
              size="small"
              sx={{
                backgroundColor: getCategoryColor(currentModelInfo.category),
                color: 'white',
                fontSize: '0.7rem',
                height: 20
              }}
            />
            {currentModelInfo.recommended && (
              <Tooltip title="Recommended for email assistance">
                <CheckCircle sx={{ color: '#34C759' }} fontSize="small" />
              </Tooltip>
            )}
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontSize: '0.8rem' }}>
            {currentModelInfo.description}
          </Typography>

          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {currentModelInfo.capabilities.map((capability, index) => (
              <Chip
                key={index}
                label={capability.replace('-', ' ')}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.7rem', height: 20 }}
              />
            ))}
          </Box>

          {modelStatus === 'switching' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
              <CircularProgress size={14} />
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                Switching to {currentModelInfo.displayName}...
              </Typography>
            </Box>
          )}

          {modelStatus === 'error' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
              <Error sx={{ color: '#FF3B30' }} fontSize="small" />
              <Typography variant="body2" sx={{ fontSize: '0.8rem', color: '#FF3B30' }}>
                Failed to switch model. Please try again.
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};

export default ModelSelector;