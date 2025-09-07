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
  Visibility,
  CheckCircle,
  Error,
  HourglassEmpty,
  Refresh,
  Image,
  TextFields,
  Category,
  ExpandMore,
} from '@mui/icons-material';

interface MediaAnalysis {
  filename: string;
  type: 'image' | 'video';
  caption?: string;
  objects?: string[];
  ocr_text?: string;
  confidence?: number;
  processing_time_ms?: number;
}

interface InterpretMediaPhaseProps {
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
  mediaAnalyses?: MediaAnalysis[];
  currentFile?: string;
  totalFiles?: number;
  processedFiles?: number;
}

const InterpretMediaPhase: React.FC<InterpretMediaPhaseProps> = ({
  phase,
  onRetry,
  onSkip,
  mediaAnalyses = [],
  currentFile = '',
  totalFiles = 0,
  processedFiles = 0,
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
        return <Visibility color="action" />;
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

  const getAnalysisIcon = (type: string) => {
    switch (type) {
      case 'caption':
        return <TextFields color="primary" />;
      case 'objects':
        return <Category color="secondary" />;
      case 'ocr':
        return <TextFields color="success" />;
      default:
        return <Image color="action" />;
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ mr: 2 }}>
            👁️
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" component="h3">
              Interpret Media
            </Typography>
            <Typography variant="body2" color="text.secondary">
              AI analysis of images/videos using vision models
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
                Files Processed
              </Typography>
              <Typography variant="h5" color="primary">
                {processedFiles}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {totalFiles} total
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
          <Grid item xs={12} sm={4}>
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
        {currentFile && phase.status === 'running' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Analyzing:</strong> {currentFile}
            </Typography>
          </Alert>
        )}

        {/* Media Analysis Results */}
        {mediaAnalyses.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Analysis Results ({mediaAnalyses.length} files)
            </Typography>

            {mediaAnalyses.slice(0, 5).map((analysis, index) => (
              <Accordion key={index} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <Image color="primary" />
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {analysis.filename}
                    </Typography>
                    {analysis.confidence && (
                      <Chip
                        label={`${(analysis.confidence * 100).toFixed(1)}%`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    {/* Caption */}
                    {analysis.caption && (
                      <Grid item xs={12}>
                        <Paper sx={{ p: 2, backgroundColor: '#f0f8ff' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <TextFields color="primary" />
                            <Typography variant="subtitle2">AI Caption</Typography>
                          </Box>
                          <Typography variant="body2">
                            {analysis.caption}
                          </Typography>
                        </Paper>
                      </Grid>
                    )}

                    {/* Detected Objects */}
                    {analysis.objects && analysis.objects.length > 0 && (
                      <Grid item xs={12} sm={6}>
                        <Paper sx={{ p: 2, backgroundColor: '#fff8f0' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Category color="secondary" />
                            <Typography variant="subtitle2">Detected Objects</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {analysis.objects.map((obj, objIndex) => (
                              <Chip
                                key={objIndex}
                                label={obj}
                                size="small"
                                variant="outlined"
                                color="secondary"
                              />
                            ))}
                          </Box>
                        </Paper>
                      </Grid>
                    )}

                    {/* OCR Text */}
                    {analysis.ocr_text && (
                      <Grid item xs={12} sm={6}>
                        <Paper sx={{ p: 2, backgroundColor: '#f0fff8' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <TextFields color="success" />
                            <Typography variant="subtitle2">Extracted Text</Typography>
                          </Box>
                          <Typography variant="body2" sx={{
                            maxHeight: 100,
                            overflow: 'auto',
                            fontFamily: 'monospace'
                          }}>
                            {analysis.ocr_text}
                          </Typography>
                        </Paper>
                      </Grid>
                    )}

                    {/* Processing Time */}
                    {analysis.processing_time_ms && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">
                          Processing time: {(analysis.processing_time_ms / 1000).toFixed(2)}s
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </AccordionDetails>
              </Accordion>
            ))}

            {mediaAnalyses.length > 5 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                ... and {mediaAnalyses.length - 5} more analyses
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

export default InterpretMediaPhase;