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
  Slider,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Timeline,
  Refresh,
  Settings,
  ShowChart,
  Assessment,
  Analytics,
  DateRange,
  FilterList,
  Warning,
  CheckCircle,
  Info,
  Error,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

// Define trend types locally for now
interface TrendResult {
  metric: string;
  trend_type: 'emerging' | 'declining' | 'seasonal' | 'stable';
  direction: 'up' | 'down' | 'stable';
  confidence: number;
  impact: 'high' | 'medium' | 'low';
  change_percentage: number;
  time_period: string;
  description: string;
}

interface ForecastResult {
  metric: string;
  forecast_values: Array<{
    timestamp: string;
    value: number;
    confidence_interval: [number, number];
  }>;
  accuracy_score: number;
  trend_direction: string;
  seasonality_detected: boolean;
}

interface AnomalyResult {
  metric: string;
  anomalies: Array<{
    timestamp: string;
    value: number;
    expected_value: number;
    deviation: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
  }>;
  total_anomalies: number;
  detection_accuracy: number;
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
      id={`trends-tabpanel-${index}`}
      aria-labelledby={`trends-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Trends: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [timePeriodDays, setTimePeriodDays] = useState(30);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['usage', 'performance', 'content']);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [anomalyThreshold, setAnomalyThreshold] = useState(0.8);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Trend Analysis Query
  const {
    data: trendAnalysis,
    isLoading: trendsLoading,
    error: trendsError,
    refetch: refetchTrends,
  } = useQuery<TrendResult[]>({
    queryKey: ['trend-analysis', timePeriodDays, selectedMetrics],
    queryFn: () => apiClient.analyzeTrends({
      time_period_days: timePeriodDays,
      metrics: selectedMetrics,
      trend_types: ['emerging', 'declining', 'seasonal'],
    }),
    refetchInterval: autoRefresh ? 300000 : false, // Auto-refresh every 5 minutes if enabled
  });

  // Forecasting Query - Using existing trend analysis for now
  const {
    data: forecastingData,
    isLoading: forecastingLoading,
    refetch: refetchForecasting,
  } = useQuery<TrendResult[]>({
    queryKey: ['forecasting', timePeriodDays, forecastHorizon, selectedMetrics],
    queryFn: () => apiClient.analyzeTrends({
      time_period_days: timePeriodDays,
      metrics: selectedMetrics,
      trend_types: ['emerging', 'declining', 'seasonal'],
    }),
    refetchInterval: autoRefresh ? 300000 : false,
  });

  // Anomaly Detection Query - Using existing trend analysis for now
  const {
    data: anomalyData,
    isLoading: anomalyLoading,
    refetch: refetchAnomalies,
  } = useQuery<TrendResult[]>({
    queryKey: ['anomaly-detection', timePeriodDays, anomalyThreshold, selectedMetrics],
    queryFn: () => apiClient.analyzeTrends({
      time_period_days: timePeriodDays,
      metrics: selectedMetrics,
      trend_types: ['emerging', 'declining', 'seasonal'],
    }),
    refetchInterval: autoRefresh ? 300000 : false,
  });

  // Alert Configuration Mutation - Placeholder for now
  const alertConfigMutation = useMutation({
    mutationFn: (config: any) => Promise.resolve(config), // Placeholder
    onSuccess: () => {
      // Handle success
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    refetchTrends();
    refetchForecasting();
    refetchAnomalies();
  };

  const handleConfigureAlert = (metric: string, threshold: number, trendType: string) => {
    alertConfigMutation.mutate({
      metric,
      threshold,
      trend_type: trendType,
      notification_channels: ['email', 'dashboard'],
    });
  };

  const getTrendIcon = (trendType: string) => {
    switch (trendType) {
      case 'emerging':
        return <TrendingUp color="success" />;
      case 'declining':
        return <TrendingDown color="error" />;
      case 'seasonal':
        return <Timeline color="info" />;
      default:
        return <ShowChart color="action" />;
    }
  };

  const getTrendColor = (trendType: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (trendType) {
      case 'emerging':
        return 'success';
      case 'declining':
        return 'error';
      case 'seasonal':
        return 'info';
      default:
        return 'default';
    }
  };

  const getSeverityColor = (severity: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  if (trendsError) {
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
          Failed to load trend analysis data. Please try again.
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
            Trend Detection & Forecasting
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Advanced trend analysis, predictive forecasting, and anomaly detection for intelligent insights.
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
            disabled={trendsLoading}
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
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Forecast Horizon (days)"
                type="number"
                value={forecastHorizon}
                onChange={(e) => setForecastHorizon(Number(e.target.value))}
                inputProps={{ min: 1, max: 90 }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                  />
                }
                label="Auto Refresh"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="trends tabs">
            <Tab icon={<TrendingUp />} label="Trend Analysis" />
            <Tab icon={<Timeline />} label="Forecasting" />
            <Tab icon={<Warning />} label="Anomaly Detection" />
            <Tab icon={<Analytics />} label="Insights" />
          </Tabs>
        </CardContent>

        {/* Trend Analysis Tab */}
        <TabPanel value={tabValue} index={0}>
          {trendsLoading ? (
            <Box>
              <Grid container spacing={3}>
                {[...Array(6)].map((_, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : trendAnalysis ? (
            <Grid container spacing={3}>
              {trendAnalysis.map((trend: TrendResult, index: number) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Card elevation={1} sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        {getTrendIcon(trend.trend_type)}
                        <Box sx={{ ml: 2, flex: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {trend.metric}
                          </Typography>
                          <Chip
                            label={trend.trend_type}
                            size="small"
                            color={getTrendColor(trend.trend_type)}
                            sx={{ mt: 0.5 }}
                          />
                        </Box>
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {trend.description || `${trend.direction} trend detected`}
                      </Typography>

                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                        <Chip
                          label={`Change: ${trend.change_percentage?.toFixed(1) || 0}%`}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          label={`Confidence: ${(trend.confidence * 100).toFixed(0)}%`}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          label={`Impact: ${trend.impact}`}
                          size="small"
                          color={
                            trend.impact === 'high' ? 'error' :
                            trend.impact === 'medium' ? 'warning' : 'success'
                          }
                        />
                      </Box>

                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleConfigureAlert(trend.metric, 0.8, trend.trend_type)}
                        disabled={alertConfigMutation.isPending}
                      >
                        Configure Alert
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
              )) || (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    No trend data available for the selected period.
                  </Typography>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No trend analysis data available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Forecasting Tab */}
        <TabPanel value={tabValue} index={1}>
          {forecastingLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : forecastingData ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                      Predictive Forecasting Results
                    </Typography>

                    <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        Forecasting visualization would be implemented here
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No forecasting data available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Anomaly Detection Tab */}
        <TabPanel value={tabValue} index={2}>
          {anomalyLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : anomalyData ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                      Anomaly Detection Results
                    </Typography>

                    <TableContainer component={Paper} elevation={0}>
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell>Metric</TableCell>
                            <TableCell>Timestamp</TableCell>
                            <TableCell>Actual Value</TableCell>
                            <TableCell>Expected Value</TableCell>
                            <TableCell>Deviation</TableCell>
                            <TableCell>Severity</TableCell>
                            <TableCell>Description</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {anomalyData.anomalies?.map((anomaly: any, index: number) => (
                            <TableRow key={index} hover>
                              <TableCell>{anomaly.metric}</TableCell>
                              <TableCell>{new Date(anomaly.timestamp).toLocaleString()}</TableCell>
                              <TableCell>{anomaly.value?.toFixed(2)}</TableCell>
                              <TableCell>{anomaly.expected_value?.toFixed(2)}</TableCell>
                              <TableCell>{(anomaly.deviation * 100)?.toFixed(1)}%</TableCell>
                              <TableCell>
                                <Chip
                                  label={anomaly.severity}
                                  size="small"
                                  color={getSeverityColor(anomaly.severity)}
                                />
                              </TableCell>
                              <TableCell>{anomaly.description}</TableCell>
                            </TableRow>
                          )) || (
                            <TableRow>
                              <TableCell colSpan={7} align="center">
                                <Typography variant="body2" color="text.secondary">
                                  No anomalies detected in the selected period.
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
                No anomaly detection data available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Insights Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Trend Analysis Insights
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                            Key Findings
                          </Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                            <Typography variant="body2">
                              • Emerging trends detected in user engagement
                            </Typography>
                            <Typography variant="body2">
                              • Seasonal patterns identified in content consumption
                            </Typography>
                            <Typography variant="body2">
                              • Performance metrics showing steady improvement
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                            Recommendations
                          </Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                            <Typography variant="body2">
                              • Monitor emerging trends for strategic planning
                            </Typography>
                            <Typography variant="body2">
                              • Optimize content delivery during peak seasons
                            </Typography>
                            <Typography variant="body2">
                              • Set up alerts for significant trend changes
                            </Typography>
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
            <Typography variant="h6">Trend Analysis Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                Anomaly Detection Threshold: {anomalyThreshold}
              </Typography>
              <Slider
                value={anomalyThreshold}
                onChange={(e, newValue) => setAnomalyThreshold(newValue as number)}
                min={0.1}
                max={0.99}
                step={0.05}
                marks
                valueLabelDisplay="auto"
              />
              <Typography variant="body2" color="text.secondary">
                Higher values detect fewer but more significant anomalies
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                  />
                }
                label="Enable Auto Refresh (every 5 minutes)"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary">
                These settings affect trend detection sensitivity, forecasting accuracy, and anomaly detection thresholds.
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

export default Trends;