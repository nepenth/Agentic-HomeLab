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
} from '@mui/material';
import {
  Api,
  Webhook,
  Queue,
  CloudQueue,
  Storage,
  Settings,
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
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import webSocketService from '../services/websocket';

// Define integration types locally for now
interface APIRoute {
  id: string;
  path: string;
  method: string;
  target_url: string;
  authentication: {
    type: 'none' | 'basic' | 'bearer' | 'api_key';
    config: any;
  };
  rate_limit: {
    requests_per_minute: number;
    burst_limit: number;
  };
  enabled: boolean;
  metrics: {
    total_requests: number;
    success_rate: number;
    average_response_time: number;
  };
}

interface WebhookSubscription {
  id: string;
  url: string;
  events: string[];
  headers: Record<string, string>;
  retry_policy: {
    max_attempts: number;
    backoff_factor: number;
  };
  enabled: boolean;
  metrics: {
    total_deliveries: number;
    success_rate: number;
    last_delivery: string;
  };
}

interface QueueItem {
  id: string;
  type: string;
  priority: 'low' | 'normal' | 'high' | 'critical';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  data: any;
  created_at: string;
  processed_at?: string;
  error?: string;
}

interface BackendService {
  id: string;
  name: string;
  url: string;
  supported_types: string[];
  max_concurrent_requests: number;
  health_status: 'healthy' | 'unhealthy' | 'unknown';
  metrics: {
    active_requests: number;
    total_requests: number;
    success_rate: number;
    average_response_time: number;
  };
}

interface IntegrationStats {
  total_routes: number;
  active_webhooks: number;
  queued_items: number;
  healthy_backends: number;
  total_requests: number;
  average_response_time: number;
  error_rate: number;
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
      id={`integration-tabpanel-${index}`}
      aria-labelledby={`integration-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const IntegrationHub: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [showRouteDialog, setShowRouteDialog] = useState(false);
  const [showWebhookDialog, setShowWebhookDialog] = useState(false);
  const [showBackendDialog, setShowBackendDialog] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState<APIRoute | null>(null);
  const [selectedWebhook, setSelectedWebhook] = useState<WebhookSubscription | null>(null);
  const [selectedBackend, setSelectedBackend] = useState<BackendService | null>(null);

  // Integration Stats Query
  const {
    data: integrationStats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useQuery<IntegrationStats>({
    queryKey: ['integration-stats'],
    queryFn: async () => {
      const [gatewayStats, webhookData, queueData, backendData] = await Promise.all([
        apiClient.getApiGatewayStats().catch(() => ({ total_routes: 0, total_requests: 0, average_response_time: 0 })),
        apiClient.getWebhooks().catch(() => []),
        apiClient.getQueues().catch(() => []),
        apiClient.getBackendServices().catch(() => [])
      ]);

      return {
        total_routes: gatewayStats.total_routes || 0,
        active_webhooks: webhookData.filter((w: any) => w.enabled).length || 0,
        queued_items: queueData.reduce((sum: number, q: any) => sum + (q.pending_count || 0), 0) || 0,
        healthy_backends: backendData.filter((b: any) => b.health_status === 'healthy').length || 0,
        total_requests: gatewayStats.total_requests || 0,
        average_response_time: gatewayStats.average_response_time || 0,
        error_rate: gatewayStats.error_rate || 0
      };
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // API Routes Query
  const {
    data: apiRoutes,
    isLoading: routesLoading,
    error: routesError,
    refetch: refetchRoutes,
  } = useQuery<APIRoute[]>({
    queryKey: ['api-routes'],
    queryFn: () => apiClient.getApiGatewayStats().then(stats => stats.routes || []),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Webhook Subscriptions Query
  const {
    data: webhookSubscriptions,
    isLoading: webhooksLoading,
    error: webhooksError,
    refetch: refetchWebhooks,
  } = useQuery<WebhookSubscription[]>({
    queryKey: ['webhook-subscriptions'],
    queryFn: () => apiClient.getWebhooks(),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Queue Items Query
  const {
    data: queueItems,
    isLoading: queueLoading,
    error: queueError,
    refetch: refetchQueue,
  } = useQuery<QueueItem[]>({
    queryKey: ['queue-items'],
    queryFn: async () => {
      const queues = await apiClient.getQueues();
      // Flatten all queue items from different queues
      const allItems: QueueItem[] = [];
      for (const queue of queues) {
        const queueStats = await apiClient.getQueueStats(queue.name);
        if (queueStats.items) {
          allItems.push(...queueStats.items);
        }
      }
      return allItems;
    },
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

  // Mutations
  const createRouteMutation = useMutation({
    mutationFn: (route: Partial<APIRoute>) => {
      // Note: API Gateway route creation would need backend implementation
      // For now, we'll use a placeholder that matches the expected API structure
      return Promise.resolve(route);
    },
    onSuccess: () => {
      setShowRouteDialog(false);
      refetchRoutes();
      refetchStats();
    },
  });

  const createWebhookMutation = useMutation({
    mutationFn: (webhook: Partial<WebhookSubscription>) => apiClient.subscribeWebhook({
      url: webhook.url!,
      events: webhook.events || [],
      secret: 'webhook-secret', // This would come from form input
      headers: webhook.headers || {}
    }),
    onSuccess: () => {
      setShowWebhookDialog(false);
      refetchWebhooks();
      refetchStats();
    },
  });

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

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    refetchStats();
    refetchRoutes();
    refetchWebhooks();
    refetchQueue();
    refetchBackends();
  };

  // WebSocket subscription for real-time integration events
  React.useEffect(() => {
    const unsubscribe = webSocketService.subscribeToIntegrationEvents(
      (event) => {
        console.log('Integration event received:', event);

        // Refresh relevant data based on event type
        if (event.type === 'webhook_delivery') {
          refetchWebhooks();
          refetchStats();
        } else if (event.type === 'queue_update') {
          refetchQueue();
          refetchStats();
        } else if (event.type === 'backend_health') {
          refetchBackends();
          refetchStats();
        } else {
          // Refresh all data for general integration events
          handleRefresh();
        }
      }
    );

    return unsubscribe;
  }, [refetchStats, refetchRoutes, refetchWebhooks, refetchQueue, refetchBackends]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
        return 'success';
      case 'unhealthy':
      case 'failed':
        return 'error';
      case 'processing':
        return 'primary';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
        return <CheckCircle />;
      case 'unhealthy':
      case 'failed':
        return <Error />;
      case 'processing':
        return <PlayArrow />;
      case 'pending':
        return <AccessTime />;
      default:
        return <Info />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'normal':
        return 'info';
      case 'low':
        return 'default';
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
            Integration Control Center
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage API Gateway, webhooks, queues, and backend services for seamless integration.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowRouteDialog(true)}
          >
            Add Route
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
          Failed to load integration statistics: {statsError.message}
          <Button size="small" onClick={() => refetchStats()} sx={{ ml: 2 }}>
            Retry
          </Button>
        </Alert>
      )}
      {integrationStats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                  {integrationStats.total_routes}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  API Routes
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                  {integrationStats.active_webhooks}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Webhooks
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                  {integrationStats.queued_items}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Queued Items
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                  {integrationStats.healthy_backends}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Healthy Backends
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="integration tabs">
            <Tab icon={<Api />} label="API Gateway" />
            <Tab icon={<Webhook />} label="Webhooks" />
            <Tab icon={<Queue />} label="Queues" />
            <Tab icon={<Storage />} label="Backends" />
            <Tab icon={<Assessment />} label="Analytics" />
          </Tabs>
        </CardContent>

        {/* API Gateway Tab */}
        <TabPanel value={tabValue} index={0}>
          {routesLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : apiRoutes ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  API Routes ({apiRoutes.length})
                </Typography>
              </Grid>

              {apiRoutes.map((route) => (
                <Grid item xs={12} md={6} key={route.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Chip
                              label={route.method}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {route.path}
                            </Typography>
                          </Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Target: {route.target_url}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Chip
                              label={route.authentication.type}
                              size="small"
                              variant="outlined"
                            />
                            <Chip
                              label={`${route.rate_limit.requests_per_minute}/min`}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={route.enabled}
                                size="small"
                              />
                            }
                            label=""
                          />
                          <IconButton size="small" onClick={() => setSelectedRoute(route)}>
                            <Edit />
                          </IconButton>
                          <IconButton size="small" color="error">
                            <Delete />
                          </IconButton>
                        </Box>
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Performance Metrics:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Chip
                            label={`${route.metrics.total_requests} requests`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${(route.metrics.success_rate * 100).toFixed(1)}% success`}
                            size="small"
                            variant="outlined"
                            color="success"
                          />
                          <Chip
                            label={`${route.metrics.average_response_time}ms avg`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {apiRoutes.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <Api sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No API routes configured
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Add your first API route to get started
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No API routes available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Webhooks Tab */}
        <TabPanel value={tabValue} index={1}>
          {webhooksLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : webhookSubscriptions ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Webhook Subscriptions ({webhookSubscriptions.length})
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={() => setShowWebhookDialog(true)}
                  >
                    Add Webhook
                  </Button>
                </Box>
              </Grid>

              {webhookSubscriptions.map((webhook) => (
                <Grid item xs={12} md={6} key={webhook.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                            {webhook.url}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                            {webhook.events.map((event) => (
                              <Chip key={event} label={event} size="small" variant="outlined" />
                            ))}
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            Last delivery: {new Date(webhook.metrics.last_delivery).toLocaleString()}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={webhook.enabled}
                                size="small"
                              />
                            }
                            label=""
                          />
                          <IconButton size="small" onClick={() => setSelectedWebhook(webhook)}>
                            <Edit />
                          </IconButton>
                          <IconButton size="small" color="error">
                            <Delete />
                          </IconButton>
                        </Box>
                      </Box>

                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Delivery Metrics:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Chip
                            label={`${webhook.metrics.total_deliveries} deliveries`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${(webhook.metrics.success_rate * 100).toFixed(1)}% success`}
                            size="small"
                            variant="outlined"
                            color="success"
                          />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {webhookSubscriptions.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <Webhook sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No webhook subscriptions
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Create webhook subscriptions to receive real-time notifications
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No webhook subscriptions available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Queues Tab */}
        <TabPanel value={tabValue} index={2}>
          {queueLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : queueItems ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Queue Items ({queueItems.length})
                </Typography>
              </Grid>

              {queueItems.map((item) => (
                <Grid item xs={12} md={6} key={item.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Chip
                              label={item.type}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            <Chip
                              label={item.priority}
                              size="small"
                              color={getPriorityColor(item.priority) as any}
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Created: {new Date(item.created_at).toLocaleString()}
                          </Typography>
                          {item.processed_at && (
                            <Typography variant="body2" color="text.secondary">
                              Processed: {new Date(item.processed_at).toLocaleString()}
                            </Typography>
                          )}
                        </Box>
                        <Chip
                          label={item.status}
                          color={getStatusColor(item.status) as any}
                          icon={getStatusIcon(item.status)}
                        />
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Data:
                        </Typography>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                          {JSON.stringify(item.data, null, 2).slice(0, 200)}...
                        </Typography>
                      </Box>

                      {item.error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                          {item.error}
                        </Alert>
                      )}

                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button size="small" variant="outlined">
                          View Details
                        </Button>
                        <Button size="small" variant="outlined">
                          Retry
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {queueItems.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <Queue sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      Queue is empty
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      No items are currently queued for processing
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No queue items available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Backends Tab */}
        <TabPanel value={tabValue} index={3}>
          {backendsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : backendServices ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Backend Services ({backendServices.length})
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={() => setShowBackendDialog(true)}
                  >
                    Register Backend
                  </Button>
                </Box>
              </Grid>

              {backendServices.map((backend) => (
                <Grid item xs={12} md={6} key={backend.id}>
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
                          <Typography variant="body2" color="text.secondary">
                            Max concurrent: {backend.max_concurrent_requests}
                          </Typography>
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
                            label={`${backend.metrics.total_requests} total`}
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

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={4}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Integration Performance Analytics
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Integration analytics visualization would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Add Route Dialog */}
      <Dialog
        open={showRouteDialog}
        onClose={() => setShowRouteDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Api sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Add API Route</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Path"
                placeholder="/api/v1/example"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Method</InputLabel>
                <Select defaultValue="GET">
                  <MenuItem value="GET">GET</MenuItem>
                  <MenuItem value="POST">POST</MenuItem>
                  <MenuItem value="PUT">PUT</MenuItem>
                  <MenuItem value="DELETE">DELETE</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Target URL"
                placeholder="http://backend:8000/api/v1/example"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Authentication</InputLabel>
                <Select defaultValue="bearer">
                  <MenuItem value="none">None</MenuItem>
                  <MenuItem value="bearer">Bearer Token</MenuItem>
                  <MenuItem value="basic">Basic Auth</MenuItem>
                  <MenuItem value="api_key">API Key</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Rate Limit (requests/min)"
                defaultValue={100}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowRouteDialog(false)}>Cancel</Button>
          <Button
            onClick={() => createRouteMutation.mutate({})}
            variant="contained"
            disabled={createRouteMutation.isPending}
          >
            {createRouteMutation.isPending ? 'Creating...' : 'Create Route'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Webhook Dialog */}
      <Dialog
        open={showWebhookDialog}
        onClose={() => setShowWebhookDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Webhook sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Add Webhook Subscription</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Webhook URL"
                placeholder="https://myapp.com/webhooks/events"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Events (comma-separated)"
                placeholder="workflow.completed, workflow.failed, task.created"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Authorization Header"
                placeholder="Bearer your-token-here"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Max Retry Attempts"
                defaultValue={3}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Backoff Factor"
                defaultValue={2.0}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowWebhookDialog(false)}>Cancel</Button>
          <Button
            onClick={() => createWebhookMutation.mutate({})}
            variant="contained"
            disabled={createWebhookMutation.isPending}
          >
            {createWebhookMutation.isPending ? 'Creating...' : 'Create Webhook'}
          </Button>
        </DialogActions>
      </Dialog>

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
    </Box>
  );
};

export default IntegrationHub;