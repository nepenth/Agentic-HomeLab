import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Typography,
  Chip,
  CircularProgress,
  alpha,
  useTheme,
  Popper,
  ClickAwayListener,
  Divider,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent
} from '@mui/material';
import {
  Search as SearchIcon,
  Close as CloseIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
  Description as TextIcon,
  InsertDriveFile as FileIcon,
  GetApp as DownloadIcon,
  Visibility as PreviewIcon,
  ArrowUpward as AscIcon,
  ArrowDownward as DescIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface AttachmentResult {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  email_subject: string;
  email_sender: string;
  email_date: string;
  email_id: string;
  is_inline: boolean;
}

interface AttachmentSearchProps {
  open: boolean;
  onClose: () => void;
  onPreview?: (attachment: AttachmentResult) => void;
  onDownload?: (attachment: AttachmentResult) => void;
}

type SortField = 'filename' | 'size_bytes' | 'email_date' | 'content_type';
type SortOrder = 'asc' | 'desc';

export const AttachmentSearch: React.FC<AttachmentSearchProps> = ({
  open,
  onClose,
  onPreview,
  onDownload
}) => {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [fileType, setFileType] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('email_date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [showFilters, setShowFilters] = useState(false);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Search attachments
  const { data: results, isLoading, error } = useQuery({
    queryKey: ['attachment-search', debouncedQuery, fileType, sortField, sortOrder],
    queryFn: async () => {
      if (!debouncedQuery.trim() && fileType === 'all') return [];

      try {
        const params: any = {
          q: debouncedQuery,
          sort_by: sortField,
          sort_order: sortOrder,
          limit: 50
        };

        if (fileType !== 'all') {
          params.content_type = fileType;
        }

        const response = await apiClient.get('/api/v1/email/search/attachments', { params });
        return response.data.attachments || [];
      } catch (error) {
        console.error('Failed to search attachments:', error);
        return [];
      }
    },
    enabled: open && (debouncedQuery.length >= 2 || fileType !== 'all')
  });

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) return <ImageIcon />;
    if (contentType === 'application/pdf') return <PdfIcon />;
    if (contentType.startsWith('text/')) return <TextIcon />;
    return <FileIcon />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileTypeOptions = () => [
    { value: 'all', label: 'All Types' },
    { value: 'image/', label: 'Images' },
    { value: 'application/pdf', label: 'PDFs' },
    { value: 'text/', label: 'Text Files' },
    { value: 'application/msword', label: 'Word Documents' },
    { value: 'application/vnd.openxmlformats-officedocument', label: 'Office Documents' },
    { value: 'application/zip', label: 'Archives' }
  ];

  const getSortFieldOptions = () => [
    { value: 'filename', label: 'Filename' },
    { value: 'size_bytes', label: 'Size' },
    { value: 'email_date', label: 'Date' },
    { value: 'content_type', label: 'Type' }
  ];

  const handleSortChange = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const isPreviewable = (contentType: string) => {
    return contentType.startsWith('image/') ||
           contentType === 'application/pdf' ||
           contentType.startsWith('text/');
  };

  if (!open) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 1300,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
      onClick={onClose}
    >
      <Paper
        sx={{
          width: '100%',
          maxWidth: 800,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <SearchIcon color="primary" />
            <Typography variant="h6">Search Attachments</Typography>
            <IconButton onClick={onClose} sx={{ ml: 'auto' }}>
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Search Input */}
          <TextField
            fullWidth
            placeholder="Search attachment names, email subjects, or sender names..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
              endAdornment: query && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setQuery('')}>
                    <CloseIcon />
                  </IconButton>
                </InputAdornment>
              )
            }}
            sx={{ mb: 2 }}
          />

          {/* Filters */}
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>File Type</InputLabel>
              <Select
                value={fileType}
                label="File Type"
                onChange={(e: SelectChangeEvent) => setFileType(e.target.value)}
              >
                {getFileTypeOptions().map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ display: 'flex', gap: 1 }}>
              {getSortFieldOptions().map(option => (
                <Button
                  key={option.value}
                  size="small"
                  variant={sortField === option.value ? 'contained' : 'outlined'}
                  onClick={() => handleSortChange(option.value as SortField)}
                  endIcon={
                    sortField === option.value ? (
                      sortOrder === 'asc' ? <AscIcon /> : <DescIcon />
                    ) : undefined
                  }
                  sx={{ textTransform: 'none' }}
                >
                  {option.label}
                </Button>
              ))}
            </Box>
          </Box>
        </Box>

        {/* Results */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 0 }}>
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="error">
                Failed to search attachments. Please try again.
              </Typography>
            </Box>
          ) : !results || results.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {debouncedQuery || fileType !== 'all'
                  ? 'No attachments found matching your search.'
                  : 'Start typing to search attachments...'}
              </Typography>
            </Box>
          ) : (
            <List dense sx={{ py: 0 }}>
              {results.map((attachment, index) => (
                <React.Fragment key={attachment.id}>
                  <ListItem sx={{ py: 1.5, px: 2 }}>
                    <ListItemIcon>
                      {getFileIcon(attachment.content_type)}
                    </ListItemIcon>

                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {attachment.filename}
                          </Typography>
                          <Chip
                            label={formatFileSize(attachment.size_bytes)}
                            size="small"
                            variant="outlined"
                          />
                          {attachment.is_inline && (
                            <Chip
                              label="Inline"
                              size="small"
                              color="info"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                            From: {attachment.email_sender} • {new Date(attachment.email_date).toLocaleDateString()}
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                            Email: {attachment.email_subject}
                          </Typography>
                        </Box>
                      }
                    />

                    <Box sx={{ display: 'flex', gap: 0.5, ml: 1 }}>
                      {isPreviewable(attachment.content_type) && onPreview && (
                        <IconButton
                          size="small"
                          onClick={() => onPreview(attachment)}
                          title="Preview"
                        >
                          <PreviewIcon />
                        </IconButton>
                      )}
                      {onDownload && (
                        <IconButton
                          size="small"
                          onClick={() => onDownload(attachment)}
                          title="Download"
                        >
                          <DownloadIcon />
                        </IconButton>
                      )}
                    </Box>
                  </ListItem>
                  {index < results.length - 1 && <Divider component="li" />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Box>

        {/* Footer */}
        {results && results.length > 0 && (
          <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}`, backgroundColor: alpha(theme.palette.background.default, 0.5) }}>
            <Typography variant="body2" color="text.secondary">
              Found {results.length} attachment{results.length !== 1 ? 's' : ''}
              {debouncedQuery && ` matching "${debouncedQuery}"`}
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default AttachmentSearch;