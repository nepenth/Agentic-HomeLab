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
} from '@mui/material';
import {
  Assessment,
  TrendingUp,
  Download,
  Refresh,
  Timeline,
  BarChart,
  PieChart,
  ShowChart,
  DateRange,
  FilterList,
  Settings,
  Info,
  Warning,
  Error,
  CheckCircle,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { AnalyticsCapabilities } from '../types';

// Define analytics types locally for now
interface AnalyticsDashboard {
  total_requests: number;
  success_rate: number;
  average_response_time_ms: number;
  active_users: number;
  [key: string]: any;
}

interface ContentInsights {
  insights: Array<{
    title: string;
    description: string;
    impact: string;
    confidence: number;
  }>;
  [key: string]: any;
}

interface TrendAnalysis {
  trends: Array<{
    metric: string;
    trend_type: string;
    direction: string;
    confidence: number;
    impact: string;
  }>;
  [key: string]: any;
}

interface AnalyticsHealth {
  status: string;
  message: string;
  active_services: number;
  data_freshness: string;
  last_updated: string;
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
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Analytics: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [timePeriodDays, setTimePeriodDays] = useState(30);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['usage', 'performance', 'content']);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportFormat, setExportFormat] = useState('pdf');
  const [startDate, setStartDate] = useState<Date | null>(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));
  const [endDate, setEndDate] = useState<Date | null>(new Date());

  // Analytics Dashboard Query
  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError,
    refetch: refetchDashboard,
  } = useQuery<AnalyticsDashboard>({
    queryKey: ['analytics-dashboard', timePeriodDays, selectedMetrics],
    queryFn: () => apiClient.getAnalyticsDashboard({
      time_period_days: timePeriodDays,
      metrics: selectedMetrics,
    }),
    refetchInterval: 300000, // Refetch every 5 minutes
  });

  // Content Insights Query
  const {
    data: contentInsights,
    isLoading: insightsLoading,
    refetch: refetchInsights,
  } = useQuery<ContentInsights>({
    queryKey: ['content-insights', timePeriodDays],
    queryFn: () => apiClient.getContentInsights(undefined, {
      time_period_days: timePeriodDays,
    }),
    refetchInterval: 300000,
  });

  // Trend Analysis Query
  const {
    data: trendAnalysis,
    isLoading: trendsLoading,
    refetch: refetchTrends,
  } = useQuery<TrendAnalysis>({
    queryKey: ['trend-analysis', timePeriodDays],
    queryFn: () => apiClient.analyzeTrends({
      time_period_days: timePeriodDays,
      metrics: selectedMetrics,
      trend_types: ['emerging', 'declining', 'seasonal'],
    }),
    refetchInterval: 300000,
  });

  // Analytics Health Query
  const {
    data: analyticsHealth,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useQuery<AnalyticsHealth>({
    queryKey: ['analytics-health'],
    queryFn: () => apiClient.getAnalyticsHealth(),
    refetchInterval: 60000, // Refetch every minute
  });

  // Analytics Capabilities Query
  const {
    data: capabilities,
    isLoading: capabilitiesLoading,
  } = useQuery<AnalyticsCapabilities>({
    queryKey: ['analytics-capabilities'],
    queryFn: () => apiClient.getAnalyticsCapabilities(),
  });

  // Export Analytics Mutation
  const exportAnalyticsMutation = useMutation({
    mutationFn: (exportParams: any) => apiClient.exportAnalyticsReport(exportParams),
    onSuccess: (data) => {
      // Handle file download
      const url = window.URL.createObjectURL(new Blob([data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analytics-report.${exportFormat}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setShowExportDialog(false);
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    refetchDashboard();
    refetchInsights();
    refetchTrends();
    refetchHealth();
  };

  const handleExport = () => {
    exportAnalyticsMutation.mutate({
      format: exportFormat,
      time_period_days: timePeriodDays,
      include_charts: true,
    });
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle color="success" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'error':
        return <Error color="error" />;
      default:
        return <Info color="info" />;
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };

  if (dashboardError) {
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
          Failed to load analytics data. Please try again.
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
              Analytics Command Center
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Comprehensive analytics, insights, and performance monitoring for your AI platform.
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={() => setShowExportDialog(true)}
              disabled={dashboardLoading}
            >
              Export Report
            </Button>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={handleRefresh}
              disabled={dashboardLoading}
            >
              Refresh
            </Button>
          </Box>
        </Box>

        {/* Controls */}
        <Card elevation={0} sx={{ mb: 4 }}>
          <CardContent>
            <Grid container spacing={3} alignItems="center">
              <Grid item xs={12} sm={6} md={3}>
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
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Start Date"
                  type="date"
                  value={startDate ? startDate.toISOString().split('T')[0] : ''}
                  onChange={(e) => setStartDate(e.target.value ? new Date(e.target.value) : null)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="End Date"
                  type="date"
                  value={endDate ? endDate.toISOString().split('T')[0] : ''}
                  onChange={(e) => setEndDate(e.target.value ? new Date(e.target.value) : null)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Metrics</InputLabel>
                  <Select
                    multiple
                    value={selectedMetrics}
                    label="Metrics"
                    onChange={(e) => setSelectedMetrics(e.target.value as string[])}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    <MenuItem value="usage">Usage</MenuItem>
                    <MenuItem value="performance">Performance</MenuItem>
                    <MenuItem value="content">Content</MenuItem>
                    <MenuItem value="user">User</MenuItem>
                    <MenuItem value="system">System</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Health Status */}
        {analyticsHealth && (
          <Card elevation={0} sx={{ mb: 4 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                {getHealthIcon(analyticsHealth.status)}
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  System Health: {analyticsHealth.status.toUpperCase()}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {analyticsHealth.message}
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Chip
                  label={`Active Services: ${analyticsHealth.active_services || 0}`}
                  variant="outlined"
                />
                <Chip
                  label={`Data Freshness: ${analyticsHealth.data_freshness || 'Unknown'}`}
                  variant="outlined"
                />
                <Chip
                  label={`Last Updated: ${new Date(analyticsHealth.last_updated).toLocaleString()}`}
                  variant="outlined"
                />
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Main Content Tabs */}
        <Card elevation={0}>
          <CardContent sx={{ pb: 0 }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="analytics tabs">
              <Tab icon={<BarChart />} label="Dashboard" />
              <Tab icon={<TrendingUp />} label="Trends" />
              <Tab icon={<Assessment />} label="Insights" />
              <Tab icon={<Timeline />} label="Performance" />
            </Tabs>
          </CardContent>

          {/* Dashboard Tab */}
          <TabPanel value={tabValue} index={0}>
            {dashboardLoading ? (
              <Box>
                <Grid container spacing={3}>
                  {[...Array(8)].map((_, index) => (
                    <Grid item xs={12} sm={6} md={3} key={index}>
                      <Skeleton variant="rectangular" width="100%" height={120} sx={{ borderRadius: 1 }} />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            ) : dashboardData ? (
              <Grid container spacing={3}>
                {/* Key Metrics */}
                <Grid item xs={12} sm={6} md={3}>
                  <Card elevation={1}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                        {dashboardData.total_requests || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Requests
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card elevation={1}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                        {dashboardData.success_rate ? `${(dashboardData.success_rate * 100).toFixed(1)}%` : '0%'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Success Rate
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card elevation={1}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                        {dashboardData.average_response_time_ms || 0}ms
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
                        {dashboardData.active_users || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Active Users
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Charts and Visualizations */}
                <Grid item xs={12} md={8}>
                  <Card elevation={1}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Usage Trends
                      </Typography>
                      <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                          Chart visualization would be implemented here
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Card elevation={1}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                        Top Content Types
                      </Typography>
                      <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Typography variant="body2" color="text.secondary">
                          Pie chart would be implemented here
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            ) : (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body1" color="text.secondary">
                  No dashboard data available
                </Typography>
              </Box>
            )}
          </TabPanel>

          {/* Trends Tab */}
          <TabPanel value={tabValue} index={1}>
            {trendsLoading ? (
              <Box>
                <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
              </Box>
            ) : trendAnalysis ? (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Card elevation={1}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                        Trend Analysis Results
                      </Typography>

                      <TableContainer component={Paper} elevation={0}>
                        <Table>
                          <TableHead>
                            <TableRow>
                              <TableCell>Metric</TableCell>
                              <TableCell>Trend Type</TableCell>
                              <TableCell>Direction</TableCell>
                              <TableCell>Confidence</TableCell>
                              <TableCell>Impact</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {trendAnalysis.trends?.map((trend, index) => (
                              <TableRow key={index} hover>
                                <TableCell>{trend.metric}</TableCell>
                                <TableCell>
                                  <Chip
                                    label={trend.trend_type}
                                    size="small"
                                    color={
                                      trend.trend_type === 'emerging' ? 'success' :
                                      trend.trend_type === 'declining' ? 'error' : 'warning'
                                    }
                                  />
                                </TableCell>
                                <TableCell>{trend.direction}</TableCell>
                                <TableCell>{(trend.confidence * 100).toFixed(1)}%</TableCell>
                                <TableCell>{trend.impact}</TableCell>
                              </TableRow>
                            )) || (
                              <TableRow>
                                <TableCell colSpan={5} align="center">
                                  <Typography variant="body2" color="text.secondary">
                                    No trend data available
                                  </Typography>
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            ) : (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body1" color="text.secondary">
                  No trend analysis data available
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
            ) : contentInsights ? (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Card elevation={1}>
                    <CardContent>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                        Content Performance Insights
                      </Typography>

                      <Grid container spacing={2}>
                        {contentInsights.insights?.map((insight, index) => (
                          <Grid item xs={12} md={6} key={index}>
                            <Card variant="outlined">
                              <CardContent>
                                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                                  {insight.title}
                                </Typography>
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
                                    label={`Confidence: ${(insight.confidence * 100).toFixed(0)}%`}
                                    size="small"
                                    variant="outlined"
                                  />
                                </Box>
                              </CardContent>
                            </Card>
                          </Grid>
                        )) || (
                          <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary" align="center">
                              No insights data available
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
                  No content insights data available
                </Typography>
              </Box>
            )}
          </TabPanel>

          {/* Performance Tab */}
          <TabPanel value={tabValue} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                      System Performance Metrics
                    </Typography>

                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                              Response Times
                            </Typography>
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                Average: {dashboardData?.average_response_time_ms || 0}ms
                              </Typography>
                              <LinearProgress
                                variant="determinate"
                                value={Math.min((dashboardData?.average_response_time_ms || 0) / 10, 100)}
                                sx={{ height: 8, borderRadius: 4 }}
                              />
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={6}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                              Success Rate
                            </Typography>
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                Rate: {dashboardData?.success_rate ? `${(dashboardData.success_rate * 100).toFixed(1)}%` : '0%'}
                              </Typography>
                              <LinearProgress
                                variant="determinate"
                                value={(dashboardData?.success_rate || 0) * 100}
                                sx={{ height: 8, borderRadius: 4 }}
                                color="success"
                              />
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </TabPanel>
        </Card>

        {/* Export Dialog */}
        <Dialog
          open={showExportDialog}
          onClose={() => setShowExportDialog(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Download sx={{ color: 'primary.main' }} />
              <Typography variant="h6">Export Analytics Report</Typography>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Format</InputLabel>
                  <Select
                    value={exportFormat}
                    label="Format"
                    onChange={(e) => setExportFormat(e.target.value)}
                  >
                    <MenuItem value="pdf">PDF Report</MenuItem>
                    <MenuItem value="csv">CSV Data</MenuItem>
                    <MenuItem value="json">JSON Data</MenuItem>
                    <MenuItem value="xlsx">Excel Spreadsheet</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  This will export the current analytics data including charts, metrics, and insights for the selected time period.
                </Typography>
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowExportDialog(false)}>Cancel</Button>
            <Button
              onClick={handleExport}
              variant="contained"
              disabled={exportAnalyticsMutation.isPending}
              startIcon={<Download />}
            >
              {exportAnalyticsMutation.isPending ? 'Exporting...' : 'Export Report'}
            </Button>
          </DialogActions>
        </Dialog>
    </Box>
  );
};

export default Analytics;