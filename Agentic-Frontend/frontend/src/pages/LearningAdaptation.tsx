import React, { useState, useRef } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  Alert,
  Skeleton,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Avatar,
  Divider,
  Tabs,
  Tab,
  InputAdornment,
  Rating,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import {
  Psychology,
  Feedback,
  School,
  Build,
  Timeline,
  ThumbUp,
  ThumbDown,
  Star,
  ExpandMore,
  Refresh,
  Settings,
  Assessment,
  TrendingUp,
  ModelTraining,
  Lightbulb,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

// Define learning types locally for now
interface FeedbackSubmission {
  feedback_id: string;
  content_id: string;
  feedback_type: 'correction' | 'rating' | 'improvement';
  original_prediction?: string;
  user_correction?: string;
  confidence_rating?: number;
  additional_context?: string;
  submitted_at: string;
}

interface ActiveLearningSample {
  sample_id: string;
  content: any;
  uncertainty_score: number;
  model_predictions: any[];
  suggested_label?: string;
  priority: 'high' | 'medium' | 'low';
  created_at: string;
}

interface FineTuningJob {
  job_id: string;
  base_model: string;
  target_model: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  training_data_size: number;
  epochs: number;
  learning_rate: number;
  created_at: string;
  completed_at?: string;
  metrics?: {
    accuracy: number;
    loss: number;
    f1_score: number;
  };
}

interface LearningStats {
  total_feedback_submissions: number;
  active_learning_samples: number;
  fine_tuning_jobs: number;
  model_improvements: number;
  average_confidence_rating: number;
  feedback_trends: Array<{
    date: string;
    submissions: number;
    average_rating: number;
  }>;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`learning-tabpanel-${index}`}
      aria-labelledby={`learning-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const LearningAdaptation: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [feedbackForm, setFeedbackForm] = useState({
    content_id: '',
    feedback_type: 'correction' as const,
    original_prediction: '',
    user_correction: '',
    confidence_rating: 5,
    additional_context: '',
  });

  // Learning Stats Query
  const {
    data: learningStats,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery<LearningStats>({
    queryKey: ['learning-stats'],
    queryFn: async () => {
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 1000));
      return {
        total_feedback_submissions: 245,
        active_learning_samples: 89,
        fine_tuning_jobs: 12,
        model_improvements: 8,
        average_confidence_rating: 4.2,
        feedback_trends: [
          { date: '2024-01-01', submissions: 15, average_rating: 4.1 },
          { date: '2024-01-02', submissions: 22, average_rating: 4.3 },
          { date: '2024-01-03', submissions: 18, average_rating: 4.0 },
        ]
      };
    },
  });

  // Active Learning Samples Query
  const {
    data: activeLearningSamples,
    isLoading: samplesLoading,
    refetch: refetchSamples,
  } = useQuery<ActiveLearningSample[]>({
    queryKey: ['active-learning-samples'],
    queryFn: async () => {
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 1200));
      return [
        {
          sample_id: 'sample_001',
          content: { text: 'Sample content for active learning analysis' },
          uncertainty_score: 0.85,
          model_predictions: [
            { model: 'llama2', prediction: 'category_a', confidence: 0.65 },
            { model: 'codellama', prediction: 'category_b', confidence: 0.72 }
          ],
          suggested_label: 'category_a',
          priority: 'high',
          created_at: '2024-01-01T10:00:00Z'
        },
        {
          sample_id: 'sample_002',
          content: { text: 'Another sample requiring human review' },
          uncertainty_score: 0.78,
          model_predictions: [
            { model: 'mistral', prediction: 'category_c', confidence: 0.58 },
            { model: 'llava', prediction: 'category_d', confidence: 0.61 }
          ],
          priority: 'medium',
          created_at: '2024-01-01T11:30:00Z'
        }
      ];
    },
  });

  // Fine-tuning Jobs Query
  const {
    data: fineTuningJobs,
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQuery<FineTuningJob[]>({
    queryKey: ['fine-tuning-jobs'],
    queryFn: async () => {
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 1400));
      return [
        {
          job_id: 'job_001',
          base_model: 'llama2:13b',
          target_model: 'llama2:13b-custom',
          status: 'running',
          progress: 65,
          training_data_size: 1000,
          epochs: 3,
          learning_rate: 0.0002,
          created_at: '2024-01-01T08:00:00Z',
          metrics: {
            accuracy: 0.87,
            loss: 0.23,
            f1_score: 0.85
          }
        },
        {
          job_id: 'job_002',
          base_model: 'codellama:7b',
          target_model: 'codellama:7b-domain',
          status: 'completed',
          progress: 100,
          training_data_size: 500,
          epochs: 2,
          learning_rate: 0.0001,
          created_at: '2023-12-28T14:00:00Z',
          completed_at: '2023-12-29T16:30:00Z',
          metrics: {
            accuracy: 0.92,
            loss: 0.15,
            f1_score: 0.91
          }
        }
      ];
    },
  });

  // Feedback Submission Mutation
  const feedbackMutation = useMutation({
    mutationFn: (feedback: FeedbackSubmission) => Promise.resolve(feedback),
    onSuccess: () => {
      setShowFeedbackDialog(false);
      setFeedbackForm({
        content_id: '',
        feedback_type: 'correction',
        original_prediction: '',
        user_correction: '',
        confidence_rating: 5,
        additional_context: '',
      });
      refetchStats();
      queryClient.invalidateQueries({ queryKey: ['feedback-history'] });
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFeedbackSubmit = () => {
    feedbackMutation.mutate({
      ...feedbackForm,
      feedback_id: `feedback_${Date.now()}`,
      submitted_at: new Date().toISOString(),
    });
  };

  const handleSampleLabel = (sampleId: string, label: string) => {
    // Placeholder for sample labeling
    console.log('Labeling sample:', sampleId, 'with label:', label);
    refetchSamples();
  };

  const handleRefresh = () => {
    refetchStats();
    refetchSamples();
    refetchJobs();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Learning & Adaptation Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Continuous model improvement through feedback, active learning, and fine-tuning.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<Feedback />}
            onClick={() => setShowFeedbackDialog(true)}
          >
            Submit Feedback
          </Button>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => setShowSettingsDialog(true)}
          >
            Settings
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Key Metrics */}
      {learningStats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                  {learningStats.total_feedback_submissions}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Feedback Submissions
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                  {learningStats.active_learning_samples}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Learning Samples
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                  {learningStats.fine_tuning_jobs}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Fine-tuning Jobs
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                  {learningStats.average_confidence_rating.toFixed(1)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Confidence Rating
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="learning tabs">
            <Tab icon={<Assessment />} label="Overview" />
            <Tab icon={<School />} label="Active Learning" />
            <Tab icon={<ModelTraining />} label="Fine-tuning" />
            <Tab icon={<Timeline />} label="Trends" />
          </Tabs>
        </CardContent>

        {/* Overview Tab */}
        <TabPanel value={tabValue} index={0}>
          {statsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : learningStats ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Learning Performance Overview
                    </Typography>
                    <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        Learning analytics chart would be implemented here
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Recent Improvements
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2">Model Accuracy</Typography>
                        <Chip label="+5.2%" size="small" color="success" />
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2">Response Time</Typography>
                        <Chip label="-12%" size="small" color="success" />
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2">User Satisfaction</Typography>
                        <Chip label="+8.1%" size="small" color="success" />
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No learning statistics available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Active Learning Tab */}
        <TabPanel value={tabValue} index={1}>
          {samplesLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : activeLearningSamples ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Samples Requiring Human Review ({activeLearningSamples.length})
                </Typography>
              </Grid>

              {activeLearningSamples.map((sample, index) => (
                <Grid item xs={12} md={6} key={sample.sample_id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          Sample {index + 1}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Chip
                            label={`Priority: ${sample.priority}`}
                            size="small"
                            color={getPriorityColor(sample.priority) as any}
                          />
                          <Chip
                            label={`Uncertainty: ${(sample.uncertainty_score * 100).toFixed(0)}%`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </Box>

                      <Typography variant="body2" sx={{ mb: 2 }}>
                        {typeof sample.content === 'object' && sample.content.text
                          ? sample.content.text
                          : 'Sample content preview'
                        }
                      </Typography>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Model Predictions:
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
                        {sample.model_predictions.map((pred, idx) => (
                          <Box key={idx} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="body2">{pred.model}:</Typography>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {pred.prediction}
                              </Typography>
                              <Chip
                                label={`${(pred.confidence * 100).toFixed(0)}%`}
                                size="small"
                                variant="outlined"
                              />
                            </Box>
                          </Box>
                        ))}
                      </Box>

                      {sample.suggested_label && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Suggested Label:
                          </Typography>
                          <Chip
                            label={sample.suggested_label}
                            color="primary"
                            onClick={() => handleSampleLabel(sample.sample_id, sample.suggested_label!)}
                          />
                        </Box>
                      )}

                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          onClick={() => handleSampleLabel(sample.sample_id, 'approved')}
                        >
                          Approve
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          color="error"
                          onClick={() => handleSampleLabel(sample.sample_id, 'rejected')}
                        >
                          Reject
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {activeLearningSamples.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <School sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No active learning samples available
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Samples will appear here when models need human review
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No active learning samples available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Fine-tuning Tab */}
        <TabPanel value={tabValue} index={2}>
          {jobsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : fineTuningJobs ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Fine-tuning Jobs ({fineTuningJobs.length})
                </Typography>
              </Grid>

              {fineTuningJobs.map((job) => (
                <Grid item xs={12} md={6} key={job.job_id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          {job.target_model}
                        </Typography>
                        <Chip
                          label={job.status}
                          color={getStatusColor(job.status) as any}
                        />
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        Base Model: {job.base_model}
                      </Typography>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          Progress: {job.progress}%
                        </Typography>
                        <LinearProgress variant="determinate" value={job.progress} />
                      </Box>

                      <Grid container spacing={2} sx={{ mb: 2 }}>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">Training Data:</Typography>
                          <Typography variant="body2">{job.training_data_size} samples</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">Epochs:</Typography>
                          <Typography variant="body2">{job.epochs}</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">Learning Rate:</Typography>
                          <Typography variant="body2">{job.learning_rate}</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">Created:</Typography>
                          <Typography variant="body2">
                            {new Date(job.created_at).toLocaleDateString()}
                          </Typography>
                        </Grid>
                      </Grid>

                      {job.metrics && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Performance Metrics:
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                              label={`Accuracy: ${(job.metrics.accuracy * 100).toFixed(1)}%`}
                              size="small"
                              variant="outlined"
                              color="success"
                            />
                            <Chip
                              label={`Loss: ${job.metrics.loss.toFixed(3)}`}
                              size="small"
                              variant="outlined"
                              color="warning"
                            />
                            <Chip
                              label={`F1: ${(job.metrics.f1_score * 100).toFixed(1)}%`}
                              size="small"
                              variant="outlined"
                              color="info"
                            />
                          </Box>
                        </Box>
                      )}

                      {job.status === 'running' && (
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Button size="small" variant="outlined" color="error">
                            Stop Job
                          </Button>
                          <Button size="small" variant="outlined">
                            View Logs
                          </Button>
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {fineTuningJobs.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <ModelTraining sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No fine-tuning jobs available
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Start a new fine-tuning job to improve model performance
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No fine-tuning jobs available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Trends Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Learning Trends Over Time
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Learning trends visualization would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Feedback Submission Dialog */}
      <Dialog
        open={showFeedbackDialog}
        onClose={() => setShowFeedbackDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Feedback sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Submit Model Feedback</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Help improve our AI models by providing feedback on their predictions and suggestions.
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Content ID"
                value={feedbackForm.content_id}
                onChange={(e) => setFeedbackForm(prev => ({ ...prev, content_id: e.target.value }))}
                placeholder="e.g., content_123 or task_456"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Feedback Type</InputLabel>
                <Select
                  value={feedbackForm.feedback_type}
                  label="Feedback Type"
                  onChange={(e) => setFeedbackForm(prev => ({ ...prev, feedback_type: e.target.value as any }))}
                >
                  <MenuItem value="correction">Correction</MenuItem>
                  <MenuItem value="rating">Rating</MenuItem>
                  <MenuItem value="improvement">Improvement Suggestion</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Original Prediction"
                value={feedbackForm.original_prediction}
                onChange={(e) => setFeedbackForm(prev => ({ ...prev, original_prediction: e.target.value }))}
                placeholder="What did the model predict?"
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Your Correction/Suggestion"
                value={feedbackForm.user_correction}
                onChange={(e) => setFeedbackForm(prev => ({ ...prev, user_correction: e.target.value }))}
                placeholder="What should the model have predicted?"
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography component="legend" sx={{ mb: 1 }}>
                Confidence Rating
              </Typography>
              <Rating
                value={feedbackForm.confidence_rating}
                onChange={(event, newValue) => {
                  setFeedbackForm(prev => ({ ...prev, confidence_rating: newValue || 5 }));
                }}
                max={5}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Additional Context (Optional)"
                value={feedbackForm.additional_context}
                onChange={(e) => setFeedbackForm(prev => ({ ...prev, additional_context: e.target.value }))}
                placeholder="Any additional context or explanation..."
                multiline
                rows={3}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowFeedbackDialog(false)}>Cancel</Button>
          <Button
            onClick={handleFeedbackSubmit}
            variant="contained"
            disabled={feedbackMutation.isPending}
          >
            {feedbackMutation.isPending ? 'Submitting...' : 'Submit Feedback'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog
        open={showSettingsDialog}
        onClose={() => setShowSettingsDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Settings sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Learning Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure learning and adaptation settings.
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Active Learning Strategy</InputLabel>
                <Select defaultValue="uncertainty">
                  <MenuItem value="uncertainty">Uncertainty Sampling</MenuItem>
                  <MenuItem value="diversity">Diversity Sampling</MenuItem>
                  <MenuItem value="query_by_committee">Query by Committee</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Feedback Collection</InputLabel>
                <Select defaultValue="continuous">
                  <MenuItem value="continuous">Continuous</MenuItem>
                  <MenuItem value="batch">Batch Processing</MenuItem>
                  <MenuItem value="manual">Manual Only</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSettingsDialog(false)}>Cancel</Button>
          <Button
            onClick={() => setShowSettingsDialog(false)}
            variant="contained"
          >
            Save Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LearningAdaptation;