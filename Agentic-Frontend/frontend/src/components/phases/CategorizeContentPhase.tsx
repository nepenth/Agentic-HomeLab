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
  Label,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  Category,
  ExpandMore,
  Tag,
} from '@mui/icons-material';

interface ContentCategory {
  item_id: string;
  title: string;
  primary_category: string;
  subcategories: string[];
  confidence: number;
  tags: string[];
  processing_time_ms?: number;
}

interface CategorizeContentPhaseProps {
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
  categorizedItems?: ContentCategory[];
  currentItem?: string;
  totalItems?: number;
  processedItems?: number;
  categoriesFound?: string[];
}

const CategorizeContentPhase: React.FC<CategorizeContentPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  categorizedItems = [],
  currentItem = '',
  totalItems = 0,
  processedItems = 0,
  categoriesFound = [],
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
        return <Label color="action" />;
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

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ mr: 2 }}>
            🏷️
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Categorize Content
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Classify content into categories and subcategories
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
              Categorization Progress
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
                Categories Found
              </Typography>
              <Typography variant="h5" color="secondary">
                {categoriesFound.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                unique categories
              </Typography>
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
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Model Used
              </Typography>
              <Typography variant="body2" color="secondary">
                {phase.model_used || 'N/A'}
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {/* Current processing status */}
        {currentItem && phase.status === 'running' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Categorizing:</strong> {currentItem}
            </Typography>
          </Alert>
        )}

        {/* Categories Overview */}
        {categoriesFound.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Categories Discovered
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {categoriesFound.map((category, index) => (
                <Chip
                  key={index}
                  label={category}
                  variant="outlined"
                  color="primary"
                  icon={<Category />}
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Categorized Items */}
        {categorizedItems.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Recent Categorizations ({categorizedItems.length} items)
            </Typography>

            {categorizedItems.slice(0, 5).map((item, index) => (
              <Accordion key={index} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <Tag color="primary" />
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {item.title}
                    </Typography>
                    <Chip
                      label={`${(item.confidence * 100).toFixed(1)}%`}
                      size="small"
                      color={getConfidenceColor(item.confidence) as any}
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    {/* Primary Category */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#f0f8ff' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Primary Category
                        </Typography>
                        <Chip
                          label={item.primary_category}
                          color="primary"
                          variant="filled"
                        />
                      </Paper>
                    </Grid>

                    {/* Subcategories */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#fff8f0' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Subcategories
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {item.subcategories.map((sub, subIndex) => (
                            <Chip
                              key={subIndex}
                              label={sub}
                              size="small"
                              variant="outlined"
                              color="secondary"
                            />
                          ))}
                        </Box>
                      </Paper>
                    </Grid>

                    {/* Tags */}
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2, backgroundColor: '#f0fff8' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Generated Tags
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {item.tags.map((tag, tagIndex) => (
                            <Chip
                              key={tagIndex}
                              label={tag}
                              size="small"
                              variant="outlined"
                              color="success"
                              icon={<Tag />}
                            />
                          ))}
                        </Box>
                      </Paper>
                    </Grid>

                    {/* Processing Time */}
                    {item.processing_time_ms && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">
                          Processing time: {(item.processing_time_ms / 1000).toFixed(2)}s
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </AccordionDetails>
              </Accordion>
            ))}

            {categorizedItems.length > 5 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                ... and {categorizedItems.length - 5} more categorizations
              </Typography>
            )}
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

export default CategorizeContentPhase;