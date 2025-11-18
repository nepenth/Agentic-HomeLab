import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  useTheme,
  Alert,
  CircularProgress,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Sync as SyncIcon,
  Email as EmailIcon,
  VpnKey as VpnKeyIcon,
  CloudUpload as CloudUploadIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
  Schedule as ScheduleIcon,
  Category as CategoryIcon,
  Rule as RuleIcon,
  Assignment as AssignmentIcon,
  Analytics as AnalyticsIcon,
  Storage as StorageIcon,
  Build as BuildIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useEmail } from '../../../hooks/useEmail';
import { EmbeddingManagement } from '../EmbeddingManagement';
import { EmbeddingModelSelector } from '../EmbeddingModelSelector';
import { AddEmailAccountWizard } from '../AddEmailAccountWizard';
import apiClient from '../../../services/api';
import { useSnackbar } from 'notistack';

export const SettingsTab: React.FC = () => {
  const theme = useTheme();
  const { accounts, addAccount, updateAccount, deleteAccount, refreshAccounts } = useEmail();
  const { enqueueSnackbar } = useSnackbar();
  const [expandedPanel, setExpandedPanel] = useState<string | false>('accounts');

  // Add email account wizard state (V2)
  const [showAddAccountWizard, setShowAddAccountWizard] = useState(false);

  // Edit account state
  const [editingAccount, setEditingAccount] = useState<any>(null);
  const [editFormData, setEditFormData] = useState({
    sync_window_days: 90,
    auto_sync_enabled: true,
    sync_interval_minutes: 15,
    // Auth credentials for updates
    auth_credentials: {
      password: '',
      server: '',
      port: 993,
      username: '',
      use_ssl: true,
      client_id: '',
      client_secret: '',
      access_token: '',
      refresh_token: '',
    } as any
  });

  // Management function loading states
  const [clearingWorkflows, setClearingWorkflows] = useState(false);
  const [purgingEmails, setPurgingEmails] = useState(false);
  const [purgingEmbeddings, setPurgingEmbeddings] = useState(false);

  // AI Assistant settings - stored in SECONDS for better UX
  // (converted to milliseconds when saving to backend)
  const [assistantSettings, setAssistantSettings] = useState({
    defaultModel: 'qwen3:30b-a3b-thinking-2507-q8_0',
    enableStreaming: true,
    showThinking: true,
    autoSave: false,
    connectionTimeout: 30, // seconds
    responseTimeout: 120,  // seconds
    maxRetries: 3,
    autoReconnect: true,
  });
  const [loadingPreferences, setLoadingPreferences] = useState(true);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [defaultModelFromServer, setDefaultModelFromServer] = useState<string>('');

  // Load available models from Ollama
  React.useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await apiClient.getAvailableModels();
        setAvailableModels(response.models || []);
        setDefaultModelFromServer(response.default_model || '');
      } catch (error) {
        console.error('Failed to load models:', error);
      }
    };
    loadModels();
  }, []);

  // Load assistant settings from backend API on mount
  React.useEffect(() => {
    const loadPreferences = async () => {
      try {
        setLoadingPreferences(true);
        const prefs = await apiClient.getUserChatPreferences();

        // Convert backend snake_case to frontend camelCase
        // Convert milliseconds to seconds for frontend display
        setAssistantSettings({
          defaultModel: prefs.default_model || defaultModelFromServer || 'qwen3:30b-a3b-thinking-2507-q8_0',
          enableStreaming: prefs.enable_streaming ?? true,
          showThinking: prefs.show_thinking ?? true,
          autoSave: prefs.auto_save_conversations ?? false,
          connectionTimeout: Math.round((prefs.connection_timeout ?? 30000) / 1000),
          responseTimeout: Math.round((prefs.response_timeout ?? 120000) / 1000),
          maxRetries: prefs.max_retries ?? 3,
          autoReconnect: prefs.auto_reconnect ?? true,
        });
      } catch (error) {
        console.error('Failed to load assistant preferences:', error);
        enqueueSnackbar('Failed to load assistant settings', { variant: 'warning' });
      } finally {
        setLoadingPreferences(false);
      }
    };

    loadPreferences();
  }, []);

  const handlePanelChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPanel(isExpanded ? panel : false);
  };

  // Handle account added from wizard
  const handleAccountAdded = async () => {
    // Refresh accounts list
    await refreshAccounts();
    enqueueSnackbar('Email account added successfully! Sync will begin shortly.', { variant: 'success' });
  };

  // Handle edit account
  const handleEditAccount = (account: any) => {
    setEditingAccount(account);
    setEditFormData({
      sync_window_days: account.sync_window_days || 90,
      auto_sync_enabled: account.auto_sync_enabled !== undefined ? account.auto_sync_enabled : true,
      sync_interval_minutes: account.sync_interval_minutes || 15,
      auth_credentials: {
        // Initialize with placeholders or current values
        password: '••••••••',
        server: account.auth_credentials?.server || '[Current Server]',
        port: account.auth_credentials?.port || 993,
        username: account.auth_credentials?.username || account.email_address,
        use_ssl: account.auth_credentials?.use_ssl ?? true,
        client_id: account.account_type === 'gmail' ? '[Current Client ID]' : '',
        client_secret: account.account_type === 'gmail' ? '••••••••••••••••' : '',
        access_token: account.account_type === 'gmail' ? '••••••••••••••••' : '',
        refresh_token: account.account_type === 'gmail' ? '••••••••••••••••' : '',
      }
    });
  };

  const handleCloseEditDialog = () => {
    setEditingAccount(null);
  };

  const handleSaveAccountSettings = async () => {
    if (!editingAccount) return;

    try {
      // Prepare update data
      const updateData: any = {
        sync_window_days: editFormData.sync_window_days,
        auto_sync_enabled: editFormData.auto_sync_enabled,
        sync_interval_minutes: editFormData.sync_interval_minutes,
      };

      // Handle auth credentials update
      const authUpdates: any = {};
      const currentAuth = editFormData.auth_credentials;

      // Only include fields that have changed from placeholders
      if (currentAuth.password && currentAuth.password !== '••••••••') {
        authUpdates.password = currentAuth.password;
      }
      if (currentAuth.server && currentAuth.server !== '[Current Server]') {
        authUpdates.server = currentAuth.server;
      }
      if (currentAuth.port) authUpdates.port = currentAuth.port;
      if (currentAuth.username) authUpdates.username = currentAuth.username;
      if (currentAuth.use_ssl !== undefined) authUpdates.use_ssl = currentAuth.use_ssl;

      if (currentAuth.client_id && currentAuth.client_id !== '[Current Client ID]') {
        authUpdates.client_id = currentAuth.client_id;
      }
      if (currentAuth.client_secret && currentAuth.client_secret !== '••••••••••••••••') {
        authUpdates.client_secret = currentAuth.client_secret;
      }
      if (currentAuth.access_token && currentAuth.access_token !== '••••••••••••••••') {
        authUpdates.access_token = currentAuth.access_token;
      }
      if (currentAuth.refresh_token && currentAuth.refresh_token !== '••••••••••••••••') {
        authUpdates.refresh_token = currentAuth.refresh_token;
      }

      if (Object.keys(authUpdates).length > 0) {
        updateData.auth_credentials = authUpdates;
      }

      await updateAccount(editingAccount.account_id, updateData);
      enqueueSnackbar('Account settings updated successfully', { variant: 'success' });
      setEditingAccount(null);
      await refreshAccounts();
    } catch (error: any) {
      enqueueSnackbar(error?.message || 'Failed to update account settings', { variant: 'error' });
    }
  };

  // Management Functions
  const handleClearStuckWorkflows = async () => {
    if (!window.confirm('Clear all stuck workflows? This cannot be undone.')) return;

    setClearingWorkflows(true);
    try {
      await apiClient.post('/workflows/cleanup-stale');
      enqueueSnackbar('Stuck workflows cleared successfully', { variant: 'success' });
    } catch (error: any) {
      enqueueSnackbar(error?.message || 'Failed to clear workflows', { variant: 'error' });
    } finally {
      setClearingWorkflows(false);
    }
  };

  const handlePurgeEmails = async () => {
    if (!window.confirm('DANGER: Purge ALL emails? They will re-sync on next sync operation. This cannot be undone!')) return;

    setPurgingEmails(true);
    try {
      await apiClient.delete('/api/v1/email-sync/emails/purge-all');
      enqueueSnackbar('All emails purged successfully', { variant: 'success' });
    } catch (error: any) {
      enqueueSnackbar(error?.message || 'Failed to purge emails', { variant: 'error' });
    } finally {
      setPurgingEmails(false);
    }
  };

  const handlePurgeEmbeddings = async () => {
    if (!window.confirm('DANGER: Purge ALL embeddings? They will regenerate on next sync. This cannot be undone!')) return;

    setPurgingEmbeddings(true);
    try {
      await apiClient.delete('/api/v1/email-sync/embeddings/purge-all');
      enqueueSnackbar('All embeddings purged successfully', { variant: 'success' });
    } catch (error: any) {
      enqueueSnackbar(error?.message || 'Failed to purge embeddings', { variant: 'error' });
    } finally {
      setPurgingEmbeddings(false);
    }
  };

  return (
    <Box sx={{ height: '100%', overflow: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
        Email Assistant Settings
      </Typography>

      {/* Email Accounts */}
      <Accordion expanded={expandedPanel === 'accounts'} onChange={handlePanelChange('accounts')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <EmailIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Email Accounts</Typography>
            <Chip label={`${accounts.length} accounts`} size="small" />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.secondary }}>
              Manage your connected email accounts. Configure sync settings and authentication.
            </Typography>

            <List>
              {accounts.map((account) => (
                <ListItem
                  key={account.account_id}
                  secondaryAction={
                    <Box>
                      <IconButton
                        edge="end"
                        aria-label="edit"
                        sx={{ mr: 1 }}
                        onClick={() => handleEditAccount(account)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() => deleteAccount(account.account_id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  }
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {account.display_name}
                        </Typography>
                        <Chip
                          label={account.sync_status}
                          size="small"
                          color={account.sync_status === 'active' ? 'success' : 'default'}
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                          {account.email_address}
                        </Typography>
                        <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                          {account.account_type} • {account.total_emails_synced} emails • Auto-sync:{' '}
                          {account.auto_sync_enabled ? 'On' : 'Off'}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              fullWidth
              sx={{ mt: 2 }}
              onClick={() => setShowAddAccountWizard(true)}
            >
              Add Email Account
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Email Sync Settings */}
      <Accordion expanded={expandedPanel === 'sync'} onChange={handlePanelChange('sync')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SyncIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Email Sync Settings</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Enable automatic email sync"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Sync Interval</InputLabel>
                <Select defaultValue={15} label="Sync Interval">
                  <MenuItem value={5}>Every 5 minutes</MenuItem>
                  <MenuItem value={15}>Every 15 minutes</MenuItem>
                  <MenuItem value={30}>Every 30 minutes</MenuItem>
                  <MenuItem value={60}>Every hour</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Sync Type</InputLabel>
                <Select defaultValue="incremental" label="Sync Type">
                  <MenuItem value="incremental">Incremental (new emails only)</MenuItem>
                  <MenuItem value="full">Full (all emails)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch />}
                label="Sync during business hours only (9 AM - 6 PM)"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Embedding Management */}
      <Accordion expanded={expandedPanel === 'embeddings'} onChange={handlePanelChange('embeddings')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <StorageIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Embedding Management</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Alert severity="info" sx={{ mb: 3 }}>
              Embeddings enable semantic search across your emails. You can configure which model to use for
              generating embeddings and regenerate them if needed.
            </Alert>

            {/* System Default Embedding Model */}
            <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                System Default Embedding Model
              </Typography>
              <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.secondary }}>
                This model will be used for all accounts unless overridden on a per-account basis.
              </Typography>
              <FormControl fullWidth>
                <InputLabel>Default Model</InputLabel>
                <Select defaultValue="snowflake-arctic-embed2:latest" label="Default Model">
                  <MenuItem value="snowflake-arctic-embed2:latest">
                    snowflake-arctic-embed2:latest (1024 dims)
                  </MenuItem>
                  <MenuItem value="nomic-embed-text:latest">nomic-embed-text:latest (768 dims)</MenuItem>
                  <MenuItem value="mxbai-embed-large:latest">mxbai-embed-large:latest (1024 dims)</MenuItem>
                </Select>
              </FormControl>
            </Paper>

            {/* Per-Account Embedding Configuration */}
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Per-Account Configuration
            </Typography>
            <List>
              {accounts.map((account) => (
                <Paper variant="outlined" key={account.account_id} sx={{ mb: 2, p: 2 }}>
                  <Typography variant="body1" sx={{ fontWeight: 600, mb: 1 }}>
                    {account.display_name}
                  </Typography>
                  <EmbeddingModelSelector accountId={account.account_id} />
                </Paper>
              ))}
            </List>

            {/* Advanced Embedding Management */}
            <Divider sx={{ my: 3 }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Advanced Management
            </Typography>
            <EmbeddingManagement />
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Processing Rules */}
      <Accordion expanded={expandedPanel === 'rules'} onChange={handlePanelChange('rules')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <RuleIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Processing Rules</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.secondary }}>
              Define rules for automatic email processing, categorization, and task creation.
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Coming soon: Create custom rules to automatically categorize emails, flag important messages, and
              create tasks based on patterns.
            </Alert>
            <Button variant="outlined" startIcon={<AddIcon />} disabled fullWidth>
              Add Processing Rule
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Task Templates */}
      <Accordion expanded={expandedPanel === 'tasks'} onChange={handlePanelChange('tasks')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AssignmentIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Task Templates</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.secondary }}>
              Create templates for common tasks to speed up task creation from emails.
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Coming soon: Save task templates with predefined titles, descriptions, priorities, and due dates.
            </Alert>
            <Button variant="outlined" startIcon={<AddIcon />} disabled fullWidth>
              Add Task Template
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Categories */}
      <Accordion expanded={expandedPanel === 'categories'} onChange={handlePanelChange('categories')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CategoryIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Email Categories</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.secondary }}>
              Manage custom categories for organizing your emails.
            </Typography>
            <Grid container spacing={1}>
              {['Work', 'Personal', 'Finance', 'Travel', 'Shopping', 'Newsletter'].map((category) => (
                <Grid item key={category}>
                  <Chip
                    label={category}
                    onDelete={() => { }}
                    color="primary"
                    variant="outlined"
                  />
                </Grid>
              ))}
            </Grid>
            <Button variant="outlined" startIcon={<AddIcon />} fullWidth sx={{ mt: 2 }}>
              Add Category
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Notifications */}
      <Accordion expanded={expandedPanel === 'notifications'} onChange={handlePanelChange('notifications')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <NotificationsIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Notifications</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Email notifications for new messages"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Notifications for high-priority tasks"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch />}
                label="Daily digest of unread emails"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch />}
                label="Sync status notifications"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* AI Assistant Settings */}
      <Accordion expanded={expandedPanel === 'assistant'} onChange={handlePanelChange('assistant')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CloudUploadIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>AI Assistant</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          {loadingPreferences ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
              <CircularProgress />
              <Typography sx={{ ml: 2 }}>Loading settings...</Typography>
            </Box>
          ) : (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Default Model</InputLabel>
                  <Select
                    value={assistantSettings.defaultModel}
                    label="Default Model"
                    onChange={(e) => setAssistantSettings({ ...assistantSettings, defaultModel: e.target.value })}
                  >
                    {availableModels.length > 0 ? (
                      availableModels.map((model) => (
                        <MenuItem key={model} value={model}>
                          {model}
                          {model === defaultModelFromServer && ' (Default)'}
                        </MenuItem>
                      ))
                    ) : (
                      <MenuItem value={assistantSettings.defaultModel}>
                        {assistantSettings.defaultModel || 'Loading models...'}
                      </MenuItem>
                    )}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={assistantSettings.enableStreaming}
                      onChange={(e) => setAssistantSettings({ ...assistantSettings, enableStreaming: e.target.checked })}
                    />
                  }
                  label="Enable streaming responses"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={assistantSettings.showThinking}
                      onChange={(e) => setAssistantSettings({ ...assistantSettings, showThinking: e.target.checked })}
                    />
                  }
                  label="Show thinking process"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={assistantSettings.autoSave}
                      onChange={(e) => setAssistantSettings({ ...assistantSettings, autoSave: e.target.checked })}
                    />
                  }
                  label="Auto-save chat sessions"
                />
              </Grid>

              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                  Connection & Timeout Settings
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Connection Timeout (seconds)"
                  type="number"
                  value={assistantSettings.connectionTimeout}
                  onChange={(e) => setAssistantSettings({
                    ...assistantSettings,
                    connectionTimeout: parseInt(e.target.value)
                  })}
                  helperText="Time to wait for initial connection"
                  InputProps={{ inputProps: { min: 5, max: 60 } }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Response Timeout (seconds)"
                  type="number"
                  value={assistantSettings.responseTimeout}
                  onChange={(e) => setAssistantSettings({
                    ...assistantSettings,
                    responseTimeout: parseInt(e.target.value)
                  })}
                  helperText="Max time to wait for AI response (30s - 30min)"
                  InputProps={{ inputProps: { min: 30, max: 1800 } }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Max Retries"
                  type="number"
                  value={assistantSettings.maxRetries}
                  onChange={(e) => setAssistantSettings({
                    ...assistantSettings,
                    maxRetries: parseInt(e.target.value)
                  })}
                  helperText="Number of retry attempts on failure"
                  InputProps={{ inputProps: { min: 0, max: 5 } }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={assistantSettings.autoReconnect}
                      onChange={(e) => setAssistantSettings({
                        ...assistantSettings,
                        autoReconnect: e.target.checked
                      })}
                    />
                  }
                  label="Auto-reconnect on disconnect"
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  fullWidth
                  disabled={savingPreferences}
                  onClick={async () => {
                    try {
                      setSavingPreferences(true);

                      // Convert frontend camelCase to backend snake_case
                      // Convert seconds to milliseconds for backend storage
                      await apiClient.updateUserChatPreferences({
                        default_model: assistantSettings.defaultModel,
                        enable_streaming: assistantSettings.enableStreaming,
                        show_thinking: assistantSettings.showThinking,
                        auto_save_conversations: assistantSettings.autoSave,
                        connection_timeout: assistantSettings.connectionTimeout * 1000, // seconds -> ms
                        response_timeout: assistantSettings.responseTimeout * 1000, // seconds -> ms
                        max_retries: assistantSettings.maxRetries,
                        auto_reconnect: assistantSettings.autoReconnect,
                      });

                      enqueueSnackbar('Assistant settings saved successfully', { variant: 'success' });
                    } catch (error) {
                      console.error('Failed to save assistant preferences:', error);
                      enqueueSnackbar('Failed to save assistant settings', { variant: 'error' });
                    } finally {
                      setSavingPreferences(false);
                    }
                  }}
                >
                  {savingPreferences ? 'Saving...' : 'Save Assistant Settings'}
                </Button>
              </Grid>
            </Grid>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Analytics & Insights */}
      <Accordion expanded={expandedPanel === 'analytics'} onChange={handlePanelChange('analytics')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AnalyticsIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Analytics & Insights</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Enable email pattern analysis"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Track sender statistics"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch />}
                label="Generate weekly insights reports"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Retention Period</InputLabel>
                <Select defaultValue={90} label="Retention Period">
                  <MenuItem value={30}>30 days</MenuItem>
                  <MenuItem value={90}>90 days</MenuItem>
                  <MenuItem value={180}>6 months</MenuItem>
                  <MenuItem value={365}>1 year</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Security & Privacy */}
      <Accordion expanded={expandedPanel === 'security'} onChange={handlePanelChange('security')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SecurityIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Security & Privacy</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Email credentials are encrypted at rest. Authentication tokens are stored securely.
              </Alert>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Encrypt email content in database"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Require re-authentication for sensitive operations"
              />
            </Grid>
            <Grid item xs={12}>
              <Button variant="outlined" color="error" fullWidth>
                Clear All Local Data
              </Button>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Management Functions */}
      <Accordion expanded={expandedPanel === 'management'} onChange={handlePanelChange('management')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BuildIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Management Functions</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Alert severity="warning" sx={{ mb: 3 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                <WarningIcon sx={{ fontSize: '1rem', verticalAlign: 'middle', mr: 0.5 }} />
                Destructive Operations
              </Typography>
              <Typography variant="body2">
                These operations are destructive and cannot be undone. Use with caution in production environments.
              </Typography>
            </Alert>

            <Stack spacing={3}>
              {/* Clear Stuck Workflows */}
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                  Clear Stuck Workflows
                </Typography>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 2 }}>
                  Remove stuck or pending Celery tasks from the workflow queue. Useful when tasks are hanging indefinitely.
                </Typography>
                <Button
                  variant="outlined"
                  color="warning"
                  onClick={handleClearStuckWorkflows}
                  disabled={clearingWorkflows}
                  startIcon={clearingWorkflows ? <CircularProgress size={20} /> : <SyncIcon />}
                  fullWidth
                >
                  {clearingWorkflows ? 'Clearing Workflows...' : 'Clear Stuck Workflows'}
                </Button>
              </Box>

              <Divider />

              {/* Purge All Emails */}
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                  Purge All Emails
                </Typography>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 2 }}>
                  Delete all synced emails from local database. Emails will re-sync on next sync operation.
                  <strong> This does not delete emails from your mail server.</strong>
                </Typography>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handlePurgeEmails}
                  disabled={purgingEmails}
                  startIcon={purgingEmails ? <CircularProgress size={20} /> : <DeleteIcon />}
                  fullWidth
                >
                  {purgingEmails ? 'Purging Emails...' : 'Purge All Emails'}
                </Button>
              </Box>

              <Divider />

              {/* Purge All Embeddings */}
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                  Purge All Embeddings
                </Typography>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary, mb: 2 }}>
                  Delete all email embeddings from the database. Embeddings will regenerate on next sync operation.
                  Useful after changing embedding models.
                </Typography>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handlePurgeEmbeddings}
                  disabled={purgingEmbeddings}
                  startIcon={purgingEmbeddings ? <CircularProgress size={20} /> : <DeleteIcon />}
                  fullWidth
                >
                  {purgingEmbeddings ? 'Purging Embeddings...' : 'Purge All Embeddings'}
                </Button>
              </Box>
            </Stack>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Advanced Settings */}
      <Accordion expanded={expandedPanel === 'advanced'} onChange={handlePanelChange('advanced')}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ScheduleIcon color="primary" />
            <Typography sx={{ fontWeight: 600 }}>Advanced Settings</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Database Optimization</InputLabel>
                <Select defaultValue="auto" label="Database Optimization">
                  <MenuItem value="auto">Automatic</MenuItem>
                  <MenuItem value="daily">Daily</MenuItem>
                  <MenuItem value="weekly">Weekly</MenuItem>
                  <MenuItem value="manual">Manual only</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={<Switch />}
                label="Enable debug logging"
              />
            </Grid>
            <Grid item xs={12}>
              <Button variant="outlined" fullWidth>
                Export Configuration
              </Button>
            </Grid>
            <Grid item xs={12}>
              <Button variant="outlined" fullWidth>
                Import Configuration
              </Button>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Add Email Account Wizard (V2) */}
      <AddEmailAccountWizard
        open={showAddAccountWizard}
        onClose={() => setShowAddAccountWizard(false)}
        onAccountAdded={handleAccountAdded}
      />

      {/* Edit Account Settings Dialog */}
      <Dialog
        open={!!editingAccount}
        onClose={handleCloseEditDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Email Account Settings</DialogTitle>
        <DialogContent>
          {editingAccount && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="body2" sx={{ mb: 3, color: theme.palette.text.secondary }}>
                Editing settings for <strong>{editingAccount.email_address}</strong>
              </Typography>

              <Stack spacing={3}>
                <TextField
                  label="Sync Window (Days)"
                  type="number"
                  fullWidth
                  value={editFormData.sync_window_days}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, sync_window_days: parseInt(e.target.value) || 90 })
                  }
                  helperText="How many days back to sync emails (applies to initial sync only)"
                  inputProps={{ min: 1, max: 3650 }}
                />

                <TextField
                  label="Sync Interval (Minutes)"
                  type="number"
                  fullWidth
                  value={editFormData.sync_interval_minutes}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, sync_interval_minutes: parseInt(e.target.value) || 15 })
                  }
                  helperText="How often to check for new emails"
                  inputProps={{ min: 5, max: 1440 }}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={editFormData.auto_sync_enabled}
                      onChange={(e) =>
                        setEditFormData({ ...editFormData, auto_sync_enabled: e.target.checked })
                      }
                    />
                  }
                  label="Auto-sync enabled"
                />

                <Divider sx={{ my: 2 }} />

                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Authentication Settings
                </Typography>

                {editingAccount.account_type === 'imap' && (
                  <>
                    <TextField
                      label="IMAP Server"
                      fullWidth
                      value={editFormData.auth_credentials.server}
                      onChange={(e) => setEditFormData({
                        ...editFormData,
                        auth_credentials: { ...editFormData.auth_credentials, server: e.target.value }
                      })}
                      helperText="Update if server address changed"
                    />
                    <Grid container spacing={2}>
                      <Grid item xs={8}>
                        <TextField
                          label="Username"
                          fullWidth
                          value={editFormData.auth_credentials.username}
                          onChange={(e) => setEditFormData({
                            ...editFormData,
                            auth_credentials: { ...editFormData.auth_credentials, username: e.target.value }
                          })}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <TextField
                          label="Port"
                          type="number"
                          fullWidth
                          value={editFormData.auth_credentials.port}
                          onChange={(e) => setEditFormData({
                            ...editFormData,
                            auth_credentials: { ...editFormData.auth_credentials, port: parseInt(e.target.value) || 993 }
                          })}
                        />
                      </Grid>
                    </Grid>
                    <TextField
                      label="Password"
                      type="password"
                      fullWidth
                      value={editFormData.auth_credentials.password}
                      onChange={(e) => setEditFormData({
                        ...editFormData,
                        auth_credentials: { ...editFormData.auth_credentials, password: e.target.value }
                      })}
                      helperText={editFormData.auth_credentials.password === '••••••••'
                        ? "Password set. Change to update."
                        : "Enter new password to update"}
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={editFormData.auth_credentials.use_ssl}
                          onChange={(e) => setEditFormData({
                            ...editFormData,
                            auth_credentials: { ...editFormData.auth_credentials, use_ssl: e.target.checked }
                          })}
                        />
                      }
                      label="Use SSL/TLS"
                    />
                  </>
                )}

                {editingAccount.account_type === 'gmail' && (
                  <>
                    <TextField
                      label="Client ID"
                      fullWidth
                      value={editFormData.auth_credentials.client_id}
                      onChange={(e) => setEditFormData({
                        ...editFormData,
                        auth_credentials: { ...editFormData.auth_credentials, client_id: e.target.value }
                      })}
                    />
                    <TextField
                      label="Client Secret"
                      type="password"
                      fullWidth
                      value={editFormData.auth_credentials.client_secret}
                      onChange={(e) => setEditFormData({
                        ...editFormData,
                        auth_credentials: { ...editFormData.auth_credentials, client_secret: e.target.value }
                      })}
                    />
                    <TextField
                      label="Access Token"
                      fullWidth
                      value={editFormData.auth_credentials.access_token}
                      onChange={(e) => setEditFormData({
                        ...editFormData,
                        auth_credentials: { ...editFormData.auth_credentials, access_token: e.target.value }
                      })}
                    />
                    <TextField
                      label="Refresh Token"
                      fullWidth
                      value={editFormData.auth_credentials.refresh_token}
                      onChange={(e) => setEditFormData({
                        ...editFormData,
                        auth_credentials: { ...editFormData.auth_credentials, refresh_token: e.target.value }
                      })}
                    />
                  </>
                )}

                <Alert severity="info">
                  Changing sync window will trigger a full resync on the next sync cycle.
                </Alert>
              </Stack>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditDialog}>Cancel</Button>
          <Button onClick={handleSaveAccountSettings} variant="contained">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SettingsTab;
