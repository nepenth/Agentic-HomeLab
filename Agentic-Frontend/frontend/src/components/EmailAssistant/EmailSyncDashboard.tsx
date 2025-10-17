import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  IconButton,
  Divider,
  Alert,
  CircularProgress,
  LinearProgress,
  Chip,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Collapse,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select
} from '@mui/material';
import {
  Sync,
  Add,
  Settings,
  Delete,
  Email,
  CheckCircle,
  Error,
  Warning,
  Schedule,
  Assessment,
  Storage,
  SmartToy,
  Refresh,
  ExpandMore,
  ExpandLess,
  AccountCircle,
  Link,
  Timeline,
  Info,
  Edit,
  Tune
} from '@mui/icons-material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/api';

interface EmailAccount {
  account_id: string;
  email_address: string;
  display_name: string;
  account_type: string;
  sync_status: string;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  next_sync_at: string | null;
  total_emails_synced: number;
  last_error: string | null;
  created_at: string;
  sync_configuration?: {
    sync_days_back: number | null;
    max_emails_limit: number | null;
    folders_to_sync: string[];
    sync_attachments: boolean;
    include_spam: boolean;
    include_trash: boolean;
  };
}

interface SyncStatus {
  total_accounts: number;
  accounts: EmailAccount[];
  overall_status: string;
  total_emails_synced: number;
  most_recent_sync?: string;
}

interface EmbeddingStats {
  total_emails: number;
  emails_with_embeddings: number;
  emails_without_embeddings: number;
  embedding_coverage_percent: number;
}

interface SyncedEmail {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  received_at: string;
  category: string;
  importance_score: number;
  is_read: boolean;
  has_attachments: boolean;
  embeddings_generated: boolean;
  tasks_generated: boolean;
}

const EmailSyncDashboard: React.FC = () => {
  const [expandedAccount, setExpandedAccount] = useState<string | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEmailsDialog, setShowEmailsDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [editingAccount, setEditingAccount] = useState<any>(null);
  const [newAccount, setNewAccount] = useState({
    account_type: 'gmail',
    email_address: '',
    display_name: '',
    auth_credentials: {
      auth_type: 'oauth2',
      // Gmail OAuth fields
      access_token: '',
      refresh_token: '',
      client_id: '',
      client_secret: '',
      // IMAP fields
      server: '',
      port: 993,
      username: '',
      password: '',
      use_ssl: true
    },
    sync_settings: {
      folders_to_sync: ['INBOX'],
      sync_attachments: true,
      max_attachment_size_mb: 25,
      include_spam: false,
      include_trash: false
    },
    sync_interval_minutes: 15,
    auto_sync_enabled: true,
    // New sync configuration fields
    sync_days_back: null as number | null,
    max_emails_limit: null as number | null
  });

  const queryClient = useQueryClient();

  // Update email account mutation
  const updateAccountMutation = useMutation({
    mutationFn: async ({ accountId, updateData }: { accountId: string; updateData: any }) => {
      return await apiClient.updateEmailAccount(accountId, updateData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-sync-status'] });
    },
    onError: (error) => {
      console.error('Failed to update email account:', error);
    }
  });

  // Fetch sync status
  const { data: syncStatus, isLoading: loadingSyncStatus, refetch: refetchSyncStatus } = useQuery<SyncStatus>({
    queryKey: ['email-sync-status'],
    queryFn: async () => {
      return await apiClient.getEmailSyncStatus();
    },
    refetchInterval: (data) => {
      // Faster refresh during active sync, slower when idle
      const isRunning = data?.overall_status === 'running' || data?.overall_status === 'syncing';
      return isRunning ? 5000 : 30000; // 5s when syncing, 30s when idle
    }
  });

  // Fetch email accounts
  const { data: accounts, isLoading: loadingAccounts } = useQuery<{accounts: EmailAccount[]}>({
    queryKey: ['email-accounts'],
    queryFn: async () => {
      return await apiClient.getEmailAccounts();
    }
  });

  // Fetch real-time email and embedding counts
  const { data: realtimeCounts, isLoading: loadingRealtimeCounts } = useQuery({
    queryKey: ['realtime-counts'],
    queryFn: async () => {
      return await apiClient.getRealtimeCounts();
    },
    refetchInterval: (data) => {
      // Faster refresh if sync is running or embeddings are generating
      const hasPendingWork = data && (
        (data.total_emails > 0 && data.total_with_embeddings < data.total_emails) ||
        syncStatus?.overall_status === 'running'
      );
      return hasPendingWork ? 5000 : 30000; // 5s when active, 30s when idle
    },
    retry: 2
  });

  // Fetch sync defaults
  const { data: syncDefaults } = useQuery({
    queryKey: ['sync-defaults'],
    queryFn: async () => {
      return await apiClient.getSyncDefaults();
    }
  });

  // Fetch synced emails
  const { data: emails, isLoading: loadingEmails } = useQuery<{emails: SyncedEmail[]}>({
    queryKey: ['synced-emails', selectedAccount],
    queryFn: async () => {
      return await apiClient.getSyncedEmails({
        limit: 50,
        offset: 0
      });
    },
    enabled: showEmailsDialog
  });

  // Create account mutation
  const createAccountMutation = useMutation({
    mutationFn: async (accountData: any) => {
      return await apiClient.createEmailAccount(accountData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
      queryClient.invalidateQueries({ queryKey: ['email-sync-status'] });
      setShowAddDialog(false);
      resetNewAccount();
    }
  });

  // Trigger sync mutation - V2 UID-based sync (no more syncType parameter)
  const triggerSyncMutation = useMutation({
    mutationFn: async ({ accountIds }: {
      accountIds?: string[];
    }) => {
      return await apiClient.triggerEmailSync({
        account_ids: accountIds,
        force_full_sync: false  // V2 UID-based sync handles incremental automatically
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-sync-status'] });
      setTimeout(() => refetchSyncStatus(), 2000); // Refresh status after 2 seconds
    }
  });

  // Generate embeddings mutation
  const generateEmbeddingsMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.generateEmailEmbeddings({
        force_regenerate: false
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-sync-status'] });
    }
  });

  // Delete account mutation
  const deleteAccountMutation = useMutation({
    mutationFn: async (accountId: string) => {
      return await apiClient.deleteEmailAccount(accountId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
      queryClient.invalidateQueries({ queryKey: ['email-sync-status'] });
    }
  });

  const handleAccountTypeChange = (accountType: string) => {
    setNewAccount(prev => ({
      ...prev,
      account_type: accountType,
      auth_credentials: {
        ...prev.auth_credentials,
        auth_type: accountType === 'imap' ? 'password' : 'oauth2'
      }
    }));
  };

  const resetNewAccount = () => {
    setNewAccount({
      account_type: 'gmail',
      email_address: '',
      display_name: '',
      auth_credentials: {
        auth_type: 'oauth2',
        // Gmail OAuth fields
        access_token: '',
        refresh_token: '',
        client_id: '',
        client_secret: '',
        // IMAP fields
        server: '',
        port: 993,
        username: '',
        password: '',
        use_ssl: true
      },
      sync_settings: {
        folders_to_sync: ['INBOX'],
        sync_attachments: true,
        max_attachment_size_mb: 25,
        include_spam: false,
        include_trash: false
      },
      sync_interval_minutes: 15,
      auto_sync_enabled: true,
      sync_days_back: null,
      max_emails_limit: null
    });
  };

  const handleEditAccount = (account: EmailAccount) => {
    setEditingAccount({
      ...account,
      // Include current sync configuration
      sync_days_back: account.sync_configuration?.sync_days_back || null,
      max_emails_limit: account.sync_configuration?.max_emails_limit || null,
      // Initialize auth_credentials with placeholder values indicating existing config
      auth_credentials: {
        auth_type: account.account_type === 'imap' ? 'password' : 'oauth2',
        // For existing accounts, show placeholder values to indicate settings exist
        server: '[Current Server - Update to Change]',
        port: 993,
        username: account.email_address,
        password: '••••••••', // Always show masked for existing accounts
        use_ssl: true,
        // OAuth fields (if applicable) - show placeholder for existing accounts
        access_token: account.account_type === 'gmail' ? '••••••••••••••••' : '',
        refresh_token: account.account_type === 'gmail' ? '••••••••••••••••' : '',
        client_id: account.account_type === 'gmail' ? '[Current Client ID - Update to Change]' : '',
        client_secret: account.account_type === 'gmail' ? '••••••••••••••••' : ''
      }
    });
    setShowEditDialog(true);
  };

  const applyPreset = (presetName: string) => {
    if (!syncDefaults?.presets?.[presetName]) return;

    const preset = syncDefaults.presets[presetName];
    setNewAccount(prev => ({
      ...prev,
      sync_days_back: preset.sync_days_back,
      max_emails_limit: preset.max_emails_limit
    }));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle color="success" />;
      case 'running': return <CircularProgress size={20} />;
      case 'error': return <Error color="error" />;
      default: return <Schedule />;
    }
  };

  const formatLastSync = (lastSync: string | null) => {
    if (!lastSync) return 'Never';
    const date = new Date(lastSync);
    const datePart = date.toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric'
    });
    const timePart = date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
    return `${datePart} ${timePart}`;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Email Synchronization Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<SmartToy />}
            onClick={() => generateEmbeddingsMutation.mutate()}
            disabled={generateEmbeddingsMutation.isPending}
          >
            {generateEmbeddingsMutation.isPending ? 'Generating...' : 'Generate Embeddings'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Sync />}
            onClick={() => triggerSyncMutation.mutate({})}
            disabled={triggerSyncMutation.isPending}
          >
            Sync All
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowAddDialog(true)}
          >
            Add Account
          </Button>
        </Box>
      </Box>

      {/* Overall Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Avatar sx={{ bgcolor: 'primary.main' }}>
                  <Email />
                </Avatar>
                <Box>
                  <Typography variant="h6">{syncStatus?.total_accounts || 0}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Email Accounts
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <Avatar sx={{ bgcolor: 'success.main' }}>
                  <Storage />
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6">
                    {realtimeCounts?.total_emails ?? syncStatus?.total_emails_realtime ?? 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Emails
                  </Typography>
                </Box>
              </Box>
              {loadingRealtimeCounts ? (
                <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={16} />
                  <Typography variant="caption" color="text.secondary">
                    Loading...
                  </Typography>
                </Box>
              ) : realtimeCounts ? (
                <>
                  <Divider sx={{ my: 1 }} />
                  <Box sx={{ mt: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        Embeddings
                      </Typography>
                      <Typography variant="caption" fontWeight="bold">
                        {realtimeCounts.total_with_embeddings} / {realtimeCounts.total_emails}
                      </Typography>
                    </Box>
                    {realtimeCounts.total_emails > 0 && (
                      <>
                        <LinearProgress
                          variant="determinate"
                          value={realtimeCounts.overall_embedding_coverage}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            backgroundColor: 'grey.200',
                            '& .MuiLinearProgress-bar': {
                              backgroundColor: realtimeCounts.overall_embedding_coverage === 100 ? 'success.main' : 'warning.main'
                            }
                          }}
                        />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">
                            {realtimeCounts.overall_embedding_coverage}% complete
                          </Typography>
                          {realtimeCounts.total_without_embeddings > 0 && (
                            <Chip
                              label={`${realtimeCounts.total_without_embeddings} ${realtimeCounts.total_with_embeddings > 0 ? 'generating' : 'pending'}`}
                              size="small"
                              color={realtimeCounts.total_with_embeddings > 0 ? 'info' : 'warning'}
                              sx={{ height: 18, fontSize: '0.65rem' }}
                            />
                          )}
                        </Box>
                      </>
                    )}
                    {realtimeCounts.total_emails === 0 && (
                      <Typography variant="caption" color="text.secondary">
                        No emails synced yet
                      </Typography>
                    )}
                  </Box>
                </>
              ) : null}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Avatar sx={{ bgcolor: getStatusColor(syncStatus?.overall_status || 'default') }}>
                  {getStatusIcon(syncStatus?.overall_status || 'pending')}
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>
                    {syncStatus?.overall_status || 'Unknown'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Overall Status
                  </Typography>
                  {syncStatus?.overall_status === 'running' && syncStatus?.accounts && (
                    <Box sx={{ mt: 1 }}>
                      {syncStatus.accounts.filter(acc => acc.sync_status === 'running').map(acc => (
                        acc.sync_progress_percent && (
                          <Box key={acc.account_id} sx={{ mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              {acc.realtime_email_count || 0} emails (~{acc.sync_progress_percent}%)
                            </Typography>
                            <LinearProgress
                              variant="determinate"
                              value={acc.sync_progress_percent}
                              sx={{ height: 4, borderRadius: 2 }}
                            />
                          </Box>
                        )
                      ))}
                    </Box>
                  )}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Avatar sx={{ bgcolor: syncStatus?.overall_status === 'running' ? 'success.main' : 'info.main' }}>
                  {syncStatus?.overall_status === 'running' ? <Sync className="spin" /> : <Timeline />}
                </Avatar>
                <Box>
                  <Typography variant="body1">
                    {syncStatus?.overall_status === 'running'
                      ? 'Syncing now...'
                      : (syncStatus?.most_recent_sync ? formatLastSync(syncStatus.most_recent_sync) : 'Never')
                    }
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {syncStatus?.overall_status === 'running' ? 'In Progress' : 'Last Sync'}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Embedding Generation Status */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Embedding Generation Status
          </Typography>
          <Tooltip title="Embeddings enable semantic search and AI conversations">
            <IconButton size="small">
              <Info />
            </IconButton>
          </Tooltip>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Box sx={{
              p: 2,
              borderRadius: 1,
              bgcolor: 'primary.50',
              border: '1px solid',
              borderColor: 'primary.200'
            }}>
              <Typography variant="subtitle2" color="primary.main" gutterBottom>
                Emails with Embeddings
              </Typography>
              <Typography variant="h4">
                {accounts?.accounts?.reduce((acc, account) =>
                  acc + (account.total_emails_synced || 0), 0) || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total processed
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{
              p: 2,
              borderRadius: 1,
              bgcolor: generateEmbeddingsMutation.isPending ? 'warning.50' : 'success.50',
              border: '1px solid',
              borderColor: generateEmbeddingsMutation.isPending ? 'warning.200' : 'success.200'
            }}>
              <Typography variant="subtitle2" color={generateEmbeddingsMutation.isPending ? "warning.main" : "success.main"} gutterBottom>
                Generation Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {generateEmbeddingsMutation.isPending ? (
                  <>
                    <CircularProgress size={16} />
                    <Typography variant="body1">Processing...</Typography>
                  </>
                ) : (
                  <>
                    <CheckCircle sx={{ fontSize: 16 }} />
                    <Typography variant="body1">Ready</Typography>
                  </>
                )}
              </Box>
              <Typography variant="body2" color="text.secondary">
                {generateEmbeddingsMutation.isPending ? 'Generating embeddings for new emails' : 'All synced emails processed'}
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{
              p: 2,
              borderRadius: 1,
              bgcolor: 'info.50',
              border: '1px solid',
              borderColor: 'info.200'
            }}>
              <Typography variant="subtitle2" color="info.main" gutterBottom>
                AI Capabilities
              </Typography>
              <List dense sx={{ py: 0 }}>
                <ListItem sx={{ px: 0, py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 20 }}>
                    <CheckCircle sx={{ fontSize: 14, color: 'success.main' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Semantic Search"
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
                <ListItem sx={{ px: 0, py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 20 }}>
                    <CheckCircle sx={{ fontSize: 14, color: 'success.main' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Email Conversations"
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
                <ListItem sx={{ px: 0, py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 20 }}>
                    <CheckCircle sx={{ fontSize: 14, color: 'success.main' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Content Analysis"
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              </List>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Accounts List */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Email Accounts
        </Typography>

        {loadingAccounts ? (
          <CircularProgress />
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Email Account</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Emails Synced</TableCell>
                  <TableCell>Last Sync</TableCell>
                  <TableCell>Auto Sync</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {accounts?.accounts?.map((account) => (
                  <React.Fragment key={account.account_id}>
                    <TableRow>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <AccountCircle />
                          <Box>
                            <Typography variant="body2" fontWeight="bold">
                              {account.email_address}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {account.display_name}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={account.account_type.toUpperCase()}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(account.sync_status)}
                          <Chip
                            label={account.sync_status}
                            color={getStatusColor(account.sync_status)}
                            size="small"
                          />
                        </Box>
                      </TableCell>
                      <TableCell>{account.total_emails_synced}</TableCell>
                      <TableCell>{formatLastSync(account.last_sync_at)}</TableCell>
                      <TableCell>
                        <Switch
                          checked={account.auto_sync_enabled}
                          size="small"
                          onChange={(e) => {
                            updateAccountMutation.mutate({
                              accountId: account.account_id,
                              updateData: { auto_sync_enabled: e.target.checked }
                            });
                          }}
                          disabled={updateAccountMutation.isPending}
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Tooltip title="Sync Account">
                            <IconButton
                              size="small"
                              onClick={() => triggerSyncMutation.mutate({ accountIds: [account.account_id] })}
                              disabled={triggerSyncMutation.isPending}
                            >
                              <Sync />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit Account">
                            <IconButton
                              size="small"
                              onClick={() => handleEditAccount(account)}
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="View Details">
                            <IconButton
                              size="small"
                              onClick={() => setExpandedAccount(
                                expandedAccount === account.account_id ? null : account.account_id
                              )}
                            >
                              {expandedAccount === account.account_id ? <ExpandLess /> : <ExpandMore />}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete Account">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => deleteAccountMutation.mutate(account.account_id)}
                              disabled={deleteAccountMutation.isPending}
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
                        <Collapse in={expandedAccount === account.account_id} timeout="auto" unmountOnExit>
                          <Box sx={{ margin: 1, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                            <Grid container spacing={2}>
                              <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" gutterBottom>
                                  Sync Configuration
                                </Typography>
                                <Typography variant="body2">
                                  Interval: {account.sync_interval_minutes} minutes
                                </Typography>
                                <Typography variant="body2">
                                  Next Sync: {formatLastSync(account.next_sync_at)}
                                </Typography>
                              </Grid>
                              <Grid item xs={12} md={6}>
                                {account.last_error && (
                                  <Alert severity="error" sx={{ mt: 1 }}>
                                    {account.last_error}
                                  </Alert>
                                )}
                              </Grid>
                            </Grid>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Add Account Dialog */}
      <Dialog open={showAddDialog} onClose={() => setShowAddDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add Email Account</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                select
                label="Account Type"
                value={newAccount.account_type}
                onChange={(e) => handleAccountTypeChange(e.target.value)}
                fullWidth
              >
                <MenuItem value="gmail">Gmail</MenuItem>
                <MenuItem value="outlook">Outlook</MenuItem>
                <MenuItem value="imap">IMAP</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Email Address"
                value={newAccount.email_address}
                onChange={(e) => setNewAccount({ ...newAccount, email_address: e.target.value })}
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Display Name"
                value={newAccount.display_name}
                onChange={(e) => setNewAccount({ ...newAccount, display_name: e.target.value })}
                fullWidth
              />
            </Grid>
            {newAccount.account_type === 'gmail' && (
              <>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Access Token"
                    value={newAccount.auth_credentials.access_token}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, access_token: e.target.value }
                    })}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Refresh Token"
                    value={newAccount.auth_credentials.refresh_token}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, refresh_token: e.target.value }
                    })}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Client ID"
                    value={newAccount.auth_credentials.client_id}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, client_id: e.target.value }
                    })}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Client Secret"
                    value={newAccount.auth_credentials.client_secret}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, client_secret: e.target.value }
                    })}
                    fullWidth
                    required
                  />
                </Grid>
              </>
            )}
            {newAccount.account_type === 'imap' && (
              <>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="IMAP Server"
                    value={newAccount.auth_credentials.server}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, server: e.target.value }
                    })}
                    fullWidth
                    required
                    placeholder="imap.gmail.com"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    type="number"
                    label="IMAP Port"
                    value={newAccount.auth_credentials.port}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, port: parseInt(e.target.value) || 993 }
                    })}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Username"
                    value={newAccount.auth_credentials.username}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, username: e.target.value }
                    })}
                    fullWidth
                    required
                    placeholder="your-email@domain.com"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    type="password"
                    label="Password"
                    value={newAccount.auth_credentials.password}
                    onChange={(e) => setNewAccount({
                      ...newAccount,
                      auth_credentials: { ...newAccount.auth_credentials, password: e.target.value }
                    })}
                    fullWidth
                    required
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={newAccount.auth_credentials.use_ssl}
                        onChange={(e) => setNewAccount({
                          ...newAccount,
                          auth_credentials: { ...newAccount.auth_credentials, use_ssl: e.target.checked }
                        })}
                      />
                    }
                    label="Use SSL/TLS"
                  />
                </Grid>
              </>
            )}
            <Grid item xs={12} md={6}>
              <TextField
                type="number"
                label="Sync Interval (minutes)"
                value={newAccount.sync_interval_minutes}
                onChange={(e) => setNewAccount({ ...newAccount, sync_interval_minutes: parseInt(e.target.value) })}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newAccount.auto_sync_enabled}
                    onChange={(e) => setNewAccount({ ...newAccount, auto_sync_enabled: e.target.checked })}
                  />
                }
                label="Enable Auto Sync"
              />
            </Grid>

            {/* Sync Configuration Section */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Tune />
                Sync Configuration
              </Typography>
            </Grid>

            {/* Preset Selection */}
            {syncDefaults?.presets && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  Quick Setup Presets
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                  {Object.entries(syncDefaults.presets).map(([key, preset]: [string, any]) => (
                    <Button
                      key={key}
                      variant="outlined"
                      size="small"
                      onClick={() => applyPreset(key)}
                      sx={{ mb: 1 }}
                    >
                      {preset.name}
                    </Button>
                  ))}
                </Box>
              </Grid>
            )}

            {/* Days to Sync Configuration */}
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Days to Sync</InputLabel>
                <Select
                  value={newAccount.sync_days_back || ''}
                  onChange={(e) => setNewAccount({
                    ...newAccount,
                    sync_days_back: e.target.value === '' ? null : Number(e.target.value)
                  })}
                  label="Days to Sync"
                >
                  <MenuItem value="">Use Default ({syncDefaults?.system_defaults?.sync_days_back || 365} days)</MenuItem>
                  {/* API-driven options */}
                  {syncDefaults?.configuration_options?.sync_days_back?.options?.map((option: any) => (
                    <MenuItem key={option.value || 'unlimited'} value={option.value || ''}>
                      {option.label} - {option.description}
                    </MenuItem>
                  ))}
                  {/* Fallback options if API doesn't provide configuration */}
                  {(!syncDefaults?.configuration_options?.sync_days_back?.options ||
                    syncDefaults.configuration_options.sync_days_back.options.length === 0) && [
                    <MenuItem key="7" value={7}>7 days - Last week</MenuItem>,
                    <MenuItem key="30" value={30}>30 days - Last month</MenuItem>,
                    <MenuItem key="90" value={90}>90 days - Last 3 months</MenuItem>,
                    <MenuItem key="180" value={180}>180 days - Last 6 months</MenuItem>,
                    <MenuItem key="365" value={365}>365 days - Last year</MenuItem>,
                    <MenuItem key="730" value={730}>730 days - Last 2 years</MenuItem>,
                    <MenuItem key="unlimited" value="">Unlimited - All emails</MenuItem>
                  ]}
                </Select>
              </FormControl>
            </Grid>

            {/* Max Emails Configuration */}
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Max Emails Limit</InputLabel>
                <Select
                  value={newAccount.max_emails_limit || ''}
                  onChange={(e) => setNewAccount({
                    ...newAccount,
                    max_emails_limit: e.target.value === '' ? null : Number(e.target.value)
                  })}
                  label="Max Emails Limit"
                >
                  <MenuItem value="">Use Default ({syncDefaults?.system_defaults?.max_emails_limit || 5000} emails)</MenuItem>
                  {/* API-driven options */}
                  {syncDefaults?.configuration_options?.max_emails_limit?.options?.map((option: any) => (
                    <MenuItem key={option.value || 'unlimited'} value={option.value || ''}>
                      {option.label} - {option.description}
                    </MenuItem>
                  ))}
                  {/* Fallback options if API doesn't provide configuration */}
                  {(!syncDefaults?.configuration_options?.max_emails_limit?.options ||
                    syncDefaults.configuration_options.max_emails_limit.options.length === 0) && [
                    <MenuItem key="100" value={100}>100 emails - Small sync</MenuItem>,
                    <MenuItem key="500" value={500}>500 emails - Medium sync</MenuItem>,
                    <MenuItem key="1000" value={1000}>1,000 emails - Large sync</MenuItem>,
                    <MenuItem key="2500" value={2500}>2,500 emails - Extra large</MenuItem>,
                    <MenuItem key="5000" value={5000}>5,000 emails - Maximum</MenuItem>,
                    <MenuItem key="10000" value={10000}>10,000 emails - Enterprise</MenuItem>,
                    <MenuItem key="unlimited" value="">Unlimited - No limit</MenuItem>
                  ]}
                </Select>
              </FormControl>
            </Grid>

            {/* Configuration Preview */}
            {(newAccount.sync_days_back || newAccount.max_emails_limit) && (
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    Configuration: Sync {newAccount.sync_days_back ? `${newAccount.sync_days_back} days` : 'default period'} back,
                    limited to {newAccount.max_emails_limit ? `${newAccount.max_emails_limit} emails` : 'default limit'}
                  </Typography>
                </Alert>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddDialog(false)}>Cancel</Button>
          <Button
            onClick={() => createAccountMutation.mutate(newAccount)}
            variant="contained"
            disabled={createAccountMutation.isPending || !newAccount.email_address}
          >
            {createAccountMutation.isPending ? <CircularProgress size={20} /> : 'Add Account'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Account Dialog */}
      <Dialog open={showEditDialog} onClose={() => setShowEditDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Account Settings</DialogTitle>
        <DialogContent>
          {editingAccount && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <TextField
                  label="Display Name"
                  value={editingAccount.display_name || ''}
                  onChange={(e) => setEditingAccount({
                    ...editingAccount,
                    display_name: e.target.value
                  })}
                  fullWidth
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  type="number"
                  label="Sync Interval (minutes)"
                  value={editingAccount.sync_interval_minutes || 15}
                  onChange={(e) => setEditingAccount({
                    ...editingAccount,
                    sync_interval_minutes: parseInt(e.target.value)
                  })}
                  fullWidth
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={editingAccount.auto_sync_enabled || false}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auto_sync_enabled: e.target.checked
                      })}
                    />
                  }
                  label="Enable Auto Sync"
                />
              </Grid>

              {/* Email Account Settings Section */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Settings />
                  Email Account Settings
                </Typography>
              </Grid>

              {editingAccount.account_type === 'imap' && (
                <>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="IMAP Server"
                      value={editingAccount.auth_credentials?.server || ''}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          server: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="imap.gmail.com"
                      helperText={
                        editingAccount.auth_credentials?.server?.includes('[Current Server')
                          ? "Server is configured. Enter new server address to update."
                          : "Your email provider's IMAP server address"
                      }
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      type="number"
                      label="IMAP Port"
                      value={editingAccount.auth_credentials?.port || 993}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          port: parseInt(e.target.value) || 993
                        }
                      })}
                      fullWidth
                      helperText="Usually 993 for SSL/TLS"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Username"
                      value={editingAccount.auth_credentials?.username || editingAccount.email_address}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          username: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="your-email@domain.com"
                      helperText="Your email address or username"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      type="password"
                      label="Password"
                      value={editingAccount.auth_credentials?.password || ''}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          password: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="Enter new password (leave blank to keep current)"
                      helperText={
                        editingAccount.auth_credentials?.password === '••••••••'
                          ? "••••••••  = Password configured. Enter new password or clear to update, leave as-is to keep current."
                          : "Enter new password or leave blank to keep existing"
                      }
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={editingAccount.auth_credentials?.use_ssl ?? true}
                          onChange={(e) => setEditingAccount({
                            ...editingAccount,
                            auth_credentials: {
                              ...editingAccount.auth_credentials,
                              use_ssl: e.target.checked
                            }
                          })}
                        />
                      }
                      label="Use SSL/TLS"
                    />
                  </Grid>
                </>
              )}

              {editingAccount.account_type === 'gmail' && (
                <>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Client ID"
                      value={editingAccount.auth_credentials?.client_id || ''}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          client_id: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="Enter new Client ID (leave blank to keep current)"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      type="password"
                      label="Client Secret"
                      value={editingAccount.auth_credentials?.client_secret || ''}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          client_secret: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="Enter new Client Secret (leave blank to keep current)"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Access Token"
                      value={editingAccount.auth_credentials?.access_token || ''}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          access_token: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="Enter new Access Token (leave blank to keep current)"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Refresh Token"
                      value={editingAccount.auth_credentials?.refresh_token || ''}
                      onChange={(e) => setEditingAccount({
                        ...editingAccount,
                        auth_credentials: {
                          ...editingAccount.auth_credentials,
                          refresh_token: e.target.value
                        }
                      })}
                      fullWidth
                      placeholder="Enter new Refresh Token (leave blank to keep current)"
                    />
                  </Grid>
                </>
              )}

              {/* Sync Configuration Section */}
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Tune />
                  Sync Configuration
                </Typography>
              </Grid>

              {/* Days to Sync Configuration */}
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Days to Sync</InputLabel>
                  <Select
                    value={
                      editingAccount.sync_days_back !== null
                        ? editingAccount.sync_days_back
                        : (syncDefaults?.system_defaults?.sync_days_back || 365)
                    }
                    onChange={(e) => setEditingAccount({
                      ...editingAccount,
                      sync_days_back: e.target.value === '' ? null : Number(e.target.value)
                    })}
                    label="Days to Sync"
                  >
                    {/* Current/Default option */}
                    <MenuItem value={syncDefaults?.system_defaults?.sync_days_back || 365}>
                      {syncDefaults?.system_defaults?.sync_days_back || 365} days (System Default)
                    </MenuItem>
                    {/* API-driven options */}
                    {syncDefaults?.configuration_options?.sync_days_back?.options?.map((option: any) => (
                      <MenuItem key={option.value || 'unlimited'} value={option.value || ''}>
                        {option.label} - {option.description}
                      </MenuItem>
                    ))}
                    {/* Fallback options if API doesn't provide configuration */}
                    {(!syncDefaults?.configuration_options?.sync_days_back?.options ||
                      syncDefaults.configuration_options.sync_days_back.options.length === 0) && [
                      <MenuItem key="7" value={7}>7 days - Last week</MenuItem>,
                      <MenuItem key="30" value={30}>30 days - Last month</MenuItem>,
                      <MenuItem key="90" value={90}>90 days - Last 3 months</MenuItem>,
                      <MenuItem key="180" value={180}>180 days - Last 6 months</MenuItem>,
                      <MenuItem key="365" value={365}>365 days - Last year</MenuItem>,
                      <MenuItem key="730" value={730}>730 days - Last 2 years</MenuItem>,
                      <MenuItem key="unlimited" value="">Unlimited - All emails</MenuItem>
                    ]}
                  </Select>
                </FormControl>
              </Grid>

              {/* Max Emails Configuration */}
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Max Emails Limit</InputLabel>
                  <Select
                    value={
                      editingAccount.max_emails_limit !== null
                        ? editingAccount.max_emails_limit
                        : (syncDefaults?.system_defaults?.max_emails_limit || 5000)
                    }
                    onChange={(e) => setEditingAccount({
                      ...editingAccount,
                      max_emails_limit: e.target.value === '' ? null : Number(e.target.value)
                    })}
                    label="Max Emails Limit"
                  >
                    {/* Current/Default option */}
                    <MenuItem value={syncDefaults?.system_defaults?.max_emails_limit || 5000}>
                      {syncDefaults?.system_defaults?.max_emails_limit || 5000} emails (System Default)
                    </MenuItem>
                    {/* API-driven options */}
                    {syncDefaults?.configuration_options?.max_emails_limit?.options?.map((option: any) => (
                      <MenuItem key={option.value || 'unlimited'} value={option.value || ''}>
                        {option.label} - {option.description}
                      </MenuItem>
                    ))}
                    {/* Fallback options if API doesn't provide configuration */}
                    {(!syncDefaults?.configuration_options?.max_emails_limit?.options ||
                      syncDefaults.configuration_options.max_emails_limit.options.length === 0) && [
                      <MenuItem key="100" value={100}>100 emails - Small sync</MenuItem>,
                      <MenuItem key="500" value={500}>500 emails - Medium sync</MenuItem>,
                      <MenuItem key="1000" value={1000}>1,000 emails - Large sync</MenuItem>,
                      <MenuItem key="2500" value={2500}>2,500 emails - Extra large</MenuItem>,
                      <MenuItem key="5000" value={5000}>5,000 emails - Maximum</MenuItem>,
                      <MenuItem key="10000" value={10000}>10,000 emails - Enterprise</MenuItem>,
                      <MenuItem key="unlimited" value="">Unlimited - No limit</MenuItem>
                    ]}
                  </Select>
                </FormControl>
              </Grid>

              {/* Current Configuration Display */}
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    <strong>Configuration:</strong> Sync {
                      editingAccount.sync_days_back !== null
                        ? `${editingAccount.sync_days_back} days`
                        : `${syncDefaults?.system_defaults?.sync_days_back || 365} days (default)`
                    } back, limited to {
                      editingAccount.max_emails_limit !== null
                        ? `${editingAccount.max_emails_limit} emails`
                        : `${syncDefaults?.system_defaults?.max_emails_limit || 5000} emails (default)`
                    }
                  </Typography>
                </Alert>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowEditDialog(false)}>Cancel</Button>
          <Button
            onClick={() => {
              if (editingAccount) {
                // Prepare auth_credentials only if there are changes (non-empty values)
                const authCredentials: any = {};
                const currentAuth = editingAccount.auth_credentials;

                // Only include fields that have been actually changed (not placeholders)
                if (currentAuth?.server && !currentAuth.server.includes('[Current Server')) {
                  authCredentials.server = currentAuth.server;
                }
                if (currentAuth?.port) authCredentials.port = currentAuth.port;
                if (currentAuth?.username) authCredentials.username = currentAuth.username;
                // Only include password if it's not the masked placeholder and has actual content
                if (currentAuth?.password && currentAuth.password !== '••••••••') {
                  authCredentials.password = currentAuth.password;
                }
                if (currentAuth?.use_ssl !== undefined) authCredentials.use_ssl = currentAuth.use_ssl;
                if (currentAuth?.client_id && !currentAuth.client_id.includes('[Current Client ID')) {
                  authCredentials.client_id = currentAuth.client_id;
                }
                if (currentAuth?.client_secret && currentAuth.client_secret !== '••••••••••••••••') {
                  authCredentials.client_secret = currentAuth.client_secret;
                }
                if (currentAuth?.access_token && currentAuth.access_token !== '••••••••••••••••') {
                  authCredentials.access_token = currentAuth.access_token;
                }
                if (currentAuth?.refresh_token && currentAuth.refresh_token !== '••••••••••••••••') {
                  authCredentials.refresh_token = currentAuth.refresh_token;
                }
                if (currentAuth?.auth_type) authCredentials.auth_type = currentAuth.auth_type;

                updateAccountMutation.mutate({
                  accountId: editingAccount.account_id,
                  updateData: {
                    display_name: editingAccount.display_name,
                    sync_interval_minutes: editingAccount.sync_interval_minutes,
                    auto_sync_enabled: editingAccount.auto_sync_enabled,
                    sync_days_back: editingAccount.sync_days_back,
                    max_emails_limit: editingAccount.max_emails_limit,
                    // Only include auth_credentials if there are values to update
                    ...(Object.keys(authCredentials).length > 0 && { auth_credentials: authCredentials })
                  }
                });
                setShowEditDialog(false);
              }
            }}
            variant="contained"
            disabled={updateAccountMutation.isPending}
          >
            {updateAccountMutation.isPending ? <CircularProgress size={20} /> : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EmailSyncDashboard;