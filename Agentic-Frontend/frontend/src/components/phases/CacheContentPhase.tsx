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
  Save,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  Storage,
  Description,
  AccessTime,
} from '@mui/icons-material';

interface ContentItem {
  id: string;
  title: string;
  content_type: string;
  size_bytes: number;
  processing_status: 'cached' | 'processing' | 'failed';
  cached_at?: string;
}

interface CacheContentPhaseProps {
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
  cachedItems?: ContentItem[];
  currentItem?: string;
  totalItems?: number;
  processedItems?: number;
  totalSizeBytes?: number;
  cachedSizeBytes?: number;
}

const CacheContentPhase: React.FC<CacheContentPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  cachedItems = [],
  currentItem = '',
  totalItems = 0,
  processedItems = 0,
  totalSizeBytes = 0,
  cachedSizeBytes = 0,
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
        return <Save color="action" />;
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

  const getContentTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'text':
      case 'article':
        return <Description color="primary" />;
      case 'tweet':
      case 'social':
        return <Description color="secondary" />;
      default:
        return <Storage color="action" />;
    }
  };

  const getItemStatusColor = (status: string) => {
    switch (status) {
      case 'cached':
        return 'success';
      case 'processing':
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
            💾
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Cache Content
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Store text content in database for processing
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
              Caching Progress
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

        {/* Processing Statistics */}
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Items Cached
              </Typography>
              <Typography variant="h5" color="primary">
                {processedItems}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {totalItems} total
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Data Stored
              </Typography>
              <Typography variant="h5" color="secondary">
                {formatFileSize(cachedSizeBytes)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {formatFileSize(totalSizeBytes)}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Cache Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                <Storage color={phase.status === 'completed' ? 'success' : 'primary'} />
                <Typography variant="body2" color={phase.status === 'completed' ? 'success.main' : 'primary'}>
                  {phase.status === 'completed' ? 'Complete' : 'Active'}
                </Typography>
              </Box>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Current Item
              </Typography>
              <Typography variant="body2" color="primary" sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {currentItem || 'None'}
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Current processing status */}
        {currentItem && phase.status === 'running' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Caching content for:</strong> {currentItem}
            </Typography>
          </Alert>
        )}

        {/* Cached Items List */}
        {cachedItems.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Recently Cached Items ({cachedItems.length})
            </Typography>
            <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
              {cachedItems.slice(0, 10).map((item, index) => (
                <React.Fragment key={item.id}>
                  <ListItem>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {getContentTypeIcon(item.content_type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" sx={{ flex: 1 }}>
                            {item.title}
                          </Typography>
                          <Chip
                            label={item.processing_status}
                            size="small"
                            color={getItemStatusColor(item.processing_status) as any}
                          />
                        </Box>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="caption" sx={{ textTransform: 'capitalize' }}>
                            {item.content_type}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            • {formatFileSize(item.size_bytes)}
                          </Typography>
                          {item.cached_at && (
                            <Typography variant="caption" color="text.secondary">
                              • {new Date(item.cached_at).toLocaleTimeString()}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < Math.min(cachedItems.length - 1, 9) && <Divider />}
                </React.Fragment>
              ))}
              {cachedItems.length > 10 && (
                <ListItem>
                  <ListItemText
                    secondary={`... and ${cachedItems.length - 10} more cached items`}
                  />
                </ListItem>
              )}
            </List>
          </Box>
        )}

        {/* Database Storage Info */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Database Storage
          </Typography>
          <Paper sx={{ p: 2, backgroundColor: '#f0f8ff' }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Storage color="primary" />
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    Structured Storage
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Content is stored in optimized database tables with full-text indexing
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <AccessTime color="secondary" />
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    Fast Retrieval
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Cached content enables rapid access for downstream processing phases
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Box>

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

export default CacheContentPhase;