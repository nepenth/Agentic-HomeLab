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
  LinearProgress,
  Avatar,
  Divider,
  Tabs,
  Tab,
  InputAdornment,
} from '@mui/material';
import {
  Search,
  Analytics,
  TrendingUp,
  Refresh,
  Settings,
  Assessment,
  QueryStats,
  Insights,
  Timeline,
  BarChart,
  PieChart,
  Speed,
  ThumbUp,
  ThumbDown,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

// Define search analytics types locally for now
interface SearchAnalytics {
  total_searches: number;
  unique_queries: number;
  average_response_time: number;
  success_rate: number;
  popular_queries: Array<{
    query: string;
    count: number;
    success_rate: number;
    average_response_time: number;
  }>;
  search_trends: Array<{
    date: string;
    searches: number;
    successful_searches: number;
  }>;
  [key: string]: any;
}

interface QueryPerformance {
  query: string;
  total_searches: number;
  successful_searches: number;
  average_response_time: number;
  click_through_rate: number;
  user_satisfaction: number;
  optimization_suggestions: string[];
  [key: string]: any;
}

interface SearchInsights {
  insights: Array<{
    type: string;
    title: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
    recommendation: string;
  }>;
  performance_score: number;
  optimization_opportunities: number;
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
      id={`search-tabpanel-${index}`}
      aria-labelledby={`search-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const SearchIntelligence: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [timePeriodDays, setTimePeriodDays] = useState(30);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Search Analytics Query
  const {
    data: searchAnalytics,
    isLoading: analyticsLoading,
    error: analyticsError,
    refetch: refetchAnalytics,
  } = useQuery<SearchAnalytics>({
    queryKey: ['search-analytics', timePeriodDays],
    queryFn: () => apiClient.getAnalyticsDashboard({
      time_period_days: timePeriodDays,
      metrics: ['search'],
    }),
    refetchInterval: autoRefresh ? 300000 : false,
  });

  // Query Performance Query
  const {
    data: queryPerformance,
    isLoading: performanceLoading,
    refetch: refetchPerformance,
  } = useQuery<QueryPerformance>({
    queryKey: ['query-performance', searchQuery, timePeriodDays],
    queryFn: () => apiClient.getAnalyticsDashboard({
      time_period_days: timePeriodDays,
      metrics: ['search'],
    }),
    enabled: !!searchQuery,
    refetchInterval: autoRefresh ? 300000 : false,
  });

  // Search Insights Query
  const {
    data: searchInsights,
    isLoading: insightsLoading,
    refetch: refetchInsights,
  } = useQuery<SearchInsights>({
    queryKey: ['search-insights', timePeriodDays],
    queryFn: () => apiClient.getContentInsights(undefined, {
      time_period_days: timePeriodDays,
    }),
    refetchInterval: autoRefresh ? 300000 : false,
  });

  // Search Event Tracking Mutation
  const trackSearchMutation = useMutation({
    mutationFn: (searchEvent: any) => Promise.resolve(searchEvent), // Placeholder
    onSuccess: () => {
      refetchAnalytics();
      refetchPerformance();
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    refetchAnalytics();
    refetchPerformance();
    refetchInsights();
  };

  const handleTrackSearch = (query: string, resultsCount: number, responseTime: number) => {
    trackSearchMutation.mutate({
      query,
      results_count: resultsCount,
      response_time_ms: responseTime,
      timestamp: new Date().toISOString(),
    });
  };

  const handleQueryAnalysis = () => {
    if (!searchQuery.trim()) return;
    // Trigger query performance analysis
    refetchPerformance();
  };

  if (analyticsError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={handleRefresh}>
              Retry
            </Button>
          }
        >
          Failed to load search analytics data. Please try again.
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
            Search Intelligence Hub
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Advanced search analytics, query optimization, and user behavior insights.
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
            disabled={analyticsLoading}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Controls */}
      <Card elevation={0} sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth>
                <InputLabel>Time Period</InputLabel>
                <Select
                  value={timePeriodDays}
                  label="Time Period"
                  onChange={(e) => setTimePeriodDays(Number(e.target.value))}
                >
                  <MenuItem value={7}>Last 7 days</MenuItem>
                  <MenuItem value={30}>Last 30 days</MenuItem>
                  <MenuItem value={90}>Last 90 days</MenuItem>
                  <MenuItem value={365}>Last year</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Analyze Specific Query"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter a search query to analyze..."
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={handleQueryAnalysis} disabled={!searchQuery.trim()}>
                        <Search />
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Auto Refresh
                </Typography>
                <IconButton
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  color={autoRefresh ? 'primary' : 'default'}
                >
                  <Refresh />
                </IconButton>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      {searchAnalytics && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                  {searchAnalytics.total_searches || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Searches
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                  {searchAnalytics.unique_queries || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Unique Queries
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                  {(searchAnalytics.average_response_time || 0).toFixed(0)}ms
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Response Time
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                  {searchAnalytics.success_rate ? `${(searchAnalytics.success_rate * 100).toFixed(1)}%` : '0%'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Success Rate
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="search tabs">
            <Tab icon={<Analytics />} label="Analytics" />
            <Tab icon={<QueryStats />} label="Query Performance" />
            <Tab icon={<Insights />} label="Insights" />
            <Tab icon={<Timeline />} label="Trends" />
          </Tabs>
        </CardContent>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={0}>
          {analyticsLoading ? (
            <Box>
              <Grid container spacing={3}>
                {[...Array(6)].map((_, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : searchAnalytics ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Search Performance Overview
                    </Typography>
                    <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        Search analytics chart would be implemented here
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Popular Queries
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {searchAnalytics.popular_queries?.slice(0, 5).map((query: any, index: number) => (
                        <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ flex: 1 }}>
                            {query.query}
                          </Typography>
                          <Chip
                            label={`${query.count} searches`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      )) || (
                        <Typography variant="body2" color="text.secondary">
                          No popular queries data available
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No search analytics data available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Query Performance Tab */}
        <TabPanel value={tabValue} index={1}>
          {performanceLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : queryPerformance ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                      Query Performance Analysis: "{searchQuery}"
                    </Typography>

                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                              Performance Metrics
                            </Typography>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="body2">Total Searches:</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {queryPerformance.total_searches || 0}
                                </Typography>
                              </Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="body2">Success Rate:</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {queryPerformance.successful_searches && queryPerformance.total_searches
                                    ? `${((queryPerformance.successful_searches / queryPerformance.total_searches) * 100).toFixed(1)}%`
                                    : '0%'
                                  }
                                </Typography>
                              </Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="body2">Avg Response Time:</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {(queryPerformance.average_response_time || 0).toFixed(0)}ms
                                </Typography>
                              </Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="body2">Click-through Rate:</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {queryPerformance.click_through_rate ? `${(queryPerformance.click_through_rate * 100).toFixed(1)}%` : '0%'}
                                </Typography>
                              </Box>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={6}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                              Optimization Suggestions
                            </Typography>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                              {queryPerformance.optimization_suggestions?.map((suggestion: string, index: number) => (
                                <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Assessment sx={{ fontSize: 16, color: 'primary.main' }} />
                                  <Typography variant="body2">{suggestion}</Typography>
                                </Box>
                              )) || (
                                <Typography variant="body2" color="text.secondary">
                                  No optimization suggestions available
                                </Typography>
                              )}
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                Enter a search query above to analyze its performance
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Insights Tab */}
        <TabPanel value={tabValue} index={2}>
          {insightsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : searchInsights ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                      Search Intelligence Insights
                    </Typography>

                    <Grid container spacing={2}>
                      {searchInsights.insights?.map((insight: any, index: number) => (
                        <Grid item xs={12} md={6} key={index}>
                          <Card variant="outlined">
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <Insights sx={{ mr: 1, color: 'primary.main' }} />
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                  {insight.title}
                                </Typography>
                              </Box>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                {insight.description}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                <Chip
                                  label={`Impact: ${insight.impact}`}
                                  size="small"
                                  color={
                                    insight.impact === 'high' ? 'error' :
                                    insight.impact === 'medium' ? 'warning' : 'success'
                                  }
                                />
                                <Chip
                                  label={`Type: ${insight.type}`}
                                  size="small"
                                  variant="outlined"
                                />
                              </Box>
                              {insight.recommendation && (
                                <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic' }}>
                                  💡 {insight.recommendation}
                                </Typography>
                              )}
                            </CardContent>
                          </Card>
                        </Grid>
                      )) || (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary" align="center">
                            No search insights available
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
                No search insights data available
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
                    Search Trends Over Time
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Search trends visualization would be implemented here
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
            <Settings sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Search Intelligence Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure search analytics and optimization settings.
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Analytics Granularity</InputLabel>
                <Select defaultValue="hourly">
                  <MenuItem value="hourly">Hourly</MenuItem>
                  <MenuItem value="daily">Daily</MenuItem>
                  <MenuItem value="weekly">Weekly</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Performance Threshold</InputLabel>
                <Select defaultValue="medium">
                  <MenuItem value="low">Low (2s)</MenuItem>
                  <MenuItem value="medium">Medium (1s)</MenuItem>
                  <MenuItem value="high">High (500ms)</MenuItem>
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

export default SearchIntelligence;