import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Typography,
  Box,
  LinearProgress,
  Alert,
  alpha,
  useTheme
} from '@mui/material';
import {
  Download as DownloadIcon,
  FileDownload as FileIcon,
  TableChart as TableIcon,
  Code as CodeIcon
} from '@mui/icons-material';
import apiClient from '../../services/api';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  searchQuery?: string;
  filters?: any;
  totalResults?: number;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  open,
  onClose,
  searchQuery,
  filters,
  totalResults = 0
}) => {
  const theme = useTheme();
  const [exportFormat, setExportFormat] = useState<'csv' | 'json' | 'xlsx'>('csv');
  const [includeAttachments, setIncludeAttachments] = useState(false);
  const [includeFullContent, setIncludeFullContent] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    if (!searchQuery && !filters) {
      setError('No search criteria to export');
      return;
    }

    setIsExporting(true);
    setExportProgress(0);
    setError(null);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setExportProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const exportData = {
        query: searchQuery,
        format: exportFormat,
        filters: {
          ...filters,
          include_attachments: includeAttachments,
          include_full_content: includeFullContent
        }
      };

      const response = await apiClient.exportEmailSearchResults(exportData);

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
      const filename = `email-export-${timestamp}.${exportFormat}`;
      link.setAttribute('download', filename);

      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      clearInterval(progressInterval);
      setExportProgress(100);

      // Close dialog after successful export
      setTimeout(() => {
        onClose();
        setIsExporting(false);
        setExportProgress(0);
      }, 1000);

    } catch (err) {
      console.error('Export failed:', err);
      setError('Export failed. Please try again.');
      setIsExporting(false);
      setExportProgress(0);
    }
  };

  const handleClose = () => {
    if (!isExporting) {
      onClose();
      setError(null);
      setExportProgress(0);
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'csv': return <TableIcon />;
      case 'json': return <CodeIcon />;
      case 'xlsx': return <FileIcon />;
      default: return <DownloadIcon />;
    }
  };

  const getFormatDescription = (format: string) => {
    switch (format) {
      case 'csv': return 'Comma-separated values, compatible with Excel and other spreadsheet applications';
      case 'json': return 'JavaScript Object Notation, suitable for developers and data analysis';
      case 'xlsx': return 'Microsoft Excel format with formatting and multiple sheets';
      default: return '';
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          boxShadow: theme.shadows[8]
        }
      }}
    >
      <DialogTitle sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        pb: 1
      }}>
        <DownloadIcon color="primary" />
        Export Search Results
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Exporting {totalResults > 0 ? `${totalResults} ` : ''}email{totalResults !== 1 ? 's' : ''} matching your search criteria
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Export Format */}
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Export Format</InputLabel>
          <Select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as 'csv' | 'json' | 'xlsx')}
            disabled={isExporting}
          >
            <MenuItem value="csv">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TableIcon fontSize="small" />
                <Box>
                  <Typography variant="body2">CSV</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Spreadsheet compatible
                  </Typography>
                </Box>
              </Box>
            </MenuItem>
            <MenuItem value="json">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CodeIcon fontSize="small" />
                <Box>
                  <Typography variant="body2">JSON</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Developer friendly
                  </Typography>
                </Box>
              </Box>
            </MenuItem>
            <MenuItem value="xlsx">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <FileIcon fontSize="small" />
                <Box>
                  <Typography variant="body2">Excel (XLSX)</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Rich formatting
                  </Typography>
                </Box>
              </Box>
            </MenuItem>
          </Select>
        </FormControl>

        {/* Export Options */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Export Options
          </Typography>

          <FormControlLabel
            control={
              <Checkbox
                checked={includeFullContent}
                onChange={(e) => setIncludeFullContent(e.target.checked)}
                disabled={isExporting}
              />
            }
            label="Include full email content (may increase file size)"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={includeAttachments}
                onChange={(e) => setIncludeAttachments(e.target.checked)}
                disabled={isExporting}
              />
            }
            label="Include attachment information"
          />
        </Box>

        {/* Format Description */}
        <Box sx={{
          p: 2,
          bgcolor: alpha(theme.palette.info.main, 0.1),
          borderRadius: 1,
          border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            {getFormatIcon(exportFormat)}
            <Typography variant="subtitle2">
              {exportFormat.toUpperCase()} Format
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {getFormatDescription(exportFormat)}
          </Typography>
        </Box>

        {/* Progress */}
        {isExporting && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" gutterBottom>
              Exporting... {exportProgress}%
            </Typography>
            <LinearProgress variant="determinate" value={exportProgress} />
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleClose}
          disabled={isExporting}
        >
          Cancel
        </Button>
        <Button
          onClick={handleExport}
          variant="contained"
          disabled={isExporting}
          startIcon={<DownloadIcon />}
        >
          {isExporting ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExportDialog;