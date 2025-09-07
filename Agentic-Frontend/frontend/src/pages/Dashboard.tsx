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
  LinearProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Skeleton,
} from '@mui/material';
import {
  Refresh,
  TrendingUp,
  SmartToy,
  Task,
  Speed,
  Email,
  Description,
  CheckCircle,
  Error,
  Warning,
  Info,
  PlayArrow,
  Circle,
  Shield,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import { CardSkeleton } from '../components';
import { useNavigate } from 'react-router-dom';

/*
interface DashboardStats {
  totalAgents: number;
  activeTasks: number;
  completedToday: number;
  systemHealth: 'healthy' | 'warning' | 'error';
  recentTasks: Array<{
    id: string;
    agent_name: string;
    status: string;
    created_at: string;
  }>;
  recentLogs: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
}
*/

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Fetch agents data with error handling
  const {
    data: agents,
    isLoading: agentsLoading,
    error: agentsError,
  } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      try {
        return await apiClient.getAgents();
      } catch (error) {
        console.warn('Agents API error, using fallback data:', error);
        // Return empty array as fallback
        return [];
      }
    },
    refetchInterval: 30000,
  });

  // Fetch tasks data with error handling
  const {
    data: tasks,
    isLoading: tasksLoading,
    error: tasksError,
  } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      try {
        return await apiClient.getTasks();
      } catch (error) {
        console.warn('Tasks API error, using fallback data:', error);
        // Return empty array as fallback
        return [];
      }
    },
    refetchInterval: 30000,
  });

  // Fetch security status
  const {
    data: securityStatus,
    isLoading: securityLoading,
  } = useQuery({
    queryKey: ['security-status'],
    queryFn: () => apiClient.getSecurityStatus(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch system metrics
  const {
    data: systemMetrics,
    isLoading: systemMetricsLoading,
  } = useQuery({
    queryKey: ['system-metrics-dashboard'],
    queryFn: () => apiClient.getSystemMetrics(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch Ollama health
  const {
    data: ollamaHealth,
    isLoading: ollamaLoading,
  } = useQuery({
    queryKey: ['ollama-health-dashboard'],
    queryFn: () => apiClient.getOllamaHealth(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Calculate system health from security status
  const systemHealth = securityStatus?.status || 'unknown';
  const isLoading = agentsLoading || tasksLoading || securityLoading || systemMetricsLoading || ollamaLoading;
  const error = agentsError || tasksError;

  // Calculate dashboard data from real API responses
  const dashboardData = React.useMemo(() => {
    if (!agents || !tasks) {
      return {
        totalAgents: 0,
        activeTasks: 0,
        completedToday: 0,
        systemHealth: 'unknown',
        recentTasks: [],
        recentLogs: [],
      };
    }

    const activeTasks = tasks.filter(task => task.status === 'running' || task.status === 'pending').length;
    const completedToday = tasks.filter(task => {
      const taskDate = new Date(task.completed_at || task.created_at);
      const today = new Date();
      return task.status === 'completed' &&
             taskDate.toDateString() === today.toDateString();
    }).length;

    const recentTasks = tasks.slice(0, 5).map(task => ({
      id: task.id,
      agent_name: agents.find(a => a.id === task.agent_id)?.name || 'Unknown Agent',
      status: task.status,
      created_at: task.created_at,
    }));

    return {
      totalAgents: agents.length,
      activeTasks,
      completedToday,
      systemHealth,
      recentTasks,
      recentLogs: [], // TODO: Implement when logs API is available
    };
  }, [agents, tasks, systemHealth]);

  const handleRefresh = async () => {
    setLastRefresh(new Date());
    // The queries will automatically refetch due to refetchInterval
    // But we can also manually trigger refetch for immediate update
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'running':
        return <PlayArrow color="info" />;
      case 'failed':
        return <Error color="error" />;
      default:
        return <Circle color="disabled" />;
    }
  };

  const getLogIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return <Error color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'info':
        return <Info color="info" />;
      default:
        return <Circle color="disabled" />;
    }
  };

  const getHealthColor = (health: string) => {
    switch (health) {
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

  if (error) {
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
          Failed to load dashboard data. Please try again.
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
            Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Welcome back! Here's what's happening with your AI agents.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </Typography>
          <IconButton onClick={handleRefresh} disabled={isLoading}>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0} sx={{ height: '100%' }}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={2} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Total Agents
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700 }}>
                        {dashboardData?.totalAgents || 0}
                      </Typography>
                    </Box>
                    <SmartToy sx={{ fontSize: 40, color: 'primary.main' }} />
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
                    <TrendingUp fontSize="small" color="success" />
                    <Typography variant="body2" color="success.main" sx={{ ml: 1 }}>
                      +2 this week
                    </Typography>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0} sx={{ height: '100%' }}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={2} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Active Tasks
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                        {dashboardData?.activeTasks || 0}
                      </Typography>
                    </Box>
                    <Task sx={{ fontSize: 40, color: 'info.main' }} />
                  </Box>
                  <Box sx={{ mt: 2 }}>
                    <LinearProgress variant="determinate" value={75} sx={{ height: 6, borderRadius: 3 }} />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Processing workload
                    </Typography>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <Card elevation={0} sx={{ height: '100%' }}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={2} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography color="text.secondary" gutterBottom variant="h6">
                        Completed Today
                      </Typography>
                      <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                        {dashboardData?.completedToday || 0}
                      </Typography>
                    </Box>
                    <CheckCircle sx={{ fontSize: 40, color: 'success.main' }} />
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
                    <TrendingUp fontSize="small" color="success" />
                    <Typography variant="body2" color="success.main" sx={{ ml: 1 }}>
                      +20% vs yesterday
                    </Typography>
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
           <Card elevation={0} sx={{ height: '100%' }}>
             <CardContent>
               {isLoading ? (
                 <CardSkeleton lines={4} />
               ) : (
                 <>
                   <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                     <Typography color="text.secondary" gutterBottom variant="h6">
                       System Health
                     </Typography>
                     <Speed sx={{ fontSize: 32, color: getHealthColor(dashboardData?.systemHealth || 'info') + '.main' }} />
                   </Box>

                   <Chip
                     label={dashboardData?.systemHealth || 'Unknown'}
                     color={getHealthColor(dashboardData?.systemHealth || 'info') as any}
                     sx={{ mb: 2, fontWeight: 600, textTransform: 'capitalize' }}
                   />

                   {/* CPU Usage */}
                   <Box sx={{ mb: 1.5 }}>
                     <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                       <Typography variant="body2" color="text.secondary">CPU</Typography>
                       <Typography variant="body2" sx={{ fontWeight: 600 }}>
                         {systemMetrics?.cpu?.usage_percent?.toFixed(1) || 'N/A'}%
                       </Typography>
                     </Box>
                     <LinearProgress
                       variant="determinate"
                       value={systemMetrics?.cpu?.usage_percent || 0}
                       sx={{ height: 4, borderRadius: 2 }}
                     />
                   </Box>

                   {/* Memory Usage */}
                   <Box sx={{ mb: 1.5 }}>
                     <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                       <Typography variant="body2" color="text.secondary">Memory</Typography>
                       <Typography variant="body2" sx={{ fontWeight: 600 }}>
                         {systemMetrics?.memory?.used_gb?.toFixed(1) || 'N/A'}GB/{systemMetrics?.memory?.total_gb?.toFixed(1) || 'N/A'}GB
                       </Typography>
                     </Box>
                     <LinearProgress
                       variant="determinate"
                       value={systemMetrics?.memory?.usage_percent || 0}
                       sx={{ height: 4, borderRadius: 2 }}
                     />
                   </Box>

                   {/* GPU Usage */}
                   <Box sx={{ mb: 1.5 }}>
                     <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                       <Typography variant="body2" color="text.secondary">GPU</Typography>
                       <Typography variant="body2" sx={{ fontWeight: 600 }}>
                         {systemMetrics?.gpu?.[0]?.temperature_fahrenheit?.toFixed(0) || 'N/A'}°F
                       </Typography>
                     </Box>
                     <LinearProgress
                       variant="determinate"
                       value={systemMetrics?.gpu?.[0]?.utilization?.gpu_percent || 0}
                       sx={{ height: 4, borderRadius: 2 }}
                       color={(systemMetrics?.gpu?.[0]?.temperature_fahrenheit && systemMetrics.gpu[0].temperature_fahrenheit > 150) ? "error" : "warning"}
                     />
                   </Box>

                   {/* GPU Memory */}
                   <Box sx={{ mb: 1 }}>
                     <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                       <Typography variant="body2" color="text.secondary">GPU Memory</Typography>
                       <Typography variant="body2" sx={{ fontWeight: 600 }}>
                         {systemMetrics?.gpu?.[0]?.memory?.used_mb ? (systemMetrics.gpu[0].memory.used_mb / 1024).toFixed(1) : 'N/A'}GB/
                         {systemMetrics?.gpu?.[0]?.memory?.total_mb ? (systemMetrics.gpu[0].memory.total_mb / 1024).toFixed(1) : 'N/A'}GB
                       </Typography>
                     </Box>
                     <LinearProgress
                       variant="determinate"
                       value={systemMetrics?.gpu?.[0]?.utilization?.memory_percent || 0}
                       sx={{ height: 4, borderRadius: 2 }}
                       color="info"
                     />
                   </Box>
                 </>
               )}
             </CardContent>
           </Card>
         </Grid>

         <Grid item xs={12} sm={6} lg={3}>
           <Card elevation={0} sx={{ height: '100%' }}>
             <CardContent>
               {isLoading ? (
                 <CardSkeleton lines={4} />
               ) : (
                 <>
                   <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                     <Typography color="text.secondary" gutterBottom variant="h6">
                       Security Status
                     </Typography>
                     <Shield sx={{ fontSize: 32, color: (securityStatus && securityStatus.active_agents && securityStatus.active_agents > 0) ? 'success.main' : 'warning.main' }} />
                   </Box>

                   <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                     <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main' }}>
                       {securityStatus?.active_agents || 0}
                     </Typography>
                     <Typography variant="body2" color="text.secondary">
                       agents secured
                     </Typography>
                   </Box>

                   {/* Security Incidents */}
                   <Box sx={{ mb: 2 }}>
                     <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                       <Typography variant="body2" color="text.secondary">Active Incidents</Typography>
                       <Typography variant="body2" sx={{ fontWeight: 600, color: (securityStatus?.total_incidents && securityStatus.total_incidents > 0) ? 'warning.main' : 'success.main' }}>
                         {securityStatus?.total_incidents || 0}
                       </Typography>
                     </Box>
                     {(securityStatus?.total_incidents && securityStatus.total_incidents > 0) ? (
                       <LinearProgress
                         variant="determinate"
                         value={Math.min(securityStatus.total_incidents * 10, 100)}
                         sx={{ height: 4, borderRadius: 2 }}
                         color="warning"
                       />
                     ) : (
                       <LinearProgress
                         variant="determinate"
                         value={100}
                         sx={{ height: 4, borderRadius: 2 }}
                         color="success"
                       />
                     )}
                   </Box>

                   {/* Resource Limits */}
                   <Box sx={{ mb: 2 }}>
                     <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                       Limits: {securityStatus?.resource_limits?.max_concurrent_agents || 8} agents max
                     </Typography>
                     <Typography variant="body2" color="text.secondary">
                       Memory: {securityStatus?.resource_limits?.max_memory_mb ? Math.round(securityStatus.resource_limits.max_memory_mb / 1024) : 128}GB limit
                     </Typography>
                   </Box>

                   <Button
                     variant="outlined"
                     size="small"
                     onClick={() => navigate('/security')}
                     sx={{ width: '100%' }}
                   >
                     View Security Center
                   </Button>
                 </>
               )}
             </CardContent>
           </Card>
         </Grid>

         <Grid item xs={12} sm={6} lg={3}>
           <Card elevation={0} sx={{ height: '100%' }}>
             <CardContent>
               {isLoading ? (
                 <CardSkeleton lines={3} />
               ) : (
                 <>
                   <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                     <Typography color="text.secondary" gutterBottom variant="h6">
                       Ollama Service
                     </Typography>
                     <CheckCircle sx={{
                       fontSize: 32,
                       color: ollamaHealth?.status === 'healthy' ? 'success.main' : 'error.main'
                     }} />
                   </Box>

                   <Chip
                     label={ollamaHealth?.status || 'Not Available'}
                     color={ollamaHealth?.status === 'healthy' ? 'success' : ollamaHealth?.status === 'error' ? 'error' : 'default'}
                     sx={{ mb: 2, fontWeight: 600, textTransform: 'capitalize' }}
                   />

                   <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                     Models Available: {ollamaHealth?.models_available || 'N/A'}
                   </Typography>
                   <Typography variant="body2" color="text.secondary">
                     Default: {ollamaHealth?.default_model || 'N/A'}
                   </Typography>

                   <Button
                     variant="outlined"
                     size="small"
                     onClick={() => navigate('/system-health')}
                     sx={{ width: '100%', mt: 2 }}
                   >
                     View System Health
                   </Button>
                 </>
               )}
             </CardContent>
           </Card>
         </Grid>
      </Grid>

     {/* Main Content Grid */}
      <Grid container spacing={3}>
        {/* Recent Tasks */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0} sx={{ height: 400 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Recent Tasks
                </Typography>
                <Button
                  variant="text"
                  size="small"
                  onClick={() => navigate('/workflows')}
                >
                  View All
                </Button>
              </Box>

              {isLoading ? (
                <Box>
                  {[...Array(4)].map((_, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', py: 2 }}>
                      <Skeleton variant="circular" width={24} height={24} sx={{ mr: 2 }} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton variant="text" width="60%" height={20} />
                        <Skeleton variant="text" width="40%" height={16} />
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : (
                <List>
                  {dashboardData?.recentTasks?.map((task: any) => (
                    <ListItem key={task.id} disableGutters>
                      <ListItemIcon>
                        {getStatusIcon(task.status)}
                      </ListItemIcon>
                      <ListItemText
                        primary={task.agent_name}
                        secondary={`${task.status} • ${new Date(task.created_at).toLocaleTimeString()}`}
                        primaryTypographyProps={{ fontWeight: 500 }}
                      />
                      <Chip
                        label={task.status}
                        size="small"
                        variant="outlined"
                        sx={{ textTransform: 'capitalize' }}
                      />
                    </ListItem>
                  )) || (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No recent tasks
                      </Typography>
                    </Box>
                  )}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* System Logs */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0} sx={{ height: 400 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  System Logs
                </Typography>
                <Button
                  variant="text"
                  size="small"
                  onClick={() => navigate('/utilities')}
                >
                  View All
                </Button>
              </Box>

              {isLoading ? (
                <Box>
                  {[...Array(4)].map((_, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', py: 2 }}>
                      <Skeleton variant="circular" width={24} height={24} sx={{ mr: 2 }} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton variant="text" width="80%" height={20} />
                        <Skeleton variant="text" width="50%" height={16} />
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : (
                <List>
                  {dashboardData?.recentLogs?.map((log: any, index: number) => (
                    <ListItem key={index} disableGutters>
                      <ListItemIcon>
                        {getLogIcon(log.level)}
                      </ListItemIcon>
                      <ListItemText
                        primary={log.message}
                        secondary={new Date(log.timestamp).toLocaleTimeString()}
                        primaryTypographyProps={{ 
                          fontSize: '0.9rem',
                          sx: { 
                            wordBreak: 'break-word',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }
                        }}
                      />
                    </ListItem>
                  )) || (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Typography variant="body2" color="text.secondary">
                        No recent logs
                      </Typography>
                    </Box>
                  )}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12}>
          <Paper elevation={0} sx={{ p: 3, textAlign: 'center', backgroundColor: 'grey.50' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                startIcon={<Email />}
                onClick={() => navigate('/workflows/email-assistant')}
                disabled
              >
                Email Assistant
              </Button>
              <Button
                variant="contained"
                startIcon={<Description />}
                onClick={() => navigate('/workflows/document-analyzer')}
                disabled
              >
                Document Analyzer
              </Button>
              <Button
                variant="outlined"
                startIcon={<SmartToy />}
                onClick={() => navigate('/agents')}
              >
                Manage Agents
              </Button>
              <Button
                variant="outlined"
                startIcon={<Speed />}
                onClick={() => navigate('/utilities')}
              >
                System Tools
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;