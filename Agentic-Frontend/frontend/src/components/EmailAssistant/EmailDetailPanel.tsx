import React from 'react';
import {
  Box,
  Typography,
  IconButton,
  Chip,
  Avatar,
  Divider,
  Button,
  Tooltip,
  alpha,
  useTheme,
  CircularProgress,
  Paper
} from '@mui/material';
import {
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Reply as ReplyIcon,
  ReplyAll as ReplyAllIcon,
  Forward as ForwardIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  MoreVert as MoreVertIcon,
  AttachFile as AttachFileIcon,
  Flag as FlagIcon,
  Drafts as DraftsIcon,
  TaskAlt as TaskIcon,
  GetApp as DownloadIcon
} from '@mui/icons-material';

interface EmailDetail {
  id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  reply_to_email?: string;
  to_recipients?: Array<{ email: string; name?: string }>;
  cc_recipients?: Array<{ email: string; name?: string }>;
  bcc_recipients?: Array<{ email: string; name?: string }>;
  body_text?: string;
  body_html?: string;
  sent_at: string;
  received_at: string;
  is_important: boolean;
  is_flagged: boolean;
  is_draft: boolean;
  is_answered: boolean;
  is_deleted: boolean;
  has_attachments: boolean;
  attachment_count?: number;
  attachments?: Array<{
    id: string;
    filename: string;
    content_type: string;
    size_bytes: number;
    is_inline: boolean;
  }>;
  category?: string;
  folder_path?: string;
}

interface EmailDetailPanelProps {
  email: EmailDetail | null;
  isLoading?: boolean;
  onToggleImportant?: (important: boolean) => void;
  onDelete?: () => void;
  onArchive?: () => void;
  onCreateTask?: () => void;
}

export const EmailDetailPanel: React.FC<EmailDetailPanelProps> = ({
  email,
  isLoading = false,
  onToggleImportant,
  onDelete,
  onArchive,
  onCreateTask
}) => {
  const theme = useTheme();

  const formatRecipients = (recipients: Array<{ email: string; name?: string }>) => {
    return recipients.map((r, i) => (
      <span key={i}>
        {i > 0 && ', '}
        {r.name ? (
          <>
            {r.name} <span style={{ color: theme.palette.text.secondary }}>&lt;{r.email}&gt;</span>
          </>
        ) : (
          r.email
        )}
      </span>
    ));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!email) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No email selected
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Select an email from the list to view its contents
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
        {/* Action Bar */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Tooltip title="Reply">
            <IconButton size="small">
              <ReplyIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Reply All">
            <IconButton size="small">
              <ReplyAllIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Forward">
            <IconButton size="small">
              <ForwardIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />

          <Tooltip title={email.is_important ? 'Unstar' : 'Star'}>
            <IconButton
              size="small"
              onClick={() => onToggleImportant?.(!email.is_important)}
            >
              {email.is_important ? (
                <StarIcon fontSize="small" sx={{ color: 'warning.main' }} />
              ) : (
                <StarBorderIcon fontSize="small" />
              )}
            </IconButton>
          </Tooltip>

          <Tooltip title="Archive">
            <IconButton size="small" onClick={onArchive}>
              <ArchiveIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Delete">
            <IconButton size="small" onClick={onDelete}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Box sx={{ flex: 1 }} />

          <Tooltip title="Create Task">
            <IconButton size="small" onClick={onCreateTask}>
              <TaskIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <IconButton size="small">
            <MoreVertIcon fontSize="small" />
          </IconButton>
        </Box>

        {/* Subject & Flags */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'start', gap: 1, mb: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, flex: 1 }}>
              {email.subject || '(No subject)'}
            </Typography>
          </Box>

          {/* Status Chips */}
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {email.is_flagged && (
              <Chip
                icon={<FlagIcon sx={{ fontSize: 14 }} />}
                label="Flagged"
                size="small"
                color="warning"
                sx={{ height: 22 }}
              />
            )}
            {email.is_draft && (
              <Chip
                icon={<DraftsIcon sx={{ fontSize: 14 }} />}
                label="Draft"
                size="small"
                sx={{ height: 22 }}
              />
            )}
            {email.is_answered && (
              <Chip
                icon={<ReplyIcon sx={{ fontSize: 14 }} />}
                label="Replied"
                size="small"
                color="success"
                sx={{ height: 22 }}
              />
            )}
            {email.category && (
              <Chip label={email.category} size="small" variant="outlined" sx={{ height: 22 }} />
            )}
          </Box>
        </Box>

        {/* Sender & Recipients */}
        <Box sx={{ fontSize: '0.875rem' }}>
          {/* From */}
          <Box sx={{ display: 'flex', mb: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60, color: 'text.secondary' }}>
              From:
            </Typography>
            <Typography variant="caption">
              {email.sender_name ? (
                <>
                  {email.sender_name}{' '}
                  <span style={{ color: theme.palette.text.secondary }}>&lt;{email.sender_email}&gt;</span>
                </>
              ) : (
                email.sender_email
              )}
            </Typography>
          </Box>

          {/* To */}
          {email.to_recipients && email.to_recipients.length > 0 && (
            <Box sx={{ display: 'flex', mb: 0.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60, color: 'text.secondary' }}>
                To:
              </Typography>
              <Typography variant="caption" sx={{ flex: 1 }}>
                {formatRecipients(email.to_recipients)}
              </Typography>
            </Box>
          )}

          {/* CC */}
          {email.cc_recipients && email.cc_recipients.length > 0 && (
            <Box sx={{ display: 'flex', mb: 0.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60, color: 'text.secondary' }}>
                CC:
              </Typography>
              <Typography variant="caption" sx={{ flex: 1 }}>
                {formatRecipients(email.cc_recipients)}
              </Typography>
            </Box>
          )}

          {/* BCC */}
          {email.bcc_recipients && email.bcc_recipients.length > 0 && (
            <Box sx={{ display: 'flex', mb: 0.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60, color: 'text.secondary' }}>
                BCC:
              </Typography>
              <Typography variant="caption" sx={{ flex: 1 }}>
                {formatRecipients(email.bcc_recipients)}
              </Typography>
            </Box>
          )}

          {/* Date */}
          <Box sx={{ display: 'flex', mb: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60, color: 'text.secondary' }}>
              Date:
            </Typography>
            <Typography variant="caption">
              {new Date(email.sent_at || email.received_at).toLocaleString()}
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Attachments */}
      {email.has_attachments && email.attachments && email.attachments.length > 0 && (
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}`, backgroundColor: alpha(theme.palette.background.default, 0.5) }}>
          <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            {email.attachments.length} Attachment{email.attachments.length > 1 ? 's' : ''}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {email.attachments.map((attachment) => (
              <Paper
                key={attachment.id}
                variant="outlined"
                sx={{
                  p: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  minWidth: 200,
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.primary.main, 0.04)
                  }
                }}
              >
                <AttachFileIcon fontSize="small" color="action" />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" sx={{ display: 'block', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {attachment.filename}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatFileSize(attachment.size_bytes)}
                  </Typography>
                </Box>
                <Tooltip title="Download">
                  <IconButton size="small">
                    <DownloadIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Paper>
            ))}
          </Box>
        </Box>
      )}

      {/* Email Body */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
        {email.body_html ? (
          <Box
            dangerouslySetInnerHTML={{ __html: email.body_html }}
            sx={{
              '& img': { maxWidth: '100%', height: 'auto' },
              '& a': { color: theme.palette.primary.main, textDecoration: 'underline' },
              '& table': { maxWidth: '100%', borderCollapse: 'collapse' },
              '& td, & th': { padding: '8px' },
              '& p': { margin: '0.5em 0' },
              '& blockquote': {
                borderLeft: `3px solid ${theme.palette.divider}`,
                paddingLeft: theme.spacing(2),
                marginLeft: 0,
                color: theme.palette.text.secondary
              }
            }}
          />
        ) : (
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {email.body_text || '(No content)'}
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default EmailDetailPanel;
