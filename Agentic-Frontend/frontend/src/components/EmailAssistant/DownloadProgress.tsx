import React, { useState, useEffect } from 'react';
import {
  Box,
  LinearProgress,
  Typography,
  IconButton,
  Paper,
  Chip,
  Button,
  alpha,
  useTheme,
  Snackbar,
  Alert
} from '@mui/material';
import {
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Download as DownloadIcon,
  Pause as PauseIcon,
  PlayArrow as ResumeIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';

interface DownloadItem {
  id: string;
  filename: string;
  size_bytes: number;
  progress: number; // 0-100
  status: 'pending' | 'downloading' | 'paused' | 'completed' | 'failed' | 'cancelled';
  speed?: number; // bytes per second
  eta?: number; // estimated time remaining in seconds
  error?: string;
  url?: string;
}

interface DownloadProgressProps {
  downloads: DownloadItem[];
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onCancel?: (id: string) => void;
  onRetry?: (id: string) => void;
  onClear?: (id: string) => void;
  onClearAll?: () => void;
}

export const DownloadProgress: React.FC<DownloadProgressProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
  onRetry,
  onClear,
  onClearAll
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [completedNotification, setCompletedNotification] = useState<DownloadItem | null>(null);

  // Show notification when downloads complete
  useEffect(() => {
    const justCompleted = downloads.filter(d =>
      d.status === 'completed' && d.progress === 100
    );

    if (justCompleted.length > 0) {
      // Show notification for the most recent completion
      const latest = justCompleted[justCompleted.length - 1];
      setCompletedNotification(latest);

      // Auto-hide notification after 3 seconds
      setTimeout(() => setCompletedNotification(null), 3000);
    }
  }, [downloads]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatSpeed = (bytesPerSecond: number) => {
    if (bytesPerSecond < 1024) return `${bytesPerSecond} B/s`;
    if (bytesPerSecond < 1024 * 1024) return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
    return `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`;
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'downloading': return theme.palette.primary.main;
      case 'completed': return theme.palette.success.main;
      case 'failed': return theme.palette.error.main;
      case 'paused': return theme.palette.warning.main;
      case 'cancelled': return theme.palette.text.disabled;
      default: return theme.palette.text.secondary;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <SuccessIcon fontSize="small" color="success" />;
      case 'failed': return <ErrorIcon fontSize="small" color="error" />;
      case 'downloading': return <DownloadIcon fontSize="small" color="primary" />;
      case 'paused': return <PauseIcon fontSize="small" color="warning" />;
      case 'cancelled': return <CancelIcon fontSize="small" color="disabled" />;
      default: return <DownloadIcon fontSize="small" />;
    }
  };

  const activeDownloads = downloads.filter(d => d.status === 'downloading' || d.status === 'pending');
  const completedDownloads = downloads.filter(d => d.status === 'completed');
  const failedDownloads = downloads.filter(d => d.status === 'failed');

  if (downloads.length === 0) {
    return null;
  }

  return (
    <>
      {/* Compact Progress Bar */}
      <Paper
        sx={{
          position: 'fixed',
          bottom: 80, // Above quick actions toolbar
          right: 24,
          zIndex: 1200,
          minWidth: 300,
          maxWidth: 400,
          cursor: 'pointer',
          border: `1px solid ${theme.palette.divider}`,
          backgroundColor: theme.palette.background.paper,
          boxShadow: theme.shadows[4],
          '&:hover': {
            backgroundColor: alpha(theme.palette.action.hover, 0.1)
          }
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ p: 2 }}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DownloadIcon color="primary" />
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Downloads ({downloads.length})
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              {expanded ? '▼' : '▶'}
            </Typography>
          </Box>

          {/* Summary */}
          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
            {activeDownloads.length > 0 && (
              <Chip
                label={`${activeDownloads.length} active`}
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
            {completedDownloads.length > 0 && (
              <Chip
                label={`${completedDownloads.length} done`}
                size="small"
                color="success"
                variant="outlined"
              />
            )}
            {failedDownloads.length > 0 && (
              <Chip
                label={`${failedDownloads.length} failed`}
                size="small"
                color="error"
                variant="outlined"
              />
            )}
          </Box>

          {/* Overall Progress */}
          {activeDownloads.length > 0 && (
            <LinearProgress
              sx={{
                height: 6,
                borderRadius: 3,
                backgroundColor: alpha(theme.palette.primary.main, 0.2),
                '& .MuiLinearProgress-bar': {
                  borderRadius: 3
                }
              }}
            />
          )}
        </Box>

        {/* Expanded Details */}
        {expanded && (
          <Box sx={{ borderTop: `1px solid ${theme.palette.divider}`, maxHeight: 300, overflow: 'auto' }}>
            {downloads.map((download) => (
              <Box
                key={download.id}
                sx={{
                  p: 1.5,
                  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
                  '&:last-child': { borderBottom: 'none' }
                }}
              >
                {/* Download Item */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  {getStatusIcon(download.status)}
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 500,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {download.filename}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatFileSize(download.size_bytes)}
                      {download.speed && download.status === 'downloading' && (
                        <span> • {formatSpeed(download.speed)}</span>
                      )}
                      {download.eta && download.status === 'downloading' && (
                        <span> • {formatTime(download.eta)} left</span>
                      )}
                    </Typography>
                  </Box>

                  {/* Action Buttons */}
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {download.status === 'downloading' && onPause && (
                      <IconButton size="small" onClick={(e) => {
                        e.stopPropagation();
                        onPause(download.id);
                      }}>
                        <PauseIcon fontSize="small" />
                      </IconButton>
                    )}
                    {download.status === 'paused' && onResume && (
                      <IconButton size="small" onClick={(e) => {
                        e.stopPropagation();
                        onResume(download.id);
                      }}>
                        <ResumeIcon fontSize="small" />
                      </IconButton>
                    )}
                    {(download.status === 'downloading' || download.status === 'paused') && onCancel && (
                      <IconButton size="small" onClick={(e) => {
                        e.stopPropagation();
                        onCancel(download.id);
                      }}>
                        <CancelIcon fontSize="small" />
                      </IconButton>
                    )}
                    {download.status === 'failed' && onRetry && (
                      <IconButton size="small" onClick={(e) => {
                        e.stopPropagation();
                        onRetry(download.id);
                      }}>
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    )}
                    {(download.status === 'completed' || download.status === 'failed' || download.status === 'cancelled') && onClear && (
                      <IconButton size="small" onClick={(e) => {
                        e.stopPropagation();
                        onClear(download.id);
                      }}>
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    )}
                  </Box>
                </Box>

                {/* Progress Bar */}
                {download.status === 'downloading' && (
                  <LinearProgress
                    variant="determinate"
                    value={download.progress}
                    sx={{
                      height: 4,
                      borderRadius: 2,
                      backgroundColor: alpha(getStatusColor(download.status), 0.2)
                    }}
                  />
                )}

                {/* Error Message */}
                {download.status === 'failed' && download.error && (
                  <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                    {download.error}
                  </Typography>
                )}
              </Box>
            ))}

            {/* Clear All Button */}
            {downloads.length > 0 && onClearAll && (
              <Box sx={{ p: 1, borderTop: `1px solid ${theme.palette.divider}` }}>
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onClearAll();
                  }}
                  sx={{ width: '100%' }}
                >
                  Clear All Completed
                </Button>
              </Box>
            )}
          </Box>
        )}
      </Paper>

      {/* Completion Notification */}
      <Snackbar
        open={!!completedNotification}
        autoHideDuration={3000}
        onClose={() => setCompletedNotification(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setCompletedNotification(null)}
          severity="success"
          sx={{ width: '100%' }}
        >
          Download completed: {completedNotification?.filename}
        </Alert>
      </Snackbar>
    </>
  );
};

export default DownloadProgress;