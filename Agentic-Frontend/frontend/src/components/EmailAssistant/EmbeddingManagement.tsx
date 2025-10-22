import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  CircularProgress,
  LinearProgress
} from '@mui/material';
import {
  Refresh,
  Assessment,
  CloudSync,
  Info,
  Warning,
  CheckCircle,
  Delete
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/api';

interface EmbeddingManagementProps {
  accountId?: string; // If provided, show account-specific management
}

export const EmbeddingManagement: React.FC<EmbeddingManagementProps> = ({ accountId }) => {
  const queryClient = useQueryClient();
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(accountId || null);
  const [targetModel, setTargetModel] = useState<string>('');
  const [filterByModel, setFilterByModel] = useState<string>('');
  const [deleteExisting, setDeleteExisting] = useState(true);

  // Fetch embedding models comparison
  const { data: comparisonData, isLoading: comparisonLoading, refetch: refetchComparison } = useQuery({
    queryKey: ['embedding-models-comparison'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/email-sync/embedding-models/comparison');
      return response.data;
    },
    enabled: !accountId // Only fetch if we're showing all accounts
  });

  // Fetch account-specific stats
  const { data: accountStats, refetch: refetchAccountStats } = useQuery({
    queryKey: ['embedding-stats', accountId],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/email-sync/accounts/${accountId}/embedding-stats`);
      return response.data;
    },
    enabled: !!accountId
  });

  // Fetch available models
  const { data: modelsData} = useQuery({
    queryKey: ['embedding-models'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/email-sync/models/embedding');
      return response.data;
    }
  });

  // Generate missing embeddings mutation
  const generateMissingMutation = useMutation({
    mutationFn: async (accountId: string) => {
      const response = await apiClient.post(
        `/api/v1/email-sync/accounts/${accountId}/generate-missing-embeddings`
      );
      return response.data;
    },
    onSuccess: () => {
      refetchComparison();
      if (accountId) {
        refetchAccountStats();
      }
    }
  });

  // Regenerate embeddings mutation
  const regenerateMutation = useMutation({
    mutationFn: async (data: {
      account_id: string;
      model_name?: string;
      filter_by_current_model?: string;
      delete_existing: boolean;
    }) => {
      const response = await apiClient.post(
        `/api/v1/email-sync/accounts/${data.account_id}/regenerate-embeddings`,
        {
          model_name: data.model_name || null,
          filter_by_current_model: data.filter_by_current_model || null,
          delete_existing: data.delete_existing
        }
      );
      return response.data;
    },
    onSuccess: () => {
      refetchComparison();
      if (accountId) {
        refetchAccountStats();
      }
      setRegenerateDialogOpen(false);
      setTargetModel('');
      setFilterByModel('');
    }
  });

  const handleOpenRegenerateDialog = (acctId: string) => {
    setSelectedAccount(acctId);
    setRegenerateDialogOpen(true);
  };

  const handleRegenerateEmbeddings = () => {
    if (!selectedAccount) return;

    regenerateMutation.mutate({
      account_id: selectedAccount,
      model_name: targetModel || undefined,
      filter_by_current_model: filterByModel || undefined,
      delete_existing: deleteExisting
    });
  };

  if (accountId && accountStats) {
    // Account-specific view
    return (
      <Box>
        <Card elevation={0}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" fontWeight={600}>
                Embedding Management
              </Typography>
              <Tooltip title="Refresh statistics">
                <IconButton onClick={() => refetchAccountStats()} size="small">
                  <Refresh />
                </IconButton>
              </Tooltip>
            </Box>

            <Grid container spacing={3}>
              {/* Statistics Cards */}
              <Grid item xs={12} md={3}>
                <Box sx={{ p: 2, bgcolor: 'primary.50', borderRadius: 2, textAlign: 'center' }}>
                  <Typography variant="h4" fontWeight={700} color="primary">
                    {accountStats.total_emails}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Emails
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={3}>
                <Box sx={{ p: 2, bgcolor: 'success.50', borderRadius: 2, textAlign: 'center' }}>
                  <Typography variant="h4" fontWeight={700} color="success.main">
                    {accountStats.emails_with_embeddings}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    With Embeddings
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={3}>
                <Box sx={{ p: 2, bgcolor: 'warning.50', borderRadius: 2, textAlign: 'center' }}>
                  <Typography variant="h4" fontWeight={700} color="warning.main">
                    {accountStats.emails_without_embeddings}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Without Embeddings
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={3}>
                <Box sx={{ p: 2, bgcolor: 'info.50', borderRadius: 2, textAlign: 'center' }}>
                  <Typography variant="h4" fontWeight={700} color="info.main">
                    {accountStats.embedding_coverage_percent}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Coverage
                  </Typography>
                </Box>
              </Grid>

              {/* Model Breakdown */}
              <Grid item xs={12}>
                <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 2 }}>
                  Embedding Models in Use
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Model Name</TableCell>
                        <TableCell>Embedding Type</TableCell>
                        <TableCell align="right">Count</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {accountStats.model_breakdown?.map((item: any, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell>
                            <Chip
                              label={item.model_name || 'Unknown'}
                              size="small"
                              color={item.model_name === accountStats.current_embedding_model ? 'primary' : 'default'}
                            />
                          </TableCell>
                          <TableCell>{item.embedding_type}</TableCell>
                          <TableCell align="right">{item.count}</TableCell>
                        </TableRow>
                      ))}
                      {(!accountStats.model_breakdown || accountStats.model_breakdown.length === 0) && (
                        <TableRow>
                          <TableCell colSpan={3} align="center">
                            <Typography variant="body2" color="text.secondary">
                              No embeddings generated yet
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>

              {/* Actions */}
              <Grid item xs={12} md={6}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={generateMissingMutation.isPending ? <CircularProgress size={16} /> : <CloudSync />}
                  onClick={() => generateMissingMutation.mutate(accountId)}
                  disabled={accountStats.emails_without_embeddings === 0 || generateMissingMutation.isPending}
                  fullWidth
                >
                  {generateMissingMutation.isPending ? 'Generating...' : 'Generate Missing Embeddings'}
                </Button>
                {accountStats.emails_without_embeddings > 0 && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, textAlign: 'center' }}>
                    {accountStats.emails_without_embeddings} emails pending
                  </Typography>
                )}
              </Grid>
              <Grid item xs={12} md={6}>
                <Button
                  variant="outlined"
                  startIcon={<CloudSync />}
                  onClick={() => handleOpenRegenerateDialog(accountId)}
                  disabled={accountStats.total_emails === 0}
                  fullWidth
                >
                  Regenerate All Embeddings
                </Button>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, textAlign: 'center' }}>
                  Change model or rebuild all
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Regenerate Dialog */}
        <RegenerateDialog
          open={regenerateDialogOpen}
          onClose={() => setRegenerateDialogOpen(false)}
          onConfirm={handleRegenerateEmbeddings}
          accountStats={accountStats}
          modelsData={modelsData}
          targetModel={targetModel}
          setTargetModel={setTargetModel}
          filterByModel={filterByModel}
          setFilterByModel={setFilterByModel}
          deleteExisting={deleteExisting}
          setDeleteExisting={setDeleteExisting}
          isLoading={regenerateMutation.isPending}
        />
      </Box>
    );
  }

  // Multi-account view
  return (
    <Box>
      <Card elevation={0}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" fontWeight={600}>
              Embedding Models Overview
            </Typography>
            <Tooltip title="Refresh data">
              <IconButton onClick={() => refetchComparison()} size="small">
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>

          {comparisonLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <Alert severity="info" icon={<Info />} sx={{ mb: 3 }}>
                <Typography variant="body2">
                  View and manage embedding models across all your email accounts.
                  Different models can provide different search accuracy and performance characteristics.
                </Typography>
              </Alert>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Email Account</TableCell>
                      <TableCell>Configured Model</TableCell>
                      <TableCell align="right">Total Emails</TableCell>
                      <TableCell align="right">Embedding Coverage</TableCell>
                      <TableCell>Models in Use</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {comparisonData?.accounts?.map((account: any) => (
                      <TableRow key={account.account_id}>
                        <TableCell>{account.email_address}</TableCell>
                        <TableCell>
                          <Chip
                            label={account.configured_model || 'System Default'}
                            size="small"
                            color={account.configured_model ? 'primary' : 'default'}
                          />
                        </TableCell>
                        <TableCell align="right">{account.total_emails || 0}</TableCell>
                        <TableCell align="right">
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'flex-end' }}>
                            <Box sx={{ width: 60 }}>
                              <LinearProgress
                                variant="determinate"
                                value={account.embedding_coverage_percent || 0}
                                sx={{
                                  height: 6,
                                  borderRadius: 1,
                                  backgroundColor: 'action.hover',
                                  '& .MuiLinearProgress-bar': {
                                    backgroundColor:
                                      account.embedding_coverage_percent >= 90 ? 'success.main' :
                                      account.embedding_coverage_percent >= 50 ? 'warning.main' : 'error.main'
                                  }
                                }}
                              />
                            </Box>
                            <Typography variant="body2" sx={{ minWidth: 45 }}>
                              {account.embedding_coverage_percent || 0}%
                            </Typography>
                          </Box>
                          {account.emails_without_embeddings > 0 && (
                            <Typography variant="caption" color="warning.main" display="block">
                              {account.emails_without_embeddings} pending
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {Object.entries(account.models_in_use || {}).map(([model, count]) => (
                              <Chip
                                key={model}
                                label={`${model}: ${count}`}
                                size="small"
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                            <Tooltip title="Generate missing embeddings">
                              <span>
                                <IconButton
                                  size="small"
                                  color="primary"
                                  onClick={() => generateMissingMutation.mutate(account.account_id)}
                                  disabled={account.emails_without_embeddings === 0 || generateMissingMutation.isPending}
                                >
                                  <Assessment />
                                </IconButton>
                              </span>
                            </Tooltip>
                            <Tooltip title="Regenerate all embeddings">
                              <IconButton
                                size="small"
                                onClick={() => handleOpenRegenerateDialog(account.account_id)}
                                disabled={account.total_emails === 0}
                              >
                                <CloudSync />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </CardContent>
      </Card>

      {/* Regenerate Dialog */}
      {selectedAccount && (
        <RegenerateDialog
          open={regenerateDialogOpen}
          onClose={() => setRegenerateDialogOpen(false)}
          onConfirm={handleRegenerateEmbeddings}
          accountStats={null}
          modelsData={modelsData}
          targetModel={targetModel}
          setTargetModel={setTargetModel}
          filterByModel={filterByModel}
          setFilterByModel={setFilterByModel}
          deleteExisting={deleteExisting}
          setDeleteExisting={setDeleteExisting}
          isLoading={regenerateMutation.isPending}
        />
      )}
    </Box>
  );
};

// Separate dialog component for regeneration
interface RegenerateDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  accountStats: any;
  modelsData: any;
  targetModel: string;
  setTargetModel: (model: string) => void;
  filterByModel: string;
  setFilterByModel: (model: string) => void;
  deleteExisting: boolean;
  setDeleteExisting: (value: boolean) => void;
  isLoading: boolean;
}

const RegenerateDialog: React.FC<RegenerateDialogProps> = ({
  open,
  onClose,
  onConfirm,
  accountStats,
  modelsData,
  targetModel,
  setTargetModel,
  filterByModel,
  setFilterByModel,
  deleteExisting,
  setDeleteExisting,
  isLoading
}) => {
  const uniqueModels = accountStats?.model_breakdown
    ? Array.from(new Set(accountStats.model_breakdown.map((item: any) => item.model_name)))
    : [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Regenerate Embeddings</DialogTitle>
      <DialogContent>
        {isLoading && <LinearProgress sx={{ mb: 2 }} />}

        <Alert severity="warning" icon={<Warning />} sx={{ mb: 3 }}>
          <Typography variant="body2">
            Regenerating embeddings is a resource-intensive operation that runs in the background.
            Depending on the number of emails, this may take several minutes to complete.
          </Typography>
        </Alert>

        <Grid container spacing={3}>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Target Model</InputLabel>
              <Select
                value={targetModel}
                label="Target Model"
                onChange={(e) => setTargetModel(e.target.value)}
                disabled={isLoading}
              >
                <MenuItem value="">
                  <em>Use account default</em>
                </MenuItem>
                {modelsData?.models?.map((model: any) => (
                  <MenuItem key={model.name} value={model.name}>
                    {model.display_name} ({model.dimensions} dims)
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Filter by Current Model</InputLabel>
              <Select
                value={filterByModel}
                label="Filter by Current Model"
                onChange={(e) => setFilterByModel(e.target.value)}
                disabled={isLoading}
              >
                <MenuItem value="">
                  <em>All models</em>
                </MenuItem>
                {uniqueModels.map((model: any) => (
                  <MenuItem key={model} value={model}>
                    {model}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Only regenerate embeddings created by a specific model
            </Typography>
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={deleteExisting}
                  onChange={(e) => setDeleteExisting(e.target.checked)}
                  disabled={isLoading}
                />
              }
              label="Delete existing embeddings before regenerating"
            />
            <Typography variant="caption" color="text.secondary" display="block" sx={{ ml: 4 }}>
              If unchecked, new embeddings will be added alongside existing ones
            </Typography>
          </Grid>

          {accountStats && (
            <Grid item xs={12}>
              <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Impact Summary:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Emails to process: {accountStats.total_emails}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Existing embeddings: {accountStats.emails_with_embeddings}
                </Typography>
                {filterByModel && (
                  <Typography variant="body2" color="text.secondary">
                    • Filtered to model: {filterByModel}
                  </Typography>
                )}
              </Box>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={onConfirm}
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={16} /> : <CloudSync />}
        >
          {isLoading ? 'Processing...' : 'Regenerate Embeddings'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
