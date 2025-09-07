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
  CardMedia,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Compare,
  Link,
  Search,
  Upload,
  Refresh,
  Settings,
  Assessment,
  Image,
  Audiotrack,
  TextFields,
  ExpandMore,
  CloudUpload,
  GetApp,
  Sync,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

// Define cross-modal types locally for now
interface CrossModalContent {
  text?: string;
  image_url?: string;
  audio_url?: string;
  video_url?: string;
}

interface FusionResult {
  fusion_id: string;
  modalities_used: string[];
  alignment_score: number;
  correlation_results: Array<{
    modality_pair: string;
    correlation_score: number;
    description: string;
  }>;
  unified_representation: any;
  processing_time_ms: number;
}

interface MultiModalSearch {
  search_id: string;
  query: CrossModalContent;
  results: Array<{
    content_id: string;
    modalities: string[];
    relevance_score: number;
    matched_modalities: string[];
    content_preview: any;
  }>;
  total_results: number;
}

interface AlignmentResult {
  alignment_id: string;
  source_modality: string;
  target_modality: string;
  alignment_score: number;
  aligned_segments: Array<{
    source_segment: any;
    target_segment: any;
    alignment_score: number;
  }>;
  processing_time_ms: number;
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
      id={`crossmodal-tabpanel-${index}`}
      aria-labelledby={`crossmodal-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const CrossModalFusion: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [contentData, setContentData] = useState<CrossModalContent>({});
  const [selectedFiles, setSelectedFiles] = useState<{[key: string]: File | null}>({
    text: null,
    image: null,
    audio: null,
    video: null,
  });
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [fusionModel, setFusionModel] = useState('clip');
  const fileInputsRef = useRef<{[key: string]: HTMLInputElement | null}>({});

  // Fusion Query
  const {
    data: fusionResult,
    isLoading: fusionLoading,
    refetch: refetchFusion,
  } = useQuery<FusionResult>({
    queryKey: ['fusion', contentData],
    queryFn: async () => {
      if (!Object.keys(contentData).length) throw new Error('No content provided');
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 2500));
      return {
        fusion_id: 'fusion_123',
        modalities_used: Object.keys(contentData).filter(key => contentData[key as keyof CrossModalContent]),
        alignment_score: 0.87,
        correlation_results: [
          { modality_pair: 'text-image', correlation_score: 0.92, description: 'High semantic alignment between text and image content' },
          { modality_pair: 'text-audio', correlation_score: 0.78, description: 'Moderate alignment with audio content' },
          { modality_pair: 'image-audio', correlation_score: 0.85, description: 'Strong visual-audio correlation detected' },
        ],
        unified_representation: { type: 'multimodal_embedding', dimensions: 512 },
        processing_time_ms: 2100
      };
    },
    enabled: !!Object.keys(contentData).length && tabValue === 0,
  });

  // Multi-Modal Search Query
  const {
    data: searchResult,
    isLoading: searchLoading,
    refetch: refetchSearch,
  } = useQuery<MultiModalSearch>({
    queryKey: ['multimodal-search', contentData],
    queryFn: async () => {
      if (!Object.keys(contentData).length) throw new Error('No search content provided');
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 2000));
      return {
        search_id: 'search_123',
        query: contentData,
        results: [
          {
            content_id: 'content_001',
            modalities: ['text', 'image'],
            relevance_score: 0.94,
            matched_modalities: ['text', 'image'],
            content_preview: { title: 'Sample Content 1', description: 'High relevance match' }
          },
          {
            content_id: 'content_002',
            modalities: ['text', 'audio'],
            relevance_score: 0.87,
            matched_modalities: ['text'],
            content_preview: { title: 'Sample Content 2', description: 'Text-based match' }
          },
          {
            content_id: 'content_003',
            modalities: ['image', 'audio'],
            relevance_score: 0.82,
            matched_modalities: ['image'],
            content_preview: { title: 'Sample Content 3', description: 'Visual match' }
          },
        ],
        total_results: 3
      };
    },
    enabled: !!Object.keys(contentData).length && tabValue === 1,
  });

  // Alignment Query
  const {
    data: alignmentResult,
    isLoading: alignmentLoading,
    refetch: refetchAlignment,
  } = useQuery<AlignmentResult>({
    queryKey: ['alignment', contentData],
    queryFn: async () => {
      if (!Object.keys(contentData).length || Object.keys(contentData).length < 2) {
        throw new Error('At least two modalities required for alignment');
      }
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 1800));
      const modalities = Object.keys(contentData).filter(key => contentData[key as keyof CrossModalContent]);
      return {
        alignment_id: 'alignment_123',
        source_modality: modalities[0],
        target_modality: modalities[1],
        alignment_score: 0.89,
        aligned_segments: [
          {
            source_segment: { type: modalities[0], content: 'Sample segment 1' },
            target_segment: { type: modalities[1], content: 'Corresponding segment 1' },
            alignment_score: 0.95
          },
          {
            source_segment: { type: modalities[0], content: 'Sample segment 2' },
            target_segment: { type: modalities[1], content: 'Corresponding segment 2' },
            alignment_score: 0.88
          },
        ],
        processing_time_ms: 1500
      };
    },
    enabled: !!Object.keys(contentData).length && Object.keys(contentData).length >= 2 && tabValue === 2,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFileSelect = (modality: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFiles(prev => ({ ...prev, [modality]: file }));

      // Create preview URL and update content data
      if (modality === 'image') {
        const url = URL.createObjectURL(file);
        setContentData(prev => ({ ...prev, image_url: url }));
      } else if (modality === 'audio') {
        const url = URL.createObjectURL(file);
        setContentData(prev => ({ ...prev, audio_url: url }));
      } else if (modality === 'video') {
        const url = URL.createObjectURL(file);
        setContentData(prev => ({ ...prev, video_url: url }));
      }
    }
  };

  const handleTextChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const text = event.target.value;
    setContentData(prev => ({ ...prev, text }));
  };

  const handleUploadClick = (modality: string) => {
    fileInputsRef.current[modality]?.click();
  };

  const handleRefresh = () => {
    if (tabValue === 0) refetchFusion();
    else if (tabValue === 1) refetchSearch();
    else if (tabValue === 2) refetchAlignment();
  };

  const handleClearContent = () => {
    setContentData({});
    setSelectedFiles({
      text: null,
      image: null,
      audio: null,
      video: null,
    });
  };

  const getModalityIcon = (modality: string) => {
    switch (modality) {
      case 'text':
        return <TextFields />;
      case 'image':
        return <Image />;
      case 'audio':
        return <Audiotrack />;
      case 'video':
        return <Sync />;
      default:
        return <Compare />;
    }
  };

  const getModalityColor = (modality: string) => {
    switch (modality) {
      case 'text':
        return 'primary';
      case 'image':
        return 'secondary';
      case 'audio':
        return 'success';
      case 'video':
        return 'warning';
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
            Cross-Modal Fusion Center
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Unified analysis and search across text, image, audio, and video modalities.
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
            disabled={!Object.keys(contentData).length}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Content Input Section */}
      <Card elevation={0} sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Multi-Modal Content Input
          </Typography>

          <Grid container spacing={3}>
            {/* Text Input */}
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <TextFields sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      Text Content
                    </Typography>
                  </Box>
                  <TextField
                    fullWidth
                    multiline
                    rows={4}
                    placeholder="Enter text content for analysis..."
                    value={contentData.text || ''}
                    onChange={handleTextChange}
                    variant="outlined"
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* File Inputs */}
            <Grid item xs={12} md={6}>
              <Grid container spacing={2}>
                {/* Image Upload */}
                <Grid item xs={12} sm={6}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Image sx={{ mr: 1, color: 'secondary.main' }} />
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          Image
                        </Typography>
                      </Box>
                      <input
                        ref={(el) => { fileInputsRef.current.image = el; }}
                        type="file"
                        accept="image/*"
                        onChange={handleFileSelect('image')}
                        style={{ display: 'none' }}
                      />
                      <Button
                        fullWidth
                        variant="outlined"
                        startIcon={<CloudUpload />}
                        onClick={() => handleUploadClick('image')}
                        size="small"
                      >
                        Upload
                      </Button>
                      {selectedFiles.image && (
                        <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                          {selectedFiles.image.name}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                {/* Audio Upload */}
                <Grid item xs={12} sm={6}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Audiotrack sx={{ mr: 1, color: 'success.main' }} />
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          Audio
                        </Typography>
                      </Box>
                      <input
                        ref={(el) => { fileInputsRef.current.audio = el; }}
                        type="file"
                        accept="audio/*"
                        onChange={handleFileSelect('audio')}
                        style={{ display: 'none' }}
                      />
                      <Button
                        fullWidth
                        variant="outlined"
                        startIcon={<CloudUpload />}
                        onClick={() => handleUploadClick('audio')}
                        size="small"
                      >
                        Upload
                      </Button>
                      {selectedFiles.audio && (
                        <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                          {selectedFiles.audio.name}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Grid>
          </Grid>

          {/* Content Preview */}
          {Object.keys(contentData).length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Content Preview
                </Typography>
                <Button variant="outlined" size="small" onClick={handleClearContent}>
                  Clear All
                </Button>
              </Box>

              <Grid container spacing={2}>
                {contentData.text && (
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                          Text Content
                        </Typography>
                        <Typography variant="body2" sx={{ maxHeight: 100, overflow: 'hidden' }}>
                          {contentData.text}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                )}

                {contentData.image_url && (
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                          Image Preview
                        </Typography>
                        <CardMedia
                          component="img"
                          image={contentData.image_url}
                          alt="Uploaded image"
                          sx={{ height: 100, objectFit: 'cover', borderRadius: 1 }}
                        />
                      </CardContent>
                    </Card>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="cross-modal tabs">
            <Tab icon={<Compare />} label="Fusion Analysis" />
            <Tab icon={<Search />} label="Multi-Modal Search" />
            <Tab icon={<Link />} label="Modality Alignment" />
          </Tabs>
        </CardContent>

        {/* Fusion Analysis Tab */}
        <TabPanel value={tabValue} index={0}>
          {!Object.keys(contentData).length ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Compare sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Add content from multiple modalities to begin fusion analysis
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Combine text, images, and audio for unified understanding
              </Typography>
            </Box>
          ) : fusionLoading ? (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Fusing Multi-Modal Content...</Typography>
              <LinearProgress sx={{ mb: 3 }} />
              <Grid container spacing={3}>
                {[...Array(6)].map((_, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : fusionResult ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Fusion Overview
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Modalities Used:</Typography>
                        <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                          {fusionResult.modalities_used.map((modality, index) => (
                            <Chip
                              key={index}
                              label={modality}
                              size="small"
                              color={getModalityColor(modality) as any}
                              icon={getModalityIcon(modality)}
                            />
                          ))}
                        </Box>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Alignment Score:</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {(fusionResult.alignment_score * 100).toFixed(1)}%
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Processing Time:</Typography>
                        <Typography variant="body2">{fusionResult.processing_time_ms}ms</Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Correlation Results
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {fusionResult.correlation_results?.map((correlation, index) => (
                        <Card key={index} variant="outlined">
                          <CardContent sx={{ pb: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                {correlation.modality_pair}
                              </Typography>
                              <Chip
                                label={`${(correlation.correlation_score * 100).toFixed(1)}%`}
                                size="small"
                                color="primary"
                              />
                            </Box>
                            <Typography variant="body2" color="text.secondary">
                              {correlation.description}
                            </Typography>
                          </CardContent>
                        </Card>
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No fusion results available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Multi-Modal Search Tab */}
        <TabPanel value={tabValue} index={1}>
          {!Object.keys(contentData).length ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Search sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Add content to perform multi-modal search
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Search across all modalities simultaneously
              </Typography>
            </Box>
          ) : searchLoading ? (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Searching Multi-Modal Content...</Typography>
              <LinearProgress sx={{ mb: 3 }} />
              <Skeleton variant="rectangular" width="100%" height={300} sx={{ borderRadius: 1 }} />
            </Box>
          ) : searchResult ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Search Results ({searchResult.total_results} found)
                </Typography>
              </Grid>

              {searchResult.results?.map((result, index) => (
                <Grid item xs={12} md={6} lg={4} key={index}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                          {result.content_preview.title}
                        </Typography>
                        <Chip
                          label={`${(result.relevance_score * 100).toFixed(1)}%`}
                          size="small"
                          color="primary"
                        />
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Modalities:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          {result.modalities.map((modality, idx) => (
                            <Chip
                              key={idx}
                              label={modality}
                              size="small"
                              variant="outlined"
                              color={getModalityColor(modality) as any}
                              icon={getModalityIcon(modality)}
                            />
                          ))}
                        </Box>
                      </Box>

                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Matched Modalities:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          {result.matched_modalities.map((modality, idx) => (
                            <Chip
                              key={idx}
                              label={modality}
                              size="small"
                              color={getModalityColor(modality) as any}
                            />
                          ))}
                        </Box>
                      </Box>

                      <Typography variant="body2" sx={{ mt: 2 }}>
                        {result.content_preview.description}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )) || (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    No search results found
                  </Typography>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No search results available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Modality Alignment Tab */}
        <TabPanel value={tabValue} index={2}>
          {Object.keys(contentData).length < 2 ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Link sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Add content from at least two modalities for alignment analysis
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Alignment requires multiple modalities to correlate
              </Typography>
            </Box>
          ) : alignmentLoading ? (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Aligning Modalities...</Typography>
              <LinearProgress sx={{ mb: 3 }} />
              <Skeleton variant="rectangular" width="100%" height={300} sx={{ borderRadius: 1 }} />
            </Box>
          ) : alignmentResult ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Alignment Overview
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Source Modality:</Typography>
                        <Chip
                          label={alignmentResult.source_modality}
                          color={getModalityColor(alignmentResult.source_modality) as any}
                          icon={getModalityIcon(alignmentResult.source_modality)}
                          sx={{ mt: 0.5 }}
                        />
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Target Modality:</Typography>
                        <Chip
                          label={alignmentResult.target_modality}
                          color={getModalityColor(alignmentResult.target_modality) as any}
                          icon={getModalityIcon(alignmentResult.target_modality)}
                          sx={{ mt: 0.5 }}
                        />
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Alignment Score:</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {(alignmentResult.alignment_score * 100).toFixed(1)}%
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Processing Time:</Typography>
                        <Typography variant="body2">{alignmentResult.processing_time_ms}ms</Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Aligned Segments
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {alignmentResult.aligned_segments?.map((segment, index) => (
                        <Card key={index} variant="outlined">
                          <CardContent sx={{ pb: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                Segment {index + 1}
                              </Typography>
                              <Chip
                                label={`${(segment.alignment_score * 100).toFixed(1)}%`}
                                size="small"
                                color="primary"
                              />
                            </Box>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                              <Box>
                                <Typography variant="caption" color="text.secondary">
                                  {segment.source_segment.type}:
                                </Typography>
                                <Typography variant="body2">
                                  {typeof segment.source_segment.content === 'string'
                                    ? segment.source_segment.content
                                    : JSON.stringify(segment.source_segment.content)
                                  }
                                </Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">
                                  {segment.target_segment.type}:
                                </Typography>
                                <Typography variant="body2">
                                  {typeof segment.target_segment.content === 'string'
                                    ? segment.target_segment.content
                                    : JSON.stringify(segment.target_segment.content)
                                  }
                                </Typography>
                              </Box>
                            </Box>
                          </CardContent>
                        </Card>
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No alignment results available
              </Typography>
            </Box>
          )}
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
            <Typography variant="h6">Cross-Modal Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure cross-modal processing and fusion settings.
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Fusion Model</InputLabel>
                <Select value={fusionModel} onChange={(e) => setFusionModel(e.target.value)}>
                  <MenuItem value="clip">CLIP (Contrastive Language-Image Pretraining)</MenuItem>
                  <MenuItem value="blip">BLIP (Bootstrapping Language-Image Pretraining)</MenuItem>
                  <MenuItem value="flava">FLAVA (Foundational Language And Vision Alignment)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Alignment Algorithm</InputLabel>
                <Select defaultValue="attention">
                  <MenuItem value="attention">Attention-based Alignment</MenuItem>
                  <MenuItem value="similarity">Similarity-based Alignment</MenuItem>
                  <MenuItem value="transformer">Transformer-based Alignment</MenuItem>
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

export default CrossModalFusion;