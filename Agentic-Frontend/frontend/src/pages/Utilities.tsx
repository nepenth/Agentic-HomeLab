import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  IconButton,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import {
  OpenInNew,
  Refresh,
  Api,
  MenuBook,
  LocalFlorist,
  Storage,
  Assessment,
  Launch,
  BugReport,
} from '@mui/icons-material';
import type { BackendEndpoint } from '../types';
import LogsViewer from '../components/LogsViewer';

const Utilities: React.FC = () => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<BackendEndpoint | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  const backendEndpoints: BackendEndpoint[] = [
    {
      service: 'API Documentation',
      url: 'https://whyland-ai.nakedsun.xyz:8000/docs',
      description: 'Interactive Swagger UI',
      icon: '🔗',
    },
    {
      service: 'ReDoc Documentation',
      url: 'https://whyland-ai.nakedsun.xyz:8000/redoc',
      description: 'Alternative API docs',
      icon: '📖',
    },
    {
      service: 'Flower (Celery Monitor)',
      url: 'https://whyland-ai.nakedsun.xyz:5555',
      description: 'Monitor background tasks',
      icon: '🌸',
    },
    {
      service: 'Adminer (Database UI)',
      url: 'https://whyland-ai.nakedsun.xyz:8080',
      description: 'Database browser',
      icon: '🗄️',
    },
    {
      service: 'Metrics',
      url: 'https://whyland-ai.nakedsun.xyz:8000/api/v1/metrics',
      description: 'Prometheus metrics',
      icon: '📊',
    },
  ];

  const handleEndpointClick = (endpoint: BackendEndpoint) => {
    setSelectedEndpoint(endpoint);
    setDialogOpen(true);
  };

  const handleOpenExternal = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
    setDialogOpen(false);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedEndpoint(null);
  };

  const getServiceIcon = (service: string) => {
    switch (service.toLowerCase()) {
      case 'api documentation':
        return <Api color="primary" />;
      case 'redoc documentation':
        return <MenuBook color="info" />;
      case 'flower (celery monitor)':
        return <LocalFlorist color="success" />;
      case 'adminer (database ui)':
        return <Storage color="warning" />;
      case 'metrics':
        return <Assessment color="secondary" />;
      default:
        return <Launch color="action" />;
    }
  };

  const getStatusChip = (service: string) => {
    // In a real app, you'd check the actual service status
    const isKnownService = backendEndpoints.some(endpoint => 
      endpoint.service.toLowerCase() === service.toLowerCase()
    );
    
    return (
      <Chip
        label={isKnownService ? 'Available' : 'Unknown'}
        color={isKnownService ? 'success' : 'default'}
        size="small"
        variant="outlined"
      />
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Backend Management & Monitoring
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Access backend services, monitor real-time logs, and manage system tools
          </Typography>
        </Box>
        <IconButton>
          <Refresh />
        </IconButton>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab
            icon={<Launch />}
            label="Backend Tools"
            iconPosition="start"
          />
          <Tab
            icon={<BugReport />}
            label="Live Logs"
            iconPosition="start"
          />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && (
        <>
          {/* Info Alert */}
          <Alert severity="info" sx={{ mb: 4 }}>
            <Typography variant="body2">
              These tools provide direct access to backend services. Some may require additional authentication.
              All links open in a new tab for security.
            </Typography>
          </Alert>

      {/* Service Cards Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {backendEndpoints.map((endpoint, index) => (
          <Grid item xs={12} sm={6} lg={4} key={index}>
            <Card 
              elevation={0}
              sx={{ 
                height: '100%',
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 3,
                },
              }}
              onClick={() => handleEndpointClick(endpoint)}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ mr: 2, fontSize: '2rem' }}>
                    {endpoint.icon}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {endpoint.service}
                    </Typography>
                    {getStatusChip(endpoint.service)}
                  </Box>
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {endpoint.description}
                </Typography>
                
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ 
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                  }}>
                    {new URL(endpoint.url).hostname}
                  </Typography>
                  <IconButton size="small" color="primary">
                    <OpenInNew fontSize="small" />
                  </IconButton>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Detailed Table View */}
      <Card elevation={0}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Service Details
          </Typography>
          
          <TableContainer component={Paper} elevation={0} sx={{ border: 1, borderColor: 'divider' }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Service</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>URL</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {backendEndpoints.map((endpoint, index) => (
                  <TableRow key={index} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {getServiceIcon(endpoint.service)}
                        <Typography variant="body2" sx={{ ml: 2, fontWeight: 500 }}>
                          {endpoint.service}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {endpoint.description}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          fontFamily: 'monospace',
                          backgroundColor: 'grey.100',
                          px: 1,
                          py: 0.5,
                          borderRadius: 1,
                        }}
                      >
                        {endpoint.url}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {getStatusChip(endpoint.service)}
                    </TableCell>
                    <TableCell align="center">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleOpenExternal(endpoint.url)}
                      >
                        <OpenInNew fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Service Detail Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ fontSize: '1.5rem' }}>
            {selectedEndpoint?.icon}
          </Box>
          Open {selectedEndpoint?.service}?
        </DialogTitle>
        
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            {selectedEndpoint?.description}
          </Typography>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              This will open the service in a new tab. You may need to authenticate separately.
            </Typography>
          </Alert>

          <Box sx={{ 
            backgroundColor: 'grey.100', 
            p: 2, 
            borderRadius: 1,
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            wordBreak: 'break-all',
          }}>
            {selectedEndpoint?.url}
          </Box>
        </DialogContent>
        
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleCloseDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={() => selectedEndpoint && handleOpenExternal(selectedEndpoint.url)}
            variant="contained"
            startIcon={<OpenInNew />}
          >
            Open Service
          </Button>
        </DialogActions>
      </Dialog>
        </>
      )}

      {activeTab === 1 && (
        <LogsViewer />
      )}
    </Box>
  );
};

export default Utilities;