import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  LinearProgress,
  Chip,
} from '@mui/material';
import {
  Description,
  CloudUpload,
  Visibility,
  Download,
  Delete,
  PlayArrow,
  PictureAsPdf,
  TextSnippet,
  Image,
} from '@mui/icons-material';
import WorkflowTemplate from '../../pages/WorkflowTemplate';

const DocumentAnalyzer: React.FC = () => {
  const mockDocuments = [
    {
      id: 1,
      name: 'Q4_Financial_Report.pdf',
      type: 'pdf',
      size: '2.4 MB',
      status: 'completed',
      progress: 100,
      uploadedAt: '2 hours ago',
      insights: ['Financial Summary', 'Risk Analysis', 'Growth Metrics'],
    },
    {
      id: 2,
      name: 'contract_agreement.docx',
      type: 'document',
      size: '1.2 MB',
      status: 'processing',
      progress: 65,
      uploadedAt: '30 minutes ago',
      insights: [],
    },
    {
      id: 3,
      name: 'presentation_slides.pdf',
      type: 'pdf',
      size: '5.8 MB',
      status: 'pending',
      progress: 0,
      uploadedAt: '5 minutes ago',
      insights: [],
    },
  ];

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <PictureAsPdf color="error" />;
      case 'document':
        return <TextSnippet color="info" />;
      case 'image':
        return <Image color="success" />;
      default:
        return <Description color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'info';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const actions = (
    <>
      <Button
        variant="contained"
        startIcon={<CloudUpload />}
        disabled
      >
        Upload Document
      </Button>
      <Button
        variant="outlined"
        startIcon={<PlayArrow />}
        disabled
      >
        Process Queue
      </Button>
    </>
  );

  return (
    <WorkflowTemplate
      title="Document Analyzer"
      description="AI-powered document analysis and insights extraction"
      status="coming-soon"
      icon={<Description />}
      actions={actions}
    >
      <Grid container spacing={3}>
        {/* Analysis Stats */}
        <Grid item xs={12} md={4}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Analysis Stats
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Documents Processed
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                  1
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Currently Processing
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main' }}>
                  1
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  In Queue
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main' }}>
                  1
                </Typography>
              </Box>

              <Box>
                <Typography variant="body2" color="text.secondary">
                  Total Insights Extracted
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main' }}>
                  3
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Document Queue */}
        <Grid item xs={12} md={8}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Document Queue
                </Typography>
                <Button
                  variant="text"
                  size="small"
                  startIcon={<CloudUpload />}
                  disabled
                >
                  Upload New
                </Button>
              </Box>

              <List>
                {mockDocuments.map((doc) => (
                  <ListItem key={doc.id}>
                    <ListItemIcon>
                      {getFileIcon(doc.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography
                            variant="body1"
                            sx={{ fontWeight: 500, flex: 1 }}
                          >
                            {doc.name}
                          </Typography>
                          <Chip
                            label={doc.status}
                            size="small"
                            color={getStatusColor(doc.status) as any}
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            {doc.size} • {doc.uploadedAt}
                          </Typography>
                          
                          {doc.status === 'processing' && (
                            <Box sx={{ mb: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={doc.progress}
                                sx={{ height: 4, borderRadius: 2 }}
                              />
                              <Typography variant="caption" color="text.secondary">
                                {doc.progress}% complete
                              </Typography>
                            </Box>
                          )}

                          {doc.insights.length > 0 && (
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                              {doc.insights.map((insight, index) => (
                                <Chip
                                  key={index}
                                  label={insight}
                                  size="small"
                                  variant="filled"
                                  sx={{ fontSize: '0.7rem', height: 20 }}
                                />
                              ))}
                            </Box>
                          )}
                        </Box>
                      }
                    />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton size="small" disabled>
                        <Visibility />
                      </IconButton>
                      <IconButton size="small" disabled>
                        <Download />
                      </IconButton>
                      <IconButton size="small" disabled>
                        <Delete />
                      </IconButton>
                    </Box>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Analysis Features */}
        <Grid item xs={12}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                Analysis Features
              </Typography>
              
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                      Text Extraction
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Extract and process text content from PDFs, images, and documents
                    </Typography>
                    <Button variant="outlined" size="small" disabled>
                      Configure
                    </Button>
                  </Box>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                      Key Insights
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      AI-powered extraction of key insights, summaries, and important data
                    </Typography>
                    <Button variant="outlined" size="small" disabled>
                      View Examples
                    </Button>
                  </Box>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                      Data Classification
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Automatically classify and categorize documents by type and content
                    </Typography>
                    <Button variant="outlined" size="small" disabled>
                      Setup Rules
                    </Button>
                  </Box>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                      Export & Integration
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Export results and integrate with external systems and workflows
                    </Typography>
                    <Button variant="outlined" size="small" disabled>
                      Setup Exports
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </WorkflowTemplate>
  );
};

export default DocumentAnalyzer;