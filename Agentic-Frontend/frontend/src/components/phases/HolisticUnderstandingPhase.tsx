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
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Psychology,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  Lightbulb,
  TrendingUp,
  ExpandMore,
  Insights,
} from '@mui/icons-material';

interface Insight {
  type: 'key_point' | 'theme' | 'pattern' | 'connection';
  content: string;
  confidence?: number;
  relevance_score?: number;
}

interface HolisticUnderstandingPhaseProps {
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
  insights?: Insight[];
  currentItem?: string;
  totalItems?: number;
  processedItems?: number;
  overallSentiment?: {
    label: string;
    score: number;
  };
  themes?: Array<{
    name: string;
    strength: number;
    items_count: number;
  }>;
}

const HolisticUnderstandingPhase: React.FC<HolisticUnderstandingPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  insights = [],
  currentItem = '',
  totalItems = 0,
  processedItems = 0,
  overallSentiment,
  themes = [],
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
        return <Psychology color="action" />;
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

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'key_point':
        return <Lightbulb color="primary" />;
      case 'theme':
        return <TrendingUp color="secondary" />;
      case 'pattern':
        return <Insights color="success" />;
      case 'connection':
        return <Psychology color="warning" />;
      default:
        return <Lightbulb color="action" />;
    }
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.6) return 'success';
    if (score > 0.4) return 'warning';
    return 'error';
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ mr: 2 }}>
            🧠
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Holistic Understanding
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Combine text and media insights for comprehensive analysis
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
              Analysis Progress
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
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Items Analyzed
              </Typography>
              <Typography variant="h5" color="primary">
                {processedItems}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {totalItems} total
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Insights Generated
              </Typography>
              <Typography variant="h5" color="secondary">
                {insights.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                key insights found
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={4}>
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

        {/* Overall Sentiment */}
        {overallSentiment && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Overall Sentiment Analysis
            </Typography>
            <Paper sx={{ p: 2, backgroundColor: '#f0f8ff' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" gutterBottom>
                    Sentiment: <strong>{overallSentiment.label}</strong>
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={overallSentiment.score * 100}
                    sx={{ height: 8, borderRadius: 4 }}
                    color={getSentimentColor(overallSentiment.score) as any}
                  />
                </Box>
                <Typography variant="h6" color="primary">
                  {(overallSentiment.score * 100).toFixed(1)}%
                </Typography>
              </Box>
            </Paper>
          </Box>
        )}

        {/* Current processing status */}
        {currentItem && phase.status === 'running' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Analyzing:</strong> {currentItem}
            </Typography>
          </Alert>
        )}

        {/* Emerging Themes */}
        {themes.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Emerging Themes
            </Typography>
            <Grid container spacing={1}>
              {themes.map((theme, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Paper sx={{ p: 2, backgroundColor: '#fff8f0' }}>
                    <Typography variant="subtitle2" gutterBottom>
                      {theme.name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={theme.strength * 100}
                        sx={{ flex: 1, height: 6, borderRadius: 3 }}
                        color="secondary"
                      />
                      <Typography variant="caption">
                        {(theme.strength * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {theme.items_count} items
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Key Insights */}
        {insights.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Key Insights ({insights.length})
            </Typography>

            <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
              {insights.map((insight, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {getInsightIcon(insight.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" sx={{ flex: 1 }}>
                            {insight.content}
                          </Typography>
                          {insight.confidence && (
                            <Chip
                              label={`${(insight.confidence * 100).toFixed(1)}%`}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="caption" sx={{ textTransform: 'capitalize' }}>
                            {insight.type.replace('_', ' ')}
                          </Typography>
                          {insight.relevance_score && (
                            <Typography variant="caption" color="text.secondary">
                              • Relevance: {(insight.relevance_score * 100).toFixed(1)}%
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < insights.length - 1 && <Divider />}
                </React.Fragment>
              ))}
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

export default HolisticUnderstandingPhase;