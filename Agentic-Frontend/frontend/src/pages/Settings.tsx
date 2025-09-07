import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  TextField,
  Switch,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Avatar,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Person,
  Security,
  Notifications,
  Palette,
  Save,
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState } from '../store';
import { setTheme } from '../store/slices/uiSlice';
import ChangePasswordDialog from '../components/ChangePasswordDialog';

const Settings: React.FC = () => {
  const { user } = useAuth();
  const dispatch = useDispatch();
  const { theme } = useSelector((state: RootState) => state.ui);
  
  const [settings, setSettings] = useState({
    // Profile settings
    username: user?.username || '',
    email: user?.email || '',
    
    // Notification settings
    emailNotifications: true,
    pushNotifications: true,
    weeklyReports: true,
    taskCompletionAlerts: true,
    
    // UI settings
    darkMode: theme === 'dark',
    compactMode: false,
    showTooltips: true,
    
    // Security settings
    twoFactorEnabled: false,
    sessionTimeout: 30,
  });

  const [saveMessage, setSaveMessage] = useState('');
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    
    // Handle theme change immediately
    if (key === 'darkMode') {
      dispatch(setTheme(value ? 'dark' : 'light'));
    }
  };

  const handleSave = () => {
    // In a real app, this would make an API call to save settings
    setSaveMessage('Settings saved successfully!');
    setTimeout(() => setSaveMessage(''), 3000);
  };

  const handlePasswordChangeSuccess = () => {
    setSaveMessage('Password changed successfully!');
    setTimeout(() => setSaveMessage(''), 3000);
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
        <SettingsIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Settings
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your account preferences and application settings
          </Typography>
        </Box>
      </Box>

      {saveMessage && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSaveMessage('')}>
          {saveMessage}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Profile Settings */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Person sx={{ mr: 2, color: 'primary.main' }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Profile Settings
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Avatar 
                  sx={{ 
                    width: 60, 
                    height: 60, 
                    mr: 2, 
                    bgcolor: 'primary.main',
                    fontSize: '1.5rem'
                  }}
                >
                  {user?.username?.[0]?.toUpperCase() || 'U'}
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {user?.username || 'User'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {user?.email || 'user@example.com'}
                  </Typography>
                </Box>
              </Box>

              <TextField
                fullWidth
                label="Username"
                value={settings.username}
                onChange={(e) => handleSettingChange('username', e.target.value)}
                sx={{ mb: 2 }}
              />

              <TextField
                fullWidth
                label="Email"
                type="email"
                value={settings.email}
                onChange={(e) => handleSettingChange('email', e.target.value)}
                sx={{ mb: 2 }}
              />

              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSave}
                sx={{ mt: 2 }}
              >
                Update Profile
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Security Settings */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Security sx={{ mr: 2, color: 'primary.main' }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Security
                </Typography>
              </Box>

              <List>
                <ListItem>
                  <ListItemText
                    primary="Two-Factor Authentication"
                    secondary="Add an extra layer of security to your account"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.twoFactorEnabled}
                      onChange={(e) => handleSettingChange('twoFactorEnabled', e.target.checked)}
                      disabled
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem>
                  <ListItemText
                    primary="Session Timeout"
                    secondary="Automatically log out after inactivity"
                  />
                  <ListItemSecondaryAction>
                    <TextField
                      size="small"
                      type="number"
                      value={settings.sessionTimeout}
                      onChange={(e) => handleSettingChange('sessionTimeout', parseInt(e.target.value))}
                      InputProps={{ endAdornment: 'min' }}
                      sx={{ width: 80 }}
                      disabled
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>

              <Button
                variant="outlined"
                sx={{ mt: 2 }}
                onClick={() => setChangePasswordOpen(true)}
              >
                Change Password
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Notifications sx={{ mr: 2, color: 'primary.main' }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Notifications
                </Typography>
              </Box>

              <List>
                <ListItem>
                  <ListItemText
                    primary="Email Notifications"
                    secondary="Receive notifications via email"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.emailNotifications}
                      onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem>
                  <ListItemText
                    primary="Push Notifications"
                    secondary="Browser push notifications"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.pushNotifications}
                      onChange={(e) => handleSettingChange('pushNotifications', e.target.checked)}
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem>
                  <ListItemText
                    primary="Weekly Reports"
                    secondary="Weekly summary of your activity"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.weeklyReports}
                      onChange={(e) => handleSettingChange('weeklyReports', e.target.checked)}
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem>
                  <ListItemText
                    primary="Task Completion Alerts"
                    secondary="Get notified when tasks complete"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.taskCompletionAlerts}
                      onChange={(e) => handleSettingChange('taskCompletionAlerts', e.target.checked)}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* UI Settings */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Palette sx={{ mr: 2, color: 'primary.main' }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Appearance
                </Typography>
              </Box>

              <List>
                <ListItem>
                  <ListItemText
                    primary="Dark Mode"
                    secondary="Use dark theme throughout the application"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.darkMode}
                      onChange={(e) => handleSettingChange('darkMode', e.target.checked)}
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem>
                  <ListItemText
                    primary="Compact Mode"
                    secondary="Use smaller spacing and components"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.compactMode}
                      onChange={(e) => handleSettingChange('compactMode', e.target.checked)}
                      disabled
                    />
                  </ListItemSecondaryAction>
                </ListItem>

                <ListItem>
                  <ListItemText
                    primary="Show Tooltips"
                    secondary="Display helpful tooltips throughout the app"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      checked={settings.showTooltips}
                      onChange={(e) => handleSettingChange('showTooltips', e.target.checked)}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* System Information */}
        <Grid item xs={12}>
          <Paper elevation={0} sx={{ p: 3, backgroundColor: 'grey.50' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              System Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">
                  Version
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  v0.1.0
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">
                  Last Updated
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {new Date().toLocaleDateString()}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">
                  Environment
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  Development
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">
                  Server Status
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500, color: 'success.main' }}>
                  Connected
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Save Changes */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'center', pt: 2 }}>
            <Button
              variant="contained"
              size="large"
              startIcon={<Save />}
              onClick={handleSave}
              sx={{ px: 4 }}
            >
              Save All Changes
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Change Password Dialog */}
      <ChangePasswordDialog
        open={changePasswordOpen}
        onClose={() => setChangePasswordOpen(false)}
        onSuccess={handlePasswordChangeSuccess}
      />
    </Box>
  );
};

export default Settings;