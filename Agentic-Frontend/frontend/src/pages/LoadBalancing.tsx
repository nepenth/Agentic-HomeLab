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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  CircularProgress,
} from '@mui/material';
import {
  Storage,
  Add,
  Delete,
  Edit,
  Refresh,
  PlayArrow,
  Stop,
  Assessment,
  ExpandMore,
  CheckCircle,
  Error,
  Warning,
  Info,
  TrendingUp,
  Speed,
  Memory,
  AccessTime,
  CallReceived,
  CallMade,
  Http,
  Security,
  Route,
  Transform,
  Send,
  Notifications,
  NotificationsOff,
  CloudQueue,
  Balance,
  Scale,
  NetworkCheck,
  Timeline,
  Settings,
  Tune,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import webSocketService from '../services/websocket';

// Define load balancing types locally for now
interface BackendService {
  id: string;
  name: string;
  url: string;
  supported_types: string[];
  max_concurrent_requests: number;
  health_status: 'healthy' | 'unhealthy' | 'unknown';
  load_factor: number;
  metrics: {
    active_requests: number;
    total_requests: number;
    success_rate: number;
    average_response_time: number;
    error_rate: number;
    uptime_percentage: number;
  };
  last_health_check: string;
}

interface LoadBalancerConfig {
  id: string;
  name: string;
  algorithm: 'round_robin' | 'least_connections' | 'weighted_round_robin' | 'ip_hash';
  health_check_interval: number;
  max_failures: number;
  retry_timeout: number;
  enabled: boolean;
  backend_services: string[];
}

interface LoadDistribution {
  total_requests: number;
  requests_per_backend: Record<string, number>;
  response_time_distribution: Record<string, number>;
  error_distribution: Record<string, number>;
  load_balance_efficiency: number;
}

interface LoadBalancingStats {
  total_backends: number;
  healthy_backends: number;
  total_requests: number;
  average_response_time: number;
  error_rate: number;
  load_balance_efficiency: number;
  uptime_percentage: number;
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
      id={`loadbalancing-tabpanel-${index}`}
      aria-labelledby={`loadbalancing-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const LoadBalancing: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [showBackendDialog, setShowBackendDialog] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [selectedBackend, setSelectedBackend] = useState<BackendService | null>(null);
  const [selectedConfig, setSelectedConfig] = useState<LoadBalancerConfig | null>(null);

  // Load Balancing Stats Query
  const {
    data: loadBalancingStats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useQuery<LoadBalancingStats>({
    queryKey: ['load-balancing-stats'],
    queryFn: () => apiClient.getLoadBalancerStats(),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Backend Services Query
  const {
    data: backendServices,
    isLoading: backendsLoading,
    error: backendsError,
    refetch: refetchBackends,
  } = useQuery<BackendService[]>({
    queryKey: ['backend-services'],
    queryFn: () => apiClient.getBackendServices(),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Load Balancer Configurations Query
  const {
    data: loadBalancerConfigs,
    isLoading: configsLoading,
    refetch: refetchConfigs,
  } = useQuery<LoadBalancerConfig[]>({
    queryKey: ['load-balancer-configs'],
    queryFn: async () => {
      // Note: Load balancer configurations endpoint may need to be implemented
      // For now, return empty array - configurations would be managed via backend
      return [];
    },
  });

  // Load Distribution Query
  const {
    data: loadDistribution,
    isLoading: distributionLoading,
    error: distributionError,
    refetch: refetchDistribution,
  } = useQuery<LoadDistribution>({
    queryKey: ['load-distribution'],
    queryFn: async () => {
      // Note: Load distribution endpoint may need to be implemented
      // For now, derive from backend services data
      const backends = await apiClient.getBackendServices();
      const totalRequests = backends.reduce((sum: number, backend: BackendService) => sum + backend.metrics.total_requests, 0);

      const requestsPerBackend: Record<string, number> = {};
      const responseTimeDistribution: Record<string, number> = {};
      const errorDistribution: Record<string, number> = {};

      backends.forEach((backend: BackendService) => {
        requestsPerBackend[backend.id] = backend.metrics.total_requests;
        responseTimeDistribution[backend.id] = backend.metrics.average_response_time;
        errorDistribution[backend.id] = backend.metrics.error_rate;
      });

      // Calculate load balance efficiency based on request distribution variance
      const requestValues = Object.values(requestsPerBackend);
      const mean = totalRequests / requestValues.length;
      const variance = requestValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / requestValues.length;
      const stdDev = Math.sqrt(variance);
      const efficiency = Math.max(0, 1 - (stdDev / mean)); // Higher efficiency = more balanced

      return {
        total_requests: totalRequests,
        requests_per_backend: requestsPerBackend,
        response_time_distribution: responseTimeDistribution,
        error_distribution: errorDistribution,
        load_balance_efficiency: efficiency
      };
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Mutations
  const registerBackendMutation = useMutation({
    mutationFn: (backend: Partial<BackendService>) => apiClient.registerBackendService({
      id: backend.id || `backend_${Date.now()}`,
      url: backend.url!,
      supported_request_types: backend.supported_types || [],
      max_concurrent_requests: backend.max_concurrent_requests || 10,
      health_check_url: `${backend.url}/health`
    }),
    onSuccess: () => {
      setShowBackendDialog(false);
      refetchBackends();
      refetchStats();
    },
  });

  const updateConfigMutation = useMutation({
    mutationFn: (config: Partial<LoadBalancerConfig>) => {
      // Note: Load balancer configuration endpoint may need to be implemented
      // For now, return placeholder - configurations would be managed via backend
      return Promise.resolve(config);
    },
    onSuccess: () => {
      setShowConfigDialog(false);
      refetchConfigs();
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    refetchStats();
    refetchBackends();
    refetchConfigs();
    refetchDistribution();
  };

  // WebSocket subscription for real-time load balancing metrics
  React.useEffect(() => {
    const unsubscribe = webSocketService.subscribeToLoadBalancingMetrics(
      (metrics) => {
        console.log('Load balancing metrics received:', metrics);

        // Refresh relevant data based on metric type
        if (metrics.type === 'backend_metrics') {
          refetchBackends();
          refetchStats();
        } else if (metrics.type === 'load_distribution') {
          refetchDistribution();
          refetchStats();
        } else if (metrics.type === 'health_check') {
          refetchBackends();
          refetchStats();
        } else {
          // Refresh all data for general metrics
          handleRefresh();
        }
      }
    );

    return unsubscribe;
  }, [refetchStats, refetchBackends, refetchConfigs, refetchDistribution]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'unhealthy':
        return 'error';
      case 'unknown':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle />;
      case 'unhealthy':
        return <Error />;
      case 'unknown':
        return <Warning />;
      default:
        return <Info />;
    }
  };

  const getLoadFactorColor = (factor: number) => {
    if (factor >= 0.8) return 'error';
    if (factor >= 0.6) return 'warning';
    return 'success';
  };

  const getAlgorithmLabel = (algorithm: string) => {
    switch (algorithm) {
      case 'round_robin':
        return 'Round Robin';
      case 'least_connections':
        return 'Least Connections';
      case 'weighted_round_robin':
        return 'Weighted Round Robin';
      case 'ip_hash':
        return 'IP Hash';
      default:
        return algorithm;
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Load Balancing Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor and manage backend service distribution, health, and performance optimization.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowBackendDialog(true)}
          >
            Register Backend
          </Button>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => setShowConfigDialog(true)}
          >
            Configure LB
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
      {statsError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load load balancing statistics: {statsError.message}
          <Button size="small" onClick={() => refetchStats()} sx={{ ml: 2 }}>
            Retry
          </Button>
        </Alert>
      )}
      {loadBalancingStats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                  {loadBalancingStats.total_backends}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Backends
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                  {loadBalancingStats.healthy_backends}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Healthy Backends
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                  {(loadBalancingStats.load_balance_efficiency * 100).toFixed(1)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Load Efficiency
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                  {loadBalancingStats.uptime_percentage.toFixed(1)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Uptime
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="loadbalancing tabs">
            <Tab icon={<Storage />} label="Backend Services" />
            <Tab icon={<Balance />} label="Load Distribution" />
            <Tab icon={<Settings />} label="Configuration" />
            <Tab icon={<Assessment />} label="Analytics" />
          </Tabs>
        </CardContent>

        {/* Backend Services Tab */}
        <TabPanel value={tabValue} index={0}>
          {backendsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : backendServices ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Backend Services ({backendServices.length})
                </Typography>
              </Grid>

              {backendServices.map((backend) => (
                <Grid item xs={12} md={6} lg={4} key={backend.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                            {backend.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            {backend.url}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                            {backend.supported_types.map((type) => (
                              <Chip key={type} label={type} size="small" variant="outlined" />
                            ))}
                          </Box>
                        </Box>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                          <Chip
                            label={backend.health_status}
                            color={getStatusColor(backend.health_status) as any}
                            icon={getStatusIcon(backend.health_status)}
                          />
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <IconButton size="small" onClick={() => setSelectedBackend(backend)}>
                              <Edit />
                            </IconButton>
                            <IconButton size="small" color="error">
                              <Delete />
                            </IconButton>
                          </Box>
                        </Box>
                      </Box>

                      {/* Load Factor */}
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            Load Factor
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {(backend.load_factor * 100).toFixed(0)}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={backend.load_factor * 100}
                          color={getLoadFactorColor(backend.load_factor) as any}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                      </Box>

                      {/* Performance Metrics */}
                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Performance Metrics:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Chip
                            label={`${backend.metrics.active_requests} active`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${(backend.metrics.success_rate * 100).toFixed(1)}% success`}
                            size="small"
                            variant="outlined"
                            color="success"
                          />
                          <Chip
                            label={`${backend.metrics.average_response_time}ms avg`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${backend.metrics.uptime_percentage.toFixed(1)}% uptime`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {backendServices.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <Storage sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No backend services registered
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Register backend services to enable load balancing
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No backend services available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Load Distribution Tab */}
        <TabPanel value={tabValue} index={1}>
          {distributionLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : loadDistribution ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Load Distribution Analysis
                </Typography>
              </Grid>

              {/* Distribution Overview */}
              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Request Distribution
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {Object.entries(loadDistribution.requests_per_backend).map(([backendId, requests]) => {
                        const percentage = (requests / loadDistribution.total_requests) * 100;
                        return (
                          <Box key={backendId}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                              <Typography variant="body2">{backendId}</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {requests} ({percentage.toFixed(1)}%)
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={percentage}
                              sx={{ height: 8, borderRadius: 4 }}
                            />
                          </Box>
                        );
                      })}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              {/* Performance Comparison */}
              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Performance Comparison
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Backend</TableCell>
                            <TableCell align="right">Response Time</TableCell>
                            <TableCell align="right">Error Rate</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.entries(loadDistribution.response_time_distribution).map(([backendId, responseTime]) => {
                            const errorRate = loadDistribution.error_distribution[backendId] || 0;
                            return (
                              <TableRow key={backendId}>
                                <TableCell>{backendId}</TableCell>
                                <TableCell align="right">{responseTime}ms</TableCell>
                                <TableCell align="right">
                                  <Chip
                                    label={`${(errorRate * 100).toFixed(1)}%`}
                                    size="small"
                                    color={errorRate > 0.1 ? 'error' : 'success'}
                                    variant="outlined"
                                  />
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Grid>

              {/* Load Balance Efficiency */}
              <Grid item xs={12}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Load Balance Efficiency: {(loadDistribution.load_balance_efficiency * 100).toFixed(1)}%
                    </Typography>
                    <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <CircularProgress
                        variant="determinate"
                        value={loadDistribution.load_balance_efficiency * 100}
                        size={120}
                        thickness={8}
                        sx={{ color: loadDistribution.load_balance_efficiency > 0.8 ? 'success.main' : 'warning.main' }}
                      />
                      <Box sx={{ position: 'absolute', textAlign: 'center' }}>
                        <Typography variant="h4" sx={{ fontWeight: 700 }}>
                          {(loadDistribution.load_balance_efficiency * 100).toFixed(0)}%
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Efficiency
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No load distribution data available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Configuration Tab */}
        <TabPanel value={tabValue} index={2}>
          {configsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : loadBalancerConfigs ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Load Balancer Configurations ({loadBalancerConfigs.length})
                </Typography>
              </Grid>

              {loadBalancerConfigs.map((config) => (
                <Grid item xs={12} md={6} key={config.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                            {config.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Algorithm: {getAlgorithmLabel(config.algorithm)}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                            <Chip
                              label={`${config.health_check_interval}s health check`}
                              size="small"
                              variant="outlined"
                            />
                            <Chip
                              label={`Max ${config.max_failures} failures`}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            Backend Services: {config.backend_services.length}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={config.enabled}
                                size="small"
                              />
                            }
                            label=""
                          />
                          <IconButton size="small" onClick={() => setSelectedConfig(config)}>
                            <Edit />
                          </IconButton>
                          <IconButton size="small" color="error">
                            <Delete />
                          </IconButton>
                        </Box>
                      </Box>

                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Configured Backends:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          {config.backend_services.map((backendId) => (
                            <Chip key={backendId} label={backendId} size="small" variant="outlined" />
                          ))}
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {loadBalancerConfigs.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <Settings sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No load balancer configurations
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Create configurations to manage backend service distribution
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No configurations available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Load Balancing Performance Analytics
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Load balancing analytics visualization would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Register Backend Dialog */}
      <Dialog
        open={showBackendDialog}
        onClose={() => setShowBackendDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Storage sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Register Backend Service</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Service Name"
                placeholder="AI Processing Service"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Service URL"
                placeholder="http://ai-service:8001"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Supported Request Types"
                placeholder="text_analysis, image_processing, data_cleaning"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="Max Concurrent Requests"
                defaultValue={10}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowBackendDialog(false)}>Cancel</Button>
          <Button
            onClick={() => registerBackendMutation.mutate({})}
            variant="contained"
            disabled={registerBackendMutation.isPending}
          >
            {registerBackendMutation.isPending ? 'Registering...' : 'Register Backend'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Configure Load Balancer Dialog */}
      <Dialog
        open={showConfigDialog}
        onClose={() => setShowConfigDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Settings sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Configure Load Balancer</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Configuration Name"
                placeholder="AI Services Load Balancer"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Load Balancing Algorithm</InputLabel>
                <Select defaultValue="least_connections">
                  <MenuItem value="round_robin">Round Robin</MenuItem>
                  <MenuItem value="least_connections">Least Connections</MenuItem>
                  <MenuItem value="weighted_round_robin">Weighted Round Robin</MenuItem>
                  <MenuItem value="ip_hash">IP Hash</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Health Check Interval (seconds)"
                defaultValue={30}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Failures"
                defaultValue={3}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Retry Timeout (seconds)"
                defaultValue={60}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Backend Services"
                placeholder="backend_001, backend_002, backend_003"
                helperText="Comma-separated list of backend service IDs"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfigDialog(false)}>Cancel</Button>
          <Button
            onClick={() => updateConfigMutation.mutate({})}
            variant="contained"
            disabled={updateConfigMutation.isPending}
          >
            {updateConfigMutation.isPending ? 'Saving...' : 'Save Configuration'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LoadBalancing;