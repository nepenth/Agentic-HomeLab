import React, { useState, useEffect } from 'react';
import {
  Box,
  Chip,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  SignalCellularAlt as SignalIcon,
} from '@mui/icons-material';

export type ConnectionStatus = 'online' | 'offline' | 'slow' | 'reconnecting';
export type ConnectionQuality = 'excellent' | 'good' | 'fair' | 'poor';

interface ConnectionStatusProps {
  status: ConnectionStatus;
  quality?: ConnectionQuality;
  latency?: number;
  onRetry?: () => void;
}

export const ConnectionStatusIndicator: React.FC<ConnectionStatusProps> = ({
  status,
  quality = 'good',
  latency,
  onRetry,
}) => {
  const theme = useTheme();

  const getStatusColor = () => {
    switch (status) {
      case 'online':
        switch (quality) {
          case 'excellent':
            return theme.palette.success.main;
          case 'good':
            return theme.palette.success.light;
          case 'fair':
            return theme.palette.warning.main;
          case 'poor':
            return theme.palette.error.light;
          default:
            return theme.palette.success.main;
        }
      case 'slow':
        return theme.palette.warning.main;
      case 'reconnecting':
        return theme.palette.info.main;
      case 'offline':
        return theme.palette.error.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'online':
        return <SignalIcon fontSize="small" />;
      case 'slow':
      case 'reconnecting':
        return <WifiIcon fontSize="small" />;
      case 'offline':
        return <WifiOffIcon fontSize="small" />;
      default:
        return <WifiIcon fontSize="small" />;
    }
  };

  const getStatusLabel = () => {
    if (status === 'online' && latency !== undefined) {
      return `${latency}ms`;
    }
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const getTooltipText = () => {
    let text = `Connection: ${status}`;
    if (status === 'online') {
      text += `\nQuality: ${quality}`;
      if (latency !== undefined) {
        text += `\nLatency: ${latency}ms`;
      }
    }
    if (status === 'offline' && onRetry) {
      text += '\nClick to retry';
    }
    return text;
  };

  return (
    <Tooltip title={getTooltipText()} arrow>
      <Chip
        icon={getStatusIcon()}
        label={getStatusLabel()}
        size="small"
        onClick={status === 'offline' ? onRetry : undefined}
        sx={{
          height: 24,
          bgcolor: alpha(getStatusColor(), 0.1),
          color: getStatusColor(),
          border: `1px solid ${getStatusColor()}`,
          fontWeight: 600,
          fontSize: '0.7rem',
          cursor: status === 'offline' && onRetry ? 'pointer' : 'default',
          '& .MuiChip-icon': {
            color: getStatusColor(),
          },
          animation: status === 'reconnecting' ? 'pulse 2s infinite' : 'none',
          '@keyframes pulse': {
            '0%': {
              opacity: 1,
            },
            '50%': {
              opacity: 0.5,
            },
            '100%': {
              opacity: 1,
            },
          },
        }}
      />
    </Tooltip>
  );
};

// Hook to monitor connection quality
export const useConnectionQuality = () => {
  const [status, setStatus] = useState<ConnectionStatus>('online');
  const [quality, setQuality] = useState<ConnectionQuality>('good');
  const [latency, setLatency] = useState<number>(0);

  useEffect(() => {
    // Monitor online/offline status
    const handleOnline = () => setStatus('online');
    const handleOffline = () => setStatus('offline');

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial status
    setStatus(navigator.onLine ? 'online' : 'offline');

    // Ping server every 30 seconds to measure latency
    const pingInterval = setInterval(async () => {
      if (!navigator.onLine) {
        setStatus('offline');
        return;
      }

      const startTime = Date.now();
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/health`, {
          method: 'GET',
          cache: 'no-cache',
        });

        if (!response.ok) {
          setStatus('slow');
          setQuality('poor');
          return;
        }

        const endTime = Date.now();
        const responseTime = endTime - startTime;
        setLatency(responseTime);

        // Determine quality based on latency
        if (responseTime < 100) {
          setQuality('excellent');
          setStatus('online');
        } else if (responseTime < 300) {
          setQuality('good');
          setStatus('online');
        } else if (responseTime < 1000) {
          setQuality('fair');
          setStatus('slow');
        } else {
          setQuality('poor');
          setStatus('slow');
        }
      } catch (error) {
        setStatus('offline');
        setQuality('poor');
      }
    }, 30000); // Check every 30 seconds

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(pingInterval);
    };
  }, []);

  const retry = async () => {
    setStatus('reconnecting');
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/health`);
      if (response.ok) {
        setStatus('online');
      } else {
        setStatus('offline');
      }
    } catch (error) {
      setStatus('offline');
    }
  };

  return { status, quality, latency, retry };
};
