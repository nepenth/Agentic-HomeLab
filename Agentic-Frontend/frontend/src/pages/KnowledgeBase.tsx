import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  Tabs,
  Tab,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Psychology,
  PlayArrow,
  Settings,
  Search,
  Add,
  Edit,
  Delete,
  ExpandMore,
  Refresh,
  Timeline,
  Assessment,
  LibraryBooks,
  Category,
  SmartToy,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Import components
import WorkflowVisualization from '../components/WorkflowVisualization';
import ItemEditor from '../components/ItemEditor';
import WorkflowSettingsManager from '../components/WorkflowSettingsManager';
import KnowledgeBaseSearch from '../components/KnowledgeBaseSearch';
import KnowledgeBaseChat from '../components/KnowledgeBaseChat';

// Import API functions (to be implemented)
import apiClient from '../services/api';
import webSocketService from '../services/websocket';

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
      id={`knowledge-base-tabpanel-${index}`}
      aria-labelledby={`knowledge-base-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const KnowledgeBase: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [workflowSettings, setWorkflowSettings] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [logFilters, setLogFilters] = useState({
    level: '',
    agent_id: '',
    task_id: ''
  });
  const [isLogsConnected, setIsLogsConnected] = useState(false);
  const queryClient = useQueryClient();

  // API Queries with error handling for missing endpoints
  const { data: activeProgress, isLoading: progressLoading, error: progressError, refetch: refetchProgress } = useQuery({
    queryKey: ['knowledge-progress-active'],
    queryFn: () => apiClient.getActiveProgress(20),
    refetchInterval: 3000, // Refresh every 3 seconds
    retry: (failureCount, error: any) => {
      // Don't retry on 404/405 errors (endpoint not implemented)
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  const { data: knowledgeItems, isLoading: itemsLoading, error: itemsError, refetch: refetchItems } = useQuery({
    queryKey: ['knowledge-items'],
    queryFn: () => apiClient.getKnowledgeItems({ limit: 50 }),
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  const { data: bookmarks, isLoading: bookmarksLoading, error: bookmarksError, refetch: refetchBookmarks } = useQuery({
    queryKey: ['twitter-bookmarks'],
    queryFn: () => apiClient.getTwitterBookmarks({ limit: 50 }),
    retry: (failureCount, error: any) => {
      return failureCount < 3;
    },
  });

  const { data: knowledgeStats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['knowledge-stats'],
    queryFn: () => apiClient.getKnowledgeStats(),
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  const { data: workflowSettingsList, error: settingsError, refetch: refetchSettings } = useQuery({
    queryKey: ['workflow-settings'],
    queryFn: () => apiClient.getWorkflowSettings(),
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 405) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Mutations
  const startWorkflowMutation = useMutation({
    mutationFn: (data: any) => apiClient.fetchTwitterBookmarks(data),
    onSuccess: () => {
      refetchProgress();
      queryClient.invalidateQueries({ queryKey: ['knowledge-items'] });
    },
  });

  const cancelWorkflowMutation = useMutation({
    mutationFn: (itemId: string) => apiClient.cancelKnowledgeItemProcessing(itemId),
    onSuccess: () => {
      refetchProgress();
      queryClient.invalidateQueries({ queryKey: ['knowledge-items'] });
    },
  });

  const reprocessItemMutation = useMutation({
    mutationFn: ({ itemId, options }: { itemId: string; options?: any }) =>
      apiClient.reprocessKnowledgeItem(itemId, options),
    onSuccess: () => {
      refetchProgress();
    },
  });

  // Computed data
  const workflowProgress = activeProgress?.active_processing?.[0] || null;
  const mockWorkflowProgress = workflowProgress ? {
    overall_progress: workflowProgress.overall_progress_percentage,
    current_phase: workflowProgress.current_phase,
    phases: workflowProgress.phases.map((phase: any) => ({
      name: phase.phase_name,
      status: phase.status,
      progress: phase.progress_percentage,
      progress_percentage: phase.progress_percentage,
      start_time: phase.started_at,
      end_time: phase.completed_at,
      duration_ms: phase.processing_duration_ms,
      model_used: phase.model_used,
      error_message: phase.status_message,
      status_message: phase.status_message,
    }))
  } : {
    overall_progress: 0,
    current_phase: 'pending',
    phases: [
      { name: 'fetch_bookmarks', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'cache_content', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'cache_media', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'interpret_media', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'categorize_content', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'holistic_understanding', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'synthesized_learning', status: 'pending', progress: 0, progress_percentage: 0 },
      { name: 'embeddings', status: 'pending', progress: 0, progress_percentage: 0 },
    ]
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleStartWorkflow = async () => {
    try {
      await startWorkflowMutation.mutateAsync({
        bookmark_url: "https://twitter.com/username/bookmarks",
        max_results: 50,
        process_items: true,
        workflow_settings_id: workflowSettings?.id
      });
    } catch (error) {
      console.error('Failed to start workflow:', error);
    }
  };

  const handleSettingsSave = () => {
    // TODO: Implement settings save
    setShowSettings(false);
  };

  const handleReprocessItem = async (itemId: string) => {
    try {
      await reprocessItemMutation.mutateAsync({
        itemId,
        options: {
          reason: "User requested reprocessing",
          start_immediately: true,
          workflow_settings_id: workflowSettings?.id
        }
      });
    } catch (error) {
      console.error('Failed to reprocess item:', error);
    }
  };

  const handleCancelWorkflow = async () => {
    if (!workflowProgress?.item_id) return;

    try {
      await cancelWorkflowMutation.mutateAsync(workflowProgress.item_id);
    } catch (error) {
      console.error('Failed to cancel workflow:', error);
    }
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleLogFilterChange = (filterType: string, value: string) => {
    setLogFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const getLogLevelColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'error': return '#f44336';
      case 'warning': return '#ff9800';
      case 'info': return '#2196f3';
      case 'debug': return '#9c27b0';
      default: return '#757575';
    }
  };

  const formatLogTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  // WebSocket subscriptions for real-time updates (only if backend supports them)
  useEffect(() => {
    // Wait for API queries to complete before attempting WebSocket connections
    const isLoading = progressLoading || itemsLoading;
    const hasErrors = progressError || itemsError;

    // Don't attempt WebSocket connections while loading or if there are errors
    if (isLoading || hasErrors) {
      console.log('Skipping WebSocket connections - API queries still loading or have errors');
      return;
    }

    // Only connect WebSocket if API calls were successful (no errors and not loading)
    const hasBackendSupport = !hasErrors && !isLoading && (activeProgress !== undefined || knowledgeItems !== undefined);

    if (!hasBackendSupport) {
      console.log('Skipping WebSocket connections - backend endpoints not available or still loading');
      return;
    }

    console.log('Attempting WebSocket connections - backend appears to be available');

    let unsubscribeProgress: (() => void) | undefined;
    let unsubscribeItems: (() => void) | undefined;
    let unsubscribeLogs: (() => void) | undefined;

    // Add a small delay to ensure backend is ready
    const connectionTimer = setTimeout(() => {
      try {
        // Subscribe to Knowledge Base progress updates
        unsubscribeProgress = webSocketService.subscribeToKnowledgeBaseProgress(
          (update) => {
            console.log('Real-time progress update:', update);
            refetchProgress();
            refetchItems();
            refetchBookmarks();
            refetchSettings();
          }
        );

        // Subscribe to Knowledge Base item updates
        unsubscribeItems = webSocketService.subscribeToKnowledgeBaseItems(
          (update) => {
            console.log('Real-time item update:', update);
            refetchItems();
            refetchBookmarks();
            refetchProgress();
          }
        );

        // Subscribe to real-time logs
        unsubscribeLogs = webSocketService.subscribeToLogs(
          (logEntry) => {
            console.log('Real-time log entry:', logEntry);
            setLogs(prev => [logEntry, ...prev].slice(0, 1000)); // Keep last 1000 logs
          },
          logFilters
        );

        // Monitor connection status for logs
        const unsubscribeConnectionStatus = webSocketService.onConnectionStatus((status) => {
          setIsLogsConnected(status === 'connected');
        });

        // Cleanup connection status listener
        return () => {
          if (unsubscribeConnectionStatus) unsubscribeConnectionStatus();
        };
      } catch (error) {
        console.log('WebSocket connection failed - backend may not support real-time updates yet');
      }
    }, 2000); // Wait 2 seconds after API calls complete

    // Cleanup subscriptions on unmount
    return () => {
      clearTimeout(connectionTimer);
      if (unsubscribeProgress) unsubscribeProgress();
      if (unsubscribeItems) unsubscribeItems();
      if (unsubscribeLogs) unsubscribeLogs();
    };
  }, [progressLoading, itemsLoading, bookmarksLoading, progressError, itemsError, bookmarksError, activeProgress, knowledgeItems, bookmarks, logFilters]);


  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Psychology color="primary" />
          Knowledge Base Workflow
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Process Twitter/X bookmarks into an intelligent, searchable knowledge base with AI-powered analysis
        </Typography>
      </Box>

      {/* Action Buttons */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          startIcon={<PlayArrow />}
          onClick={handleStartWorkflow}
          size="large"
        >
          Start Processing
        </Button>
        <Button
          variant="outlined"
          startIcon={<Settings />}
          onClick={() => setShowSettings(true)}
        >
          Workflow Settings
        </Button>
        <Button
          variant="outlined"
          startIcon={<Search />}
          onClick={() => setActiveTab(1)}
        >
          Browse Knowledge Base
        </Button>
      </Box>

      {/* Main Content */}
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab
            icon={<Timeline />}
            label="Workflow Progress"
            iconPosition="start"
          />
          <Tab
            icon={<LibraryBooks />}
            label="Bookmarks"
            iconPosition="start"
          />
          <Tab
            icon={<Psychology />}
            label="Knowledge Base"
            iconPosition="start"
          />
          <Tab
            icon={<Search />}
            label="Search"
            iconPosition="start"
          />
          <Tab
            icon={<SmartToy />}
            label="Chat"
            iconPosition="start"
          />
          <Tab
            icon={<Assessment />}
            label="Analytics"
            iconPosition="start"
          />
          <Tab
            icon={<Timeline />}
            label="Real-time Logs"
            iconPosition="start"
          />
        </Tabs>

        {/* Workflow Progress Tab */}
        <TabPanel value={activeTab} index={0}>
          <WorkflowVisualization
            phases={mockWorkflowProgress.phases.map(phase => ({
              ...phase,
              display_name: phase.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              progress_percentage: phase.progress,
              status: phase.status as 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
            }))}
            overallProgress={mockWorkflowProgress.overall_progress}
            currentPhase={mockWorkflowProgress.current_phase}
            isRunning={mockWorkflowProgress.phases.some(p => p.status === 'running')}
            itemId={workflowProgress?.item_id}
            onStart={handleStartWorkflow}
            onStop={() => console.log('Stop workflow')}
            onCancel={handleCancelWorkflow}
            onSettings={() => setShowSettings(true)}
            onSkipPhase={(phaseName) => console.log('Skip phase:', phaseName)}
            onRetryPhase={(phaseName) => console.log('Retry phase:', phaseName)}
          />
        </TabPanel>

        {/* Bookmarks Tab */}
        <TabPanel value={activeTab} index={1}>
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>Twitter Bookmarks:</strong> This tab shows your raw Twitter bookmarks that can be processed into the Knowledge Base.
              Use the "Fetch & Process Bookmarks" button to retrieve and process your Twitter bookmarks through the 8-phase AI workflow.
            </Typography>
          </Alert>

          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              Twitter Bookmarks ({bookmarksLoading ? '...' : bookmarks?.bookmarks?.length || 0})
            </Typography>
            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleStartWorkflow}
              disabled={startWorkflowMutation.isPending}
            >
              {startWorkflowMutation.isPending ? 'Processing...' : 'Fetch & Process Bookmarks'}
            </Button>
          </Box>

          {bookmarksLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography>Loading bookmarks...</Typography>
            </Box>
          ) : bookmarksError ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography color="text.secondary">
                Unable to load bookmarks. {bookmarksError?.message || 'Please try again later.'}
              </Typography>
            </Box>
          ) : (
            <>
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {bookmarks?.bookmarks?.length === 0
                    ? "No bookmarks found. Click 'Fetch & Process Bookmarks' to retrieve your Twitter bookmarks and process them through the Knowledge Base workflow."
                    : "Your Twitter bookmarks are listed below. Click 'Fetch & Process Bookmarks' to process them through the Knowledge Base workflow."
                  }
                </Typography>

                <Paper sx={{ p: 3, backgroundColor: '#f8f9fa' }}>
                  <Typography variant="h6" gutterBottom>
                    📥 How Bookmarks Processing Works
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    1. **Fetch**: Retrieve bookmarks from your Twitter/X account
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    2. **Process**: Run each bookmark through the 8-phase AI workflow
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    3. **Store**: Save processed content in the Knowledge Base
                  </Typography>
                  <Typography variant="body2">
                    4. **Search**: Make bookmarks searchable with semantic search
                  </Typography>
                </Paper>
              </Box>

              {bookmarks?.bookmarks?.length > 0 && (
                <Grid container spacing={3}>
                  {bookmarks.bookmarks.map((bookmark: any, index: number) => (
                    <Grid item xs={12} md={6} key={bookmark.id || index}>
                      <Card>
                        <CardContent>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                            <Typography variant="h6" component="h3">
                              {bookmark.title || `Bookmark ${index + 1}`}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Chip
                                label={bookmark.processing_phase === 'completed' ? 'Processed' : 'Raw Bookmark'}
                                size="small"
                                color={bookmark.processing_phase === 'completed' ? 'success' : 'secondary'}
                                variant="outlined"
                              />
                              {bookmark.has_been_processed && (
                                <Chip
                                  label="✅ Processed"
                                  size="small"
                                  color="success"
                                  variant="filled"
                                />
                              )}
                            </Box>
                          </Box>

                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {bookmark.content || bookmark.summary || 'Bookmark content not available'}
                          </Typography>

                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                            {bookmark.tags?.map((tag: string, tagIndex: number) => (
                              <Chip key={tagIndex} label={tag} size="small" variant="outlined" />
                            ))}
                            {bookmark.hashtags?.map((hashtag: string, tagIndex: number) => (
                              <Chip key={`hashtag-${tagIndex}`} label={`#${hashtag}`} size="small" variant="outlined" color="primary" />
                            ))}
                          </Box>

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" color="text.secondary">
                              Bookmarked: {bookmark.bookmarked_at ? new Date(bookmark.bookmarked_at).toLocaleDateString() : 'Unknown'}
                            </Typography>
                            {bookmark.likes && (
                              <Typography variant="caption" color="text.secondary">
                                ❤️ {bookmark.likes} • 🔄 {bookmark.retweets || 0} • 💬 {bookmark.replies || 0}
                              </Typography>
                            )}
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}

              {bookmarks?.filters_applied && (
                <Alert severity="info" sx={{ mt: 3 }}>
                  <Typography variant="body2">
                    <strong>Filters Applied:</strong> {JSON.stringify(bookmarks.filters_applied)}
                  </Typography>
                </Alert>
              )}
            </>
          )}

          {startWorkflowMutation.isPending && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4, mt: 3 }}>
              <Typography>Fetching and processing Twitter bookmarks...</Typography>
            </Box>
          )}
        </TabPanel>

        {/* Knowledge Base Tab */}
        <TabPanel value={activeTab} index={2}>
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>Processed Knowledge Base Items:</strong> This tab shows only items that have been fully processed through the 8-phase AI workflow.
              Raw bookmarks are displayed in the Bookmarks tab above.
            </Typography>
          </Alert>

          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              Processed Knowledge Base Items ({itemsLoading ? '...' : knowledgeItems?.items?.length || 0})
            </Typography>
            <Button variant="contained" startIcon={<Add />} disabled={!!itemsError}>
              Add Item
            </Button>
          </Box>

          {itemsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography>Loading processed knowledge items...</Typography>
            </Box>
          ) : itemsError ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography color="text.secondary">
                Unable to load knowledge items. {itemsError?.message || 'Please try again later.'}
              </Typography>
            </Box>
          ) : knowledgeItems?.items?.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography color="text.secondary">
                No processed knowledge items yet. Use the Bookmarks tab to fetch and process your Twitter bookmarks.
              </Typography>
            </Box>
          ) : (
            <Grid container spacing={3}>
              {knowledgeItems?.items?.map((item: any) => (
                <Grid item xs={12} md={6} key={item.id}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Typography variant="h6" component="h3">
                          {item.title}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Chip
                            label="✅ Processed"
                            size="small"
                            color="success"
                            variant="filled"
                          />
                          <Box>
                            <IconButton size="small" onClick={() => setSelectedItem(item)}>
                              <Edit fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => handleReprocessItem(item.id)}
                              disabled={reprocessItemMutation.isPending}
                            >
                              <Refresh fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Chip
                          label={item.category || 'Uncategorized'}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {item.summary || item.content?.substring(0, 200) + '...'}
                      </Typography>

                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        {item.tags?.map((tag: string, index: number) => (
                          <Chip key={index} label={tag} size="small" variant="outlined" />
                        ))}
                      </Box>

                      <Typography variant="caption" color="text.secondary">
                        Processed: {item.processed_at ? new Date(item.processed_at).toLocaleDateString() : 'Unknown'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )) || []}
            </Grid>
          )}

          {knowledgeItems?.filter_note && (
            <Alert severity="info" sx={{ mt: 3 }}>
              <Typography variant="body2">
                {knowledgeItems.filter_note}
              </Typography>
            </Alert>
          )}
        </TabPanel>

        {/* Search Tab */}
        <TabPanel value={activeTab} index={3}>
          <KnowledgeBaseSearch
            onResultSelect={(result) => {
              setSelectedItem(result);
            }}
          />
        </TabPanel>

        {/* Chat Tab */}
        <TabPanel value={activeTab} index={4}>
          <KnowledgeBaseChat />
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={activeTab} index={5}>
          {statsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography>Loading analytics...</Typography>
            </Box>
          ) : statsError ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <Typography color="text.secondary">
                Unable to load analytics. {statsError?.message || 'Please try again later.'}
              </Typography>
            </Box>
          ) : (
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Total Items
                    </Typography>
                    <Typography variant="h3" color="primary">
                      {knowledgeStats?.total_items || 0}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Categories
                    </Typography>
                    <Typography variant="h3" color="secondary">
                      {knowledgeStats?.total_categories || 0}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Processing Success Rate
                    </Typography>
                    <Typography variant="h3" color="success.main">
                      {knowledgeStats?.processing_success_rate ? Math.round(knowledgeStats.processing_success_rate * 100) : 0}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Items by Status
                    </Typography>
                    <Grid container spacing={1}>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="success.main">
                          Completed: {knowledgeStats?.items_by_status?.completed || 0}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="warning.main">
                          Processing: {knowledgeStats?.items_by_status?.processing || 0}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="error.main">
                          Failed: {knowledgeStats?.items_by_status?.failed || 0}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Pending: {knowledgeStats?.items_by_status?.pending || 0}
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Recent Activity
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Items processed today: {knowledgeStats?.recent_activity?.processed_today || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Average processing time: {knowledgeStats?.recent_activity?.avg_processing_time_seconds || 0}s
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </TabPanel>

        {/* Real-time Logs Tab */}
        <TabPanel value={activeTab} index={6}>
          <Box sx={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Real-time Workflow Logs
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={isLogsConnected ? 'Connected' : 'Disconnected'}
                  color={isLogsConnected ? 'success' : 'error'}
                  size="small"
                />
                <Typography variant="body2" color="text.secondary">
                  {logs.length} logs
                </Typography>
              </Box>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Live logs from the Knowledge Base workflow processing. Logs will appear here as processing occurs.
            </Typography>

            {/* Log Filters */}
            <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Level</InputLabel>
                <Select
                  value={logFilters.level}
                  label="Level"
                  onChange={(e) => handleLogFilterChange('level', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="error">Error</MenuItem>
                  <MenuItem value="warning">Warning</MenuItem>
                  <MenuItem value="info">Info</MenuItem>
                  <MenuItem value="debug">Debug</MenuItem>
                </Select>
              </FormControl>
              <TextField
                size="small"
                label="Agent ID"
                value={logFilters.agent_id}
                onChange={(e) => handleLogFilterChange('agent_id', e.target.value)}
                placeholder="Filter by agent ID"
              />
              <TextField
                size="small"
                label="Task ID"
                value={logFilters.task_id}
                onChange={(e) => handleLogFilterChange('task_id', e.target.value)}
                placeholder="Filter by task ID"
              />
            </Box>

            {/* Logs Display */}
            <Box sx={{
              flex: 1,
              border: '1px solid #e0e0e0',
              borderRadius: 1,
              p: 2,
              backgroundColor: '#f5f5f5',
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.875rem'
            }}>
              {logs.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                  {isLogsConnected
                    ? 'Waiting for logs... Start a workflow to see real-time logs.'
                    : 'Connecting to real-time logs...'}
                </Typography>
              ) : (
                logs.map((log, index) => (
                  <Box
                    key={index}
                    sx={{
                      mb: 1,
                      p: 1,
                      borderRadius: 1,
                      backgroundColor: 'white',
                      border: '1px solid #e0e0e0'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography
                        variant="caption"
                        sx={{
                          color: getLogLevelColor(log.level),
                          fontWeight: 'bold',
                          textTransform: 'uppercase'
                        }}
                      >
                        {log.level}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatLogTimestamp(log.timestamp)}
                      </Typography>
                      {log.agent_id && (
                        <Chip label={`Agent: ${log.agent_id}`} size="small" variant="outlined" />
                      )}
                      {log.task_id && (
                        <Chip label={`Task: ${log.task_id}`} size="small" variant="outlined" />
                      )}
                    </Box>
                    <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                      {log.message}
                    </Typography>
                    {log.source && (
                      <Typography variant="caption" color="text.secondary">
                        Source: {log.source}
                      </Typography>
                    )}
                  </Box>
                ))
              )}
            </Box>

            {/* Action Buttons */}
            <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                size="small"
                onClick={handleClearLogs}
                disabled={logs.length === 0}
              >
                Clear Logs ({logs.length})
              </Button>
              <Button variant="outlined" size="small">
                Export Logs
              </Button>
              <Button variant="outlined" size="small">
                Auto-scroll
              </Button>
            </Box>
          </Box>
        </TabPanel>
      </Paper>

      {/* Workflow Settings Manager */}
      <WorkflowSettingsManager
        open={showSettings}
        onClose={() => setShowSettings(false)}
        onSettingsActivated={(settings) => {
          setWorkflowSettings(settings);
          setShowSettings(false);
        }}
      />

      {/* Item Editor Dialog */}
      <ItemEditor
        open={!!selectedItem}
        onClose={() => setSelectedItem(null)}
        item={selectedItem}
      />
    </Box>
  );
};

export default KnowledgeBase;