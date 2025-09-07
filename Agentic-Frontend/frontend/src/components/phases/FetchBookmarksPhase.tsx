import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Button,
  Alert,
  Grid,
  Paper,
} from '@mui/material';
import {
  CloudDownload,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
} from '@mui/icons-material';

interface FetchBookmarksPhaseProps {
  phase: {
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
    progress_percentage: number;
    start_time?: string;
    end_time?: string;
    duration_ms?: number;
    model_used?: string;
    error_message?: string;
    status_message?: string;
  };
  onRetry?: () => void;
  onSkip?: () => void;
  bookmarksFound?: number;
  totalBookmarks?: number;
  currentUrl?: string;
}

const FetchBookmarksPhase: React.FC<FetchBookmarksPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  bookmarksFound = 0,
  totalBookmarks = 0,
  currentUrl = '',
}) => {
  const getStatusIcon = () => {
    switch (phase.status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'running':
        return <HourglassEmpty color="primary" />;
      case 'failed':
        return <Error color="error" />;
      default:
        return <CloudDownload color="action" />;
    }
  };

  const getStatusColor = () => {
    switch (phase.status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ mr: 2 }}>
            📥
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Fetch Bookmarks
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Retrieve Twitter/X bookmarks from configured folder
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getStatusIcon()}
            <Chip
              label={phase.status}
              color={getStatusColor() as any}
              size="small"
            />
          </Box>
        </Box>

        {/* Progress Bar */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Progress
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {phase.progress_percentage.toFixed(1)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={phase.progress_percentage}
            sx={{ height: 8, borderRadius: 4 }}
            color={phase.status === 'completed' ? 'success' :
                   phase.status === 'running' ? 'primary' :
                   phase.status === 'failed' ? 'error' : 'inherit'}
          />
        </Box>

        {/* Phase-specific content */}
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
              <Typography variant="subtitle2" gutterBottom>
                Connection Status
              </Typography>
              {phase.status === 'running' && (
                <Alert severity="info" sx={{ mb: 1 }}>
                  Connecting to X API...
                </Alert>
              )}
              {phase.status === 'completed' && (
                <Alert severity="success" sx={{ mb: 1 }}>
                  Successfully connected to X API
                </Alert>
              )}
              {phase.status === 'failed' && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  Failed to connect to X API
                </Alert>
              )}
              {currentUrl && (
                <Typography variant="caption" color="text.secondary">
                  URL: {currentUrl}
                </Typography>
              )}
            </Paper>
          </Grid>

          <Grid item xs={12} sm={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
              <Typography variant="subtitle2" gutterBottom>
                Bookmarks Found
              </Typography>
              <Typography variant="h4" color="primary">
                {bookmarksFound}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {totalBookmarks} total bookmarks
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Status message */}
        {phase.status_message && (
          <Alert
            severity={phase.status === 'failed' ? 'error' : 'info'}
            sx={{ mt: 2 }}
          >
            {phase.status_message}
          </Alert>
        )}

        {/* Error message */}
        {phase.error_message && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {phase.error_message}
          </Alert>
        )}

        {/* Action buttons */}
        {(phase.status === 'failed' || phase.status === 'pending') && (
          <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
            {phase.status === 'failed' && onRetry && (
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={onRetry}
                size="small"
              >
                Retry
              </Button>
            )}
            {phase.status === 'pending' && onSkip && (
              <Button
                variant="outlined"
                color="warning"
                onClick={onSkip}
                size="small"
              >
                Skip Phase
              </Button>
            )}
          </Box>
        )}

        {/* Timing information */}
        {(phase.start_time || phase.end_time) && (
          <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
            <Typography variant="caption" color="text.secondary">
              {phase.start_time && `Started: ${new Date(phase.start_time).toLocaleTimeString()}`}
              {phase.start_time && phase.end_time && ' • '}
              {phase.end_time && `Completed: ${new Date(phase.end_time).toLocaleTimeString()}`}
              {phase.duration_ms && ` • Duration: ${Math.round(phase.duration_ms / 1000)}s`}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default FetchBookmarksPhase;