import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardHeader,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress,
  Paper,
  Fade,
  useTheme,
  alpha,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Upload as UploadIcon,
  PictureAsPdf as PdfIcon,
  Description as DocxIcon,
  Refresh as RefreshIcon,
  ModelTraining as ModelIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Psychology as PsychologyIcon,
  Image as ImageIcon,
  TextFields as TextFieldsIcon,
  CloudUpload as CloudUploadIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Download as DownloadIcon,
  Settings as SettingsIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
  Queue as QueueIcon,
  Delete as DeleteIcon,
  DeleteSweep as DeleteSweepIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import apiClient from '../services/api';
import webSocketService from '../services/websocket';
import ModelSelector from '../components/EmailAssistant/ModelSelector';
import type { OCRWorkflow, OCRBatch, OCRImage } from '../types';

// OCR Model Selector using the shared ModelSelector component
interface OCRModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
}

const OCRModelSelector: React.FC<OCRModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  disabled = false
}) => {
  return (
    <ModelSelector
      selectedModel={selectedModel}
      onModelChange={onModelChange}
      disabled={disabled}
      showStatus={true}
      capabilityFilter="vision"
    />
  );
};

const OCRWorkflow: React.FC = () => {
  const theme = useTheme();
  const [selectedModel, setSelectedModel] = useState<string>('deepseek-ocr');
  const [images, setImages] = useState<File[]>([]);
  const [batchName, setBatchName] = useState<string>('Document Scan');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [results, setResults] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [workflowId, setWorkflowId] = useState<string>('');
  const [status, setStatus] = useState<string>('idle');
  const [progress, setProgress] = useState<{ current: number; total: number; message: string } | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsDebug, setLogsDebug] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [queueItems, setQueueItems] = useState<any[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueExpanded, setQueueExpanded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const webSocketUnsubscribeRef = useRef<(() => void) | null>(null);

  // Cleanup WebSocket subscriptions on unmount
  useEffect(() => {
    return () => {
      if (webSocketUnsubscribeRef.current) {
        webSocketUnsubscribeRef.current();
        webSocketUnsubscribeRef.current = null;
      }
    };
  }, []);

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files).filter(file =>
      file.type.startsWith('image/')
    );

    if (files.length > 0) {
      setImages(prev => [...prev, ...files]);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      setImages(prev => [...prev, ...files]);
    }
  };

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  const startOCRWorkflow = async () => {
    console.log('=== START OCR WORKFLOW CALLED ===');
    console.log('Images selected:', images.length);
    console.log('Selected model:', selectedModel);
    console.log('Is processing:', isProcessing);

    if (images.length === 0) {
      console.log('No images selected, returning early');
      setError('Please select at least one image');
      return;
    }

    if (!selectedModel) {
      console.log('No model selected, returning early');
      setError('Please select an OCR model');
      return;
    }

    console.log('Starting OCR workflow with model:', selectedModel);
    setIsProcessing(true);
    setError('');
    setStatus('processing');
    setProgress({ current: 0, total: images.length, message: 'Initializing OCR workflow...' });

    try {
      console.log('Creating workflow...');
      // Create workflow
      const workflowResponse = await apiClient.createOCRWorkflow({
        workflow_name: batchName,
        ocr_model: selectedModel,
      });
      console.log('Workflow created:', workflowResponse);
      setWorkflowId(workflowResponse.workflow_id);

      console.log('Uploading batch...');
      // Upload batch
      const batchResponse = await apiClient.uploadOCRBatch(workflowResponse.workflow_id, {
        batch_name: batchName,
        images: images,
      });
      console.log('Batch uploaded:', batchResponse);

      console.log('Triggering processing...');
      // Trigger processing
      await apiClient.processOCRWorkflow(workflowResponse.workflow_id, {
        batch_id: batchResponse.batch_id,
      });
      console.log('Processing triggered');

      // Load initial logs
      console.log('Loading initial logs...');
      loadLogs(true);

      // Subscribe to WebSocket updates for this workflow
      console.log('Subscribing to WebSocket updates for workflow:', workflowResponse.workflow_id);
      const unsubscribe = webSocketService.subscribeToOCRProgress(
        workflowResponse.workflow_id,
        (update: any) => {
          console.log('Received WebSocket update:', update);

          if (update.type === 'ocr_workflow_status') {
            const workflowData = update.data || update;

            if (workflowData.status === 'completed') {
              // Workflow completed successfully
              if (workflowData.progress?.processed_images > 0) {
                // Load final results
                apiClient.getOCRWorkflowResults(workflowResponse.workflow_id).then(resultResponse => {
                  setResults(resultResponse.combined_markdown);
                  setStatus('completed');
                  setProgress(null);
                  setIsProcessing(false);
                  setShowResults(true);
                  // Load final logs
                  loadLogs(true);
                }).catch(err => {
                  console.error('Failed to load results:', err);
                  setError('Failed to load OCR results');
                  setIsProcessing(false);
                  setStatus('error');
                  setProgress(null);
                });
              } else {
                // No images processed - this is a failure
                setError('OCR processing failed - no images were successfully processed');
                setIsProcessing(false);
                setStatus('failed');
                setProgress(null);
              }

              // Unsubscribe from WebSocket updates
              if (webSocketUnsubscribeRef.current) {
                webSocketUnsubscribeRef.current();
                webSocketUnsubscribeRef.current = null;
              }
            } else if (workflowData.status === 'failed') {
              setError('OCR processing failed');
              setIsProcessing(false);
              setStatus('failed');
              setProgress(null);

              // Load error logs
              loadLogs(true);

              // Unsubscribe from WebSocket updates
              if (webSocketUnsubscribeRef.current) {
                webSocketUnsubscribeRef.current();
                webSocketUnsubscribeRef.current = null;
              }
            } else {
              // Update progress for running workflows
              const totalImages = workflowData.progress?.total_images || images.length;
              const processedImages = workflowData.progress?.processed_images || 0;
              setProgress({
                current: processedImages,
                total: totalImages,
                message: `Processing ${processedImages}/${totalImages} images...`
              });
            }
          }
        }
      );

      // Store unsubscribe function for cleanup
      webSocketUnsubscribeRef.current = unsubscribe;

    } catch (err: any) {
      console.error('OCR workflow failed:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'OCR workflow failed';
      console.error('Error details:', errorMessage);
      setError(errorMessage);
      setIsProcessing(false);
      setStatus('error');
      setProgress(null);
    }
  };

  const exportResult = async (format: 'pdf' | 'docx') => {
    try {
      const response = await apiClient.exportOCRResults(workflowId, { format });
      const url = response.download_url;
      const a = document.createElement('a');
      a.href = url;
      a.download = `${batchName}.${format}`;
      a.click();
    } catch (err) {
      setError('Export failed');
    }
  };

  const loadLogs = async (background = false) => {
    console.log(`loadLogs called: background=${background}, workflowId=${workflowId}, current logs=${logs.length}`);
    if (!workflowId && !background) {
      console.log('loadLogs: No workflowId and not background, returning');
      return;
    }

    try {
      if (!background) {
        console.log('loadLogs: Setting loading to true');
        setLogsLoading(true);
      }

      let logsResponse;
      if (workflowId) {
        console.log(`loadLogs: Fetching logs for workflow ${workflowId}`);
        logsResponse = await apiClient.getOCRWorkflowLogs(workflowId);
        console.log(`loadLogs: Got ${logsResponse.logs?.length || 0} logs from API`);
      } else {
        // If no workflowId yet, try to get recent logs for current user
        // This is a fallback for when logs are created before workflowId is set
        console.log('loadLogs: No workflowId, using empty logs');
        logsResponse = { logs: [] };
      }

      // Sort logs by timestamp descending if not already
      const sortedLogs = (logsResponse.logs || []).sort((a: any, b: any) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

      console.log(`loadLogs: Setting ${sortedLogs.length} logs in state`);
      setLogsDebug(prev => [...prev, `Set ${sortedLogs.length} logs at ${new Date().toLocaleTimeString()}`]);
      setLogs(sortedLogs);

      // If no logs found and we're in background mode, try again in 1 second
      if (background && sortedLogs.length === 0 && workflowId) {
        console.log('loadLogs: No logs found, retrying in 1 second...');
        setTimeout(() => loadLogs(true), 1000);
      }
    } catch (err) {
      console.error('loadLogs: Failed to load logs:', err);
      // If background loading fails, retry once after a delay
      if (background && workflowId) {
        console.log('loadLogs: Log loading failed, retrying in 2 seconds...');
        setTimeout(() => loadLogs(true), 2000);
      }
    } finally {
      if (!background) {
        console.log('loadLogs: Setting loading to false');
        setLogsLoading(false);
      }
    }
  };

  const resetWorkflow = () => {
    console.log('resetWorkflow: Clearing all state');
    setLogsDebug(prev => [...prev, `Reset workflow at ${new Date().toLocaleTimeString()}`]);

    // Clean up WebSocket subscription
    if (webSocketUnsubscribeRef.current) {
      webSocketUnsubscribeRef.current();
      webSocketUnsubscribeRef.current = null;
    }

    setImages([]);
    setBatchName('Document Scan');
    setResults('');
    setError('');
    setWorkflowId('');
    setStatus('idle');
    setProgress(null);
    setShowResults(false);
    setLogs([]);
    setLogsExpanded(false);
  };

  const loadQueueStatus = async () => {
    try {
      setQueueLoading(true);
      const queueResponse = await apiClient.getOCRQueueStatus();
      setQueueItems(queueResponse.queue_items || []);
    } catch (err) {
      console.error('Failed to load queue status:', err);
    } finally {
      setQueueLoading(false);
    }
  };

  const cancelWorkflow = async (workflowId: string) => {
    try {
      await apiClient.cancelOCRWorkflow(workflowId);
      // Reload queue after cancellation
      await loadQueueStatus();
      setError('');
    } catch (err: any) {
      console.error('Failed to cancel workflow:', err);
      setError(err.response?.data?.detail || 'Failed to cancel workflow');
    }
  };

  const clearAllWorkflows = async () => {
    try {
      await apiClient.clearAllOCRWorkflows();
      // Reload queue after clearing
      await loadQueueStatus();
      setError('');
    } catch (err: any) {
      console.error('Failed to clear all workflows:', err);
      setError(err.response?.data?.detail || 'Failed to clear all workflows');
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h3"
          sx={{
            fontWeight: 700,
            background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            mb: 2
          }}
        >
          OCR Workflow
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
          Transform images into editable documents with AI-powered OCR
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload screenshots, scanned documents, or images to extract text and convert them to structured markdown documents.
        </Typography>
      </Box>

      <Grid container spacing={4}>
        {/* Left Panel - Configuration */}
        <Grid item xs={12} lg={4}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

            {/* Model Selection */}
            <Card sx={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(0,0,0,0.08)',
              borderRadius: 3
            }}>
              <CardHeader
                title="AI Model"
                titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                avatar={<PsychologyIcon sx={{ color: '#007AFF' }} />}
              />
              <CardContent>
                <OCRModelSelector
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  disabled={isProcessing}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Choose an AI model optimized for document text extraction and image understanding.
                </Typography>
              </CardContent>
            </Card>

            {/* Document Settings */}
            <Card sx={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(0,0,0,0.08)',
              borderRadius: 3
            }}>
              <CardHeader
                title="Document Settings"
                titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                avatar={<SettingsIcon sx={{ color: '#007AFF' }} />}
              />
              <CardContent>
                <input
                  type="text"
                  placeholder="Document name"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    border: '1px solid rgba(0, 0, 0, 0.12)',
                    borderRadius: '8px',
                    fontSize: '0.9rem',
                    outline: 'none',
                    backgroundColor: 'background.paper'
                  }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Give your document a descriptive name for easy identification.
                </Typography>
              </CardContent>
            </Card>

            {/* File Upload */}
            <Card sx={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(0,0,0,0.08)',
              borderRadius: 3
            }}>
              <CardHeader
                title="Upload Images"
                titleTypographyProps={{ variant: 'h6', fontWeight: 600 }}
                avatar={<CloudUploadIcon sx={{ color: '#007AFF' }} />}
              />
              <CardContent>
                {/* Drag & Drop Zone */}
                <Box
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  sx={{
                    border: `2px dashed ${dragOver ? '#007AFF' : 'rgba(0, 0, 0, 0.12)'}`,
                    borderRadius: 2,
                    p: 3,
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    backgroundColor: dragOver ? 'rgba(0, 122, 255, 0.05)' : 'transparent',
                    '&:hover': {
                      borderColor: '#007AFF',
                      backgroundColor: 'rgba(0, 122, 255, 0.05)'
                    }
                  }}
                >
                  <ImageIcon sx={{ fontSize: '3rem', color: dragOver ? '#007AFF' : 'text.secondary', mb: 1 }} />
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    {dragOver ? 'Drop images here' : 'Drag & drop images'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    or click to browse files
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Supports: JPG, PNG, GIF, WebP
                  </Typography>
                </Box>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />

                {/* Uploaded Images Preview */}
                {images.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      {images.length} image{images.length !== 1 ? 's' : ''} selected
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {images.map((image, index) => (
                        <Box key={index} sx={{ position: 'relative' }}>
                          <Avatar
                            src={URL.createObjectURL(image)}
                            variant="rounded"
                            sx={{ width: 60, height: 60 }}
                          />
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeImage(index);
                            }}
                            sx={{
                              position: 'absolute',
                              top: -8,
                              right: -8,
                              backgroundColor: 'rgba(255, 255, 255, 0.9)',
                              '&:hover': { backgroundColor: 'white' }
                            }}
                          >
                            <ClearIcon sx={{ fontSize: '1rem' }} />
                          </IconButton>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                fullWidth
                variant="contained"
                onClick={() => {
                  console.log('=== BUTTON CLICKED ===');
                  startOCRWorkflow();
                }}
                disabled={isProcessing || images.length === 0}
                startIcon={isProcessing ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                sx={{
                  py: 1.5,
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, #007AFF 0%, #5856D6 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #0056CC 0%, #4A4AC0 100%)'
                  }
                }}
              >
                {isProcessing ? 'Processing...' : 'Start OCR'}
              </Button>

              {(results || error) && (
                <Button
                  variant="outlined"
                  onClick={resetWorkflow}
                  startIcon={<RefreshIcon />}
                  sx={{ borderRadius: 2 }}
                >
                  New Scan
                </Button>
              )}
            </Box>
          </Box>
        </Grid>

        {/* Right Panel - Results */}
        <Grid item xs={12} lg={8}>
          <Card sx={{
            height: '100%',
            background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(0,0,0,0.08)',
            borderRadius: 3,
            display: 'flex',
            flexDirection: 'column'
          }}>
            <CardHeader
              title={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TextFieldsIcon sx={{ color: '#007AFF' }} />
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    OCR Results
                  </Typography>
                </Box>
              }
              action={
                showResults && (
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Export as PDF">
                      <IconButton onClick={() => exportResult('pdf')} size="small">
                        <PdfIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Export as DOCX">
                      <IconButton onClick={() => exportResult('docx')} size="small">
                        <DocxIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                )
              }
            />

            <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>

              {/* Status Messages */}
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {status === 'completed' && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  OCR processing completed successfully!
                </Alert>
              )}

              {/* Progress */}
              {progress && (
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                    <CircularProgress size={20} />
                    <Typography variant="body2">
                      {progress.message}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(progress.current / progress.total) * 100}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {progress.current} of {progress.total} images processed
                  </Typography>
                </Box>
              )}

              {/* Results Display */}
              {showResults && results ? (
                <Box sx={{
                  flex: 1,
                  border: '1px solid rgba(0, 0, 0, 0.08)',
                  borderRadius: 2,
                  overflow: 'hidden',
                  backgroundColor: 'grey.50'
                }}>
                  <Box sx={{
                    maxHeight: 600,
                    overflow: 'auto',
                    p: 3,
                    '&::-webkit-scrollbar': {
                      width: '8px',
                    },
                    '&::-webkit-scrollbar-track': {
                      backgroundColor: 'rgba(0,0,0,0.05)',
                    },
                    '&::-webkit-scrollbar-thumb': {
                      backgroundColor: 'rgba(0,0,0,0.2)',
                      borderRadius: '4px',
                    }
                  }}>
                    <ReactMarkdown
                      components={{
                        code: ({ node, className, children, ...props }: any) => {
                          const match = /language-(\w+)/.exec(className || '');
                          const isInline = !match;
                          return !isInline && match ? (
                            <SyntaxHighlighter
                              style={vscDarkPlus}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          );
                        },
                      }}
                    >
                      {results}
                    </ReactMarkdown>
                  </Box>
                </Box>
              ) : (
                <Box sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  py: 8,
                  textAlign: 'center'
                }}>
                  <TextFieldsIcon sx={{ fontSize: '4rem', color: 'text.disabled', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                    No OCR Results Yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Upload some images and start processing to see extracted text here
                  </Typography>
                </Box>
              )}

              {/* Logs Section */}
              {(workflowId || isProcessing || logs.length > 0) && (
                <Box sx={{ mt: 3 }}>
                  <Divider sx={{ mb: 2 }} />
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      py: 1,
                      px: 2,
                      borderRadius: 1,
                      '&:hover': { backgroundColor: 'action.hover' }
                    }}
                    onClick={() => {
                      const newExpanded = !logsExpanded;
                      setLogsExpanded(newExpanded);
                      if (newExpanded && logs.length === 0 && !logsLoading) {
                        loadLogs();
                      }
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <InfoIcon sx={{ color: 'text.secondary' }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        Processing Logs
                      </Typography>
                      {logs.length > 0 && (
                        <Chip
                          label={`${logs.length} entries`}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      )}
                      {logsLoading && (
                        <CircularProgress size={14} />
                      )}
                      {isProcessing && logs.length === 0 && (
                        <Typography variant="caption" color="text.secondary">
                          Processing...
                        </Typography>
                      )}
                    </Box>
                    {logsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </Box>

                  <Collapse in={logsExpanded} timeout="auto">
                    <Box sx={{
                      mt: 2,
                      maxHeight: 300,
                      overflow: 'auto',
                      border: '1px solid rgba(0, 0, 0, 0.08)',
                      borderRadius: 1,
                      backgroundColor: 'grey.50'
                    }}>
                      {logsLoading ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 4 }}>
                          <CircularProgress size={20} />
                          <Typography variant="body2" sx={{ ml: 1 }}>
                            Loading logs...
                          </Typography>
                        </Box>
                      ) : logs.length > 0 ? (
                        <List dense sx={{ py: 0 }}>
                          {logs.map((log, index) => (
                            <ListItem key={index} sx={{ py: 0.5, px: 2 }}>
                              <ListItemIcon sx={{ minWidth: 30 }}>
                                {log.level === 'error' ? (
                                  <ErrorIcon sx={{ fontSize: '1rem', color: 'error.main' }} />
                                ) : log.level === 'warning' ? (
                                  <ErrorIcon sx={{ fontSize: '1rem', color: 'warning.main' }} />
                                ) : log.level === 'info' ? (
                                  <InfoIcon sx={{ fontSize: '1rem', color: 'info.main' }} />
                                ) : (
                                  <CheckCircleIcon sx={{ fontSize: '1rem', color: 'success.main' }} />
                                )}
                              </ListItemIcon>
                              <ListItemText
                                primary={
                                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                                    {log.message}
                                  </Typography>
                                }
                                secondary={
                                  <Typography variant="caption" color="text.secondary">
                                    {new Date(log.timestamp).toLocaleString()} • {log.workflow_phase || 'General'}
                                  </Typography>
                                }
                              />
                            </ListItem>
                          ))}
                        </List>
                      ) : (
                        <Box sx={{ textAlign: 'center', py: 4 }}>
                          <Typography variant="body2" color="text.secondary">
                            No logs available yet
                          </Typography>
                          {logsDebug.length > 0 && (
                            <Box sx={{ mt: 2, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                              <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                                Debug: {logsDebug.slice(-3).join(' | ')}
                              </Typography>
                            </Box>
                          )}
                        </Box>
                      )}
                    </Box>
                  </Collapse>
                </Box>
              )}

              {/* Queue Management Section */}
              <Box sx={{ mt: 3 }}>
                <Divider sx={{ mb: 2 }} />
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    py: 1,
                    px: 2,
                    borderRadius: 1,
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => {
                    setQueueExpanded(!queueExpanded);
                    if (!queueExpanded) {
                      loadQueueStatus();
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <QueueIcon sx={{ color: 'text.secondary' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Queue Management
                    </Typography>
                    {queueItems.length > 0 && (
                      <Chip
                        label={`${queueItems.length} active`}
                        size="small"
                        variant="outlined"
                        color="warning"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    )}
                    {queueLoading && (
                      <CircularProgress size={14} />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {queueItems.length > 0 && (
                      <Tooltip title="Clear All Workflows">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            clearAllWorkflows();
                          }}
                          sx={{ color: 'error.main' }}
                        >
                          <DeleteSweepIcon sx={{ fontSize: '1rem' }} />
                        </IconButton>
                      </Tooltip>
                    )}
                    <IconButton size="small" onClick={() => loadQueueStatus()}>
                      <RefreshIcon sx={{ fontSize: '1rem' }} />
                    </IconButton>
                    {queueExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </Box>
                </Box>

                <Collapse in={queueExpanded} timeout="auto">
                  <Box sx={{
                    mt: 2,
                    maxHeight: 400,
                    overflow: 'auto',
                    border: '1px solid rgba(0, 0, 0, 0.08)',
                    borderRadius: 1,
                    backgroundColor: 'grey.50'
                  }}>
                    {queueLoading ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 4 }}>
                        <CircularProgress size={20} />
                        <Typography variant="body2" sx={{ ml: 1 }}>
                          Loading queue...
                        </Typography>
                      </Box>
                    ) : queueItems.length > 0 ? (
                      <List dense sx={{ py: 0 }}>
                        {queueItems.map((item, index) => (
                          <ListItem key={index} sx={{ py: 1, px: 2, flexDirection: 'column', alignItems: 'stretch' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', mb: 1 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                  {item.workflow_name || `Workflow ${item.workflow_id.slice(0, 8)}`}
                                </Typography>
                                <Chip
                                  label={item.status}
                                  size="small"
                                  color={item.status === 'running' ? 'warning' : 'default'}
                                  sx={{ fontSize: '0.7rem' }}
                                />
                              </Box>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="caption" color="text.secondary">
                                  {item.ocr_model}
                                </Typography>
                                <Tooltip title="Cancel Workflow">
                                  <IconButton
                                    size="small"
                                    onClick={() => cancelWorkflow(item.workflow_id)}
                                    sx={{ color: 'error.main' }}
                                  >
                                    <DeleteIcon sx={{ fontSize: '1rem' }} />
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Typography variant="caption" color="text.secondary">
                                {item.total_images} images • {item.processed_images} processed
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {new Date(item.created_at).toLocaleString()}
                              </Typography>
                            </Box>
                            {item.batches && item.batches.length > 0 && (
                              <Box sx={{ mt: 1, pl: 2, borderLeft: '2px solid rgba(0, 0, 0, 0.12)' }}>
                                {item.batches.map((batch: any, batchIndex: number) => (
                                  <Typography key={batchIndex} variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                    Batch: {batch.batch_name || `Batch ${batchIndex + 1}`} ({batch.processed_images}/{batch.total_images} images)
                                  </Typography>
                                ))}
                              </Box>
                            )}
                          </ListItem>
                        ))}
                      </List>
                    ) : (
                      <Box sx={{ textAlign: 'center', py: 4 }}>
                        <QueueIcon sx={{ fontSize: '2rem', color: 'text.disabled', mb: 1 }} />
                        <Typography variant="body2" color="text.secondary">
                          No active workflows in queue
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Collapse>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default OCRWorkflow;