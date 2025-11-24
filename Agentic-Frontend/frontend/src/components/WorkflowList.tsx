
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  Avatar,
} from '@mui/material';
import {
  Psychology,
  Email,
  Description,
  SmartToy,
} from '@mui/icons-material';

const WorkflowList: React.FC = () => {
  const navigate = useNavigate();

  const workflows = [
    {
      id: 'knowledge-base',
      title: 'Knowledge Base',
      description: 'Build and manage your AI knowledge base with advanced content processing and semantic search.',
      icon: <Psychology />,
      path: '/workflows/knowledge-base',
      status: 'active',
      color: '#007AFF',
    },
    {
      id: 'email-assistant',
      title: 'Email Assistant',
      description: 'AI-powered email analysis, task creation, and automated follow-ups.',
      icon: <Email />,
      path: '/workflows/email-assistant',
      status: 'active',
      color: '#34C759',
    },
    {
      id: 'ocr-workflow',
      title: 'OCR Workflow',
      description: 'Convert images and screenshots to editable markdown documents using advanced OCR models.',
      icon: <Description />,
      path: '/workflows/ocr-workflow',
      status: 'active',
      color: '#FF9500',
    },
    {
      id: 'document-analyzer',
      title: 'Document Analyzer',
      description: 'Advanced document processing and analysis capabilities.',
      icon: <SmartToy />,
      path: '/workflows/document-analyzer',
      status: 'coming-soon',
      color: '#8E8E93',
    },
  ];

  const handleWorkflowClick = (path: string) => {
    navigate(path);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        AI Workflows
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Choose from our collection of AI-powered workflows to automate your tasks and boost productivity.
      </Typography>

      <Grid container spacing={3}>
        {workflows.map((workflow) => (
          <Grid item xs={12} sm={6} md={4} key={workflow.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: (theme) => theme.shadows[8],
                },
                opacity: workflow.status === 'coming-soon' ? 0.7 : 1,
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar
                    sx={{
                      bgcolor: workflow.color,
                      mr: 2,
                      width: 48,
                      height: 48,
                    }}
                  >
                    {workflow.icon}
                  </Avatar>
                  <Box>
                    <Typography variant="h6" component="h2">
                      {workflow.title}
                    </Typography>
                    {workflow.status === 'coming-soon' && (
                      <Chip
                        label="Coming Soon"
                        size="small"
                        sx={{
                          mt: 0.5,
                          bgcolor: 'warning.light',
                          color: 'warning.contrastText',
                        }}
                      />
                    )}
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {workflow.description}
                </Typography>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  variant="contained"
                  fullWidth
                  onClick={() => handleWorkflowClick(workflow.path)}
                  disabled={workflow.status === 'coming-soon'}
                  sx={{
                    bgcolor: workflow.color,
                    '&:hover': {
                      bgcolor: workflow.color,
                      opacity: 0.9,
                    },
                  }}
                >
                  {workflow.status === 'coming-soon' ? 'Coming Soon' : 'Launch Workflow'}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default WorkflowList;