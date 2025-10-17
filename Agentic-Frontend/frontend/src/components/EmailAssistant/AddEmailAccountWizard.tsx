/**
 * Add Email Account Wizard - Multi-Step Email Account Setup
 *
 * Implements a comprehensive wizard for adding email accounts with proper
 * IMAP folder discovery and V2 sync configuration.
 *
 * Steps:
 * 1. Account Credentials - Basic account info and IMAP credentials
 * 2. Folder Discovery - Connect to IMAP, discover and select folders
 * 3. Sync Configuration - Configure sync window and limits
 * 4. Review & Confirm - Summary and account creation
 *
 * RFC Compliance:
 * - RFC 3501: IMAP4rev1 protocol
 * - RFC 6154: Special-Use Mailbox Extensions (INBOX, Sent, Drafts, etc.)
 * - RFC 4551: CONDSTORE extension for efficient sync
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stepper,
  Step,
  StepLabel,
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Alert,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  Chip,
  CircularProgress,
  Stack,
  Paper,
  Divider,
  Grid,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Folder as FolderIcon,
  FolderSpecial as FolderSpecialIcon,
  Inbox as InboxIcon,
  Send as SendIcon,
  Drafts as DraftsIcon,
  Delete as DeleteIcon,
  Star as StarIcon,
  Archive as ArchiveIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import apiClient from '../../services/api';

interface AddEmailAccountWizardProps {
  open: boolean;
  onClose: () => void;
  onAccountAdded: () => void;
}

interface AccountCredentials {
  account_type: string;
  email_address: string;
  display_name: string;
  server: string;
  port: number;
  username: string;
  password: string;
  use_ssl: boolean;
}

interface FolderInfo {
  name: string;
  flags: string[];
  delim: string;
  special_use?: string; // RFC 6154 special-use flags
}

interface SyncConfig {
  sync_window_value: number;
  sync_window_unit: 'days' | 'weeks' | 'months' | 'years' | 'all';
  selected_folders: string[];
  sync_attachments: boolean;
  max_attachment_size_mb: number;
  include_spam: boolean;
  include_trash: boolean;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
}

const STEPS = ['Account Credentials', 'Folder Selection', 'Sync Configuration', 'Review'];

// RFC 6154 Special-Use folder types
const SPECIAL_FOLDER_ICONS: Record<string, React.ReactNode> = {
  '\\Inbox': <InboxIcon />,
  '\\Sent': <SendIcon />,
  '\\Drafts': <DraftsIcon />,
  '\\Trash': <DeleteIcon />,
  '\\Junk': <WarningIcon />,
  '\\Archive': <ArchiveIcon />,
  '\\Flagged': <StarIcon />,
  '\\All': <FolderSpecialIcon />,
};

const RECOMMENDED_FOLDERS = ['INBOX', 'Sent', 'Drafts', 'Sent Items', 'Sent Mail'];

export const AddEmailAccountWizard: React.FC<AddEmailAccountWizardProps> = ({
  open,
  onClose,
  onAccountAdded,
}) => {
  const { enqueueSnackbar } = useSnackbar();
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [discoveringFolders, setDiscoveringFolders] = useState(false);
  const [temporaryAccountId, setTemporaryAccountId] = useState<string | null>(null);

  // Step 1: Account Credentials
  const [credentials, setCredentials] = useState<AccountCredentials>({
    account_type: 'imap',
    email_address: '',
    display_name: '',
    server: '',
    port: 993,
    username: '',
    password: '',
    use_ssl: true,
  });

  // Step 2: Folder Discovery
  const [availableFolders, setAvailableFolders] = useState<FolderInfo[]>([]);
  const [folderDiscoveryError, setFolderDiscoveryError] = useState<string | null>(null);

  // Step 3: Sync Configuration
  const [syncConfig, setSyncConfig] = useState<SyncConfig>({
    sync_window_value: 90,
    sync_window_unit: 'days',
    selected_folders: ['INBOX'],
    sync_attachments: true,
    max_attachment_size_mb: 25,
    include_spam: false,
    include_trash: false,
    auto_sync_enabled: true,
    sync_interval_minutes: 15,
  });

  // Handle credential changes
  const handleCredentialChange = (field: keyof AccountCredentials, value: any) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
  };

  // Handle sync config changes
  const handleSyncConfigChange = (field: keyof SyncConfig, value: any) => {
    setSyncConfig(prev => ({ ...prev, [field]: value }));
  };

  // Step 1: Test Connection & Create Temporary Account
  const testConnection = async (): Promise<boolean> => {
    setTestingConnection(true);
    setFolderDiscoveryError(null);

    try {
      // Create temporary account for folder discovery
      const accountData = {
        account_type: credentials.account_type,
        email_address: credentials.email_address,
        display_name: credentials.display_name || credentials.email_address,
        auth_credentials: {
          auth_type: 'password',
          server: credentials.server,
          port: credentials.port,
          username: credentials.username || credentials.email_address,
          password: credentials.password,
          use_ssl: credentials.use_ssl,
        },
        sync_settings: {
          folders_to_sync: ['INBOX'], // Temporary - will be updated in step 3
        },
        sync_interval_minutes: 15,
        auto_sync_enabled: false, // Don't start syncing yet
      };

      const response = await apiClient.post('/api/v1/email-sync/accounts', accountData);
      setTemporaryAccountId(response.data.account_id);

      enqueueSnackbar('Connection successful! Account created.', { variant: 'success' });
      return true;
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Connection failed';
      setFolderDiscoveryError(errorMsg);
      enqueueSnackbar(`Connection failed: ${errorMsg}`, { variant: 'error' });
      return false;
    } finally {
      setTestingConnection(false);
    }
  };

  // Auto-discover folders when user reaches Step 2 (Folder Selection)
  useEffect(() => {
    if (activeStep === 1 && temporaryAccountId && availableFolders.length === 0 && !discoveringFolders) {
      // Automatically discover folders when step 2 is rendered
      discoverFolders();
    }
  }, [activeStep, temporaryAccountId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Step 2: Discover Folders
  const discoverFolders = async () => {
    if (!temporaryAccountId) {
      enqueueSnackbar('Account ID not found. Please retry connection.', { variant: 'error' });
      return;
    }

    setDiscoveringFolders(true);
    setFolderDiscoveryError(null);

    try {
      const response = await apiClient.get(`/api/v1/email-sync/v2/accounts/${temporaryAccountId}/folders`);
      const folders: FolderInfo[] = response.data.folders || [];

      setAvailableFolders(folders);

      // Auto-select recommended folders
      const recommended = folders
        .filter(f => RECOMMENDED_FOLDERS.some(rec => f.name.toLowerCase().includes(rec.toLowerCase())))
        .map(f => f.name);

      setSyncConfig(prev => ({
        ...prev,
        selected_folders: recommended.length > 0 ? recommended : ['INBOX'],
      }));

      enqueueSnackbar(`Discovered ${folders.length} folders`, { variant: 'success' });
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to discover folders';
      setFolderDiscoveryError(errorMsg);
      enqueueSnackbar(`Folder discovery failed: ${errorMsg}`, { variant: 'error' });
    } finally {
      setDiscoveringFolders(false);
    }
  };

  // Toggle folder selection
  const toggleFolder = (folderName: string) => {
    setSyncConfig(prev => {
      const isSelected = prev.selected_folders.includes(folderName);
      if (isSelected) {
        // Don't allow deselecting all folders
        if (prev.selected_folders.length === 1) {
          enqueueSnackbar('At least one folder must be selected', { variant: 'warning' });
          return prev;
        }
        return {
          ...prev,
          selected_folders: prev.selected_folders.filter(f => f !== folderName),
        };
      } else {
        return {
          ...prev,
          selected_folders: [...prev.selected_folders, folderName],
        };
      }
    });
  };

  // Get folder icon based on special-use flags
  const getFolderIcon = (folder: FolderInfo): React.ReactNode => {
    if (folder.special_use && SPECIAL_FOLDER_ICONS[folder.special_use]) {
      return SPECIAL_FOLDER_ICONS[folder.special_use];
    }
    return <FolderIcon />;
  };

  // Check if folder is recommended
  const isRecommendedFolder = (folderName: string): boolean => {
    return RECOMMENDED_FOLDERS.some(rec => folderName.toLowerCase().includes(rec.toLowerCase()));
  };

  // Handle next step
  const handleNext = async () => {
    if (activeStep === 0) {
      // Test connection before moving to step 2
      const success = await testConnection();
      if (!success) return;
    }
    // Note: Folder discovery now happens automatically via useEffect when step 1 is rendered

    setActiveStep(prev => prev + 1);
  };

  // Handle back
  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  // Handle final account creation
  const handleFinish = async () => {
    if (!temporaryAccountId) {
      enqueueSnackbar('Account ID not found', { variant: 'error' });
      return;
    }

    setLoading(true);

    try {
      // Update account with final configuration using V2 API
      const syncConfigPayload = {
        sync_window: {
          value: syncConfig.sync_window_value,
          unit: syncConfig.sync_window_unit,
        },
        sync_folders: syncConfig.selected_folders,
      };

      await apiClient.put(
        `/api/v1/email-sync/v2/accounts/${temporaryAccountId}/sync-config`,
        syncConfigPayload
      );

      // Update other account settings
      await apiClient.put(`/api/v1/email-sync/accounts/${temporaryAccountId}`, {
        auto_sync_enabled: syncConfig.auto_sync_enabled,
        sync_interval_minutes: syncConfig.sync_interval_minutes,
        sync_settings: {
          sync_attachments: syncConfig.sync_attachments,
          max_attachment_size_mb: syncConfig.max_attachment_size_mb,
          include_spam: syncConfig.include_spam,
          include_trash: syncConfig.include_trash,
        },
      });

      // Trigger initial sync for the account
      try {
        await apiClient.post('/api/v1/email-sync/v2/sync', null, {
          params: {
            account_ids: [temporaryAccountId],
            force_full_sync: false,
          },
        });
        enqueueSnackbar('Email account configured successfully! Initial sync started.', { variant: 'success' });
      } catch (syncError) {
        console.warn('Failed to trigger initial sync:', syncError);
        enqueueSnackbar('Email account configured successfully! Sync will start automatically.', { variant: 'success' });
      }

      onAccountAdded();
      handleClose();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to configure account';
      enqueueSnackbar(`Configuration failed: ${errorMsg}`, { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Handle close (cleanup temporary account if needed)
  const handleClose = async () => {
    // If user closes wizard before completing, delete temporary account
    if (temporaryAccountId && activeStep < STEPS.length - 1) {
      try {
        await apiClient.delete(`/api/v1/email-sync/accounts/${temporaryAccountId}`);
      } catch (error) {
        console.error('Failed to cleanup temporary account:', error);
      }
    }

    // Reset state
    setActiveStep(0);
    setCredentials({
      account_type: 'imap',
      email_address: '',
      display_name: '',
      server: '',
      port: 993,
      username: '',
      password: '',
      use_ssl: true,
    });
    setAvailableFolders([]);
    setFolderDiscoveryError(null);
    setTemporaryAccountId(null);
    setSyncConfig({
      sync_window_value: 90,
      sync_window_unit: 'days',
      selected_folders: ['INBOX'],
      sync_attachments: true,
      max_attachment_size_mb: 25,
      include_spam: false,
      include_trash: false,
      auto_sync_enabled: true,
      sync_interval_minutes: 15,
    });

    onClose();
  };

  // Render step content
  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return renderCredentialsStep();
      case 1:
        return renderFolderSelectionStep();
      case 2:
        return renderSyncConfigStep();
      case 3:
        return renderReviewStep();
      default:
        return null;
    }
  };

  // Step 1: Credentials
  const renderCredentialsStep = () => (
    <Stack spacing={3}>
      <Alert severity="info">
        Enter your email account credentials. We'll test the connection before proceeding.
      </Alert>

      <FormControl fullWidth>
        <InputLabel>Account Type</InputLabel>
        <Select
          value={credentials.account_type}
          label="Account Type"
          onChange={e => handleCredentialChange('account_type', e.target.value)}
        >
          <MenuItem value="imap">IMAP (Universal)</MenuItem>
          <MenuItem value="gmail">Gmail (OAuth2)</MenuItem>
          <MenuItem value="outlook">Outlook (OAuth2)</MenuItem>
        </Select>
      </FormControl>

      <TextField
        label="Email Address"
        type="email"
        value={credentials.email_address}
        onChange={e => handleCredentialChange('email_address', e.target.value)}
        required
        fullWidth
        helperText="Your email address"
      />

      <TextField
        label="Display Name"
        value={credentials.display_name}
        onChange={e => handleCredentialChange('display_name', e.target.value)}
        placeholder="Optional - defaults to email address"
        fullWidth
      />

      {credentials.account_type === 'imap' && (
        <>
          <Grid container spacing={2}>
            <Grid item xs={8}>
              <TextField
                label="IMAP Server"
                value={credentials.server}
                onChange={e => handleCredentialChange('server', e.target.value)}
                placeholder="imap.gmail.com"
                required
                fullWidth
                helperText="IMAP server hostname"
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                label="Port"
                type="number"
                value={credentials.port}
                onChange={e => handleCredentialChange('port', parseInt(e.target.value) || 993)}
                required
                fullWidth
              />
            </Grid>
          </Grid>

          <TextField
            label="Username"
            value={credentials.username}
            onChange={e => handleCredentialChange('username', e.target.value)}
            placeholder="Usually your email address"
            fullWidth
          />

          <TextField
            label="Password"
            type="password"
            value={credentials.password}
            onChange={e => handleCredentialChange('password', e.target.value)}
            required
            fullWidth
            helperText="For Gmail, use an App Password"
          />

          <FormControlLabel
            control={
              <Switch
                checked={credentials.use_ssl}
                onChange={e => handleCredentialChange('use_ssl', e.target.checked)}
              />
            }
            label="Use SSL/TLS (recommended)"
          />
        </>
      )}

      {credentials.account_type === 'gmail' && (
        <Alert severity="info">
          Gmail OAuth2 setup coming soon. Please use IMAP for now with an App Password.
        </Alert>
      )}

      {credentials.account_type === 'outlook' && (
        <Alert severity="info">
          Outlook OAuth2 setup coming soon. Please use IMAP for now.
        </Alert>
      )}

      {folderDiscoveryError && (
        <Alert severity="error" onClose={() => setFolderDiscoveryError(null)}>
          {folderDiscoveryError}
        </Alert>
      )}
    </Stack>
  );

  // Step 2: Folder Selection
  const renderFolderSelectionStep = () => (
    <Stack spacing={3}>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">Select Folders to Sync</Typography>
          <Tooltip title="Refresh folder list">
            <IconButton onClick={discoverFolders} disabled={discoveringFolders}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          Select which folders you want to sync. Recommended folders are pre-selected. You can change this later.
        </Alert>

        {discoveringFolders && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        )}

        {!discoveringFolders && availableFolders.length > 0 && (
          <>
            <Paper variant="outlined" sx={{ mb: 2 }}>
              <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                {availableFolders.map((folder, index) => {
                  const isSelected = syncConfig.selected_folders.includes(folder.name);
                  const isRecommended = isRecommendedFolder(folder.name);

                  return (
                    <ListItem
                      key={folder.name}
                      button
                      onClick={() => toggleFolder(folder.name)}
                      divider={index < availableFolders.length - 1}
                    >
                      <ListItemIcon>
                        <Checkbox checked={isSelected} />
                      </ListItemIcon>
                      <ListItemIcon>{getFolderIcon(folder)}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {folder.name}
                            {isRecommended && (
                              <Chip label="Recommended" size="small" color="primary" />
                            )}
                          </Box>
                        }
                        secondary={folder.special_use ? `Special use: ${folder.special_use}` : undefined}
                      />
                    </ListItem>
                  );
                })}
              </List>
            </Paper>

            <Typography variant="body2" color="text.secondary">
              Selected: {syncConfig.selected_folders.length} folder{syncConfig.selected_folders.length !== 1 ? 's' : ''}
            </Typography>
          </>
        )}

        {!discoveringFolders && availableFolders.length === 0 && (
          <Alert severity="warning">
            No folders discovered. Click the refresh button to try again.
          </Alert>
        )}

        {folderDiscoveryError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {folderDiscoveryError}
          </Alert>
        )}
      </Box>
    </Stack>
  );

  // Step 3: Sync Configuration
  const renderSyncConfigStep = () => (
    <Stack spacing={3}>
      <Alert severity="info">
        Configure how emails should be synchronized. These settings affect performance and storage.
      </Alert>

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Sync Window
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          How far back should we sync emails?
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={6}>
            <TextField
              label="Value"
              type="number"
              value={syncConfig.sync_window_value}
              onChange={e => handleSyncConfigChange('sync_window_value', parseInt(e.target.value) || 1)}
              fullWidth
              InputProps={{ inputProps: { min: 1 } }}
            />
          </Grid>
          <Grid item xs={6}>
            <FormControl fullWidth>
              <InputLabel>Unit</InputLabel>
              <Select
                value={syncConfig.sync_window_unit}
                label="Unit"
                onChange={e => handleSyncConfigChange('sync_window_unit', e.target.value)}
              >
                <MenuItem value="days">Days</MenuItem>
                <MenuItem value="weeks">Weeks</MenuItem>
                <MenuItem value="months">Months</MenuItem>
                <MenuItem value="years">Years</MenuItem>
                <MenuItem value="all">All Time</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        <Alert severity="info" sx={{ mt: 2 }}>
          Will sync emails from the last{' '}
          {syncConfig.sync_window_unit === 'all'
            ? 'all time (entire mailbox)'
            : `${syncConfig.sync_window_value} ${syncConfig.sync_window_unit}`}
        </Alert>
      </Box>

      <Divider />

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Sync Options
        </Typography>

        <Stack spacing={2}>
          <FormControlLabel
            control={
              <Switch
                checked={syncConfig.sync_attachments}
                onChange={e => handleSyncConfigChange('sync_attachments', e.target.checked)}
              />
            }
            label="Sync email attachments"
          />

          {syncConfig.sync_attachments && (
            <TextField
              label="Max Attachment Size (MB)"
              type="number"
              value={syncConfig.max_attachment_size_mb}
              onChange={e => handleSyncConfigChange('max_attachment_size_mb', parseInt(e.target.value) || 25)}
              fullWidth
              sx={{ ml: 4 }}
              InputProps={{ inputProps: { min: 1, max: 100 } }}
            />
          )}

          <FormControlLabel
            control={
              <Switch
                checked={syncConfig.include_spam}
                onChange={e => handleSyncConfigChange('include_spam', e.target.checked)}
              />
            }
            label="Include Spam/Junk folder"
          />

          <FormControlLabel
            control={
              <Switch
                checked={syncConfig.include_trash}
                onChange={e => handleSyncConfigChange('include_trash', e.target.checked)}
              />
            }
            label="Include Trash/Deleted Items folder"
          />
        </Stack>
      </Box>

      <Divider />

      <Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Auto-Sync Settings
        </Typography>

        <Stack spacing={2}>
          <FormControlLabel
            control={
              <Switch
                checked={syncConfig.auto_sync_enabled}
                onChange={e => handleSyncConfigChange('auto_sync_enabled', e.target.checked)}
              />
            }
            label="Enable automatic synchronization"
          />

          {syncConfig.auto_sync_enabled && (
            <FormControl fullWidth sx={{ ml: 4 }}>
              <InputLabel>Sync Interval</InputLabel>
              <Select
                value={syncConfig.sync_interval_minutes}
                label="Sync Interval"
                onChange={e => handleSyncConfigChange('sync_interval_minutes', e.target.value)}
              >
                <MenuItem value={5}>Every 5 minutes</MenuItem>
                <MenuItem value={15}>Every 15 minutes (recommended)</MenuItem>
                <MenuItem value={30}>Every 30 minutes</MenuItem>
                <MenuItem value={60}>Every hour</MenuItem>
              </Select>
            </FormControl>
          )}
        </Stack>
      </Box>
    </Stack>
  );

  // Step 4: Review
  const renderReviewStep = () => (
    <Stack spacing={3}>
      <Alert severity="success" icon={<CheckCircleIcon />}>
        Review your configuration before completing setup.
      </Alert>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Account Details
        </Typography>
        <Grid container spacing={1}>
          <Grid item xs={4}>
            <Typography variant="body2" color="text.secondary">
              Email:
            </Typography>
          </Grid>
          <Grid item xs={8}>
            <Typography variant="body2">{credentials.email_address}</Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="body2" color="text.secondary">
              Display Name:
            </Typography>
          </Grid>
          <Grid item xs={8}>
            <Typography variant="body2">
              {credentials.display_name || credentials.email_address}
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="body2" color="text.secondary">
              Server:
            </Typography>
          </Grid>
          <Grid item xs={8}>
            <Typography variant="body2">
              {credentials.server}:{credentials.port} (SSL: {credentials.use_ssl ? 'Yes' : 'No'})
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Folders to Sync ({syncConfig.selected_folders.length})
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {syncConfig.selected_folders.map(folder => (
            <Chip key={folder} label={folder} size="small" color="primary" />
          ))}
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Sync Configuration
        </Typography>
        <Grid container spacing={1}>
          <Grid item xs={4}>
            <Typography variant="body2" color="text.secondary">
              Sync Window:
            </Typography>
          </Grid>
          <Grid item xs={8}>
            <Typography variant="body2">
              {syncConfig.sync_window_unit === 'all'
                ? 'All time (entire mailbox)'
                : `Last ${syncConfig.sync_window_value} ${syncConfig.sync_window_unit}`}
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="body2" color="text.secondary">
              Attachments:
            </Typography>
          </Grid>
          <Grid item xs={8}>
            <Typography variant="body2">
              {syncConfig.sync_attachments
                ? `Yes (max ${syncConfig.max_attachment_size_mb} MB)`
                : 'No'}
            </Typography>
          </Grid>
          <Grid item xs={4}>
            <Typography variant="body2" color="text.secondary">
              Auto-sync:
            </Typography>
          </Grid>
          <Grid item xs={8}>
            <Typography variant="body2">
              {syncConfig.auto_sync_enabled
                ? `Every ${syncConfig.sync_interval_minutes} minutes`
                : 'Disabled'}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      <Alert severity="info">
        After setup completes, your emails will be synced and indexed for semantic search.
        You'll be able to chat with your email assistant to find and manage emails intelligently.
      </Alert>
    </Stack>
  );

  // Determine if we can proceed to next step
  const canProceed = () => {
    switch (activeStep) {
      case 0:
        return (
          credentials.email_address &&
          (credentials.account_type !== 'imap' || (credentials.server && credentials.password))
        );
      case 1:
        return syncConfig.selected_folders.length > 0;
      case 2:
        return true;
      case 3:
        return true;
      default:
        return false;
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box>
          <Typography variant="h6">Add Email Account</Typography>
          <Typography variant="body2" color="text.secondary">
            Configure your email account with V2 UID-based sync
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
            {STEPS.map(label => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {renderStepContent()}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Box sx={{ flex: '1 1 auto' }} />
        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={loading || testingConnection}>
            Back
          </Button>
        )}
        {activeStep < STEPS.length - 1 ? (
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={!canProceed() || loading || testingConnection}
          >
            {testingConnection ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                Testing Connection...
              </>
            ) : (
              'Next'
            )}
          </Button>
        ) : (
          <Button variant="contained" onClick={handleFinish} disabled={loading}>
            {loading ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                Completing Setup...
              </>
            ) : (
              'Complete Setup'
            )}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AddEmailAccountWizard;
