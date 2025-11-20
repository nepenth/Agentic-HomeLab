import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  Typography,
  Chip,
  Checkbox,
  IconButton,
  Avatar,
  Tooltip,
  alpha,
  useTheme,
  Skeleton,
  Fade
} from '@mui/material';
import {
  StarBorder as StarBorderIcon,
  Star as StarIcon,
  AttachFile as AttachFileIcon,
  Reply as ReplyIcon,
  Delete as DeleteIcon,
  Drafts as DraftsIcon,
  Flag as FlagIcon,
  Circle as CircleIcon,
  Archive as ArchiveIcon,
  MarkEmailRead as MarkEmailReadIcon,
  MarkEmailUnread as MarkEmailUnreadIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { decodeMimeHeader } from '../../utils/emailUtils';

interface Email {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  body_text: string;
  sent_at: string;
  received_at: string;
  is_read: boolean;
  is_important: boolean;
  is_flagged: boolean;
  is_draft: boolean;
  is_answered: boolean;
  is_deleted: boolean;
  is_spam: boolean;
  has_attachments: boolean;
  attachment_count?: number;
  category?: string;
  folder_path?: string;
}

interface EmailListPanelProps {
  emails: Email[];
  selectedEmailId: string | null;
  selectedItems: string[];
  onEmailSelect: (email: Email) => void;
  onToggleSelection: (id: string) => void;
  onToggleImportant: (id: string, important: boolean) => void;
  onMarkAsRead: (id: string) => void;
  isLoading?: boolean;
}

export const EmailListPanel: React.FC<EmailListPanelProps> = ({
  emails,
  selectedEmailId,
  selectedItems,
  onEmailSelect,
  onToggleSelection,
  onToggleImportant,
  onMarkAsRead,
  isLoading = false
}) => {
  const theme = useTheme();

  const getInitials = (name: string, email: string) => {
    if (name && name !== email) {
      const parts = name.split(' ');
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  };

  const getAvatarColor = (email: string) => {
    const colors = [
      theme.palette.primary.main,
      theme.palette.secondary.main,
      theme.palette.error.main,
      theme.palette.warning.main,
      theme.palette.info.main,
      theme.palette.success.main,
    ];
    const hash = email.split('').reduce((acc, char) => char.charCodeAt(0) + acc, 0);
    return colors[hash % colors.length];
  };

  // Loading Skeleton
  if (isLoading) {
    return (
      <Box sx={{ p: 0, height: '100%', overflow: 'hidden' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Box
            key={i}
            sx={{
              display: 'flex',
              p: 2,
              borderBottom: `1px solid ${theme.palette.divider}`,
              alignItems: 'flex-start'
            }}
          >
            <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2, flexShrink: 0 }} />
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Skeleton variant="text" width="40%" height={24} />
                <Skeleton variant="text" width="15%" height={20} />
              </Box>
              <Skeleton variant="text" width="80%" height={20} />
              <Skeleton variant="text" width="60%" height={16} />
            </Box>
          </Box>
        ))}
      </Box>
    );
  }

  // Empty State
  if (!isLoading && emails.length === 0) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
        <Box
          sx={{
            width: 120,
            height: 120,
            borderRadius: '50%',
            backgroundColor: alpha(theme.palette.primary.main, 0.05),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 3
          }}
        >
          <DraftsIcon sx={{ fontSize: 60, color: theme.palette.primary.main, opacity: 0.5 }} />
        </Box>
        <Typography variant="h6" color="text.primary" gutterBottom>
          All caught up!
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No emails found in this folder.
        </Typography>
      </Box>
    );
  }

  return (
    <List sx={{
      p: 0,
      height: '100%',
      overflow: 'auto',
      '& .MuiListItem-root': {
        // Hover styles for the list item to show actions
        '&:hover .email-actions': {
          opacity: 1,
          visibility: 'visible',
        },
        '&:hover .email-date': {
          opacity: 0,
          visibility: 'hidden',
        }
      }
    }}>
      {emails.map((email) => {
        const isSelected = selectedEmailId === email.email_id;
        const isChecked = selectedItems.includes(email.email_id);

        return (
          <ListItem
            key={email.email_id}
            disablePadding
            sx={{
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.4)}`,
              backgroundColor: isSelected
                ? alpha(theme.palette.primary.main, 0.08)
                : !email.is_read
                  ? alpha(theme.palette.background.paper, 1)
                  : alpha(theme.palette.background.default, 0.4),
              transition: 'all 0.2s ease',
            }}
          >
            <ListItemButton
              selected={isSelected}
              onClick={() => onEmailSelect(email)}
              alignItems="flex-start"
              sx={{
                px: 2,
                py: 2,
                gap: 2,
                '&.Mui-selected': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.08),
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.primary.main, 0.12)
                  }
                }
              }}
            >
              {/* Selection & Avatar Column */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                {/* Show checkbox on hover or if checked, otherwise show avatar */}
                <Box sx={{ position: 'relative', width: 40, height: 40 }}>
                  <Fade in={!isChecked} timeout={200}>
                    <Avatar
                      sx={{
                        width: 40,
                        height: 40,
                        bgcolor: getAvatarColor(email.sender_email),
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        opacity: isChecked ? 0 : 1
                      }}
                    >
                      {getInitials(email.sender_name, email.sender_email)}
                    </Avatar>
                  </Fade>
                  <Fade in={true} timeout={200}>
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: isChecked ? alpha(theme.palette.primary.main, 0.1) : 'rgba(255,255,255,0.8)',
                        borderRadius: '50%',
                        opacity: isChecked ? 1 : 0,
                        transition: 'opacity 0.2s',
                        '.MuiListItem-root:hover &': {
                          opacity: 1
                        }
                      }}
                    >
                      <Checkbox
                        checked={isChecked}
                        onChange={(e) => {
                          e.stopPropagation();
                          onToggleSelection(email.email_id);
                        }}
                        size="small"
                      />
                    </Box>
                  </Fade>
                </Box>

                <Tooltip title={email.is_important ? 'Unstar' : 'Star'}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleImportant(email.email_id, !email.is_important);
                    }}
                    sx={{ p: 0.5 }}
                  >
                    {email.is_important ? (
                      <StarIcon sx={{ fontSize: 18, color: 'warning.main' }} />
                    ) : (
                      <StarBorderIcon sx={{ fontSize: 18, color: 'text.disabled' }} />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>

              {/* Content Column */}
              <Box sx={{ flex: 1, minWidth: 0 }}>
                {/* Header: Sender & Date/Actions */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5, height: 24 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, overflow: 'hidden' }}>
                    {!email.is_read && (
                      <CircleIcon sx={{ fontSize: 8, color: theme.palette.primary.main, flexShrink: 0 }} />
                    )}
                    <Typography
                      variant="subtitle2"
                      sx={{
                        fontWeight: !email.is_read ? 700 : 500,
                        color: 'text.primary',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {email.sender_name || email.sender_email}
                    </Typography>
                  </Box>

                  {/* Date (Hidden on Hover) */}
                  <Typography
                    className="email-date"
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      flexShrink: 0,
                      fontSize: '0.75rem',
                      fontWeight: !email.is_read ? 600 : 400,
                      transition: 'opacity 0.2s',
                      position: 'absolute',
                      right: 16,
                      top: 16
                    }}
                  >
                    {formatDistanceToNow(new Date(email.received_at || email.sent_at), { addSuffix: true })}
                  </Typography>

                  {/* Hover Actions (Visible on Hover) */}
                  <Box
                    className="email-actions"
                    sx={{
                      display: 'flex',
                      gap: 0.5,
                      opacity: 0,
                      visibility: 'hidden',
                      transition: 'all 0.2s',
                      position: 'absolute',
                      right: 8,
                      top: 8,
                      backgroundColor: isSelected ? 'transparent' : theme.palette.background.paper,
                      borderRadius: 4,
                      boxShadow: isSelected ? 'none' : theme.shadows[2],
                      p: 0.5,
                      zIndex: 2
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Tooltip title="Archive">
                      <IconButton size="small" sx={{ p: 0.5 }}>
                        <ArchiveIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" sx={{ p: 0.5 }}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={email.is_read ? "Mark as unread" : "Mark as read"}>
                      <IconButton
                        size="small"
                        sx={{ p: 0.5 }}
                        onClick={() => onMarkAsRead(email.email_id)}
                      >
                        {email.is_read ? <MarkEmailUnreadIcon fontSize="small" /> : <MarkEmailReadIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>

                {/* Subject */}
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: !email.is_read ? 600 : 400,
                    color: 'text.primary',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    mb: 0.5
                  }}
                >
                  {decodeMimeHeader(email.subject) || '(No subject)'}
                </Typography>

                {/* Preview */}
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    fontSize: '0.8rem',
                    lineHeight: 1.4
                  }}
                >
                  {email.body_text?.substring(0, 150) || '(No preview available)'}
                </Typography>

                {/* Footer: Chips */}
                <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
                  {email.has_attachments && (
                    <Chip
                      icon={<AttachFileIcon sx={{ fontSize: 12 }} />}
                      label={email.attachment_count ? email.attachment_count.toString() : ''}
                      size="small"
                      variant="outlined"
                      sx={{ height: 20, fontSize: '0.625rem', '& .MuiChip-icon': { ml: 0.5 }, border: 'none', bgcolor: alpha(theme.palette.action.active, 0.05) }}
                    />
                  )}
                  {email.is_flagged && (
                    <Chip
                      icon={<FlagIcon sx={{ fontSize: 12 }} />}
                      label="Flagged"
                      size="small"
                      color="warning"
                      variant="outlined"
                      sx={{ height: 20, fontSize: '0.625rem', '& .MuiChip-icon': { ml: 0.5 } }}
                    />
                  )}
                  {email.category && email.category.toLowerCase() !== 'general' && (
                    <Chip
                      label={email.category}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.625rem',
                        bgcolor: alpha(theme.palette.primary.main, 0.1),
                        color: theme.palette.primary.main,
                        fontWeight: 600
                      }}
                    />
                  )}
                </Box>
              </Box>
            </ListItemButton>
          </ListItem>
        );
      })}
    </List>
  );
};

export default EmailListPanel;
