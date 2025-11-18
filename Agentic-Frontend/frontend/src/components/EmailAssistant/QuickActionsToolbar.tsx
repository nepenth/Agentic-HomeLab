import React, { useState } from 'react';
import {
  Box,
  Paper,
  IconButton,
  Tooltip,
  Typography,
  Divider,
  alpha,
  useTheme,
  Popper,
  ClickAwayListener,
  MenuList,
  MenuItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  Reply as ReplyIcon,
  ReplyAll as ReplyAllIcon,
  Forward as ForwardIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Flag as FlagIcon,
  Label as LabelIcon,
  MoreVert as MoreIcon,
  TaskAlt as TaskIcon,
  Markunread as MarkUnreadIcon,
  Drafts as MarkReadIcon,
  Schedule as SnoozeIcon,
  Folder as MoveIcon,
  GetApp as DownloadIcon,
  Print as PrintIcon,
  Block as BlockIcon
} from '@mui/icons-material';

interface Email {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  is_read: boolean;
  is_important: boolean;
  is_flagged: boolean;
  is_answered: boolean;
  has_attachments: boolean;
}

interface QuickActionsToolbarProps {
  selectedEmail: Email | null;
  selectedCount: number;
  onReply?: () => void;
  onReplyAll?: () => void;
  onForward?: () => void;
  onDelete?: () => void;
  onArchive?: () => void;
  onToggleImportant?: (important: boolean) => void;
  onToggleFlag?: (flagged: boolean) => void;
  onMarkAsRead?: () => void;
  onMarkAsUnread?: () => void;
  onCreateTask?: () => void;
  onMove?: () => void;
  onLabel?: () => void;
  onDownload?: () => void;
  onPrint?: () => void;
  onBlock?: () => void;
  onSnooze?: () => void;
}

export const QuickActionsToolbar: React.FC<QuickActionsToolbarProps> = ({
  selectedEmail,
  selectedCount,
  onReply,
  onReplyAll,
  onForward,
  onDelete,
  onArchive,
  onToggleImportant,
  onToggleFlag,
  onMarkAsRead,
  onMarkAsUnread,
  onCreateTask,
  onMove,
  onLabel,
  onDownload,
  onPrint,
  onBlock,
  onSnooze
}) => {
  const theme = useTheme();
  const [moreMenuAnchor, setMoreMenuAnchor] = useState<null | HTMLElement>(null);

  const handleMoreClick = (event: React.MouseEvent<HTMLElement>) => {
    setMoreMenuAnchor(event.currentTarget);
  };

  const handleMoreClose = () => {
    setMoreMenuAnchor(null);
  };

  const hasSelection = selectedCount > 0;
  const hasSingleSelection = selectedCount === 1 && selectedEmail;

  const primaryActions = [
    {
      icon: <ReplyIcon fontSize="small" />,
      tooltip: 'Reply',
      onClick: onReply,
      disabled: !hasSingleSelection,
      show: true
    },
    {
      icon: <ReplyAllIcon fontSize="small" />,
      tooltip: 'Reply All',
      onClick: onReplyAll,
      disabled: !hasSingleSelection,
      show: true
    },
    {
      icon: <ForwardIcon fontSize="small" />,
      tooltip: 'Forward',
      onClick: onForward,
      disabled: !hasSingleSelection,
      show: true
    },
    {
      icon: <ArchiveIcon fontSize="small" />,
      tooltip: 'Archive',
      onClick: onArchive,
      disabled: !hasSelection,
      show: true
    },
    {
      icon: <DeleteIcon fontSize="small" />,
      tooltip: 'Delete',
      onClick: onDelete,
      disabled: !hasSelection,
      show: true
    }
  ];

  const secondaryActions = [
    {
      icon: selectedEmail?.is_important ? <StarIcon fontSize="small" /> : <StarBorderIcon fontSize="small" />,
      tooltip: selectedEmail?.is_important ? 'Unstar' : 'Star',
      onClick: () => onToggleImportant?.(!selectedEmail?.is_important),
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    },
    {
      icon: <FlagIcon fontSize="small" />,
      tooltip: selectedEmail?.is_flagged ? 'Unflag' : 'Flag',
      onClick: () => onToggleFlag?.(!selectedEmail?.is_flagged),
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    },
    {
      icon: selectedEmail?.is_read ? <MarkUnreadIcon fontSize="small" /> : <MarkReadIcon fontSize="small" />,
      tooltip: selectedEmail?.is_read ? 'Mark as Unread' : 'Mark as Read',
      onClick: selectedEmail?.is_read ? onMarkAsUnread : onMarkAsRead,
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    },
    {
      icon: <TaskIcon fontSize="small" />,
      tooltip: 'Create Task',
      onClick: onCreateTask,
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    },
    {
      icon: <MoveIcon fontSize="small" />,
      tooltip: 'Move to Folder',
      onClick: onMove,
      disabled: !hasSelection,
      show: true
    },
    {
      icon: <LabelIcon fontSize="small" />,
      tooltip: 'Add Label',
      onClick: onLabel,
      disabled: !hasSelection,
      show: true
    },
    {
      icon: <DownloadIcon fontSize="small" />,
      tooltip: 'Download',
      onClick: onDownload,
      disabled: !hasSelection,
      show: true
    },
    {
      icon: <PrintIcon fontSize="small" />,
      tooltip: 'Print',
      onClick: onPrint,
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    },
    {
      icon: <SnoozeIcon fontSize="small" />,
      tooltip: 'Snooze',
      onClick: onSnooze,
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    },
    {
      icon: <BlockIcon fontSize="small" />,
      tooltip: 'Block Sender',
      onClick: onBlock,
      disabled: !hasSingleSelection,
      show: hasSingleSelection
    }
  ];

  if (!hasSelection) {
    return null;
  }

  return (
    <>
      <Paper
        sx={{
          position: 'fixed',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1200,
          borderRadius: 3,
          boxShadow: theme.shadows[8],
          border: `1px solid ${theme.palette.divider}`,
          backgroundColor: theme.palette.background.paper,
          px: 1,
          py: 0.5,
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          maxWidth: '90vw',
          overflow: 'hidden'
        }}
      >
        {/* Selection Count */}
        <Box sx={{ px: 1, py: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>
            {selectedCount} selected
          </Typography>
        </Box>

        <Divider orientation="vertical" flexItem />

        {/* Primary Actions */}
        {primaryActions.map((action, index) => (
          action.show && (
            <Tooltip key={index} title={action.tooltip}>
              <span>
                <IconButton
                  size="small"
                  onClick={action.onClick}
                  disabled={action.disabled}
                  sx={{
                    color: action.disabled ? 'text.disabled' : 'text.primary',
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.primary.main, 0.1)
                    }
                  }}
                >
                  {action.icon}
                </IconButton>
              </span>
            </Tooltip>
          )
        ))}

        <Divider orientation="vertical" flexItem />

        {/* Secondary Actions - Show first few */}
        {secondaryActions.slice(0, 4).map((action, index) => (
          action.show && (
            <Tooltip key={index} title={action.tooltip}>
              <span>
                <IconButton
                  size="small"
                  onClick={action.onClick}
                  disabled={action.disabled}
                  sx={{
                    color: action.disabled ? 'text.disabled' : 'text.secondary',
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.primary.main, 0.1)
                    }
                  }}
                >
                  {action.icon}
                </IconButton>
              </span>
            </Tooltip>
          )
        ))}

        {/* More Actions Menu */}
        <Tooltip title="More actions">
          <IconButton
            size="small"
            onClick={handleMoreClick}
            sx={{
              color: 'text.secondary',
              '&:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.1)
              }
            }}
          >
            <MoreIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Paper>

      {/* More Actions Menu */}
      <Popper
        open={Boolean(moreMenuAnchor)}
        anchorEl={moreMenuAnchor}
        placement="top"
        sx={{ zIndex: 1300 }}
      >
        <ClickAwayListener onClickAway={handleMoreClose}>
          <Paper sx={{ minWidth: 200, maxWidth: 300 }}>
            <MenuList dense>
              {secondaryActions.slice(4).map((action, index) => (
                action.show && (
                  <MenuItem
                    key={index}
                    onClick={() => {
                      action.onClick?.();
                      handleMoreClose();
                    }}
                    disabled={action.disabled}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      {action.icon}
                    </ListItemIcon>
                    <ListItemText primary={action.tooltip} />
                  </MenuItem>
                )
              ))}
            </MenuList>
          </Paper>
        </ClickAwayListener>
      </Popper>
    </>
  );
};

export default QuickActionsToolbar;