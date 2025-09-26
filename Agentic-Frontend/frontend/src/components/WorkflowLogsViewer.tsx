import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
  IconButton,
  Switch,
  FormControlLabel,
  TextField,
  MenuItem,
  Tooltip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Clear,
  FilterList,
  Error,
  Warning,
  Info,
  BugReport,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import webSocketService from '../services/websocket';

interface LogEntry {
  id: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  timestamp: string;
  component?: string;
  context?: any;
  workflow_id?: string;
  workflow_type?: string;
  user_id?: number;
}

interface WorkflowLogsViewerProps {
  workflowType: 'email_sync' | 'knowledge_base' | 'agent_task';
  workflowId?: string;
  title?: string;
  height?: number;
}

const LOG_LEVEL_COLORS = {
  debug: '#9e9e9e',
  info: '#2196f3',
  warning: '#ff9800',
  error: '#f44336',
};

const WorkflowLogsViewer: React.FC<WorkflowLogsViewerProps> = ({
  workflowType,
  workflowId,
  title = 'Workflow Logs',
  height = 600
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [searchFilter, setSearchFilter] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);

  // Check login status and get current user
  useEffect(() => {
    const checkAuth = async () => {
      const token = apiClient.getAuthToken();
      if (token) {
        setIsLoggedIn(true);
        setCurrentUserId(1); // TODO: Extract from token or fetch user info
      } else {
        setIsLoggedIn(false);
        setCurrentUserId(null);
      }
    };
    checkAuth();
  }, []);

  // Load historical logs for the workflow
  const loadHistoricalLogs = useCallback(async () => {
    if (!isLoggedIn || !currentUserId) return;

    try {
      let historicalLogs: LogEntry[] = [];

      // Load user-scoped logs filtered by workflow type
      historicalLogs = await apiClient.getUserLogs(currentUserId, {
        workflow_type: workflowType,
        limit: 100
      });

      // Filter by specific workflow ID if provided
      if (workflowId) {
        historicalLogs = historicalLogs.filter(log =>
          log.context?.workflow_id === workflowId
        );
      }

      setLogs(historicalLogs.reverse()); // Show newest at bottom
      console.log(`Loaded ${historicalLogs.length} historical logs for ${workflowType}`);
    } catch (error) {
      console.error(`Failed to load historical logs for ${workflowType}:`, error);
      setConnectionError(`Failed to load historical logs: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [isLoggedIn, currentUserId, workflowType, workflowId]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Handle incoming log messages
  const handleLogMessage = useCallback((message: any) => {
    console.log('Received log message:', message);

    // Extract log entry from message data
    const logEntry: LogEntry = message.data || message;

    // Filter by workflow type
    if (logEntry.context?.workflow_type !== workflowType) {
      return;
    }

    // Filter by specific workflow ID if provided
    if (workflowId && logEntry.context?.workflow_id !== workflowId) {
      return;
    }

    setLogs(prevLogs => {
      const newLogs = [...prevLogs, logEntry];
      // Keep only last 500 logs for performance
      return newLogs.slice(-500);
    });
  }, [workflowType, workflowId]);

  // Start/stop log streaming
  const toggleLogStreaming = useCallback(async () => {
    if (isStreaming) {
      // Stop streaming
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      setIsStreaming(false);
      setConnectionStatus('disconnected');
      setConnectionError(null);
    } else {
      // Start streaming
      console.log('Starting workflow log streaming for:', workflowType);
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

        // Load historical logs first
        await loadHistoricalLogs();

        // Subscribe to live logs with workflow type filter
        unsubscribeRef.current = webSocketService.subscribeToLogs(
          handleLogMessage,
          { workflow_type: workflowType }
        );

        setIsStreaming(true);

        // Check connection status after a short delay
        setTimeout(() => {
          if (webSocketService.isConnected()) {
            setConnectionStatus('connected');
          } else {
            setConnectionStatus('error');
            setConnectionError('Failed to establish WebSocket connection');
          }
        }, 1000);

      } catch (error) {
        console.error('Failed to start log streaming:', error);
        setConnectionError('Failed to start log streaming. Please try again.');
        setConnectionStatus('error');
      }
    }
  }, [isStreaming, handleLogMessage, loadHistoricalLogs, workflowType]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  // Get log level icon
  const getLogLevelIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return <Error sx={{ color: LOG_LEVEL_COLORS.error }} />;
      case 'warning':
        return <Warning sx={{ color: LOG_LEVEL_COLORS.warning }} />;
      case 'info':
        return <Info sx={{ color: LOG_LEVEL_COLORS.info }} />;
      case 'debug':
        return <BugReport sx={{ color: LOG_LEVEL_COLORS.debug }} />;
      default:
        return <Info sx={{ color: LOG_LEVEL_COLORS.info }} />;
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  // Filter logs based on level and search
  const filteredLogs = logs.filter(log => {
    const levelMatch = levelFilter === 'all' || log.level === levelFilter;
    const searchMatch = searchFilter === '' ||
      log.message.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (log.component && log.component.toLowerCase().includes(searchFilter.toLowerCase()));
    return levelMatch && searchMatch;
  });

  // Clear logs
  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <Paper elevation={1} sx={{ p: 2, height: height }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">{title}</Typography>

        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <TextField
            select
            size="small"
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            label="Level"
            sx={{ minWidth: 100 }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="error">Error</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="info">Info</MenuItem>
            <MenuItem value="debug">Debug</MenuItem>
          </TextField>

          <TextField
            size="small"
            placeholder="Search logs..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            sx={{ minWidth: 150 }}
            InputProps={{
              startAdornment: <FilterList sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          />

          <Tooltip title="Clear logs">
            <IconButton onClick={clearLogs} size="small">
              <Clear />
            </IconButton>
          </Tooltip>

          <IconButton
            onClick={toggleLogStreaming}
            disabled={!isLoggedIn || connectionStatus === 'connecting'}
            color={connectionStatus === 'connected' ? 'success' : 'primary'}
            size="small"
          >
            {connectionStatus === 'connecting' ? <CircularProgress size={20} /> :
             connectionStatus === 'error' ? <Error /> :
             isStreaming ? <Stop /> : <PlayArrow />}
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
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

          <Chip
            label={`${filteredLogs.length} logs`}
            size="small"
            variant="outlined"
          />

          <Chip
            label={connectionStatus === 'connected' ? 'Live' : connectionStatus}
            size="small"
            color={
              connectionStatus === 'connected' ? 'success' :
              connectionStatus === 'error' ? 'error' :
              connectionStatus === 'connecting' ? 'warning' : 'default'
            }
          />
        </Box>
      </Box>

      {connectionError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setConnectionError(null)}>
          {connectionError}
        </Alert>
      )}

      <Box
        sx={{
          height: height - 150,
          overflow: 'auto',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: 'grey.50'
        }}
      >
        <List dense sx={{ p: 0 }}>
          {filteredLogs.length === 0 ? (
            <ListItem>
              <ListItemText
                primary="No logs available"
                secondary={!isLoggedIn ? "Please log in to view logs" : `No ${workflowType} logs found`}
              />
            </ListItem>
          ) : (
            filteredLogs.map((log) => (
              <ListItem
                key={log.id}
                sx={{
                  borderBottom: 1,
                  borderColor: 'divider',
                  py: 1,
                  '&:hover': { bgcolor: 'action.hover' }
                }}
              >
                <Box sx={{ display: 'flex', width: '100%', alignItems: 'flex-start', gap: 1 }}>
                  <Box sx={{ mt: 0.5 }}>
                    {getLogLevelIcon(log.level)}
                  </Box>
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: 'monospace',
                        wordBreak: 'break-word',
                        mb: 0.5
                      }}
                    >
                      {log.message}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        {formatTimestamp(log.timestamp)}
                      </Typography>
                      {log.component && (
                        <Chip label={log.component} size="small" variant="outlined" />
                      )}
                      {log.context?.workflow_id && (
                        <Chip
                          label={`ID: ${log.context.workflow_id.slice(-8)}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      <Chip
                        label={log.level.toUpperCase()}
                        size="small"
                        sx={{
                          bgcolor: LOG_LEVEL_COLORS[log.level as keyof typeof LOG_LEVEL_COLORS],
                          color: 'white',
                          fontWeight: 'bold'
                        }}
                      />
                    </Box>
                  </Box>
                </Box>
              </ListItem>
            ))
          )}
        </List>
        <div ref={logsEndRef} />
      </Box>
    </Paper>
  );
};

export default WorkflowLogsViewer;