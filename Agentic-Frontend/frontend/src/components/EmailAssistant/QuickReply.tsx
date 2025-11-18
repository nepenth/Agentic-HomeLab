import React, { useState, useRef, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  IconButton,
  Tooltip,
  Chip,
  Paper,
  alpha,
  useTheme,
  CircularProgress,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import {
  Close as CloseIcon,
  Send as SendIcon,
  AttachFile as AttachIcon,
  FormatBold as BoldIcon,
  FormatItalic as ItalicIcon,
  FormatUnderlined as UnderlineIcon,
  FormatListBulleted as ListIcon,
  FormatListNumbered as NumberedListIcon,
  InsertLink as LinkIcon,
  Image as ImageIcon,
  Reply as ReplyIcon,
  ReplyAll as ReplyAllIcon,
  Forward as ForwardIcon
} from '@mui/icons-material';

interface Email {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  body_text?: string;
  body_html?: string;
  to_recipients?: Array<{ email: string; name?: string }>;
  cc_recipients?: Array<{ email: string; name?: string }>;
}

interface QuickReplyProps {
  open: boolean;
  onClose: () => void;
  email: Email | null;
  mode: 'reply' | 'reply-all' | 'forward';
  onSend?: (data: {
    to: string[];
    cc: string[];
    subject: string;
    body: string;
    attachments: File[];
  }) => Promise<void>;
}

export const QuickReply: React.FC<QuickReplyProps> = ({
  open,
  onClose,
  email,
  mode,
  onSend
}) => {
  const theme = useTheme();
  const [toRecipients, setToRecipients] = useState('');
  const [ccRecipients, setCcRecipients] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [showCc, setShowCc] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize form based on mode and email
  useEffect(() => {
    if (email && open) {
      // Set recipients based on mode
      if (mode === 'reply') {
        setToRecipients(email.sender_email);
        setCcRecipients('');
      } else if (mode === 'reply-all') {
        setToRecipients(email.sender_email);
        // Add other recipients to CC
        const otherRecipients = [
          ...(email.to_recipients || []).filter(r => r.email !== email.sender_email),
          ...(email.cc_recipients || [])
        ];
        setCcRecipients(otherRecipients.map(r => r.email).join(', '));
      } else if (mode === 'forward') {
        setToRecipients('');
        setCcRecipients('');
      }

      // Set subject
      const prefix = mode === 'forward' ? 'Fwd: ' : 'Re: ';
      const baseSubject = email.subject.startsWith('Re: ') || email.subject.startsWith('Fwd: ')
        ? email.subject
        : prefix + email.subject;
      setSubject(baseSubject);

      // Set body with quote
      const quote = `\n\nOn ${new Date().toLocaleString()}, ${email.sender_name || email.sender_email} wrote:\n${email.body_text || email.body_html || ''}`;
      setBody(mode === 'forward' ? quote : quote);
    }
  }, [email, mode, open]);

  const handleSend = async () => {
    if (!onSend || !email) return;

    setIsSending(true);
    try {
      await onSend({
        to: toRecipients.split(',').map(email => email.trim()).filter(Boolean),
        cc: ccRecipients.split(',').map(email => email.trim()).filter(Boolean),
        subject,
        body,
        attachments
      });

      // Reset form
      setToRecipients('');
      setCcRecipients('');
      setSubject('');
      setBody('');
      setAttachments([]);
      setShowCc(false);

      onClose();
    } catch (error) {
      console.error('Failed to send email:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleAttachFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setAttachments(prev => [...prev, ...files]);
    event.target.value = ''; // Reset input
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const formatText = (command: string) => {
    // Basic text formatting (would need a rich text editor for full functionality)
    const textarea = document.getElementById('email-body') as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = body.substring(start, end);

    let formattedText = '';
    switch (command) {
      case 'bold':
        formattedText = `**${selectedText}**`;
        break;
      case 'italic':
        formattedText = `*${selectedText}*`;
        break;
      case 'underline':
        formattedText = `<u>${selectedText}</u>`;
        break;
      case 'link':
        const url = prompt('Enter URL:');
        if (url) formattedText = `[${selectedText}](${url})`;
        break;
      default:
        return;
    }

    const newBody = body.substring(0, start) + formattedText + body.substring(end);
    setBody(newBody);
  };

  const getModeTitle = () => {
    switch (mode) {
      case 'reply': return 'Reply';
      case 'reply-all': return 'Reply All';
      case 'forward': return 'Forward';
      default: return 'Compose';
    }
  };

  const getModeIcon = () => {
    switch (mode) {
      case 'reply': return <ReplyIcon />;
      case 'reply-all': return <ReplyAllIcon />;
      case 'forward': return <ForwardIcon />;
      default: return <SendIcon />;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh', maxHeight: '80vh' }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        pb: 1
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getModeIcon()}
          <Typography variant="h6">
            {getModeTitle()} to: {email?.sender_name || email?.sender_email}
          </Typography>
        </Box>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Recipients */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <TextField
            fullWidth
            label="To"
            value={toRecipients}
            onChange={(e) => setToRecipients(e.target.value)}
            size="small"
            sx={{ mb: 1 }}
          />

          {showCc ? (
            <TextField
              fullWidth
              label="CC"
              value={ccRecipients}
              onChange={(e) => setCcRecipients(e.target.value)}
              size="small"
              sx={{ mb: 1 }}
            />
          ) : (
            <Button
              size="small"
              onClick={() => setShowCc(true)}
              sx={{ mb: 1, textTransform: 'none' }}
            >
              Add CC
            </Button>
          )}

          <TextField
            fullWidth
            label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            size="small"
          />
        </Box>

        {/* Formatting Toolbar */}
        <Box sx={{
          p: 1,
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          gap: 0.5,
          flexWrap: 'wrap'
        }}>
          <Tooltip title="Bold">
            <IconButton size="small" onClick={() => formatText('bold')}>
              <BoldIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Italic">
            <IconButton size="small" onClick={() => formatText('italic')}>
              <ItalicIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Underline">
            <IconButton size="small" onClick={() => formatText('underline')}>
              <UnderlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Link">
            <IconButton size="small" onClick={() => formatText('link')}>
              <LinkIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Box sx={{ width: 1, height: 1, backgroundColor: theme.palette.divider, my: 0.5, mx: 1 }} />

          <Tooltip title="Attach File">
            <IconButton size="small" onClick={handleAttachFile}>
              <AttachIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </Box>

        {/* Message Body */}
        <Box sx={{ flex: 1, p: 2, overflow: 'auto' }}>
          <TextField
            id="email-body"
            fullWidth
            multiline
            minRows={10}
            placeholder="Type your message here..."
            value={body}
            onChange={(e) => setBody(e.target.value)}
            sx={{
              '& .MuiOutlinedInput-root': {
                minHeight: 300
              }
            }}
          />
        </Box>

        {/* Attachments */}
        {attachments.length > 0 && (
          <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
            <Typography variant="subtitle2" gutterBottom>
              Attachments ({attachments.length})
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {attachments.map((file, index) => (
                <Chip
                  key={index}
                  label={`${file.name} (${(file.size / 1024).toFixed(1)} KB)`}
                  onDelete={() => removeAttachment(index)}
                  size="small"
                  variant="outlined"
                />
              ))}
            </Box>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
        <Button onClick={onClose} disabled={isSending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          startIcon={isSending ? <CircularProgress size={16} /> : <SendIcon />}
          onClick={handleSend}
          disabled={isSending || !toRecipients.trim() || !subject.trim() || !body.trim()}
        >
          {isSending ? 'Sending...' : 'Send'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default QuickReply;