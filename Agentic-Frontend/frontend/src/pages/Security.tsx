import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  IconButton,
  Button,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Skeleton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  LinearProgress,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Shield,
  Warning,
  Error,
  CheckCircle,
  Refresh,
  Gavel,
  Timeline,
  ReportProblem,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type {
  SecurityIncident
} from '../types';

const Security: React.FC = () => {
  const queryClient = useQueryClient();
  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<SecurityIncident | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [incidentFilters, setIncidentFilters] = useState({
    severity: 'all',
    resolved: 'all',
    limit: 50,
  });

  // Fetch security status
  const {
    data: securityStatus,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ['security-status'],
    queryFn: () => apiClient.getSecurityStatus(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch security health
  const {
    data: securityHealth,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['security-health'],
    queryFn: () => apiClient.getSecurityHealth(),
    refetchInterval: 30000,
  });

  // Fetch security incidents
  const {
    data: incidents,
    isLoading: incidentsLoading,
    refetch: refetchIncidents,
  } = useQuery({
    queryKey: ['security-incidents', incidentFilters],
    queryFn: () => apiClient.getSecurityIncidents({
      limit: incidentFilters.limit,
      severity: incidentFilters.severity !== 'all' ? incidentFilters.severity : undefined,
      resolved: incidentFilters.resolved !== 'all' ? incidentFilters.resolved === 'true' : undefined,
    }),
    refetchInterval: 30000,
  });

  // Security limits are included in security status response
  const securityLimits = securityStatus ? {
    concurrent_agents: {
      current: securityStatus.current_usage.active_agents,
      max: securityStatus.resource_limits.max_concurrent_agents,
    },
    memory_usage: {
      current_mb: securityStatus.current_usage.total_memory_mb,
      max_mb: securityStatus.resource_limits.max_memory_mb,
    },
    rate_limits: {
      tool_execution_per_hour: 100, // Default values from backend docs
      agent_creation_per_hour: 10,
      external_requests_per_hour: 1000,
    },
  } : null;

  // Resolve incident mutation
  const resolveIncidentMutation = useMutation({
    mutationFn: ({ incidentId, notes }: { incidentId: string; notes: string }) =>
      apiClient.resolveSecurityIncident(incidentId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['security-incidents'] });
      queryClient.invalidateQueries({ queryKey: ['security-status'] });
      setResolveDialogOpen(false);
      setSelectedIncident(null);
      setResolutionNotes('');
    },
  });

  const handleRefresh = async () => {
    await Promise.all([
      refetchStatus(),
      refetchHealth(),
      refetchIncidents(),
    ]);
  };

  // Loading states
  const limitsLoading = statusLoading;

  const handleResolveIncident = (incident: SecurityIncident) => {
    setSelectedIncident(incident);
    setResolveDialogOpen(true);
  };

  const handleConfirmResolve = () => {
    if (selectedIncident && resolutionNotes.trim()) {
      resolveIncidentMutation.mutate({
        incidentId: selectedIncident.incident_id,
        notes: resolutionNotes.trim(),
      });
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <Error color="error" />;
      case 'medium':
        return <Warning color="warning" />;
      case 'low':
        return <ReportProblem color="info" />;
      default:
        return <SecurityIcon color="action" />;
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle color="success" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'error':
        return <Error color="error" />;
      default:
        return <SecurityIcon color="info" />;
    }
  };

  if (statusError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={handleRefresh}>
              Retry
            </Button>
          }
        >
          <Typography variant="body1" sx={{ fontWeight: 600, mb: 1 }}>
            Failed to load security data
          </Typography>
          <Typography variant="body2">
            {statusError?.message?.includes('500')
              ? "Server error (500): The backend service may not be running or has encountered an internal error."
              : statusError?.message?.includes('404')
              ? "Endpoint not found (404): The security API endpoints may not be available."
              : statusError?.message?.includes('Network')
              ? "Network error: Unable to connect to the backend. Please check if the backend service is running."
              : "Please try again. If the problem persists, check the backend service status."}
          </Typography>
          {statusError?.message && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Error: {statusError.message}
            </Typography>
          )}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Security Center
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor and manage security incidents, agent sandboxing, and system protection.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={statusLoading || healthLoading || incidentsLoading}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Security Overview */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {statusLoading ? (
                <Skeleton variant="rectangular" width="100%" height={80} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Security Status
                    </Typography>
                    {getHealthIcon(securityHealth?.status || 'healthy')}
                  </Box>
                  <Chip
                    label={securityHealth?.status || 'healthy'}
                    color={getHealthColor(securityHealth?.status || 'healthy') as any}
                    sx={{ mb: 2, fontWeight: 600, textTransform: 'capitalize' }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {securityHealth?.message || 'All systems secure'}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              {statusLoading ? (
                <Skeleton variant="rectangular" width="100%" height={80} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Active Agents
                    </Typography>
                    <Shield color="primary" />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                    {securityStatus?.active_agents || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Currently running in sandbox
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              {incidentsLoading ? (
                <Skeleton variant="rectangular" width="100%" height={80} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Security Incidents
                    </Typography>
                    <ReportProblem color="warning" />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                    {incidents?.total_count || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total incidents detected
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0}>
            <CardContent>
              {limitsLoading ? (
                <Skeleton variant="rectangular" width="100%" height={80} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Memory Usage
                    </Typography>
                    <Timeline color="info" />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                    {securityLimits ? Math.round((securityLimits.memory_usage.current_mb / securityLimits.memory_usage.max_mb) * 100) : 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {securityLimits?.memory_usage.current_mb || 0}MB / {securityLimits?.memory_usage.max_mb || 0}MB
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Resource Limits */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                Resource Limits
              </Typography>

              {limitsLoading ? (
                <Box>
                  {[...Array(4)].map((_, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Skeleton variant="text" width="40%" height={24} />
                      <Skeleton variant="rectangular" width="100%" height={8} sx={{ borderRadius: 1 }} />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Box>
                  {/* Concurrent Agents */}
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>Concurrent Agents</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {securityLimits?.concurrent_agents.current || 0} / {securityLimits?.concurrent_agents.max || 8}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={securityLimits ? (securityLimits.concurrent_agents.current / securityLimits.concurrent_agents.max) * 100 : 0}
                      sx={{ height: 8, borderRadius: 1 }}
                      color="primary"
                    />
                  </Box>

                  {/* Memory Usage */}
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>Memory Usage</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {securityLimits?.memory_usage.current_mb || 0}MB / {securityLimits?.memory_usage.max_mb || 0}MB
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={securityLimits ? (securityLimits.memory_usage.current_mb / securityLimits.memory_usage.max_mb) * 100 : 0}
                      sx={{ height: 8, borderRadius: 1 }}
                      color="info"
                    />
                  </Box>

                  {/* Rate Limits */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Rate Limits (per hour)
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                      <Chip
                        label={`Tool Exec: ${securityLimits?.rate_limits.tool_execution_per_hour || 100}`}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={`Agent Create: ${securityLimits?.rate_limits.agent_creation_per_hour || 10}`}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={`Ext Requests: ${securityLimits?.rate_limits.external_requests_per_hour || 1000}`}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                Security Configuration
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    Execution Sandboxing
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    All agents run in isolated execution environments with resource monitoring.
                  </Typography>
                  <FormControlLabel
                    control={<Switch checked={true} disabled />}
                    label="Enabled"
                  />
                </Box>

                <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    Input Validation
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Automatic validation of all input data for malicious content detection.
                  </Typography>
                  <FormControlLabel
                    control={<Switch checked={true} disabled />}
                    label="Enabled"
                  />
                </Box>

                <Box sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                    Rate Limiting
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Configurable rate limits prevent system abuse and ensure fair resource usage.
                  </Typography>
                  <FormControlLabel
                    control={<Switch checked={true} disabled />}
                    label="Enabled"
                  />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Security Incidents */}
      <Card elevation={0}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Security Incidents
            </Typography>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Severity</InputLabel>
                <Select
                  value={incidentFilters.severity}
                  label="Severity"
                  onChange={(e) => setIncidentFilters({ ...incidentFilters, severity: e.target.value })}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={incidentFilters.resolved}
                  label="Status"
                  onChange={(e) => setIncidentFilters({ ...incidentFilters, resolved: e.target.value })}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="false">Open</MenuItem>
                  <MenuItem value="true">Resolved</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>

          {incidentsLoading ? (
            <Box>
              {[...Array(5)].map((_, index) => (
                <Box key={index} sx={{ mb: 2 }}>
                  <Skeleton variant="rectangular" width="100%" height={60} sx={{ borderRadius: 1 }} />
                </Box>
              ))}
            </Box>
          ) : (
            <TableContainer component={Paper} elevation={0}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Severity</TableCell>
                    <TableCell>Incident ID</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Agent</TableCell>
                    <TableCell>Time</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {incidents?.incidents?.map((incident: SecurityIncident) => (
                    <TableRow key={incident.incident_id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getSeverityIcon(incident.severity)}
                          <Chip
                            label={incident.severity}
                            size="small"
                            color={getSeverityColor(incident.severity) as any}
                            variant="outlined"
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {incident.incident_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {incident.violation_type.replace(/_/g, ' ')}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{
                          maxWidth: 300,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {incident.description}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {incident.agent_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {new Date(incident.timestamp).toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={incident.resolved ? 'Resolved' : 'Open'}
                          size="small"
                          color={incident.resolved ? 'success' : 'warning'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        {!incident.resolved && (
                          <Tooltip title="Resolve Incident">
                            <IconButton
                              size="small"
                              onClick={() => handleResolveIncident(incident)}
                              color="primary"
                            >
                              <Gavel />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  )) || (
                    <TableRow>
                      <TableCell colSpan={8} sx={{ textAlign: 'center', py: 4 }}>
                        <Typography variant="body2" color="text.secondary">
                          No security incidents found.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Resolve Incident Dialog */}
      <Dialog
        open={resolveDialogOpen}
        onClose={() => setResolveDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Resolve Security Incident</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            {selectedIncident && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                  Incident Details
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <Chip
                    label={selectedIncident.severity}
                    color={getSeverityColor(selectedIncident.severity) as any}
                  />
                  <Chip
                    label={selectedIncident.violation_type.replace(/_/g, ' ')}
                    variant="outlined"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {selectedIncident.description}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Agent: {selectedIncident.agent_id} • Time: {new Date(selectedIncident.timestamp).toLocaleString()}
                </Typography>
              </Box>
            )}

            <TextField
              fullWidth
              label="Resolution Notes"
              multiline
              rows={4}
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Describe how this incident was resolved..."
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResolveDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmResolve}
            variant="contained"
            disabled={!resolutionNotes.trim() || resolveIncidentMutation.isPending}
          >
            {resolveIncidentMutation.isPending ? 'Resolving...' : 'Resolve Incident'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Security;