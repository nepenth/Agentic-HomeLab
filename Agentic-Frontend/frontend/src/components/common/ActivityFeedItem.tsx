import React from 'react';
import {
  Box,
  Typography,
  Avatar,
  Chip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Email as EmailIcon,
  Task as TaskIcon,
  Chat as ChatIcon,
  Sync as SyncIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

interface ActivityFeedItemProps {
  type: 'email' | 'task' | 'chat' | 'sync' | 'system';
  title: string;
  description?: string;
  timestamp: string;
  status?: 'success' | 'error' | 'pending' | 'info';
  metadata?: {
    sender?: string;
    priority?: 'low' | 'medium' | 'high';
    count?: number;
    model?: string;
  };
  onClick?: () => void;
}

export const ActivityFeedItem: React.FC<ActivityFeedItemProps> = ({
  type,
  title,
  description,
  timestamp,
  status,
  metadata,
  onClick,
}) => {
  const theme = useTheme();

  const getActivityIcon = () => {
    switch (type) {
      case 'email':
        return <EmailIcon fontSize="small" />;
      case 'task':
        return <TaskIcon fontSize="small" />;
      case 'chat':
        return <ChatIcon fontSize="small" />;
      case 'sync':
        return <SyncIcon fontSize="small" />;
      default:
        return <ScheduleIcon fontSize="small" />;
    }
  };

  const getActivityColor = () => {
    if (status) {
      switch (status) {
        case 'success':
          return theme.palette.success.main;
        case 'error':
          return theme.palette.error.main;
        case 'pending':
          return theme.palette.warning.main;
        case 'info':
          return theme.palette.info.main;
      }
    }

    switch (type) {
      case 'email':
        return theme.palette.primary.main;
      case 'task':
        return theme.palette.secondary.main;
      case 'chat':
        return theme.palette.info.main;
      case 'sync':
        return theme.palette.success.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getStatusIcon = () => {
    if (!status) return null;

    switch (status) {
      case 'success':
        return <CheckCircleIcon sx={{ fontSize: 16, color: theme.palette.success.main }} />;
      case 'error':
        return <ErrorIcon sx={{ fontSize: 16, color: theme.palette.error.main }} />;
      case 'pending':
        return <ScheduleIcon sx={{ fontSize: 16, color: theme.palette.warning.main }} />;
      default:
        return null;
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case 'high':
        return theme.palette.error.main;
      case 'medium':
        return theme.palette.warning.main;
      case 'low':
        return theme.palette.info.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const activityColor = getActivityColor();

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 2,
        py: 2,
        px: 2,
        borderRadius: 1,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background-color 0.2s ease-in-out',
        '&:hover': onClick ? {
          bgcolor: alpha(theme.palette.primary.main, 0.04),
        } : {},
      }}
      onClick={onClick}
    >
      <Box sx={{ position: 'relative' }}>
        <Avatar
          sx={{
            width: 40,
            height: 40,
            bgcolor: alpha(activityColor, 0.1),
            color: activityColor,
          }}
        >
          {getActivityIcon()}
        </Avatar>
        {status && (
          <Box
            sx={{
              position: 'absolute',
              bottom: -2,
              right: -2,
              bgcolor: theme.palette.background.paper,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              p: 0.25,
            }}
          >
            {getStatusIcon()}
          </Box>
        )}
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 1,
            mb: 0.5,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              color: theme.palette.text.primary,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {title}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              color: theme.palette.text.secondary,
              flexShrink: 0,
              fontSize: '0.7rem',
            }}
          >
            {formatDistanceToNow(new Date(timestamp), { addSuffix: true })}
          </Typography>
        </Box>

        {description && (
          <Typography
            variant="body2"
            sx={{
              color: theme.palette.text.secondary,
              fontSize: '0.875rem',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              mb: 1,
            }}
          >
            {description}
          </Typography>
        )}

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            flexWrap: 'wrap',
          }}
        >
          {metadata?.sender && (
            <Chip
              label={metadata.sender}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                color: theme.palette.primary.main,
              }}
            />
          )}

          {metadata?.priority && (
            <Chip
              label={metadata.priority.toUpperCase()}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                bgcolor: alpha(getPriorityColor(metadata.priority), 0.1),
                color: getPriorityColor(metadata.priority),
                fontWeight: 600,
              }}
            />
          )}

          {metadata?.count !== undefined && (
            <Chip
              label={`${metadata.count} items`}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                bgcolor: alpha(theme.palette.info.main, 0.1),
                color: theme.palette.info.main,
              }}
            />
          )}

          {metadata?.model && (
            <Chip
              label={metadata.model}
              size="small"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                bgcolor: alpha(theme.palette.secondary.main, 0.1),
                color: theme.palette.secondary.main,
              }}
            />
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default ActivityFeedItem;
