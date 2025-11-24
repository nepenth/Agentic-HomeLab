import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  CircularProgress,
  Alert,
  TextField,
  Divider,
  Card,
  CardContent,
  CardHeader,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Upload as UploadIcon,
  PictureAsPdf as PdfIcon,
  Description as DocxIcon,
  Refresh as RefreshIcon,
  ModelTraining as ModelIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import apiClient from '../services/api';
import type { OCRWorkflow, OCRBatch, OCRImage } from '../types';

const OCRWorkflow: React.FC = () => {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('deepseek-ocr');
  const [images, setImages] = useState<File[]>([]);
  const [batchName, setBatchName] = useState<string>('New Document');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [results, setResults] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [workflowId, setWorkflowId] = useState<string>('');
  const [status, setStatus] = useState<string>('idle');

  const loadModels = useCallback(async () => {
    try {
      const response = await apiClient.get('/ocr/models');
      const modelNames = response.data.models.map((m: any) => m.name);
      setModels(modelNames);
    } catch (err) {
      setError('Failed to load models');
    }
  }, []);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setImages(Array.from(event.target.files));
    }
  };

  const startOCRWorkflow = async () => {
    if (images.length === 0) {
      setError('Please select at least one image');
      return;
    }

    setIsProcessing(true);
    setError('');
    setStatus('processing');

    try {
      // Create workflow
      const workflowResponse = await apiClient.post('/ocr/workflows', {
        workflow_name: 'OCR Workflow',
        ocr_model: selectedModel,
      });
      setWorkflowId(workflowResponse.data.workflow_id);

      // Upload batch
      const formData = new FormData();
      formData.append('batch_name', batchName);
      images.forEach((image) => {
        formData.append('images', image);
      });

      const batchResponse = await apiClient.post(`/ocr/workflows/${workflowResponse.data.workflow_id}/batches`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // Trigger processing
      const task = await apiClient.post('/ocr/workflows/' + workflowResponse.data.workflow_id + '/process', {
        batch_id: batchResponse.data.batch_id,
      });

      // Poll for results
      const pollInterval = setInterval(async () => {
        const statusResponse = await apiClient.get(`/ocr/workflows/${workflowResponse.data.workflow_id}/status`);
        if (statusResponse.data.status === 'completed') {
          clearInterval(pollInterval);
          const resultResponse = await apiClient.get(`/ocr/workflows/${workflowResponse.data.workflow_id}/results`);
          setResults(resultResponse.data.combined_markdown);
          setStatus('completed');
          setIsProcessing(false);
        } else if (statusResponse.data.status === 'failed') {
          clearInterval(pollInterval);
          setError('OCR processing failed');
          setIsProcessing(false);
          setStatus('failed');
        }
      }, 2000);

    } catch (err) {
      setError('OCR workflow failed');
      setIsProcessing(false);
      setStatus('error');
    }
  };

  const exportResult = async (format: 'pdf' | 'docx') => {
    try {
      const response = await apiClient.post(`/ocr/workflows/${workflowId}/export`, { format });
      const url = response.data.download_url;
      const a = document.createElement('a');
      a.href = url;
      a.download = `ocr-${batchName}.${format}`;
      a.click();
    } catch (err) {
      setError('Export failed');
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          OCR Workflow
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Upload images or screenshots and convert them to editable markdown documents using advanced OCR models.
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Model Selection" />
              <CardContent>
                <FormControl fullWidth>
                  <InputLabel>OCR Model</InputLabel>
                  <Select
                    value={selectedModel}
                    label="OCR Model"
                    onChange={(e) => setSelectedModel(e.target.value as string)}
                  >
                    {models.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Batch Settings" />
              <CardContent>
                <TextField
                  fullWidth
                  label="Batch Name"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                  margin="normal"
                />
                <Box sx={{ mt: 2 }}>
                  <input
                    accept="image/*"
                    style={{ display: 'none' }}
                    id="image-upload"
                    multiple
                    type="file"
                    onChange={handleFileUpload}
                  />
                  <label htmlFor="image-upload">
                    <Button
                      variant="outlined"
                      component="span"
                      startIcon={<UploadIcon />}
                      fullWidth
                    >
                      Upload Images
                    </Button>
                  </label>
                  {images.length > 0 && (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      {images.length} image(s) selected
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardHeader
                title="Processing"
                action={
                  <Button
                    variant="contained"
                    onClick={startOCRWorkflow}
                    disabled={isProcessing || images.length === 0}
                    startIcon={isProcessing ? <CircularProgress size={20} /> : <ModelIcon />}
                  >
                    {isProcessing ? 'Processing...' : 'Start OCR'}
                  </Button>
                }
              />
              <CardContent>
                {error && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                  </Alert>
                )}
                {status === 'processing' && (
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CircularProgress size={20} sx={{ mr: 2 }} />
                    <Typography>Processing images...</Typography>
                  </Box>
                )}
                {status === 'completed' && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    OCR processing completed successfully!
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          {results && (
            <Grid item xs={12}>
              <Card>
                <CardHeader
                  title="OCR Results"
                  action={
                    <Box>
                      <Button
                        variant="outlined"
                        startIcon={<PdfIcon />}
                        onClick={() => exportResult('pdf')}
                        sx={{ mr: 1 }}
                      >
                        Export PDF
                      </Button>
                      <Button
                        variant="outlined"
                        startIcon={<DocxIcon />}
                        onClick={() => exportResult('docx')}
                      >
                        Export DOCX
                      </Button>
                    </Box>
                  }
                />
                <CardContent>
                  <Box sx={{
                    maxHeight: 600,
                    overflow: 'auto',
                    border: '1px solid #e0e0e0',
                    borderRadius: 1,
                    p: 2,
                    backgroundColor: '#f5f5f5'
                  }}>
                    <ReactMarkdown
                      components={{
                        code: ({ node, inline, className, children, ...props }) => {
                          const match = /language-(\w+)/.exec(className || '');
                          return !inline && match ? (
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
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      </Paper>
    </Container>
  );
};

export default OCRWorkflow;