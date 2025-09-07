import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  Typography,
  IconButton,
  InputAdornment,
  LinearProgress,
} from '@mui/material';
import {
  Close,
  Visibility,
  VisibilityOff,
  Security,
} from '@mui/icons-material';
import apiClient from '../services/api';

interface ChangePasswordDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface PasswordStrength {
  score: number;
  text: string;
  color: 'error' | 'warning' | 'info' | 'success';
}

const ChangePasswordDialog: React.FC<ChangePasswordDialogProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const getPasswordStrength = (password: string): PasswordStrength => {
    if (password.length === 0) {
      return { score: 0, text: '', color: 'error' };
    }
    
    let score = 0;
    const checks = {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      numbers: /\d/.test(password),
      symbols: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    };

    score = Object.values(checks).filter(Boolean).length;

    if (score < 2) return { score: 20, text: 'Very Weak', color: 'error' };
    if (score < 3) return { score: 40, text: 'Weak', color: 'warning' };
    if (score < 4) return { score: 60, text: 'Fair', color: 'info' };
    if (score < 5) return { score: 80, text: 'Good', color: 'success' };
    return { score: 100, text: 'Strong', color: 'success' };
  };

  const passwordStrength = getPasswordStrength(newPassword);

  const validate = (): boolean => {
    setError('');

    if (!currentPassword.trim()) {
      setError('Current password is required');
      return false;
    }

    if (!newPassword.trim()) {
      setError('New password is required');
      return false;
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long');
      return false;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return false;
    }

    if (currentPassword === newPassword) {
      setError('New password must be different from current password');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;

    setLoading(true);
    setError('');

    try {
      await apiClient.changePassword(currentPassword, newPassword);
      setSuccess('Password changed successfully!');
      
      // Clear form
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      
      // Close dialog after delay
      setTimeout(() => {
        setSuccess('');
        onSuccess?.();
        onClose();
      }, 2000);
    } catch (err: any) {
      setError(err.detail || 'Failed to change password. Please check your current password.');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (loading) return;
    
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setSuccess('');
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3 }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Security color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Change Password
          </Typography>
        </Box>
        <IconButton
          onClick={handleClose}
          disabled={loading}
          sx={{ color: 'text.secondary' }}
        >
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Enter your current password and choose a new secure password.
        </Typography>

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }}>
            {success}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Current Password"
            type={showCurrentPassword ? 'text' : 'password'}
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            disabled={loading}
            required
            sx={{ mb: 3 }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    edge="end"
                    disabled={loading}
                  >
                    {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            label="New Password"
            type={showNewPassword ? 'text' : 'password'}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            disabled={loading}
            required
            sx={{ mb: 2 }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    edge="end"
                    disabled={loading}
                  >
                    {showNewPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {newPassword && (
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Password Strength
                </Typography>
                <Typography 
                  variant="caption" 
                  color={`${passwordStrength.color}.main`}
                  sx={{ fontWeight: 500 }}
                >
                  {passwordStrength.text}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={passwordStrength.score}
                color={passwordStrength.color}
                sx={{ height: 6, borderRadius: 3 }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Use at least 8 characters with uppercase, lowercase, numbers, and symbols
              </Typography>
            </Box>
          )}

          <TextField
            fullWidth
            label="Confirm New Password"
            type={showConfirmPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={loading}
            required
            sx={{ mb: 3 }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    edge="end"
                    disabled={loading}
                  >
                    {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button
          onClick={handleClose}
          disabled={loading}
          color="inherit"
        >
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || !currentPassword || !newPassword || !confirmPassword}
          sx={{ px: 4 }}
        >
          {loading ? 'Changing...' : 'Change Password'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ChangePasswordDialog;