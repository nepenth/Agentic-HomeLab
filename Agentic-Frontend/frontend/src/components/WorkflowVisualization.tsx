import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Stop,
  Settings,
  ExpandMore,
  Timeline,
  CheckCircle,
  Error,
  HourglassEmpty,
  SkipNext,
  Refresh,
} from '@mui/icons-material';

interface Phase {
  name: string;
  display_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  progress_percentage: number;
  start_time?: string;
  end_time?: string;
  duration_ms?: number;
  model_used?: string;
  error_message?: string;
  status_message?: string;
}

interface WorkflowVisualizationProps {
  phases: Phase[];
  overallProgress: number;
  currentPhase?: string;
  isRunning?: boolean;
  itemId?: string; // For cancellation
  onStart?: () => void;
  onPause?: () => void;
  onStop?: () => void;
  onCancel?: () => void; // New cancel callback
  onSettings?: () => void;
  onSkipPhase?: (phaseName: string) => void;
  onRetryPhase?: (phaseName: string) => void;
}

const WorkflowVisualization: React.FC<WorkflowVisualizationProps> = ({
  phases,
  overallProgress,
  currentPhase,
  isRunning = false,
  itemId,
  onStart,
  onPause,
  onStop,
  onCancel,
  onSettings,
  onSkipPhase,
  onRetryPhase,
}) => {
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null);

  const getPhaseIcon = (phaseName: string) => {
    const icons: Record<string, string> = {
      'fetch_bookmarks': '📥',
      'cache_content': '💾',
      'cache_media': '📎',
      'interpret_media': '👁️',
      'categorize_content': '🏷️',
      'holistic_understanding': '🧠',
      'synthesized_learning': '📚',
      'embeddings': '🔍'
    };
    return icons[phaseName] || '⏳';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'running':
        return <HourglassEmpty color="primary" />;
      case 'failed':
        return <Error color="error" />;
      case 'skipped':
        return <SkipNext color="warning" />;
      default:
        return <HourglassEmpty color="disabled" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      case 'skipped':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return 'N/A';
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
  };

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Overall Progress Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" component="h3">
              Knowledge Base Processing Pipeline
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {onStart && (
                <Tooltip title="Start Processing">
                  <IconButton onClick={onStart} disabled={isRunning} color="primary">
                    <PlayArrow />
                  </IconButton>
                </Tooltip>
              )}
              {onPause && (
                <Tooltip title="Pause Processing">
                  <IconButton onClick={onPause} disabled={!isRunning} color="warning">
                    <Pause />
                  </IconButton>
                </Tooltip>
              )}
              {onStop && (
                <Tooltip title="Stop Processing">
                  <IconButton onClick={onStop} color="error">
                    <Stop />
                  </IconButton>
                </Tooltip>
              )}
              {onCancel && itemId && (
                <Tooltip title="Cancel Processing">
                  <IconButton onClick={onCancel} color="error">
                    <Stop />
                  </IconButton>
                </Tooltip>
              )}
              {onSettings && (
                <Tooltip title="Workflow Settings">
                  <IconButton onClick={onSettings}>
                    <Settings />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Overall Progress
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {overallProgress.toFixed(1)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={overallProgress}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>

          {currentPhase && (
            <Typography variant="body2" color="primary">
              Current Phase: {currentPhase.replace(/_/g, ' ')}
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Phase Grid */}
      <Grid container spacing={2}>
        {phases.map((phase, index) => (
          <Grid item xs={12} sm={6} md={3} key={phase.name}>
            <Card
              sx={{
                height: '100%',
                border: phase.status === 'running' ? '2px solid #1976d2' : '1px solid #e0e0e0',
                backgroundColor: phase.status === 'running' ? '#f3f9ff' : 'transparent',
              }}
            >
              <CardContent sx={{ p: 2 }}>
                {/* Phase Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h4" sx={{ mr: 1 }}>
                    {getPhaseIcon(phase.name)}
                  </Typography>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {phase.display_name || phase.name.replace(/_/g, ' ')}
                    </Typography>
                    <Chip
                      label={phase.status}
                      size="small"
                      color={getStatusColor(phase.status) as any}
                      sx={{ mt: 0.5 }}
                    />
                  </Box>
                </Box>

                {/* Progress Bar */}
                <Box sx={{ mb: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={phase.progress_percentage}
                    sx={{ height: 6, borderRadius: 3 }}
                    color={phase.status === 'completed' ? 'success' :
                           phase.status === 'running' ? 'primary' :
                           phase.status === 'failed' ? 'error' : 'inherit'}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {phase.progress_percentage.toFixed(1)}%
                  </Typography>
                </Box>

                {/* Phase Actions */}
                <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                  {phase.status === 'failed' && onRetryPhase && (
                    <Tooltip title="Retry Phase">
                      <IconButton size="small" onClick={() => onRetryPhase(phase.name)}>
                        <Refresh fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                  {(phase.status === 'pending' || phase.status === 'running') && onSkipPhase && (
                    <Tooltip title="Skip Phase">
                      <IconButton size="small" onClick={() => onSkipPhase(phase.name)}>
                        <SkipNext fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Detailed Phase Information */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Phase Details
          </Typography>
          <List>
            {phases.map((phase, index) => (
              <React.Fragment key={phase.name}>
                <ListItem
                  button
                  onClick={() => setExpandedPhase(expandedPhase === phase.name ? null : phase.name)}
                >
                  <ListItemIcon>
                    {getStatusIcon(phase.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={phase.display_name || phase.name.replace(/_/g, ' ')}
                    secondary={
                      <Box>
                        <Typography variant="caption" component="span">
                          Status: {phase.status} • Progress: {phase.progress_percentage.toFixed(1)}%
                        </Typography>
                        {phase.duration_ms && (
                          <Typography variant="caption" component="span" sx={{ ml: 2 }}>
                            Duration: {formatDuration(phase.duration_ms)}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <ExpandMore
                    sx={{
                      transform: expandedPhase === phase.name ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s',
                    }}
                  />
                </ListItem>

                {expandedPhase === phase.name && (
                  <Box sx={{ pl: 4, pr: 2, pb: 2 }}>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Start Time:</strong> {formatTimestamp(phase.start_time)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          <strong>End Time:</strong> {formatTimestamp(phase.end_time)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Duration:</strong> {formatDuration(phase.duration_ms)}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Model Used:</strong> {phase.model_used || 'N/A'}
                        </Typography>
                        {phase.status_message && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Status:</strong> {phase.status_message}
                          </Typography>
                        )}
                        {phase.error_message && (
                          <Typography variant="body2" color="error">
                            <strong>Error:</strong> {phase.error_message}
                          </Typography>
                        )}
                      </Grid>
                    </Grid>
                  </Box>
                )}

                {index < phases.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
};

export default WorkflowVisualization;