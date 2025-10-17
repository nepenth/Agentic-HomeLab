import React, { useState, useEffect } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Chip,
  Tooltip,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControlLabel,
  Switch
} from '@mui/material';
import { Info, Refresh, CheckCircle } from '@mui/icons-material';
import { apiClient } from '../../services/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface EmbeddingModel {
  name: string;
  display_name: string;
  description: string;
  dimensions: number;
  capabilities: string[];
  parameter_size: string | null;
  is_available: boolean;
}

interface EmbeddingModelSelectorProps {
  accountId: string;
  currentModel?: string | null;
  onModelChanged?: (model: string | null) => void;
  showStats?: boolean;
}

export const EmbeddingModelSelector: React.FC<EmbeddingModelSelectorProps> = ({
  accountId,
  currentModel,
  onModelChanged,
  showStats = true
}) => {
  const queryClient = useQueryClient();
  const [selectedModel, setSelectedModel] = useState<string | null>(currentModel || null);
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [regenerateExisting, setRegenerateExisting] = useState(false);

  // Fetch available models
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['embedding-models'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/email-sync/models/embedding');
      return response.data;
    }
  });

  // Fetch embedding stats for this account
  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['embedding-stats', accountId],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/email-sync/accounts/${accountId}/embedding-stats`);
      return response.data;
    },
    enabled: showStats && !!accountId
  });

  // Update model mutation
  const updateModelMutation = useMutation({
    mutationFn: async (data: { model_name: string | null; regenerate_embeddings: boolean }) => {
      const response = await apiClient.patch(
        `/email-sync/accounts/${accountId}/embedding-model`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['embedding-stats', accountId] });
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
      if (onModelChanged) {
        onModelChanged(selectedModel);
      }
    }
  });

  const handleModelChange = (newModel: string | null) => {
    setSelectedModel(newModel);
    if (statsData && statsData.emails_with_embeddings > 0) {
      // Ask if user wants to regenerate existing embeddings
      setRegenerateDialogOpen(true);
    } else {
      // No existing embeddings, just update
      updateModelMutation.mutate({
        model_name: newModel,
        regenerate_embeddings: false
      });
    }
  };

  const handleConfirmModelChange = () => {
    updateModelMutation.mutate({
      model_name: selectedModel,
      regenerate_embeddings: regenerateExisting
    });
    setRegenerateDialogOpen(false);
    setRegenerateExisting(false);
  };

  const handleCancelModelChange = () => {
    setSelectedModel(currentModel || null);
    setRegenerateDialogOpen(false);
    setRegenerateExisting(false);
  };

  const getModelInfo = (modelName: string | null): EmbeddingModel | undefined => {
    if (!modelsData || !modelName) return undefined;
    return modelsData.models.find((m: EmbeddingModel) => m.name === modelName);
  };

  const displayedModel = selectedModel || modelsData?.system_default || 'system default';
  const modelInfo = getModelInfo(selectedModel || modelsData?.system_default);

  if (modelsLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Loading embedding models...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <FormControl fullWidth size="small">
        <InputLabel>Embedding Model</InputLabel>
        <Select
          value={selectedModel || ''}
          label="Embedding Model"
          onChange={(e) => handleModelChange(e.target.value || null)}
          disabled={updateModelMutation.isPending}
        >
          <MenuItem value="">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography>System Default</Typography>
              <Chip
                label={modelsData?.system_default || 'loading...'}
                size="small"
                color="primary"
                variant="outlined"
              />
            </Box>
          </MenuItem>
          {modelsData?.models?.map((model: EmbeddingModel) => (
            <MenuItem key={model.name} value={model.name}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <Box>
                  <Typography>{model.display_name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {model.dimensions} dimensions
                    {model.parameter_size && ` • ${model.parameter_size}`}
                  </Typography>
                </Box>
                {model.is_available && (
                  <CheckCircle fontSize="small" color="success" />
                )}
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {modelInfo && (
        <Box sx={{ mt: 1, p: 1.5, bgcolor: 'background.default', borderRadius: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Info fontSize="small" color="info" />
            <Typography variant="caption" fontWeight={600}>
              Model Information
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary" display="block">
            {modelInfo.description}
          </Typography>
          {modelInfo.capabilities && modelInfo.capabilities.length > 0 && (
            <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {modelInfo.capabilities.map((cap) => (
                <Chip key={cap} label={cap} size="small" variant="outlined" />
              ))}
            </Box>
          )}
        </Box>
      )}

      {showStats && statsData && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle2" fontWeight={600}>
              Embedding Statistics
            </Typography>
            <Tooltip title="Refresh stats">
              <IconButton size="small" onClick={() => refetchStats()}>
                <Refresh fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>

          <Box sx={{ p: 1.5, bgcolor: 'background.default', borderRadius: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Total Emails:</Typography>
              <Typography variant="body2" fontWeight={600}>{statsData.total_emails}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">With Embeddings:</Typography>
              <Typography variant="body2" fontWeight={600} color="success.main">
                {statsData.emails_with_embeddings}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Without Embeddings:</Typography>
              <Typography variant="body2" fontWeight={600} color="warning.main">
                {statsData.emails_without_embeddings}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">Coverage:</Typography>
              <Typography variant="body2" fontWeight={600}>
                {statsData.embedding_coverage_percent}%
              </Typography>
            </Box>
          </Box>

          {statsData.model_breakdown && statsData.model_breakdown.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" display="block" sx={{ mb: 1 }}>
                Models in Use:
              </Typography>
              {statsData.model_breakdown.map((item: any, idx: number) => (
                <Box
                  key={idx}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    py: 0.5,
                    borderBottom: idx < statsData.model_breakdown.length - 1 ? 1 : 0,
                    borderColor: 'divider'
                  }}
                >
                  <Box>
                    <Typography variant="caption" fontWeight={600}>
                      {item.model_name || 'Unknown'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {item.embedding_type}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {item.count}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      )}

      {/* Regenerate Confirmation Dialog */}
      <Dialog open={regenerateDialogOpen} onClose={handleCancelModelChange} maxWidth="sm" fullWidth>
        <DialogTitle>Change Embedding Model</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            This account has {statsData?.emails_with_embeddings || 0} emails with existing embeddings.
          </Alert>

          <Typography variant="body2" sx={{ mb: 2 }}>
            You're changing the embedding model from:
          </Typography>
          <Box sx={{ pl: 2, mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Current:</strong> {currentModel || 'system default'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              <strong>New:</strong> {selectedModel || 'system default'}
            </Typography>
          </Box>

          <FormControlLabel
            control={
              <Switch
                checked={regenerateExisting}
                onChange={(e) => setRegenerateExisting(e.target.checked)}
              />
            }
            label={
              <Box>
                <Typography variant="body2">
                  Regenerate existing embeddings
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  This will delete and recreate all embeddings using the new model.
                  This process runs in the background and may take several minutes.
                </Typography>
              </Box>
            }
          />

          {!regenerateExisting && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Only new emails will use the new model. Existing embeddings will remain unchanged.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelModelChange}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleConfirmModelChange}
            disabled={updateModelMutation.isPending}
          >
            {regenerateExisting ? 'Change & Regenerate' : 'Change Model'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
