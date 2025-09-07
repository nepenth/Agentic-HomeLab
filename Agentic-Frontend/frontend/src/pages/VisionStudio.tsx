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
} from '@mui/material';
import {
  Image,
  Search,
  TextFields,
  Upload,
  Refresh,
  Settings,
  Assessment,
  Visibility,
  PhotoCamera,
  CloudUpload,
  GetApp,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

// Define vision AI types locally for now
interface VisionAnalysis {
  analysis_id: string;
  image_url?: string;
  results: {
    objects?: Array<{
      label: string;
      confidence: number;
      bbox: [number, number, number, number];
    }>;
    caption?: string;
    ocr_text?: string;
    scene?: string;
    quality_score?: number;
  };
  processing_time_ms: number;
  model_used: string;
}

interface VisualSearch {
  search_id: string;
  query_image?: string;
  results: Array<{
    image_url: string;
    similarity_score: number;
    metadata: any;
  }>;
  total_results: number;
}

interface OCRResult {
  text: string;
  confidence: number;
  language: string;
  regions: Array<{
    text: string;
    bbox: [number, number, number, number];
    confidence: number;
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
      id={`vision-tabpanel-${index}`}
      aria-labelledby={`vision-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const VisionStudio: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [analysisModel, setAnalysisModel] = useState('llava:13b');
  const [searchQuery, setSearchQuery] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Vision Analysis Query
  const {
    data: visionAnalysis,
    isLoading: analysisLoading,
    refetch: refetchAnalysis,
  } = useQuery<VisionAnalysis>({
    queryKey: ['vision-analysis', selectedImage],
    queryFn: async () => {
      if (!selectedImage) throw new Error('No image selected');
      // Convert image to base64 for API
      const reader = new FileReader();
      return new Promise((resolve, reject) => {
        reader.onload = async () => {
          try {
            const base64 = reader.result as string;
            const result = await apiClient.analyzeImage({
              image_data: base64.split(',')[1], // Remove data:image/jpeg;base64, prefix
              tasks: ['objects', 'caption', 'ocr'],
              model: analysisModel
            });
            resolve(result);
          } catch (error) {
            reject(error);
          }
        };
        reader.onerror = () => reject(new Error('Failed to read image'));
        reader.readAsDataURL(selectedImage);
      });
    },
    enabled: !!selectedImage,
  });

  // Visual Search Query
  const {
    data: visualSearch,
    isLoading: searchLoading,
    refetch: refetchSearch,
  } = useQuery<VisualSearch>({
    queryKey: ['visual-search', selectedImage],
    queryFn: async () => {
      if (!selectedImage) throw new Error('No image selected');
      // Convert image to base64 for API
      const reader = new FileReader();
      return new Promise((resolve, reject) => {
        reader.onload = async () => {
          try {
            const base64 = reader.result as string;
            const result = await apiClient.findSimilarImages({
              image_data: base64.split(',')[1], // Remove data:image/jpeg;base64, prefix
              limit: 10
            });
            resolve(result);
          } catch (error) {
            reject(error);
          }
        };
        reader.onerror = () => reject(new Error('Failed to read image'));
        reader.readAsDataURL(selectedImage);
      });
    },
    enabled: !!selectedImage && tabValue === 1,
  });

  // OCR Analysis Query
  const {
    data: ocrResult,
    isLoading: ocrLoading,
    refetch: refetchOCR,
  } = useQuery<OCRResult>({
    queryKey: ['ocr-analysis', selectedImage],
    queryFn: async () => {
      if (!selectedImage) throw new Error('No image selected');
      // Convert image to base64 for API
      const reader = new FileReader();
      return new Promise((resolve, reject) => {
        reader.onload = async () => {
          try {
            const base64 = reader.result as string;
            const result = await apiClient.extractTextFromImage({
              image_data: base64.split(',')[1], // Remove data:image/jpeg;base64, prefix
              language: 'en'
            });
            resolve(result);
          } catch (error) {
            reject(error);
          }
        };
        reader.onerror = () => reject(new Error('Failed to read image'));
        reader.readAsDataURL(selectedImage);
      });
    },
    enabled: !!selectedImage && tabValue === 2,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleRefresh = () => {
    if (tabValue === 0) refetchAnalysis();
    else if (tabValue === 1) refetchSearch();
    else if (tabValue === 2) refetchOCR();
  };

  const handleClearImage = () => {
    setSelectedImage(null);
    setImagePreview('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Vision AI Studio
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Advanced image analysis, visual search, and OCR processing powered by AI.
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
            disabled={!selectedImage}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Image Upload Section */}
      <Card elevation={0} sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={8}>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
                <Button
                  variant="outlined"
                  startIcon={<CloudUpload />}
                  onClick={handleUploadClick}
                  sx={{ minWidth: 200 }}
                >
                  Upload Image
                </Button>
                {selectedImage && (
                  <Button
                    variant="outlined"
                    color="error"
                    onClick={handleClearImage}
                  >
                    Clear
                  </Button>
                )}
                <FormControl sx={{ minWidth: 150 }}>
                  <InputLabel>Model</InputLabel>
                  <Select
                    value={analysisModel}
                    label="Model"
                    onChange={(e) => setAnalysisModel(e.target.value)}
                  >
                    <MenuItem value="llava:13b">LLaVA 13B</MenuItem>
                    <MenuItem value="moondream:1.8b">Moondream 1.8B</MenuItem>
                    <MenuItem value="bakllava:7b">BakLLaVA 7B</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              {selectedImage && (
                <Typography variant="body2" color="text.secondary">
                  Selected: {selectedImage.name} ({(selectedImage.size / 1024 / 1024).toFixed(2)} MB)
                </Typography>
              )}
            </Grid>
          </Grid>

          {/* Image Preview */}
          {imagePreview && (
            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Card sx={{ maxWidth: 400, mx: 'auto' }}>
                <CardMedia
                  component="img"
                  image={imagePreview}
                  alt="Selected image"
                  sx={{ height: 300, objectFit: 'contain' }}
                />
              </Card>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="vision tabs">
            <Tab icon={<Assessment />} label="Image Analysis" />
            <Tab icon={<Search />} label="Visual Search" />
            <Tab icon={<TextFields />} label="OCR Processing" />
          </Tabs>
        </CardContent>

        {/* Image Analysis Tab */}
        <TabPanel value={tabValue} index={0}>
          {!selectedImage ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Image sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Upload an image to begin analysis
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Supported formats: JPEG, PNG, WebP, GIF
              </Typography>
            </Box>
          ) : analysisLoading ? (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Analyzing Image...</Typography>
              <LinearProgress sx={{ mb: 3 }} />
              <Grid container spacing={3}>
                {[...Array(6)].map((_, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : visionAnalysis ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Object Detection
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {visionAnalysis.results.objects?.map((obj, index) => (
                        <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="body2">{obj.label}</Typography>
                          <Chip
                            label={`${(obj.confidence * 100).toFixed(1)}%`}
                            size="small"
                            color="primary"
                          />
                        </Box>
                      )) || (
                        <Typography variant="body2" color="text.secondary">
                          No objects detected
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Image Caption
                    </Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {visionAnalysis.results.caption || 'No caption generated'}
                    </Typography>

                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, mt: 3 }}>
                      Scene Analysis
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {visionAnalysis.results.scene || 'No scene analysis available'}
                    </Typography>

                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        Quality Score: {visionAnalysis.results.quality_score
                          ? `${(visionAnalysis.results.quality_score * 100).toFixed(1)}%`
                          : 'N/A'
                        }
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Processing Time: {visionAnalysis.processing_time_ms}ms
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Model: {visionAnalysis.model_used}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No analysis results available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Visual Search Tab */}
        <TabPanel value={tabValue} index={1}>
          {!selectedImage ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Search sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Upload an image to search for similar images
              </Typography>
            </Box>
          ) : searchLoading ? (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Searching...</Typography>
              <LinearProgress sx={{ mb: 3 }} />
              <Grid container spacing={3}>
                {[...Array(8)].map((_, index) => (
                  <Grid item xs={12} sm={6} md={3} key={index}>
                    <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : visualSearch ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Similar Images Found ({visualSearch.total_results})
                </Typography>
              </Grid>
              {visualSearch.results?.map((result, index) => (
                <Grid item xs={12} sm={6} md={3} key={index}>
                  <Card elevation={1} sx={{ height: '100%' }}>
                    <CardMedia
                      component="img"
                      image={result.image_url}
                      alt={`Similar image ${index + 1}`}
                      sx={{ height: 150, objectFit: 'cover' }}
                    />
                    <CardContent sx={{ pb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2">Similarity:</Typography>
                        <Chip
                          label={`${(result.similarity_score * 100).toFixed(1)}%`}
                          size="small"
                          color="primary"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              )) || (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    No similar images found
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

        {/* OCR Processing Tab */}
        <TabPanel value={tabValue} index={2}>
          {!selectedImage ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <TextFields sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Upload an image to extract text
              </Typography>
            </Box>
          ) : ocrLoading ? (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Extracting Text...</Typography>
              <LinearProgress sx={{ mb: 3 }} />
              <Skeleton variant="rectangular" width="100%" height={200} sx={{ borderRadius: 1 }} />
            </Box>
          ) : ocrResult ? (
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Extracted Text
                    </Typography>
                    <Box sx={{
                      p: 2,
                      bgcolor: 'grey.50',
                      borderRadius: 1,
                      minHeight: 150,
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace'
                    }}>
                      {ocrResult.text || 'No text extracted'}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Analysis Details
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Language:</Typography>
                        <Typography variant="body2">{ocrResult.language || 'Unknown'}</Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Confidence:</Typography>
                        <Typography variant="body2">
                          {ocrResult.confidence ? `${(ocrResult.confidence * 100).toFixed(1)}%` : 'N/A'}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Text Regions:</Typography>
                        <Typography variant="body2">{ocrResult.regions?.length || 0}</Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No OCR results available
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
            <Typography variant="h6">Vision AI Settings</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure vision AI processing settings and preferences.
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Default Analysis Model</InputLabel>
                <Select value={analysisModel} onChange={(e) => setAnalysisModel(e.target.value)}>
                  <MenuItem value="llava:13b">LLaVA 13B (High Quality)</MenuItem>
                  <MenuItem value="moondream:1.8b">Moondream 1.8B (Fast)</MenuItem>
                  <MenuItem value="bakllava:7b">BakLLaVA 7B (Balanced)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Image Quality</InputLabel>
                <Select defaultValue="high">
                  <MenuItem value="high">High (Best Results)</MenuItem>
                  <MenuItem value="medium">Medium (Balanced)</MenuItem>
                  <MenuItem value="low">Low (Fast Processing)</MenuItem>
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

export default VisionStudio;