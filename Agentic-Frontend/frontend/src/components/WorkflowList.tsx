import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Grid, Card, CardContent, Typography, Box, Button, Chip } from '@mui/material';
import { Email, Description } from '@mui/icons-material';

const WorkflowList: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Card elevation={0} sx={{ cursor: 'pointer' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Email sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Email Assistant
                </Typography>
                <Chip label="Coming Soon" color="info" size="small" />
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              AI-powered email management and response generation
            </Typography>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/workflows/email-assistant')}
              disabled
            >
              Launch Workflow
            </Button>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card elevation={0} sx={{ cursor: 'pointer' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Description sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Document Analyzer
                </Typography>
                <Chip label="Coming Soon" color="info" size="small" />
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              AI-powered document analysis and insights extraction
            </Typography>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/workflows/document-analyzer')}
              disabled
            >
              Launch Workflow
            </Button>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default WorkflowList;