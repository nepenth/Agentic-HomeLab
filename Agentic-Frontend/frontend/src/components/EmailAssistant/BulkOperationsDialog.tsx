import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  LinearProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  alpha,
  useTheme
} from '@mui/material';
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Markunread as MarkUnreadIcon,
  Drafts as MarkReadIcon,
  Star as StarIcon,
  Label as LabelIcon
} from '@mui/icons-material';

interface BulkOperation {
  id: string;
  type: 'delete' | 'archive' | 'mark_read' | 'mark_unread' | 'star' | 'unstar' | 'move' | 'label';
  emailId: string;
  emailSubject: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
}

interface BulkOperationsDialogProps {
  open: boolean;
  onClose: () => void;
  operations: BulkOperation[];
  operationType: string;
  totalCount: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export const BulkOperationsDialog: React.FC<BulkOperationsDialogProps> = ({
  open,
  onClose,
  operations,
  operationType,
  totalCount,
  onConfirm,
  onCancel
}) => {
  const theme = useTheme();
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  const getOperationIcon = (type: string) => {
    switch (type) {
      case 'delete': return <DeleteIcon color="error" />;
      case 'archive': return <ArchiveIcon color="action" />;
      case 'mark_read': return <MarkReadIcon color="action" />;
      case 'mark_unread': return <MarkUnreadIcon color="primary" />;
      case 'star': return <StarIcon color="warning" />;
      case 'unstar': return <StarIcon color="action" />;
      case 'move': return <ArchiveIcon color="action" />;
      case 'label': return <LabelIcon color="action" />;
      default: return <InfoIcon color="action" />;
    }
  };

  const getOperationLabel = (type: string) => {
    switch (type) {
      case 'delete': return 'Delete';
      case 'archive': return 'Archive';
      case 'mark_read': return 'Mark as Read';
      case 'mark_unread': return 'Mark as Unread';
      case 'star': return 'Star';
      case 'unstar': return 'Unstar';
      case 'move': return 'Move';
      case 'label': return 'Label';
      default: return 'Process';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <SuccessIcon color="success" fontSize="small" />;
      case 'failed': return <ErrorIcon color="error" fontSize="small" />;
      case 'processing': return <WarningIcon color="warning" fontSize="small" />;
      default: return <InfoIcon color="action" fontSize="small" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success.main';
      case 'failed': return 'error.main';
      case 'processing': return 'warning.main';
      default: return 'text.secondary';
    }
  };

  const completedCount = operations.filter(op => op.status === 'completed').length;
  const failedCount = operations.filter(op => op.status === 'failed').length;
  const processingCount = operations.filter(op => op.status === 'processing').length;

  const handleConfirm = async () => {
    setIsProcessing(true);
    setProgress(0);

    // Simulate progress updates
    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + 5, 95));
    }, 100);

    try {
      await onConfirm();
      setProgress(100);
      clearInterval(progressInterval);

      // Close dialog after completion
      setTimeout(() => {
        onClose();
        setIsProcessing(false);
        setProgress(0);
      }, 1000);
    } catch (error) {
      console.error('Bulk operation failed:', error);
      clearInterval(progressInterval);
      setIsProcessing(false);
      setProgress(0);
    }
  };

  const handleCancel = () => {
    if (!isProcessing) {
      onCancel();
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="md"
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
        {getOperationIcon(operationType)}
        <Typography variant="h6">
          {getOperationLabel(operationType)} {totalCount} Email{totalCount !== 1 ? 's' : ''}
        </Typography>
      </DialogTitle>

      <DialogContent>
        {/* Progress Summary */}
        {isProcessing && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" gutterBottom>
              Processing... {progress}%
            </Typography>
            <LinearProgress variant="determinate" value={progress} />

            <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
              <Chip
                label={`${completedCount} completed`}
                color="success"
                size="small"
                variant="outlined"
              />
              <Chip
                label={`${processingCount} processing`}
                color="warning"
                size="small"
                variant="outlined"
              />
              <Chip
                label={`${failedCount} failed`}
                color="error"
                size="small"
                variant="outlined"
              />
            </Box>
          </Box>
        )}

        {/* Confirmation Message */}
        {!isProcessing && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            <Typography variant="body2">
              Are you sure you want to {getOperationLabel(operationType).toLowerCase()} {totalCount} email{totalCount !== 1 ? 's' : ''}?
              This action cannot be undone.
            </Typography>
          </Alert>
        )}

        {/* Operations List */}
        <Box sx={{
          maxHeight: 300,
          overflow: 'auto',
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1
        }}>
          <List dense sx={{ py: 0 }}>
            {operations.slice(0, 10).map((operation, index) => (
              <React.Fragment key={operation.id}>
                <ListItem sx={{ py: 1 }}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {getStatusIcon(operation.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography variant="body2" sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: 400
                      }}>
                        {operation.emailSubject || '(No subject)'}
                      </Typography>
                    }
                    secondary={
                      <Typography variant="caption" color={getStatusColor(operation.status)}>
                        {operation.status === 'failed' && operation.error
                          ? operation.error
                          : operation.status.charAt(0).toUpperCase() + operation.status.slice(1)
                        }
                      </Typography>
                    }
                  />
                </ListItem>
                {index < operations.length - 1 && index < 9 && (
                  <Divider component="li" />
                )}
              </React.Fragment>
            ))}

            {operations.length > 10 && (
              <ListItem sx={{ py: 1, bgcolor: alpha(theme.palette.background.default, 0.5) }}>
                <ListItemText
                  primary={
                    <Typography variant="body2" color="text.secondary">
                      ... and {operations.length - 10} more emails
                    </Typography>
                  }
                />
              </ListItem>
            )}
          </List>
        </Box>

        {/* Bulk Operation Tips */}
        <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.info.main, 0.1), borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            💡 Tips for bulk operations:
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            • Operations are processed in batches to avoid overwhelming the server<br/>
            • You can monitor progress in real-time<br/>
            • Failed operations will be reported individually<br/>
            • Some operations may take longer depending on email size and attachments
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleCancel}
          disabled={isProcessing}
        >
          {isProcessing ? 'Processing...' : 'Cancel'}
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color={operationType === 'delete' ? 'error' : 'primary'}
          disabled={isProcessing}
          startIcon={isProcessing ? undefined : getOperationIcon(operationType)}
        >
          {isProcessing ? 'Processing...' : `Confirm ${getOperationLabel(operationType)}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BulkOperationsDialog;