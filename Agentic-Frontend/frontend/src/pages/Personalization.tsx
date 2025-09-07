import React, { useState } from 'react';
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
  Avatar,
  Divider,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Slider,
} from '@mui/material';
import {
  Person,
  Recommend,
  Timeline,
  Refresh,
  Settings,
  TrendingUp,
  ThumbUp,
  ThumbDown,
  Star,
  Psychology,
  Analytics,
  Group,
  Tune,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { PersonalizationCapabilities } from '../types';

// Define personalization types locally for now
interface PersonalizationRecommendations {
  recommendations: Array<{
    content_id: string;
    title: string;
    type: string;
    score: number;
    reason: string;
  }>;
  [key: string]: any;
}

interface UserInsights {
  user_id: string;
  insights: Array<{
    type: string;
    description: string;
    confidence: number;
    impact: string;
  }>;
  preferences: any;
  behavior_patterns: any;
  [key: string]: any;
}

interface InteractionData {
  user_id: string;
  content_id: string;
  interaction_type: string;
  metadata?: any;
  timestamp?: string;
}

interface PersonalizationStats {
  total_users: number;
  active_users: number;
  total_recommendations: number;
  average_engagement: number;
  personalization_effectiveness: number;
  [key: string]: any;
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
      id={`personalization-tabpanel-${index}`}
      aria-labelledby={`personalization-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Personalization: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [personalizationEnabled, setPersonalizationEnabled] = useState(true);
  const [recommendationLimit, setRecommendationLimit] = useState(10);
  const [diversityWeight, setDiversityWeight] = useState(0.5);

  // Personalization queries
  const {
    data: recommendations,
    isLoading: recommendationsLoading,
    refetch: refetchRecommendations,
  } = useQuery<PersonalizationRecommendations>({
    queryKey: ['personalization-recommendations', selectedUserId],
    queryFn: () => apiClient.getPersonalizedRecommendations({
      user_id: selectedUserId,
      limit: recommendationLimit,
    }),
    enabled: !!selectedUserId,
    refetchInterval: 300000,
  });

  const {
    data: userInsights,
    isLoading: insightsLoading,
    refetch: refetchInsights,
  } = useQuery<UserInsights>({
    queryKey: ['user-insights', selectedUserId],
    queryFn: () => apiClient.getUserInsights(selectedUserId),
    enabled: !!selectedUserId,
    refetchInterval: 300000,
  });

  const {
    data: personalizationStats,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery<PersonalizationStats>({
    queryKey: ['personalization-stats'],
    queryFn: () => apiClient.getPersonalizationStats(),
    refetchInterval: 60000,
  });

  const {
    data: capabilities,
    isLoading: capabilitiesLoading,
  } = useQuery<PersonalizationCapabilities>({
    queryKey: ['personalization-capabilities'],
    queryFn: () => apiClient.getPersonalizationCapabilities(),
  });

  // Mutations
  const trackInteractionMutation = useMutation({
    mutationFn: (interactionData: InteractionData) => apiClient.trackInteraction(interactionData),
    onSuccess: () => {
      refetchRecommendations();
      refetchInsights();
    },
  });

  const resetProfileMutation = useMutation({
    mutationFn: (userId: string) => apiClient.resetUserProfile(userId),
    onSuccess: () => {
      refetchRecommendations();
      refetchInsights();
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    refetchRecommendations();
    refetchInsights();
    refetchStats();
  };

  const handleTrackInteraction = (contentId: string, interactionType: string) => {
    if (!selectedUserId) return;

    trackInteractionMutation.mutate({
      user_id: selectedUserId,
      content_id: contentId,
      interaction_type: interactionType,
      timestamp: new Date().toISOString(),
    });
  };

  const handleResetProfile = () => {
    if (!selectedUserId) return;
    resetProfileMutation.mutate(selectedUserId);
  };

  const getInteractionIcon = (type: string) => {
    switch (type) {
      case 'like':
        return <ThumbUp color="success" />;
      case 'dislike':
        return <ThumbDown color="error" />;
      case 'view':
        return <Psychology color="info" />;
      case 'share':
        return <Group color="primary" />;
      default:
        return <Star color="warning" />;
    }
  };

  if (!selectedUserId && tabValue > 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          Please select a user ID to view personalized content and insights.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Personalization Studio
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI-powered user personalization, recommendations, and behavioral analytics.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
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
            disabled={!selectedUserId}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* User Selection */}
      <Card elevation={0} sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="User ID"
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                placeholder="Enter user ID to personalize"
                helperText="Enter a user ID to see personalized recommendations and insights"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth>
                <InputLabel>Recommendation Limit</InputLabel>
                <Select
                  value={recommendationLimit}
                  label="Recommendation Limit"
                  onChange={(e) => setRecommendationLimit(Number(e.target.value))}
                >
                  <MenuItem value={5}>5 recommendations</MenuItem>
                  <MenuItem value={10}>10 recommendations</MenuItem>
                  <MenuItem value={20}>20 recommendations</MenuItem>
                  <MenuItem value={50}>50 recommendations</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Button
                variant="outlined"
                color="error"
                onClick={handleResetProfile}
                disabled={!selectedUserId || resetProfileMutation.isPending}
                fullWidth
              >
                Reset User Profile
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Stats Overview */}
      {personalizationStats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                  {personalizationStats.total_users || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Users
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                  {personalizationStats.active_users || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Users
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                  {(personalizationStats.average_engagement * 100)?.toFixed(1) || '0'}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Engagement
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                  {(personalizationStats.personalization_effectiveness * 100)?.toFixed(1) || '0'}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Effectiveness
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="personalization tabs">
            <Tab icon={<Recommend />} label="Recommendations" />
            <Tab icon={<Psychology />} label="User Insights" />
            <Tab icon={<Timeline />} label="Behavior" />
            <Tab icon={<Analytics />} label="Analytics" />
          </Tabs>
        </CardContent>

        {/* Recommendations Tab */}
        <TabPanel value={tabValue} index={0}>
          {recommendationsLoading ? (
            <Box>
              <Grid container spacing={3}>
                {[...Array(6)].map((_, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : recommendations ? (
            <Grid container spacing={3}>
              {recommendations.recommendations?.map((rec, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Card elevation={1} sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                          {rec.type[0]?.toUpperCase()}
                        </Avatar>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {rec.title}
                          </Typography>
                          <Chip
                            label={rec.type}
                            size="small"
                            variant="outlined"
                            sx={{ mt: 0.5 }}
                          />
                        </Box>
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {rec.reason}
                      </Typography>

                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Chip
                          label={`Score: ${(rec.score * 100).toFixed(0)}%`}
                          size="small"
                          color="primary"
                        />
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleTrackInteraction(rec.content_id, 'like')}
                            disabled={trackInteractionMutation.isPending}
                          >
                            <ThumbUp fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleTrackInteraction(rec.content_id, 'dislike')}
                            disabled={trackInteractionMutation.isPending}
                          >
                            <ThumbDown fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              )) || (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    No recommendations available for this user.
                  </Typography>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                Select a user ID to see personalized recommendations
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* User Insights Tab */}
        <TabPanel value={tabValue} index={1}>
          {insightsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : userInsights ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                      User Insights & Preferences
                    </Typography>

                    <Grid container spacing={2}>
                      {userInsights.insights?.map((insight, index) => (
                        <Grid item xs={12} md={6} key={index}>
                          <Card variant="outlined">
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <Psychology sx={{ mr: 1, color: 'primary.main' }} />
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                  {insight.type}
                                </Typography>
                              </Box>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                {insight.description}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                <Chip
                                  label={`Confidence: ${(insight.confidence * 100).toFixed(0)}%`}
                                  size="small"
                                  variant="outlined"
                                />
                                <Chip
                                  label={`Impact: ${insight.impact}`}
                                  size="small"
                                  color={
                                    insight.impact === 'high' ? 'error' :
                                    insight.impact === 'medium' ? 'warning' : 'success'
                                  }
                                />
                              </Box>
                            </CardContent>
                          </Card>
                        </Grid>
                      )) || (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary" align="center">
                            No insights available for this user.
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                Select a user ID to see user insights
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Behavior Tab */}
        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    User Behavior Patterns
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Behavior visualization would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Personalization Analytics
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Personalization analytics charts would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Settings Dialog */}
      <Dialog
        open={showSettingsDialog}
        onClose={() => setShowSettingsDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tune sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Personalization Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={personalizationEnabled}
                    onChange={(e) => setPersonalizationEnabled(e.target.checked)}
                  />
                }
                label="Enable Personalization"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                Diversity Weight: {diversityWeight}
              </Typography>
              <Slider
                value={diversityWeight}
                onChange={(e, newValue) => setDiversityWeight(newValue as number)}
                min={0}
                max={1}
                step={0.1}
                marks
                valueLabelDisplay="auto"
              />
              <Typography variant="body2" color="text.secondary">
                Higher values promote more diverse recommendations
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary">
                These settings affect how recommendations are generated and personalized for users.
              </Typography>
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

export default Personalization;