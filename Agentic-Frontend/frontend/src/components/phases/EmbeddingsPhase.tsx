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
  Search,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  Analytics,
  Storage,
  Timeline,
} from '@mui/icons-material';

interface EmbeddingStats {
  total_vectors: number;
  dimensions: number;
  model_used: string;
  index_type: string;
  search_enabled: boolean;
  average_processing_time_ms: number;
}

interface EmbeddingsPhaseProps {
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
  embeddingStats?: EmbeddingStats;
  currentItem?: string;
  totalItems?: number;
  processedItems?: number;
  vectorsGenerated?: number;
  searchIndexReady?: boolean;
}

const EmbeddingsPhase: React.FC<EmbeddingsPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  embeddingStats,
  currentItem = '',
  totalItems = 0,
  processedItems = 0,
  vectorsGenerated = 0,
  searchIndexReady = false,
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
        return <Search color="action" />;
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
            🔍
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Embeddings
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Create semantic search vectors for similarity search
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
              Vector Generation Progress
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
                Items Processed
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
                Vectors Generated
              </Typography>
              <Typography variant="h5" color="secondary">
                {vectorsGenerated}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                semantic vectors
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Search Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                <Search color={searchIndexReady ? 'success' : 'disabled'} />
                <Typography variant="body2" color={searchIndexReady ? 'success.main' : 'text.secondary'}>
                  {searchIndexReady ? 'Ready' : 'Building'}
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
              <strong>Generating embeddings for:</strong> {currentItem}
            </Typography>
          </Alert>
        )}

        {/* Embedding Statistics */}
        {embeddingStats && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Embedding Configuration
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Paper sx={{ p: 2, backgroundColor: '#f0f8ff', textAlign: 'center' }}>
                  <Analytics color="primary" sx={{ mb: 1 }} />
                  <Typography variant="subtitle2" gutterBottom>
                    Total Vectors
                  </Typography>
                  <Typography variant="h6" color="primary">
                    {embeddingStats.total_vectors.toLocaleString()}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Paper sx={{ p: 2, backgroundColor: '#fff8f0', textAlign: 'center' }}>
                  <Storage color="secondary" sx={{ mb: 1 }} />
                  <Typography variant="subtitle2" gutterBottom>
                    Dimensions
                  </Typography>
                  <Typography variant="h6" color="secondary">
                    {embeddingStats.dimensions}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Paper sx={{ p: 2, backgroundColor: '#f0fff8', textAlign: 'center' }}>
                  <Timeline color="success" sx={{ mb: 1 }} />
                  <Typography variant="subtitle2" gutterBottom>
                    Avg Processing Time
                  </Typography>
                  <Typography variant="h6" color="success.main">
                    {(embeddingStats.average_processing_time_ms / 1000).toFixed(2)}s
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Paper sx={{ p: 2, backgroundColor: '#f8f0ff', textAlign: 'center' }}>
                  <Search color="warning" sx={{ mb: 1 }} />
                  <Typography variant="subtitle2" gutterBottom>
                    Index Type
                  </Typography>
                  <Typography variant="body2" color="warning.main">
                    {embeddingStats.index_type}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Search Capabilities */}
        {searchIndexReady && (
          <Alert severity="success" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Semantic search is now enabled!</strong> You can search through your knowledge base using natural language queries.
            </Typography>
          </Alert>
        )}

        {/* Model Information */}
        {phase.model_used && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Embedding Model
            </Typography>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" color="primary" sx={{ fontWeight: 500 }}>
                  {phase.model_used}
                </Typography>
                <Chip
                  label="Active"
                  size="small"
                  color="success"
                  variant="outlined"
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                This model generates high-quality semantic vectors for accurate similarity search
              </Typography>
            </Paper>
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

export default EmbeddingsPhase;