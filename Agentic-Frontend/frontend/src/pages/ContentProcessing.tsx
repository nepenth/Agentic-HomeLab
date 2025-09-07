import React, { useState, useRef } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
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
  Skeleton,
  Tooltip,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Avatar,
  Divider,
} from '@mui/material';
import {
  Add,
  Refresh,
  CloudUpload,
  Web,
  RssFeed,
  Twitter,
  Reddit,
  Email,
  Folder,
  Storage,
  PlayArrow,
  Stop,
  CheckCircle,
  Error,
  ExpandMore,
  Memory,
  Assessment,
  Settings,
  Search,
  FilterList,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type {
  ContentDiscoveryRequest,
  DiscoveredContent,
  ProcessedContent,
  ContentProcessingRequest,
  WebContentConfig,
  SocialContentConfig,
  CommunicationContentConfig,
  FilesystemContentConfig,
  ContentCacheStats,
} from '../types';

interface ContentSource {
  type: 'web' | 'social' | 'communication' | 'filesystem' | 'api';
  name: string;
  icon: React.ReactNode;
  config: any;
  active: boolean;
}

const ContentProcessing: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedSource, setSelectedSource] = useState<ContentSource | null>(null);
  const [showSourceDialog, setShowSourceDialog] = useState(false);
  const [showProcessingDialog, setShowProcessingDialog] = useState(false);
  const [selectedContent, setSelectedContent] = useState<DiscoveredContent | null>(null);
  const [processingResults, setProcessingResults] = useState<ProcessedContent | null>(null);
  const [activeDiscoveries, setActiveDiscoveries] = useState<Set<string>>(new Set());

  // Source configuration state
  const [webConfig, setWebConfig] = useState<WebContentConfig>({
    feed_url: '',
    max_items: 50,
  });

  const [socialConfig, setSocialConfig] = useState<SocialContentConfig>({
    platform: 'twitter',
    max_items: 100,
  });

  const [communicationConfig, setCommunicationConfig] = useState<CommunicationContentConfig>({
    platform: 'email',
    max_messages: 50,
  });

  const [filesystemConfig, setFilesystemConfig] = useState<FilesystemContentConfig>({
    recursive: true,
    max_keys: 100,
  });

  // Available content sources
  const contentSources: ContentSource[] = [
    {
      type: 'web',
      name: 'Web Content',
      icon: <Web />,
      config: webConfig,
      active: true,
    },
    {
      type: 'social',
      name: 'Social Media',
      icon: <Twitter />,
      config: socialConfig,
      active: true,
    },
    {
      type: 'communication',
      name: 'Communication',
      icon: <Email />,
      config: communicationConfig,
      active: true,
    },
    {
      type: 'filesystem',
      name: 'File System',
      icon: <Folder />,
      config: filesystemConfig,
      active: true,
    },
  ];

  // Fetch cache statistics
  const {
    data: cacheStats,
    isLoading: cacheLoading,
    refetch: refetchCache,
  } = useQuery<ContentCacheStats>({
    queryKey: ['content-cache-stats'],
    queryFn: () => apiClient.getContentCacheStats(),
    refetchInterval: 30000,
  });

  // Content discovery mutation
  const discoverContentMutation = useMutation({
    mutationFn: (request: ContentDiscoveryRequest) => apiClient.discoverContent(request),
    onSuccess: (results) => {
      // Handle discovered content
      console.log('Discovered content:', results);
    },
  });

  // Content processing mutation
  const processContentMutation = useMutation({
    mutationFn: (request: ContentProcessingRequest) => apiClient.processContent(request),
    onSuccess: (result) => {
      setProcessingResults(result);
      setShowProcessingDialog(true);
    },
  });

  const handleSourceSelect = (source: ContentSource) => {
    setSelectedSource(source);
    setShowSourceDialog(true);
  };

  const handleDiscoverContent = () => {
    if (!selectedSource) return;

    const discoveryId = `${selectedSource.type}-${Date.now()}`;
    setActiveDiscoveries(prev => new Set(prev).add(discoveryId));

    const request: ContentDiscoveryRequest = {
      sources: [{
        type: selectedSource.type,
        config: selectedSource.config,
      }],
    };

    discoverContentMutation.mutate(request, {
      onSettled: () => {
        setActiveDiscoveries(prev => {
          const newSet = new Set(prev);
          newSet.delete(discoveryId);
          return newSet;
        });
      },
    });

    setShowSourceDialog(false);
  };

  const handleProcessContent = (content: DiscoveredContent) => {
    setSelectedContent(content);
    processContentMutation.mutate({
      content: content.content,
      content_type: content.content_type,
      operations: ['summarize', 'extract_entities', 'classify'],
    });
  };

  const handleClearCache = () => {
    // Cache clearing not implemented in backend yet
    console.log('Cache clearing not available');
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'web': return <Web />;
      case 'social': return <Twitter />;
      case 'communication': return <Email />;
      case 'filesystem': return <Folder />;
      default: return <Storage />;
    }
  };

  const getContentTypeColor = (type: string) => {
    switch (type) {
      case 'text': return 'primary';
      case 'image': return 'secondary';
      case 'audio': return 'warning';
      case 'video': return 'info';
      default: return 'default';
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Content Processing Hub
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Discover, process, and analyze content from diverse sources using AI-powered tools.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetchCache()}
            disabled={cacheLoading}
          >
            Refresh Stats
          </Button>
          <Button
            variant="outlined"
            startIcon={<Memory />}
            onClick={handleClearCache}
          >
            Clear Cache
          </Button>
        </Box>
      </Box>

      {/* Cache Statistics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Cache Entries
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    {cacheLoading ? '...' : cacheStats?.total_entries || 0}
                  </Typography>
                </Box>
                <Memory sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Hit Rate
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                    {cacheLoading ? '...' : `${((cacheStats?.cache_hit_rate || 0) * 100).toFixed(1)}%`}
                  </Typography>
                </Box>
                <CheckCircle sx={{ fontSize: 40, color: 'success.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Cache Size
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                    {cacheLoading ? '...' : `${((cacheStats?.cache_size_bytes || 0) / 1024 / 1024).toFixed(1)}MB`}
                  </Typography>
                </Box>
                <Storage sx={{ fontSize: 40, color: 'info.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Active Sources
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main' }}>
                    {contentSources.filter(s => s.active).length}
                  </Typography>
                </Box>
                <Assessment sx={{ fontSize: 40, color: 'warning.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Content Sources */}
      <Card elevation={0} sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Content Sources
          </Typography>

          <Grid container spacing={2}>
            {contentSources.map((source) => (
              <Grid item xs={12} sm={6} md={3} key={source.type}>
                <Card
                  elevation={1}
                  sx={{
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': { elevation: 3 },
                  }}
                  onClick={() => handleSourceSelect(source)}
                >
                  <CardContent sx={{ textAlign: 'center', py: 3 }}>
                    <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48, mx: 'auto', mb: 2 }}>
                      {source.icon}
                    </Avatar>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      {source.name}
                    </Typography>
                    <Chip
                      label={source.active ? 'Active' : 'Inactive'}
                      color={source.active ? 'success' : 'default'}
                      size="small"
                    />
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Recent Discoveries */}
      <Card elevation={0}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Recent Content Discoveries
          </Typography>

          {discoverContentMutation.isPending ? (
            <Box>
              {[...Array(3)].map((_, index) => (
                <Box key={index} sx={{ mb: 2 }}>
                  <Skeleton variant="rectangular" width="100%" height={80} sx={{ borderRadius: 1 }} />
                </Box>
              ))}
            </Box>
          ) : (
            <TableContainer component={Paper} elevation={0}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Source</TableCell>
                    <TableCell>Content Type</TableCell>
                    <TableCell>Title/Preview</TableCell>
                    <TableCell>Discovered</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {/* Mock data for demonstration - replace with real data */}
                  <TableRow hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Web sx={{ color: 'primary.main' }} />
                        <Typography variant="body2">Web</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label="text" color="primary" size="small" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{
                        maxWidth: 300,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        Latest AI developments in machine learning...
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        2 min ago
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PlayArrow />}
                        onClick={() => handleProcessContent({
                          id: 'mock-1',
                          source: 'web',
                          content: 'Sample content...',
                          content_type: 'text',
                          metadata: {},
                          discovered_at: new Date().toISOString(),
                        })}
                      >
                        Process
                      </Button>
                    </TableCell>
                  </TableRow>
                  <TableRow hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Twitter sx={{ color: 'info.main' }} />
                        <Typography variant="body2">Social</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label="text" color="primary" size="small" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{
                        maxWidth: 300,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        Exciting new features in our latest update...
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        5 min ago
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PlayArrow />}
                      >
                        Process
                      </Button>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Source Configuration Dialog */}
      <Dialog
        open={showSourceDialog}
        onClose={() => setShowSourceDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {selectedSource?.icon}
            <Typography variant="h6">Configure {selectedSource?.name}</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedSource?.type === 'web' && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="RSS Feed URL"
                  value={webConfig.feed_url}
                  onChange={(e) => setWebConfig(prev => ({ ...prev, feed_url: e.target.value }))}
                  placeholder="https://example.com/feed.xml"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Items"
                  value={webConfig.max_items}
                  onChange={(e) => setWebConfig(prev => ({ ...prev, max_items: parseInt(e.target.value) }))}
                  inputProps={{ min: 1, max: 1000 }}
                />
              </Grid>
            </Grid>
          )}

          {selectedSource?.type === 'social' && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Platform</InputLabel>
                  <Select
                    value={socialConfig.platform}
                    label="Platform"
                    onChange={(e) => setSocialConfig(prev => ({ ...prev, platform: e.target.value }))}
                  >
                    <MenuItem value="twitter">Twitter</MenuItem>
                    <MenuItem value="reddit">Reddit</MenuItem>
                    <MenuItem value="linkedin">LinkedIn</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Items"
                  value={socialConfig.max_items}
                  onChange={(e) => setSocialConfig(prev => ({ ...prev, max_items: parseInt(e.target.value) }))}
                  inputProps={{ min: 1, max: 1000 }}
                />
              </Grid>
            </Grid>
          )}

          {selectedSource?.type === 'communication' && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Platform</InputLabel>
                  <Select
                    value={communicationConfig.platform}
                    label="Platform"
                    onChange={(e) => setCommunicationConfig(prev => ({ ...prev, platform: e.target.value }))}
                  >
                    <MenuItem value="email">Email</MenuItem>
                    <MenuItem value="slack">Slack</MenuItem>
                    <MenuItem value="discord">Discord</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Messages"
                  value={communicationConfig.max_messages}
                  onChange={(e) => setCommunicationConfig(prev => ({ ...prev, max_messages: parseInt(e.target.value) }))}
                  inputProps={{ min: 1, max: 1000 }}
                />
              </Grid>
            </Grid>
          )}

          {selectedSource?.type === 'filesystem' && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Directory Path"
                  value={filesystemConfig.directory}
                  onChange={(e) => setFilesystemConfig(prev => ({ ...prev, directory: e.target.value }))}
                  placeholder="/path/to/documents"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Keys"
                  value={filesystemConfig.max_keys}
                  onChange={(e) => setFilesystemConfig(prev => ({ ...prev, max_keys: parseInt(e.target.value) }))}
                  inputProps={{ min: 1, max: 10000 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>File Patterns</InputLabel>
                  <Select
                    multiple
                    value={filesystemConfig.file_patterns || []}
                    label="File Patterns"
                    onChange={(e) => setFilesystemConfig(prev => ({
                      ...prev,
                      file_patterns: e.target.value as string[]
                    }))}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    <MenuItem value="*.pdf">PDF Files</MenuItem>
                    <MenuItem value="*.docx">Word Documents</MenuItem>
                    <MenuItem value="*.txt">Text Files</MenuItem>
                    <MenuItem value="*.json">JSON Files</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSourceDialog(false)}>Cancel</Button>
          <Button
            onClick={handleDiscoverContent}
            variant="contained"
            disabled={discoverContentMutation.isPending}
            startIcon={<Search />}
          >
            {discoverContentMutation.isPending ? 'Discovering...' : 'Discover Content'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Processing Results Dialog */}
      <Dialog
        open={showProcessingDialog}
        onClose={() => setShowProcessingDialog(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Memory sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Content Processing Results</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {processingResults && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Summary</Typography>
                <Typography variant="body1">
                  {processingResults.processed_content?.summary || 'No summary available'}
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Extracted Entities</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {processingResults.processed_content?.entities?.map((entity: any, index: number) => (
                    <Chip
                      key={index}
                      label={`${entity.text} (${entity.type})`}
                      variant="outlined"
                      size="small"
                    />
                  )) || <Typography variant="body2" color="text.secondary">No entities found</Typography>}
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 2 }}>Processing Metadata</Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Chip
                    label={`Processing Time: ${processingResults.processing_time_ms}ms`}
                    variant="outlined"
                  />
                  <Chip
                    label={`Content Type: ${processingResults.content_type}`}
                    variant="outlined"
                  />
                </Box>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowProcessingDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ContentProcessing;