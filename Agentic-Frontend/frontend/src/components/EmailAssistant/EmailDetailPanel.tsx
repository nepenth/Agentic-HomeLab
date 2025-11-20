import React, { useState, useEffect, useRef } from 'react';
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
  Paper,
  Collapse,
  TextField
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
  GetApp as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Image as ImageIcon,
  Description as FileIcon,
  PictureAsPdf as PdfIcon,
  Send as SendIcon
} from '@mui/icons-material';
import { decodeMimeHeader } from '../../utils/emailUtils';
import { AttachmentPreview } from './AttachmentPreview';

interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  is_inline: boolean;
}

interface EmailDetail {
  email_id: string;
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
  attachments?: Attachment[];
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

const SafeHtmlRenderer: React.FC<{ html: string }> = ({ html }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(200); // Start with a reasonable min-height

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    let observer: ResizeObserver | null = null;

    const handleLoad = () => {
      const doc = iframe.contentWindow?.document;
      if (!doc) return;

      // Inject some default styles to ensure good rendering
      if (!doc.querySelector('style#default-styles')) {
        const style = doc.createElement('style');
        style.id = 'default-styles';
        style.textContent = `
          body { margin: 0; padding: 8px; font-family: sans-serif; overflow-y: hidden; }
          img { max-width: 100%; height: auto; }
          a { color: #1976d2; target: _blank; }
          pre { white-space: pre-wrap; word-wrap: break-word; }
        `;
        doc.head.appendChild(style);
      }

      // Ensure links open in new tab
      if (!doc.querySelector('base')) {
        const base = doc.createElement('base');
        base.target = '_blank';
        doc.head.appendChild(base);
      }

      const updateHeight = () => {
        if (doc.body) {
          const newHeight = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight);
          setHeight(Math.max(newHeight + 20, 200)); // Ensure at least 200px
        }
      };

      updateHeight();

      // Observe body for size changes
      if (typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(updateHeight);
        observer.observe(doc.body);
      }
    };

    iframe.addEventListener('load', handleLoad);

    // Handle case where load event might have already fired
    if (iframe.contentDocument?.readyState === 'complete') {
      handleLoad();
    }

    return () => {
      iframe.removeEventListener('load', handleLoad);
      observer?.disconnect();
    };
  }, [html]);

  return (
    <iframe
      ref={iframeRef}
      srcDoc={html}
      style={{
        width: '100%',
        height: `${height}px`,
        border: 'none',
        overflow: 'hidden',
        display: 'block'
      }}
      sandbox="allow-same-origin"
      title="Email Content"
    />
  );
};

export const EmailDetailPanel: React.FC<EmailDetailPanelProps> = ({
  email,
  isLoading = false,
  onToggleImportant,
  onDelete,
  onArchive,
  onCreateTask
}) => {
  const theme = useTheme();
  const [previewAttachment, setPreviewAttachment] = useState<Attachment | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [replyText, setReplyText] = useState('');

  // Sanitize HTML to remove external resources that cause mixed content errors
  const sanitizeEmailHtml = (html: string): string => {
    if (!html) return '';

    // Remove external stylesheets and scripts
    let sanitized = html
      .replace(/<link[^>]*>/gi, '') // Remove all <link> tags
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '') // Remove all <script> tags (multi-line)
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '') // Remove inline styles (multi-line)
      .replace(/ on\w+="[^"]*"/gi, ''); // Remove inline event handlers like onload="..."

    return sanitized;
  };

  // Enhanced email content rendering with better multipart support
  const renderEmailContent = (email: EmailDetail) => {
    // Priority: HTML > Text > Multipart alternatives
    if (email.body_html) {
      return <SafeHtmlRenderer html={sanitizeEmailHtml(email.body_html)} />;
    }

    // Fallback to text content with better formatting
    if (email.body_text) {
      return (
        <Typography
          variant="body2"
          sx={{
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            lineHeight: 1.6,
            '& > p': { margin: '0.5em 0' },
            '& > br': { display: 'block', content: '""', marginTop: '0.5em' }
          }}
        >
          {email.body_text}
        </Typography>
      );
    }

    // No content available
    return (
      <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
        (No content available)
      </Typography>
    );
  };

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

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) return <ImageIcon color="primary" />;
    if (contentType.includes('pdf')) return <PdfIcon color="error" />;
    return <FileIcon color="action" />;
  };

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

  // Conditional rendering within single return statement
  return (
    <>
      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
          <CircularProgress />
        </Box>
      )}

      {/* No email selected */}
      {!isLoading && !email && (
        <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', p: 4 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No email selected
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Select an email from the list to view its contents
          </Typography>
        </Box>
      )}

      {/* Email content */}
      {!isLoading && email && (
        <Box sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: theme.palette.background.paper,
          borderRadius: '0 0 8px 8px',
          overflow: 'hidden'
        }}>
          {/* Action Toolbar - Sticky Top */}
          <Box sx={{
            p: 1,
            px: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            borderBottom: `1px solid ${theme.palette.divider}`,
            backgroundColor: alpha(theme.palette.background.paper, 0.8),
            backdropFilter: 'blur(8px)',
            zIndex: 10
          }}>
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

            <Divider orientation="vertical" flexItem sx={{ mx: 1, height: 24, alignSelf: 'center' }} />

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

            <Box sx={{ flex: 1 }} />

            <Tooltip title="Create Task">
              <Button
                size="small"
                startIcon={<TaskIcon />}
                onClick={onCreateTask}
                sx={{ textTransform: 'none', borderRadius: 2 }}
              >
                Create Task
              </Button>
            </Tooltip>

            <IconButton size="small">
              <MoreVertIcon fontSize="small" />
            </IconButton>
          </Box>

          {/* Scrollable Content Area */}
          <Box sx={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
            {/* Email Header */}
            <Box sx={{ p: 3, pb: 2 }}>
              {/* Subject & Labels */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                  <Typography variant="h5" sx={{ fontWeight: 600, flex: 1, lineHeight: 1.3 }}>
                    {decodeMimeHeader(email.subject) || '(No subject)'}
                  </Typography>
                  {email.is_important && <StarIcon sx={{ color: 'warning.main', mt: 0.5 }} />}
                </Box>

                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {email.is_flagged && (
                    <Chip icon={<FlagIcon sx={{ fontSize: 14 }} />} label="Flagged" size="small" color="warning" sx={{ height: 22 }} />
                  )}
                  {email.category && email.category.toLowerCase() !== 'general' && (
                    <Chip label={email.category} size="small" variant="outlined" sx={{ height: 22 }} />
                  )}
                </Box>
              </Box>

              {/* Sender Info */}
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Avatar
                  sx={{
                    width: 48,
                    height: 48,
                    bgcolor: theme.palette.primary.main,
                    fontSize: '1.2rem'
                  }}
                >
                  {getInitials(email.sender_name, email.sender_email)}
                </Avatar>

                <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {email.sender_name || email.sender_email}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(email.sent_at || email.received_at).toLocaleString(undefined, {
                        weekday: 'short',
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: 'numeric'
                      })}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="body2" color="text.secondary">
                      to {email.to_recipients && email.to_recipients.length > 0 ? email.to_recipients[0].name || email.to_recipients[0].email : 'me'}
                    </Typography>
                    {(email.to_recipients && email.to_recipients.length > 1 || email.cc_recipients?.length || email.bcc_recipients?.length) && (
                      <IconButton size="small" onClick={() => setShowDetails(!showDetails)} sx={{ p: 0.25 }}>
                        {showDetails ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                      </IconButton>
                    )}
                  </Box>

                  {/* Collapsible Details */}
                  <Collapse in={showDetails}>
                    <Paper variant="outlined" sx={{ p: 1.5, mt: 1, bgcolor: alpha(theme.palette.background.default, 0.5) }}>
                      <Box sx={{ display: 'grid', gap: 0.5, fontSize: '0.875rem' }}>
                        <Box sx={{ display: 'flex' }}>
                          <Typography variant="caption" sx={{ width: 60, color: 'text.secondary', fontWeight: 600 }}>From:</Typography>
                          <Typography variant="caption">{email.sender_name} &lt;{email.sender_email}&gt;</Typography>
                        </Box>
                        {email.to_recipients && (
                          <Box sx={{ display: 'flex' }}>
                            <Typography variant="caption" sx={{ width: 60, color: 'text.secondary', fontWeight: 600 }}>To:</Typography>
                            <Typography variant="caption">{formatRecipients(email.to_recipients)}</Typography>
                          </Box>
                        )}
                        {email.cc_recipients && email.cc_recipients.length > 0 && (
                          <Box sx={{ display: 'flex' }}>
                            <Typography variant="caption" sx={{ width: 60, color: 'text.secondary', fontWeight: 600 }}>Cc:</Typography>
                            <Typography variant="caption">{formatRecipients(email.cc_recipients)}</Typography>
                          </Box>
                        )}
                      </Box>
                    </Paper>
                  </Collapse>
                </Box>
              </Box>
            </Box>

            <Divider sx={{ mx: 3 }} />

            {/* Email Body */}
            <Box sx={{ p: 3, minHeight: 200 }}>
              {renderEmailContent(email)}
            </Box>

            {/* Attachments */}
            {email.has_attachments && email.attachments && email.attachments.length > 0 && (
              <Box sx={{ px: 3, pb: 3 }}>
                <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AttachFileIcon fontSize="small" />
                  {email.attachments.length} Attachments
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 2 }}>
                  {email.attachments.map((attachment) => {
                    const isImage = attachment.content_type?.startsWith('image/');
                    const isPreviewable = isImage || attachment.content_type?.includes('pdf') || attachment.content_type?.includes('text');

                    return (
                      <Paper
                        key={attachment.id}
                        variant="outlined"
                        sx={{
                          p: 1.5,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1.5,
                          cursor: isPreviewable ? 'pointer' : 'default',
                          transition: 'all 0.2s',
                          '&:hover': {
                            borderColor: theme.palette.primary.main,
                            backgroundColor: alpha(theme.palette.primary.main, 0.02),
                            transform: 'translateY(-2px)',
                            boxShadow: theme.shadows[2]
                          }
                        }}
                        onClick={() => {
                          if (isPreviewable) {
                            setPreviewAttachment(attachment);
                            setShowPreview(true);
                          }
                        }}
                      >
                        <Box sx={{
                          width: 40,
                          height: 40,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          bgcolor: alpha(theme.palette.primary.main, 0.1),
                          borderRadius: 1,
                          color: theme.palette.primary.main
                        }}>
                          {getFileIcon(attachment.content_type)}
                        </Box>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" sx={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {attachment.filename}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatFileSize(attachment.size_bytes)}
                          </Typography>
                        </Box>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            console.log('Download attachment:', attachment.filename);
                          }}
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Paper>
                    );
                  })}
                </Box>
              </Box>
            )}

            {/* Quick Reply Box */}
            <Box sx={{ p: 3, mt: 'auto', borderTop: `1px solid ${theme.palette.divider}`, bgcolor: alpha(theme.palette.background.default, 0.3) }}>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                <Avatar sx={{ width: 32, height: 32, bgcolor: theme.palette.primary.main }}>
                  Me
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Paper variant="outlined" sx={{ p: 0, overflow: 'hidden', borderRadius: 2 }}>
                    <TextField
                      fullWidth
                      multiline
                      minRows={2}
                      placeholder="Reply to this email..."
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      variant="standard"
                      InputProps={{
                        disableUnderline: true,
                        sx: { p: 2 }
                      }}
                    />
                    <Box sx={{ p: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: alpha(theme.palette.action.hover, 0.05), borderTop: `1px solid ${theme.palette.divider}` }}>
                      <Box>
                        <IconButton size="small"><AttachFileIcon fontSize="small" /></IconButton>
                        <IconButton size="small"><ImageIcon fontSize="small" /></IconButton>
                      </Box>
                      <Button
                        variant="contained"
                        size="small"
                        endIcon={<SendIcon />}
                        disabled={!replyText.trim()}
                        sx={{ borderRadius: 4 }}
                      >
                        Send
                      </Button>
                    </Box>
                  </Paper>
                </Box>
              </Box>
            </Box>
          </Box>

          {/* Attachment Preview Dialog */}
          <AttachmentPreview
            open={showPreview}
            onClose={() => {
              setShowPreview(false);
              setPreviewAttachment(null);
            }}
            attachment={previewAttachment}
            emailId={email.email_id}
          />
        </Box>
      )}
    </>
  );
};

export default EmailDetailPanel;
