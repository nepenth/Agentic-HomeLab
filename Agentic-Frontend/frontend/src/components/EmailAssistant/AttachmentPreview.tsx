import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
  LinearProgress,
  Alert,
  Paper,
  Chip,
  alpha,
  useTheme
} from '@mui/material';
import {
  Close as CloseIcon,
  Download as DownloadIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  RotateRight as RotateIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
  Description as TextIcon,
  GetApp as SaveIcon
} from '@mui/icons-material';

interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  is_inline: boolean;
}

interface AttachmentPreviewProps {
  open: boolean;
  onClose: () => void;
  attachment: Attachment | null;
  emailId?: string;
}

export const AttachmentPreview: React.FC<AttachmentPreviewProps> = ({
  open,
  onClose,
  attachment,
  emailId
}) => {
  const theme = useTheme();
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);

  // Reset state when attachment changes
  useEffect(() => {
    if (attachment && open) {
      setContent(null);
      setLoading(true);
      setError(null);
      setZoom(1);
      setRotation(0);
      loadAttachment();
    }
  }, [attachment, open]);

  const loadAttachment = async () => {
    if (!attachment || !emailId) return;

    try {
      setLoading(true);
      // TODO: Implement attachment download API
      // For now, simulate loading
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock content based on file type
      if (attachment.content_type.startsWith('image/')) {
        setContent(`data:${attachment.content_type};base64,${btoa('mock-image-data')}`);
      } else if (attachment.content_type === 'application/pdf') {
        setContent('mock-pdf-content');
      } else if (attachment.content_type.startsWith('text/')) {
        setContent('This is mock text content for preview.');
      } else {
        setContent('Binary file - preview not available');
      }
    } catch (err) {
      console.error('Failed to load attachment:', err);
      setError('Failed to load attachment');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!attachment || !emailId) return;

    try {
      // TODO: Implement attachment download API
      console.log('Downloading attachment:', attachment.filename);

      // Create a mock download link
      const link = document.createElement('a');
      link.href = content || '#';
      link.download = attachment.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.25));
  const handleRotate = () => setRotation(prev => (prev + 90) % 360);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) return <ImageIcon />;
    if (contentType === 'application/pdf') return <PdfIcon />;
    if (contentType.startsWith('text/')) return <TextIcon />;
    return <SaveIcon />;
  };

  const renderContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
          <LinearProgress sx={{ width: '100%', maxWidth: 300, mb: 2 }} />
          <Typography variant="body2" color="text.secondary">
            Loading attachment...
          </Typography>
        </Box>
      );
    }

    if (error) {
      return (
        <Alert severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      );
    }

    if (!content || !attachment) {
      return (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No preview available
          </Typography>
        </Box>
      );
    }

    // Image preview
    if (attachment.content_type.startsWith('image/')) {
      return (
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
          <Box
            component="img"
            src={content}
            alt={attachment.filename}
            sx={{
              maxWidth: '100%',
              maxHeight: '100%',
              transform: `scale(${zoom}) rotate(${rotation}deg)`,
              transition: 'transform 0.2s ease',
              borderRadius: 1,
              boxShadow: theme.shadows[2]
            }}
          />
        </Box>
      );
    }

    // PDF preview (placeholder)
    if (attachment.content_type === 'application/pdf') {
      return (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <PdfIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            PDF Preview
          </Typography>
          <Typography variant="body2" color="text.secondary">
            PDF preview will be implemented with a PDF viewer library
          </Typography>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            sx={{ mt: 2 }}
          >
            Download PDF
          </Button>
        </Box>
      );
    }

    // Text preview
    if (attachment.content_type.startsWith('text/')) {
      return (
        <Box sx={{ p: 2 }}>
          <Paper
            sx={{
              p: 2,
              backgroundColor: alpha(theme.palette.background.default, 0.5),
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
              maxHeight: 400,
              overflow: 'auto'
            }}
          >
            {content}
          </Paper>
        </Box>
      );
    }

    // Other file types
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        {getFileIcon(attachment.content_type)}
        <Typography variant="h6" sx={{ mt: 2 }}>
          {attachment.filename}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Preview not available for this file type
        </Typography>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
        >
          Download File
        </Button>
      </Box>
    );
  };

  const showZoomControls = attachment?.content_type.startsWith('image/');

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          height: '80vh',
          maxHeight: '80vh'
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        pb: 1
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {attachment && getFileIcon(attachment.content_type)}
          <Box>
            <Typography variant="h6" sx={{ fontSize: '1.1rem' }}>
              {attachment?.filename || 'Attachment Preview'}
            </Typography>
            {attachment && (
              <Typography variant="caption" color="text.secondary">
                {formatFileSize(attachment.size_bytes)} • {attachment.content_type}
              </Typography>
            )}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {showZoomControls && (
            <>
              <IconButton size="small" onClick={handleZoomOut} disabled={zoom <= 0.25}>
                <ZoomOutIcon />
              </IconButton>
              <Chip
                label={`${Math.round(zoom * 100)}%`}
                size="small"
                sx={{ minWidth: 60 }}
              />
              <IconButton size="small" onClick={handleZoomIn} disabled={zoom >= 3}>
                <ZoomInIcon />
              </IconButton>
              <IconButton size="small" onClick={handleRotate}>
                <RotateIcon />
              </IconButton>
            </>
          )}

          <IconButton onClick={handleDownload} disabled={!attachment}>
            <DownloadIcon />
          </IconButton>

          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 0, overflow: 'hidden' }}>
        {renderContent()}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
        <Button onClick={onClose}>
          Close
        </Button>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          disabled={!attachment}
        >
          Download
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AttachmentPreview;