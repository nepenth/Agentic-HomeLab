import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  Chip,
  Divider,
  IconButton,
  Tooltip,
  alpha,
  useTheme,
  Grid
} from '@mui/material';
import {
  Keyboard as KeyboardIcon,
  Close as CloseIcon,
  Help as HelpIcon,
  ArrowUpward as UpIcon,
  ArrowDownward as DownIcon,
  ArrowBack as LeftIcon,
  ArrowForward as RightIcon,
  KeyboardReturn as EnterIcon,
  Backspace as BackspaceIcon,
  SpaceBar as SpaceIcon
} from '@mui/icons-material';

interface ShortcutGroup {
  title: string;
  shortcuts: Array<{
    keys: string[];
    description: string;
    category?: string;
  }>;
}

interface KeyboardShortcutHelpProps {
  open: boolean;
  onClose: () => void;
}

export const KeyboardShortcutHelp: React.FC<KeyboardShortcutHelpProps> = ({
  open,
  onClose
}) => {
  const theme = useTheme();

  const shortcutGroups: ShortcutGroup[] = [
    {
      title: 'Navigation',
      shortcuts: [
        { keys: ['↑', '↓'], description: 'Navigate between emails' },
        { keys: ['Page Up', 'Page Down'], description: 'Navigate by page' },
        { keys: ['Home', 'End'], description: 'Go to first/last email' },
        { keys: ['Ctrl', '+', '↑'], description: 'Previous email (anywhere)' },
        { keys: ['Ctrl', '+', '↓'], description: 'Next email (anywhere)' }
      ]
    },
    {
      title: 'Email Actions',
      shortcuts: [
        { keys: ['Enter'], description: 'Open selected email' },
        { keys: ['Ctrl', '+', 'Enter'], description: 'Mark as read/unread' },
        { keys: ['Delete'], description: 'Delete selected email' },
        { keys: ['Ctrl', '+', 'S'], description: 'Star/unstar email' },
        { keys: ['Ctrl', '+', 'R'], description: 'Reply to email' },
        { keys: ['Ctrl', '+', 'Shift', '+', 'R'], description: 'Reply all' },
        { keys: ['Ctrl', '+', 'F'], description: 'Forward email' }
      ]
    },
    {
      title: 'Layout & Views',
      shortcuts: [
        { keys: ['Ctrl', '+', 'B'], description: 'Toggle folder sidebar' },
        { keys: ['Ctrl', '+', '1'], description: 'Three column layout' },
        { keys: ['Ctrl', '+', '2'], description: 'Horizontal split layout' },
        { keys: ['Ctrl', '+', '3'], description: 'Vertical split layout' },
        { keys: ['Ctrl', '+', 'L'], description: 'Toggle email viewer position' }
      ]
    },
    {
      title: 'Search & Filter',
      shortcuts: [
        { keys: ['Ctrl', '+', 'K'], description: 'Focus search bar' },
        { keys: ['Ctrl', '+', 'F'], description: 'Open advanced filters' },
        { keys: ['Escape'], description: 'Clear search/close dialogs' }
      ]
    },
    {
      title: 'Bulk Operations',
      shortcuts: [
        { keys: ['Ctrl', '+', 'A'], description: 'Select all emails' },
        { keys: ['Ctrl', '+', 'Shift', '+', 'A'], description: 'Clear selection' },
        { keys: ['Ctrl', '+', 'Shift', '+', 'Delete'], description: 'Bulk delete selected' },
        { keys: ['Ctrl', '+', 'Shift', '+', 'M'], description: 'Bulk mark as read' }
      ]
    },
    {
      title: 'General',
      shortcuts: [
        { keys: ['Ctrl', '+', 'R'], description: 'Refresh emails' },
        { keys: ['Ctrl', '+', '/'], description: 'Show keyboard shortcuts' },
        { keys: ['F1'], description: 'Show help' },
        { keys: ['Ctrl', '+', 'Q'], description: 'Quick compose' }
      ]
    }
  ];

  const KeyChip: React.FC<{ children: React.ReactNode; variant?: 'filled' | 'outlined' }> = ({
    children,
    variant = 'outlined'
  }) => (
    <Chip
      label={children}
      size="small"
      variant={variant}
      sx={{
        height: 24,
        fontSize: '0.75rem',
        fontWeight: 600,
        fontFamily: 'monospace',
        backgroundColor: variant === 'filled' ? alpha(theme.palette.primary.main, 0.1) : 'transparent',
        borderColor: alpha(theme.palette.primary.main, 0.3),
        color: theme.palette.primary.main,
        '& .MuiChip-label': {
          px: 0.5
        }
      }}
    />
  );

  const ShortcutRow: React.FC<{
    keys: string[];
    description: string;
  }> = ({ keys, description }) => (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      py: 1,
      px: 2,
      '&:hover': {
        backgroundColor: alpha(theme.palette.action.hover, 0.5)
      }
    }}>
      <Typography variant="body2" sx={{ flex: 1, mr: 2 }}>
        {description}
      </Typography>
      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        {keys.map((key, index) => (
          <React.Fragment key={index}>
            <KeyChip>{key}</KeyChip>
            {index < keys.length - 1 && (
              <Typography variant="caption" sx={{ mx: 0.5, color: 'text.secondary' }}>
                +
              </Typography>
            )}
          </React.Fragment>
        ))}
      </Box>
    </Box>
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          height: '80vh',
          maxHeight: '80vh'
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        pb: 1
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <KeyboardIcon color="primary" />
          <Typography variant="h6">
            Keyboard Shortcuts
          </Typography>
        </Box>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0, overflow: 'auto' }}>
        {/* Quick Reference */}
        <Box sx={{ p: 3, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Quick Reference
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <KeyChip>↑↓</KeyChip>
                <Typography variant="body2">Navigate emails</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <KeyChip>Enter</KeyChip>
                <Typography variant="body2">Open email</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <KeyChip>Ctrl</KeyChip>
                <Typography variant="caption" sx={{ mx: 0.5 }}>+</Typography>
                <KeyChip>R</KeyChip>
                <Typography variant="body2">Reply</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <KeyChip>Ctrl</KeyChip>
                <Typography variant="caption" sx={{ mx: 0.5 }}>+</Typography>
                <KeyChip>K</KeyChip>
                <Typography variant="body2">Search</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <KeyChip>Ctrl</KeyChip>
                <Typography variant="caption" sx={{ mx: 0.5 }}>+</Typography>
                <KeyChip>B</KeyChip>
                <Typography variant="body2">Toggle sidebar</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <KeyChip>Ctrl</KeyChip>
                <Typography variant="caption" sx={{ mx: 0.5 }}>+</Typography>
                <KeyChip variant="filled">/</KeyChip>
                <Typography variant="body2">Show this help</Typography>
              </Box>
            </Grid>
          </Grid>
        </Box>

        {/* Detailed Shortcuts */}
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
            All Keyboard Shortcuts
          </Typography>

          {shortcutGroups.map((group, groupIndex) => (
            <Box key={group.title} sx={{ mb: 3 }}>
              <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 600, color: 'primary.main' }}>
                {group.title}
              </Typography>

              <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
                {group.shortcuts.map((shortcut, index) => (
                  <React.Fragment key={index}>
                    <ShortcutRow
                      keys={shortcut.keys}
                      description={shortcut.description}
                    />
                    {index < group.shortcuts.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </Paper>
            </Box>
          ))}
        </Box>

        {/* Tips */}
        <Box sx={{ p: 3, backgroundColor: alpha(theme.palette.info.main, 0.05), mx: 3, mb: 3, borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            💡 Pro Tips:
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
              Shortcuts only work when not typing in input fields
            </Typography>
            <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
              Use <KeyChip>Ctrl</KeyChip> + <KeyChip>A</KeyChip> to select all emails in the current view
            </Typography>
            <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
              Press <KeyChip>Escape</KeyChip> to clear search or close dialogs
            </Typography>
            <Typography component="li" variant="body2">
              Most shortcuts work from anywhere in the email interface
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
        <Button onClick={onClose}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

// Help Button Component
interface KeyboardShortcutHelpButtonProps {
  onClick: () => void;
}

export const KeyboardShortcutHelpButton: React.FC<KeyboardShortcutHelpButtonProps> = ({ onClick }) => {
  return (
    <Tooltip title="Keyboard shortcuts (Ctrl+/)">
      <IconButton onClick={onClick} size="small">
        <HelpIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  );
};

export default KeyboardShortcutHelp;