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
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  AttachFile,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  Download,
  Image,
  Videocam,
} from '@mui/icons-material';

interface MediaFile {
  filename: string;
  size_bytes: number;
  type: 'image' | 'video' | 'other';
  status: 'downloading' | 'completed' | 'failed';
  url: string;
}

interface CacheMediaPhaseProps {
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
  mediaFiles?: MediaFile[];
  totalSizeBytes?: number;
  downloadedSizeBytes?: number;
  currentFile?: string;
}

const CacheMediaPhase: React.FC<CacheMediaPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  mediaFiles = [],
  totalSizeBytes = 0,
  downloadedSizeBytes = 0,
  currentFile = '',
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
        return <Download color="action" />;
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

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image color="primary" />;
      case 'video':
        return <Videocam color="secondary" />;
      default:
        return <AttachFile color="action" />;
    }
  };

  const getFileStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'downloading':
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
            📎
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Cache Media
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Download and store media assets (images, videos)
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
              Download Progress
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

        {/* Download Statistics */}
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Downloaded
              </Typography>
              <Typography variant="h5" color="primary">
                {formatFileSize(downloadedSizeBytes)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {formatFileSize(totalSizeBytes)}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Files Completed
              </Typography>
              <Typography variant="h5" color="success.main">
                {mediaFiles.filter(f => f.status === 'completed').length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {mediaFiles.length} total
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Current File
              </Typography>
              <Typography variant="body2" color="primary" sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {currentFile || 'None'}
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Current file being downloaded */}
        {currentFile && phase.status === 'running' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Downloading:</strong> {currentFile}
            </Typography>
          </Alert>
        )}

        {/* Media files list */}
        {mediaFiles.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Media Files ({mediaFiles.length})
            </Typography>
            <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
              {mediaFiles.slice(0, 10).map((file, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {getFileIcon(file.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            flex: 1
                          }}>
                            {file.filename}
                          </Typography>
                          <Chip
                            label={file.status}
                            size="small"
                            color={getFileStatusColor(file.status) as any}
                          />
                        </Box>
                      }
                      secondary={`${formatFileSize(file.size_bytes)} • ${file.type}`}
                    />
                  </ListItem>
                  {index < Math.min(mediaFiles.length - 1, 9) && <Divider />}
                </React.Fragment>
              ))}
              {mediaFiles.length > 10 && (
                <ListItem>
                  <ListItemText
                    secondary={`... and ${mediaFiles.length - 10} more files`}
                  />
                </ListItem>
              )}
            </List>
          </Box>
        )}

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

export default CacheMediaPhase;