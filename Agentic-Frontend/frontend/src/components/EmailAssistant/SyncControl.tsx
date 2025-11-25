import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  IconButton,
  LinearProgress,
  Collapse,
  List,
  ListItem,
  Chip,
  Tooltip,
  alpha,
  useTheme,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Sync as SyncIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useEmail } from '../../hooks/useEmail';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';
import { getSyncHealth } from '../../services/emailApi';

interface SyncControlProps {
  accountIds?: string[];
}

export const SyncControl: React.FC<SyncControlProps> = ({ accountIds }) => {
  const theme = useTheme();
  const { syncEmails, isSyncing } = useEmail();
  const [statusExpanded, setStatusExpanded] = useState(false);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info',
  });
  const [wasSyncing, setWasSyncing] = useState(false);

  // Fetch sync status periodically when syncing
  const { data: syncStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['sync-status'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/email-sync/sync/status');
      return response.data;
    },
    refetchInterval: isSyncing ? 2000 : false, // Poll every 2 seconds when syncing
    enabled: true,
  });

  // Fetch sync health
  const { data: syncHealth } = useQuery({
    queryKey: ['sync-health'],
    queryFn: getSyncHealth,
    refetchInterval: 10000, // Check health every 10s
  });

  // Auto-expand status when sync starts and show notifications
  useEffect(() => {
    // Sync started
    if (isSyncing && !wasSyncing) {
      setStatusExpanded(true);
      setToast({
        open: true,
        message: 'Email sync started...',
        severity: 'info',
      });
      setWasSyncing(true);
    }

    // Sync completed
    if (!isSyncing && wasSyncing) {
      const lastStatus = syncStatus?.accounts?.[0]?.sync_status;
      if (lastStatus === 'success' || lastStatus === 'completed') {
        const emailsProcessed = syncStatus?.accounts?.[0]?.recent_syncs?.[0]?.emails_processed || 0;
        setToast({
          open: true,
          message: `Sync completed! ${emailsProcessed} emails processed.`,
          severity: 'success',
        });
      } else if (lastStatus === 'error' || lastStatus === 'failed') {
        setToast({
          open: true,
          message: `Sync failed. Please check the status panel for details.`,
          severity: 'error',
        });
      }
      setWasSyncing(false);
    }
  }, [isSyncing, wasSyncing, syncStatus]);

  const handleSync = () => {
    // Prevent multiple simultaneous syncs
    if (isSyncing) {
      return;
    }

    // Use V2 UID-based sync (no more incremental/full distinction needed)
    syncEmails({ accountIds });
  };

  const getSyncStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'success':
        return theme.palette.success.main;
      case 'running':
      case 'syncing':
        return theme.palette.info.main;
      case 'error':
      case 'failed':
        return theme.palette.error.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getSyncStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'success':
        return <CheckCircleIcon fontSize="small" />;
      case 'running':
      case 'syncing':
        return <SyncIcon fontSize="small" className="spinning" />;
      case 'error':
      case 'failed':
        return <ErrorIcon fontSize="small" />;
      default:
        return <InfoIcon fontSize="small" />;
    }
  };

  return (
    <Box>
      {/* Health Alerts */}
      {syncHealth?.accounts?.filter((acc: any) => acc.circuit_breaker_open || acc.lock_stale).map((acc: any) => (
        <Alert severity="warning" sx={{ mb: 2 }} key={acc.account_id}>
          {acc.circuit_breaker_open
            ? `Sync paused for ${acc.email_address}: Too many failures (Circuit Breaker Open).`
            : `Sync lock stale for ${acc.email_address}. System will auto-recover.`}
        </Alert>
      ))}

      {/* Simplified Sync Button - No more Quick/Full distinction */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Button
          variant="contained"
          fullWidth
          disabled={isSyncing}
          onClick={handleSync}
          startIcon={isSyncing ? <SyncIcon className="spinning" /> : <SyncIcon />}
          sx={{ py: 1.5 }}
        >
          {isSyncing ? 'Syncing...' : 'Sync Emails'}
        </Button>
        <Typography variant="caption" sx={{ color: theme.palette.text.secondary, textAlign: 'center' }}>
          Syncs new emails, updates flags, and detects deletions
        </Typography>
      </Box>

      {/* Sync Status Panel */}
      <Paper
        sx={{
          mt: 2,
          overflow: 'hidden',
          borderRadius: 2,
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 1.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            bgcolor: alpha(theme.palette.primary.main, 0.05),
            cursor: 'pointer',
          }}
          onClick={() => setStatusExpanded(!statusExpanded)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Sync Status
            </Typography>
            {isSyncing && (
              <Chip
                label="Syncing"
                size="small"
                color="info"
                sx={{ height: 20, fontSize: '0.7rem', fontWeight: 600 }}
              />
            )}
          </Box>
          <IconButton size="small">
            {statusExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>

        {/* Progress Bar */}
        {isSyncing && (
          <LinearProgress
            sx={{
              height: 2,
              bgcolor: alpha(theme.palette.primary.main, 0.1),
            }}
          />
        )}

        {/* Status Details */}
        <Collapse in={statusExpanded}>
          <Box sx={{ p: 2 }}>
            {syncStatus?.accounts?.map((account: any) => (
              <Box key={account.account_id} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {account.email_address}
                  </Typography>
                  <Chip
                    icon={getSyncStatusIcon(account.sync_status)}
                    label={account.sync_status}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.7rem',
                      bgcolor: alpha(getSyncStatusColor(account.sync_status), 0.1),
                      color: getSyncStatusColor(account.sync_status),
                      '& .MuiChip-icon': {
                        color: 'inherit',
                      },
                    }}
                  />
                </Box>

                {/* Account Stats */}
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: 1,
                    mb: 1,
                  }}
                >
                  <Box>
                    <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                      Total Synced
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {account.total_emails_synced?.toLocaleString() || 0}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                      Last Sync
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.75rem' }}>
                      {account.last_sync_at
                        ? new Date(account.last_sync_at).toLocaleTimeString()
                        : 'Never'}
                    </Typography>
                  </Box>
                </Box>

                {/* Recent Sync History */}
                {account.recent_syncs && account.recent_syncs.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography
                      variant="caption"
                      sx={{ color: theme.palette.text.secondary, fontWeight: 600 }}
                    >
                      Recent Activity
                    </Typography>
                    <List dense disablePadding>
                      {account.recent_syncs.slice(0, 3).map((sync: any, index: number) => (
                        <ListItem
                          key={index}
                          disablePadding
                          sx={{
                            py: 0.5,
                            borderBottom:
                              index < 2 ? `1px solid ${alpha(theme.palette.divider, 0.1)}` : 'none',
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                            {getSyncStatusIcon(sync.status)}
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="caption">
                                {sync.emails_processed} emails • {sync.status}
                              </Typography>
                              <Typography
                                variant="caption"
                                sx={{
                                  color: theme.palette.text.secondary,
                                  display: 'block',
                                  fontSize: '0.65rem',
                                }}
                              >
                                {new Date(sync.started_at).toLocaleString()}
                              </Typography>
                            </Box>
                            {sync.duration_seconds && (
                              <Typography
                                variant="caption"
                                sx={{ color: theme.palette.text.secondary }}
                              >
                                {sync.duration_seconds}s
                              </Typography>
                            )}
                          </Box>
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {/* Error Display */}
                {account.last_error && (
                  <Box
                    sx={{
                      mt: 1,
                      p: 1,
                      bgcolor: alpha(theme.palette.error.main, 0.1),
                      borderRadius: 1,
                      border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: theme.palette.error.main }}>
                      <strong>Error:</strong> {account.last_error}
                    </Typography>
                  </Box>
                )}
              </Box>
            ))}

            {/* Overall Status */}
            <Box
              sx={{
                mt: 2,
                pt: 2,
                borderTop: `1px solid ${theme.palette.divider}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                Overall Status: <strong>{syncStatus?.overall_status || 'Unknown'}</strong>
              </Typography>
              <Tooltip title="Click to refresh status">
                <IconButton size="small" onClick={() => refetchStatus()}>
                  <SyncIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </Collapse>
      </Paper>

      {/* Toast Notifications */}
      <Snackbar
        open={toast.open}
        autoHideDuration={6000}
        onClose={() => setToast({ ...toast, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setToast({ ...toast, open: false })}
          severity={toast.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {toast.message}
        </Alert>
      </Snackbar>

      {/* Add spinning animation */}
      <style>
        {`
          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
          .spinning {
            animation: spin 1s linear infinite;
          }
        `}
      </style>
    </Box>
  );
};
