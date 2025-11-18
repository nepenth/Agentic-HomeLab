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
  CircularProgress
} from '@mui/material';
import {
  StarBorder as StarBorderIcon,
  Star as StarIcon,
  AttachFile as AttachFileIcon,
  Reply as ReplyIcon,
  Delete as DeleteIcon,
  Drafts as DraftsIcon,
  Flag as FlagIcon,
  Circle as CircleIcon
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

  // Conditional rendering within single return statement
  return (
    <>
      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
          <CircularProgress />
        </Box>
      )}

      {/* Empty state */}
      {!isLoading && emails.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
          <Typography variant="body2" color="text.secondary">
            No emails in this folder
          </Typography>
        </Box>
      )}

      {/* Email list */}
      {!isLoading && emails.length > 0 && (
    <List sx={{
      p: 0,
      height: '100%',
      overflow: 'auto',
      '& .MuiListItem-root:hover': {
        backgroundColor: alpha(theme.palette.primary.main, 0.04),
        transition: 'background-color 0.2s ease'
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
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.3)}`,
              backgroundColor: isSelected
                ? alpha(theme.palette.primary.main, 0.08)
                : !email.is_read
                ? alpha(theme.palette.primary.main, 0.02)
                : 'transparent',
              transition: 'all 0.2s ease',
              '&:hover': {
                backgroundColor: isSelected
                  ? alpha(theme.palette.primary.main, 0.12)
                  : alpha(theme.palette.primary.main, 0.04)
              }
            }}
          >
            <ListItemButton
              selected={isSelected}
              onClick={() => onEmailSelect(email)}
              sx={{
                px: 2,
                py: 1.5,
                '&.Mui-selected': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.08),
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.primary.main, 0.12)
                  }
                },
                '&:hover': {
                  backgroundColor: alpha(theme.palette.action.hover, 0.04)
                }
              }}
            >
              {/* Selection Checkbox */}
              <Checkbox
                checked={isChecked}
                onChange={(e) => {
                  e.stopPropagation();
                  onToggleSelection(email.email_id);
                }}
                size="small"
                sx={{ mr: 1 }}
              />

              {/* Avatar */}
              <Avatar
                sx={{
                  width: 40,
                  height: 40,
                  mr: 2,
                  bgcolor: getAvatarColor(email.sender_email),
                  fontSize: '0.875rem',
                  fontWeight: 600
                }}
              >
                {getInitials(email.sender_name, email.sender_email)}
              </Avatar>

              {/* Email Content */}
              <Box sx={{ flex: 1, minWidth: 0, mr: 2 }}>
                {/* Header Row */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  {!email.is_read && (
                    <CircleIcon sx={{ fontSize: 8, color: theme.palette.primary.main }} />
                  )}
                  {email.is_important && (
                    <StarIcon sx={{ fontSize: 12, color: theme.palette.warning.main }} />
                  )}
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: !email.is_read ? 700 : (email.is_important ? 600 : 500),
                      color: 'text.primary',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1
                    }}
                  >
                    {email.sender_name || email.sender_email}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0, fontSize: '0.7rem', fontWeight: !email.is_read ? 600 : 400 }}>
                    {formatDistanceToNow(new Date(email.received_at || email.sent_at), { addSuffix: true })}
                  </Typography>
                </Box>

                {/* Subject */}
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: !email.is_read ? 600 : (email.is_important ? 500 : 400),
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
                  variant="caption"
                  sx={{
                    color: 'text.secondary',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    lineHeight: 1.4,
                    minHeight: '2.8em' // Ensure consistent height for 2 lines
                  }}
                >
                  {email.body_text?.substring(0, 200) || '(No preview available)'}
                </Typography>

                {/* Flags & Labels */}
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.75, flexWrap: 'wrap' }}>
                  {email.is_flagged && (
                    <Chip
                      icon={<FlagIcon sx={{ fontSize: 12 }} />}
                      label="Flagged"
                      size="small"
                      color="warning"
                      sx={{ height: 20, fontSize: '0.625rem', '& .MuiChip-icon': { ml: 0.5 } }}
                    />
                  )}
                  {email.is_draft && (
                    <Chip
                      icon={<DraftsIcon sx={{ fontSize: 12 }} />}
                      label="Draft"
                      size="small"
                      sx={{ height: 20, fontSize: '0.625rem', bgcolor: 'grey.300', '& .MuiChip-icon': { ml: 0.5 } }}
                    />
                  )}
                  {email.is_answered && (
                    <Chip
                      icon={<ReplyIcon sx={{ fontSize: 12 }} />}
                      label="Replied"
                      size="small"
                      color="success"
                      sx={{ height: 20, fontSize: '0.625rem', '& .MuiChip-icon': { ml: 0.5 } }}
                    />
                  )}
                  {email.has_attachments && (
                    <Chip
                      icon={<AttachFileIcon sx={{ fontSize: 12 }} />}
                      label={email.attachment_count ? email.attachment_count.toString() : '1'}
                      size="small"
                      color="info"
                      sx={{ height: 20, fontSize: '0.625rem', '& .MuiChip-icon': { ml: 0.5 } }}
                    />
                  )}
                  {email.category && email.category.toLowerCase() !== 'general' && (
                    <Chip
                      label={email.category}
                      size="small"
                      variant="outlined"
                      sx={{ height: 20, fontSize: '0.625rem' }}
                    />
                  )}
                </Box>
              </Box>

              {/* Actions */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, alignItems: 'center' }}>
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
                      <StarBorderIcon sx={{ fontSize: 18 }} />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>
            </ListItemButton>
          </ListItem>
        );
      })}
    </List>
      )}
    </>
  );
};

export default EmailListPanel;
