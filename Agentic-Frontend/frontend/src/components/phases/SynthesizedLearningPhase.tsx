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
  School,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  LibraryBooks,
  ExpandMore,
  Article,
  Lightbulb,
} from '@mui/icons-material';

interface LearningContent {
  category: string;
  title: string;
  summary: string;
  key_points: string[];
  learning_objectives: string[];
  related_concepts: string[];
  difficulty_level: 'beginner' | 'intermediate' | 'advanced';
  estimated_read_time: number; // minutes
  content_type: 'summary' | 'tutorial' | 'reference' | 'analysis';
}

interface SynthesizedLearningPhaseProps {
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
  learningContent?: LearningContent[];
  currentCategory?: string;
  totalCategories?: number;
  processedCategories?: number;
  contentGenerated?: number;
}

const SynthesizedLearningPhase: React.FC<SynthesizedLearningPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  learningContent = [],
  currentCategory = '',
  totalCategories = 0,
  processedCategories = 0,
  contentGenerated = 0,
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
        return <School color="action" />;
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

  const getDifficultyColor = (level: string) => {
    switch (level) {
      case 'beginner':
        return 'success';
      case 'intermediate':
        return 'warning';
      case 'advanced':
        return 'error';
      default:
        return 'default';
    }
  };

  const getContentTypeIcon = (type: string) => {
    switch (type) {
      case 'summary':
        return <Article color="primary" />;
      case 'tutorial':
        return <School color="secondary" />;
      case 'reference':
        return <LibraryBooks color="success" />;
      case 'analysis':
        return <Lightbulb color="warning" />;
      default:
        return <Article color="action" />;
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ mr: 2 }}>
            📚
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Synthesized Learning
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Generate category-specific learning documents
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
              Synthesis Progress
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
                Categories Processed
              </Typography>
              <Typography variant="h5" color="primary">
                {processedCategories}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {totalCategories} total
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Content Generated
              </Typography>
              <Typography variant="h5" color="secondary">
                {contentGenerated}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                learning documents
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={3}>
            <Paper sx={{ p: 2, backgroundColor: '#f8f9fa', textAlign: 'center' }}>
              <Typography variant="subtitle2" gutterBottom>
                Current Category
              </Typography>
              <Typography variant="body2" color="primary" sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {currentCategory || 'None'}
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
        {currentCategory && phase.status === 'running' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Synthesizing learning content for:</strong> {currentCategory}
            </Typography>
          </Alert>
        )}

        {/* Generated Learning Content */}
        {learningContent.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Generated Learning Content ({learningContent.length} documents)
            </Typography>

            {learningContent.slice(0, 3).map((content, index) => (
              <Accordion key={index} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    {getContentTypeIcon(content.content_type)}
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {content.title}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                        <Chip
                          label={content.category}
                          size="small"
                          variant="outlined"
                          color="primary"
                        />
                        <Chip
                          label={content.difficulty_level}
                          size="small"
                          color={getDifficultyColor(content.difficulty_level) as any}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {content.estimated_read_time} min read
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    {/* Summary */}
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2, backgroundColor: '#f0f8ff' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Summary
                        </Typography>
                        <Typography variant="body2">
                          {content.summary}
                        </Typography>
                      </Paper>
                    </Grid>

                    {/* Key Points */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#fff8f0' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Key Points
                        </Typography>
                        <List dense>
                          {content.key_points.map((point, pointIndex) => (
                            <ListItem key={pointIndex} sx={{ px: 0 }}>
                              <ListItemIcon sx={{ minWidth: 24 }}>
                                <Typography variant="body2" color="primary">
                                  •
                                </Typography>
                              </ListItemIcon>
                              <ListItemText
                                primary={
                                  <Typography variant="body2">
                                    {point}
                                  </Typography>
                                }
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Paper>
                    </Grid>

                    {/* Learning Objectives */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#f0fff8' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Learning Objectives
                        </Typography>
                        <List dense>
                          {content.learning_objectives.map((objective, objIndex) => (
                            <ListItem key={objIndex} sx={{ px: 0 }}>
                              <ListItemIcon sx={{ minWidth: 24 }}>
                                <Typography variant="body2" color="secondary">
                                  ✓
                                </Typography>
                              </ListItemIcon>
                              <ListItemText
                                primary={
                                  <Typography variant="body2">
                                    {objective}
                                  </Typography>
                                }
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Paper>
                    </Grid>

                    {/* Related Concepts */}
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2, backgroundColor: '#f8f0ff' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Related Concepts
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {content.related_concepts.map((concept, conceptIndex) => (
                            <Chip
                              key={conceptIndex}
                              label={concept}
                              size="small"
                              variant="outlined"
                              color="secondary"
                            />
                          ))}
                        </Box>
                      </Paper>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            ))}

            {learningContent.length > 3 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                ... and {learningContent.length - 3} more learning documents
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

export default SynthesizedLearningPhase;