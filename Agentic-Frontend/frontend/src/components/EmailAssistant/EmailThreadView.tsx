import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  Divider,
  IconButton,
  Tooltip,
  Collapse,
  Button,
  Chip,
  alpha,
  useTheme,
  CircularProgress
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Reply as ReplyIcon,
  ReplyAll as ReplyAllIcon,
  Forward as ForwardIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  MoreVert as MoreIcon,
  Attachment as AttachmentIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { decodeMimeHeader } from '../../utils/emailUtils';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface ThreadEmail {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  body_text?: string;
  body_html?: string;
  sent_at: string;
  received_at: string;
  is_read: boolean;
  is_important: boolean;
  is_answered: boolean;
  has_attachments: boolean;
  attachment_count?: number;
  category?: string;
  folder_path?: string;
}

interface EmailThreadViewProps {
  threadId: string;
  rootEmailId: string;
  onEmailSelect?: (email: ThreadEmail) => void;
  onReply?: (email: ThreadEmail) => void;
  onReplyAll?: (email: ThreadEmail) => void;
  onForward?: (email: ThreadEmail) => void;
  onToggleImportant?: (emailId: string, important: boolean) => void;
}

export const EmailThreadView: React.FC<EmailThreadViewProps> = ({
  threadId,
  rootEmailId,
  onEmailSelect,
  onReply,
  onReplyAll,
  onForward,
  onToggleImportant
}) => {
  const theme = useTheme();
  const [expandedEmails, setExpandedEmails] = useState<Set<string>>(new Set([rootEmailId]));
  const [selectedEmailId, setSelectedEmailId] = useState<string>(rootEmailId);

  // Fetch thread emails
  const { data: threadEmails, isLoading, error } = useQuery({
    queryKey: ['email-thread', threadId],
    queryFn: async () => {
      try {
        // TODO: Implement getEmailThread API method
        // For now, return mock data or empty array
        console.log('Fetching email thread:', threadId);
        return [];
      } catch (error) {
        console.error('Failed to fetch email thread:', error);
        return [];
      }
    },
    enabled: !!threadId
  });

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

  const toggleEmailExpansion = (emailId: string) => {
    const newExpanded = new Set(expandedEmails);
    if (newExpanded.has(emailId)) {
      newExpanded.delete(emailId);
    } else {
      newExpanded.add(emailId);
    }
    setExpandedEmails(newExpanded);
  };

  const handleEmailSelect = (email: ThreadEmail) => {
    setSelectedEmailId(email.email_id);
    onEmailSelect?.(email);
  };

  const renderEmailContent = (email: ThreadEmail) => {
    // Priority: HTML > Text
    if (email.body_html) {
      return (
        <Box
          dangerouslySetInnerHTML={{
            __html: email.body_html.replace(/<style[^>]*>.*?<\/style>/gi, '') // Remove styles
          }}
          sx={{
            '& img': { maxWidth: '100%', height: 'auto' },
            '& a': { color: theme.palette.primary.main, textDecoration: 'underline' },
            '& table': { maxWidth: '100%', borderCollapse: 'collapse' },
            '& td, & th': { padding: '4px' },
            '& p': { margin: '0.25em 0' },
            '& blockquote': {
              borderLeft: `2px solid ${theme.palette.divider}`,
              paddingLeft: theme.spacing(1),
              marginLeft: 0,
              color: theme.palette.text.secondary,
              fontSize: '0.875rem'
            },
            '& pre': {
              backgroundColor: alpha(theme.palette.background.default, 0.5),
              padding: theme.spacing(0.5),
              borderRadius: 0.5,
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.8rem'
            }
          }}
        />
      );
    }

    if (email.body_text) {
      return (
        <Typography
          variant="body2"
          sx={{
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            lineHeight: 1.5,
            '& > p': { margin: '0.25em 0' }
          }}
        >
          {email.body_text}
        </Typography>
      );
    }

    return (
      <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
        (No content available)
      </Typography>
    );
  };

  const renderThreadEmail = (email: ThreadEmail, isLast: boolean = false) => {
    const isExpanded = expandedEmails.has(email.email_id);
    const isSelected = selectedEmailId === email.email_id;

    return (
      <Box key={email.email_id}>
        <Paper
          elevation={isSelected ? 2 : 0}
          sx={{
            p: 2,
            cursor: 'pointer',
            border: isSelected ? `2px solid ${theme.palette.primary.main}` : `1px solid ${theme.palette.divider}`,
            backgroundColor: isSelected
              ? alpha(theme.palette.primary.main, 0.04)
              : 'background.paper',
            '&:hover': {
              backgroundColor: isSelected
                ? alpha(theme.palette.primary.main, 0.06)
                : alpha(theme.palette.action.hover, 0.04)
            }
          }}
          onClick={() => handleEmailSelect(email)}
        >
          {/* Email Header */}
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 1 }}>
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: getAvatarColor(email.sender_email),
                fontSize: '0.75rem',
                fontWeight: 600,
                flexShrink: 0
              }}
            >
              {getInitials(email.sender_name, email.sender_email)}
            </Avatar>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1 }}>
                  {email.sender_name || email.sender_email}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatDistanceToNow(new Date(email.sent_at || email.received_at), { addSuffix: true })}
                </Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                {email.sender_email}
              </Typography>

              {/* Status indicators */}
              <Box sx={{ display: 'flex', gap: 0.5, mb: 1 }}>
                {email.is_important && (
                  <Chip
                    icon={<StarIcon sx={{ fontSize: 12 }} />}
                    label="Important"
                    size="small"
                    color="warning"
                    sx={{ height: 20, fontSize: '0.7rem' }}
                  />
                )}
                {email.is_answered && (
                  <Chip
                    icon={<ReplyIcon sx={{ fontSize: 12 }} />}
                    label="Replied"
                    size="small"
                    color="success"
                    sx={{ height: 20, fontSize: '0.7rem' }}
                  />
                )}
                {email.has_attachments && (
                  <Chip
                    icon={<AttachmentIcon sx={{ fontSize: 12 }} />}
                    label={email.attachment_count ? email.attachment_count.toString() : '1'}
                    size="small"
                    color="info"
                    sx={{ height: 20, fontSize: '0.7rem' }}
                  />
                )}
              </Box>
            </Box>

            {/* Action buttons */}
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Tooltip title={email.is_important ? 'Unstar' : 'Star'}>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleImportant?.(email.email_id, !email.is_important);
                  }}
                >
                  {email.is_important ? (
                    <StarIcon sx={{ fontSize: 16, color: 'warning.main' }} />
                  ) : (
                    <StarBorderIcon sx={{ fontSize: 16 }} />
                  )}
                </IconButton>
              </Tooltip>

              <Tooltip title={isExpanded ? 'Collapse' : 'Expand'}>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleEmailExpansion(email.email_id);
                  }}
                >
                  {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Email Subject */}
          <Typography variant="body1" sx={{ fontWeight: 500, mb: 1 }}>
            {decodeMimeHeader(email.subject) || '(No subject)'}
          </Typography>

          {/* Email Content Preview */}
          <Collapse in={isExpanded}>
            <Box sx={{ mt: 1 }}>
              <Divider sx={{ mb: 2 }} />
              {renderEmailContent(email)}

              {/* Action buttons for expanded email */}
              <Box sx={{ display: 'flex', gap: 1, mt: 2, pt: 1, borderTop: `1px solid ${theme.palette.divider}` }}>
                <Button
                  size="small"
                  startIcon={<ReplyIcon />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onReply?.(email);
                  }}
                >
                  Reply
                </Button>
                <Button
                  size="small"
                  startIcon={<ReplyAllIcon />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onReplyAll?.(email);
                  }}
                >
                  Reply All
                </Button>
                <Button
                  size="small"
                  startIcon={<ForwardIcon />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onForward?.(email);
                  }}
                >
                  Forward
                </Button>
              </Box>
            </Box>
          </Collapse>
        </Paper>

        {/* Thread connector line */}
        {!isLast && (
          <Box
            sx={{
              width: 2,
              height: 24,
              backgroundColor: theme.palette.divider,
              ml: 3.5,
              my: 1
            }}
          />
        )}
      </Box>
    );
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !threadEmails || threadEmails.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          {error ? 'Failed to load email thread' : 'No emails in this thread'}
        </Typography>
      </Box>
    );
  }

  // Sort emails by date (oldest first for thread view)
  const sortedEmails = [...threadEmails].sort((a, b) =>
    new Date(a.sent_at || a.received_at).getTime() - new Date(b.sent_at || b.received_at).getTime()
  );

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h6" sx={{ mb: 2, px: 1 }}>
        Email Thread
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {sortedEmails.map((email, index) =>
          renderThreadEmail(email, index === sortedEmails.length - 1)
        )}
      </Box>
    </Box>
  );
};

export default EmailThreadView;