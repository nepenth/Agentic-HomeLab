import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider,
  Badge,
  Switch,
  FormControlLabel,
  Grid,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Clear,
  FilterList,
  BugReport,
  Info,
  Warning,
  Error,
  CheckCircle,
  Refresh,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import webSocketService from '../services/websocket';
import apiClient from '../services/api';
import type { LogEntry } from '../types';

interface LogFilters {
  agent_id?: string;
  task_id?: string;
  level?: string;
}

interface LogChannel {
  id: string;
  name: string;
  filters: LogFilters;
  active: boolean;
  logs: LogEntry[];
  color: string;
  connectionType: 'websocket' | 'sse';
}

const LOG_LEVELS = ['debug', 'info', 'warning', 'error'];
const LOG_COLORS = {
  debug: '#9e9e9e',
  info: '#2196f3',
  warning: '#ff9800',
  error: '#f44336',
};

const LogsViewer: React.FC = () => {
  const [channels, setChannels] = useState<LogChannel[]>([
    {
      id: 'all',
      name: 'All Logs',
      filters: {},
      active: true, // This should be true for the default channel
      logs: [],
      color: '#1976d2',
      connectionType: 'websocket',
    },
  ]);

  const [selectedChannel, setSelectedChannel] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [maxLogs, setMaxLogs] = useState(1000);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Fetch available agents for filtering
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => apiClient.getAgents(),
    refetchInterval: 30000,
  });

  // Fetch available tasks for filtering
  const { data: tasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => apiClient.getTasks(),
    refetchInterval: 30000,
  });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [channels, autoScroll]);

  // Listen to WebSocket connection status
  useEffect(() => {
    const unsubscribe = webSocketService.onConnectionStatus((status, error) => {
      console.log('WebSocket connection status:', status, error);
      setConnectionStatus(status);
      if (error) {
        setConnectionError(error);
      } else if (status === 'connected') {
        setConnectionError(null);
      }
    });

    return unsubscribe;
  }, []);

  // Handle incoming log messages
  const handleLogMessage = useCallback((logEntry: LogEntry) => {
    console.log('Received log message:', logEntry);

    setChannels(prevChannels =>
      prevChannels.map(channel => {
        // Check if log matches channel filters
        const matchesFilters = Object.entries(channel.filters).every(([key, value]) => {
          if (!value) return true;
          return logEntry[key as keyof LogEntry] === value;
        });

        console.log(`Channel ${channel.name}: matches filters = ${matchesFilters}, channel.id === 'all' = ${channel.id === 'all'}`);

        if (matchesFilters || channel.id === 'all') {
          const newLogs = [...channel.logs, logEntry];
          // Keep only the most recent logs
          if (newLogs.length > maxLogs) {
            newLogs.splice(0, newLogs.length - maxLogs);
          }
          console.log(`Adding log to channel ${channel.name}, new log count: ${newLogs.length}`);
          return { ...channel, logs: newLogs };
        }
        return channel;
      })
    );
  }, [maxLogs]);

  // Start/stop log streaming
  const toggleLogStreaming = useCallback(async () => {
    const activeChannel = channels.find(c => c.id === selectedChannel);
    if (!activeChannel) {
      console.error('No active channel found for selectedChannel:', selectedChannel);
      setConnectionError('No active channel selected');
      setConnectionStatus('error');
      return;
    }

    console.log('Toggle streaming for channel:', activeChannel.name, 'active:', activeChannel.active);

    if (unsubscribeRef.current) {
      // Stop streaming
      console.log('Stopping log streaming');
      setConnectionStatus('disconnected');
      setConnectionError(null);
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    } else {
      // Start streaming
      console.log('Starting log streaming with filters:', activeChannel.filters);
      setConnectionStatus('connecting');
      setConnectionError(null);

      try {
        // Check if user is authenticated
        const token = apiClient.getAuthToken();
        if (!token) {
          setConnectionError('Authentication required. Please log in to access live logs.');
          setConnectionStatus('error');
          return;
        }

        unsubscribeRef.current = webSocketService.subscribeToLogs(
          handleLogMessage,
          activeChannel.filters
        );

        // Check connection status after a short delay
        setTimeout(() => {
          if (webSocketService.isConnected()) {
            setConnectionStatus('connected');
          } else {
            setConnectionError('Failed to connect to WebSocket. Backend may not be running.');
            setConnectionStatus('error');
            if (unsubscribeRef.current) {
              unsubscribeRef.current();
              unsubscribeRef.current = null;
            }
          }
        }, 2000);

      } catch (error) {
        console.error('Error starting log streaming:', error);
        setConnectionError('Failed to start log streaming. Please try again.');
        setConnectionStatus('error');
      }
    }
  }, [channels, selectedChannel, handleLogMessage]);

  // Add new channel
  const addChannel = useCallback(() => {
    const newChannel: LogChannel = {
      id: `channel-${Date.now()}`,
      name: `Channel ${channels.length}`,
      filters: {},
      active: false,
      logs: [],
      color: '#1976d2',
      connectionType: 'websocket',
    };
    setChannels(prev => [...prev, newChannel]);
  }, [channels.length]);

  // Update channel filters
  const updateChannelFilters = useCallback((channelId: string, filters: LogFilters) => {
    setChannels(prev =>
      prev.map(channel =>
        channel.id === channelId
          ? { ...channel, filters }
          : channel
      )
    );
  }, []);

  // Clear logs for a channel
  const clearChannelLogs = useCallback((channelId: string) => {
    setChannels(prev =>
      prev.map(channel =>
        channel.id === channelId
          ? { ...channel, logs: [] }
          : channel
      )
    );
  }, []);

  // Delete channel
  const deleteChannel = useCallback((channelId: string) => {
    if (channelId === 'all') return; // Can't delete the 'all' channel

    setChannels(prev => {
      const newChannels = prev.filter(c => c.id !== channelId);
      if (selectedChannel === channelId) {
        setSelectedChannel('all');
      }
      return newChannels;
    });
  }, [selectedChannel]);

  // Get log level icon
  const getLogLevelIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return <Error color="error" fontSize="small" />;
      case 'warning':
        return <Warning color="warning" fontSize="small" />;
      case 'info':
        return <Info color="info" fontSize="small" />;
      case 'debug':
        return <BugReport color="disabled" fontSize="small" />;
      default:
        return <Info color="action" fontSize="small" />;
    }
  };

  const selectedChannelData = channels.find(c => c.id === selectedChannel);

  // Debug logging
  console.log('LogsViewer render - Channels:', channels.length, 'Selected:', selectedChannel, 'Data:', !!selectedChannelData);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
            Real-Time Logs Viewer
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Monitor live logs from running agents and tasks
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                size="small"
              />
            }
            label="Auto-scroll"
          />

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant={unsubscribeRef.current ? "outlined" : "contained"}
              color={
                connectionStatus === 'error' ? 'error' :
                connectionStatus === 'connected' ? 'success' :
                connectionStatus === 'connecting' ? 'warning' :
                unsubscribeRef.current ? "error" : "primary"
              }
              startIcon={
                connectionStatus === 'connecting' ? <Refresh sx={{ animation: 'spin 1s linear infinite' }} /> :
                connectionStatus === 'connected' ? <CheckCircle /> :
                connectionStatus === 'error' ? <Error /> :
                unsubscribeRef.current ? <Stop /> : <PlayArrow />
              }
              onClick={toggleLogStreaming}
              disabled={(!selectedChannelData?.active && selectedChannel !== 'all') || connectionStatus === 'connecting'}
            >
              {connectionStatus === 'connecting' ? 'Connecting...' :
               connectionStatus === 'connected' ? 'Streaming' :
               connectionStatus === 'error' ? 'Connection Failed' :
               unsubscribeRef.current ? 'Stop Streaming' : 'Start Streaming'}
            </Button>

            {/* Debug button to test WebSocket without auth */}
            <Button
              variant="outlined"
              size="small"
              color="secondary"
              onClick={() => {
                console.log('Testing WebSocket connection...');
                // Try to connect without authentication for testing
                webSocketService.connect('logs');
                setTimeout(() => {
                  if (webSocketService.isConnected()) {
                    console.log('WebSocket test successful');
                    setConnectionStatus('connected');
                  } else {
                    console.log('WebSocket test failed');
                    setConnectionStatus('error');
                    setConnectionError('WebSocket connection test failed');
                  }
                }, 2000);
              }}
            >
              Test WS
            </Button>

            {/* Debug button to test backend health */}
            <Button
              variant="outlined"
              size="small"
              color="info"
              onClick={async () => {
                try {
                  console.log('Testing backend health...');
                  const response = await apiClient.getHealth();
                  console.log('Backend health check successful:', response);
                  setConnectionError('Backend is running - health check passed');
                } catch (error) {
                  console.error('Backend health check failed:', error);
                  setConnectionError('Backend health check failed - backend may not be running');
                  setConnectionStatus('error');
                }
              }}
            >
              Test API
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Connection Status Alert */}
      {connectionStatus !== 'disconnected' && (
        <Alert
          severity={
            connectionStatus === 'connected' ? 'success' :
            connectionStatus === 'connecting' ? 'info' :
            'error'
          }
          sx={{ mb: 3 }}
          action={
            connectionStatus === 'error' ? (
              <Button color="inherit" size="small" onClick={toggleLogStreaming}>
                Retry
              </Button>
            ) : undefined
          }
        >
          {connectionStatus === 'connecting' && 'Attempting to connect to live log stream...'}
          {connectionStatus === 'connected' && `Successfully connected to live log stream for "${selectedChannelData?.name}"`}
          {connectionStatus === 'error' && (connectionError || 'Failed to connect to live log stream')}
        </Alert>
      )}

      {/* Channel Management */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card elevation={0}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Log Channels
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={addChannel}
                  startIcon={<FilterList />}
                >
                  Add Channel
                </Button>
              </Box>

              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {channels.map(channel => (
                  <Chip
                    key={channel.id}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Badge
                          badgeContent={channel.logs.length}
                          color="primary"
                          max={999}
                        >
                          <Box
                            sx={{
                              width: 12,
                              height: 12,
                              borderRadius: '50%',
                              backgroundColor: channel.color,
                            }}
                          />
                        </Badge>
                        {channel.name}
                      </Box>
                    }
                    onClick={() => setSelectedChannel(channel.id)}
                    color={selectedChannel === channel.id ? 'primary' : 'default'}
                    variant={selectedChannel === channel.id ? 'filled' : 'outlined'}
                    onDelete={channel.id !== 'all' ? () => deleteChannel(channel.id) : undefined}
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Channel Filters
              </Typography>

              {selectedChannelData && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControl size="small" fullWidth>
                    <InputLabel>Agent</InputLabel>
                    <Select
                      value={selectedChannelData.filters.agent_id || ''}
                      label="Agent"
                      onChange={(e) => updateChannelFilters(selectedChannel, {
                        ...selectedChannelData.filters,
                        agent_id: e.target.value || undefined
                      })}
                    >
                      <MenuItem value="">All Agents</MenuItem>
                      {agents?.map(agent => (
                        <MenuItem key={agent.id} value={agent.id}>
                          {agent.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl size="small" fullWidth>
                    <InputLabel>Task</InputLabel>
                    <Select
                      value={selectedChannelData.filters.task_id || ''}
                      label="Task"
                      onChange={(e) => updateChannelFilters(selectedChannel, {
                        ...selectedChannelData.filters,
                        task_id: e.target.value || undefined
                      })}
                    >
                      <MenuItem value="">All Tasks</MenuItem>
                      {tasks?.map(task => (
                        <MenuItem key={task.id} value={task.id}>
                          {task.id}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl size="small" fullWidth>
                    <InputLabel>Log Level</InputLabel>
                    <Select
                      value={selectedChannelData.filters.level || ''}
                      label="Log Level"
                      onChange={(e) => updateChannelFilters(selectedChannel, {
                        ...selectedChannelData.filters,
                        level: e.target.value || undefined
                      })}
                    >
                      <MenuItem value="">All Levels</MenuItem>
                      {LOG_LEVELS.map(level => (
                        <MenuItem key={level} value={level}>
                          {level.toUpperCase()}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Logs Display */}
      <Card elevation={0}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {selectedChannelData?.name} ({selectedChannelData?.logs.length} logs)
            </Typography>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                size="small"
                type="number"
                label="Max Logs"
                value={maxLogs}
                onChange={(e) => setMaxLogs(parseInt(e.target.value) || 100)}
                sx={{ width: 100 }}
              />
              <Button
                variant="outlined"
                size="small"
                startIcon={<Clear />}
                onClick={() => clearChannelLogs(selectedChannel)}
              >
                Clear
              </Button>
            </Box>
          </Box>

          <Paper
            elevation={0}
            sx={{
              height: 500,
              overflow: 'auto',
              backgroundColor: 'grey.50',
              p: 2,
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              // Ensure scroll bars are visible
              '&::-webkit-scrollbar': {
                width: '8px',
                height: '8px',
              },
              '&::-webkit-scrollbar-track': {
                backgroundColor: 'rgba(0, 0, 0, 0.1)',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
                borderRadius: '4px',
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.5)',
                },
              },
              scrollbarWidth: 'thin',
              scrollbarColor: 'rgba(0, 0, 0, 0.3) rgba(0, 0, 0, 0.1)',
            }}
          >
            {selectedChannelData?.logs.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  {unsubscribeRef.current ? 'Waiting for logs...' : 'No logs to display. Start streaming to see live logs.'}
                </Typography>
              </Box>
            ) : (
              selectedChannelData && (
                <List dense>
                  {selectedChannelData.logs.map((log, index) => (
                    <React.Fragment key={`${log.timestamp}-${index}`}>
                      <ListItem sx={{ px: 0, py: 0.5 }}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {getLogLevelIcon(log.level)}
                              <Typography
                                variant="body2"
                                sx={{
                                  fontFamily: 'monospace',
                                  fontSize: '0.8rem',
                                  color: LOG_COLORS[log.level as keyof typeof LOG_COLORS] || '#000',
                                  flex: 1,
                                }}
                              >
                                [{new Date(log.timestamp).toLocaleTimeString()}] {log.message}
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <Box sx={{ display: 'flex', gap: 2, mt: 0.5 }}>
                              {log.agent_id && (
                                <Chip
                                  label={`Agent: ${log.agent_id}`}
                                  size="small"
                                  variant="outlined"
                                  sx={{ fontSize: '0.7rem' }}
                                />
                              )}
                              {log.task_id && (
                                <Chip
                                  label={`Task: ${log.task_id}`}
                                  size="small"
                                  variant="outlined"
                                  sx={{ fontSize: '0.7rem' }}
                                />
                              )}
                              <Chip
                                label={log.level.toUpperCase()}
                                size="small"
                                color={log.level === 'error' ? 'error' : log.level === 'warning' ? 'warning' : 'default'}
                                sx={{ fontSize: '0.7rem' }}
                              />
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < selectedChannelData.logs.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                  <div ref={logsEndRef} />
                </List>
              )
            )}
          </Paper>
        </CardContent>
      </Card>

    </Box>
  );
};

export default LogsViewer;