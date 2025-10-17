import React from 'react';
import {
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Button,
  Checkbox,
  Menu,
  MenuItem,
  Divider,
  Tooltip,
  Chip,
  alpha,
  useTheme
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  MoreVert as MoreIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  MarkunreadOutlined as MarkUnreadIcon,
  DraftsOutlined as MarkReadIcon,
  Label as LabelIcon,
  Close as CloseIcon
} from '@mui/icons-material';

interface WebmailToolbarProps {
  selectedCount: number;
  folderName?: string;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onRefresh: () => void;
  onClearSelection: () => void;
  onBulkDelete?: () => void;
  onBulkArchive?: () => void;
  onBulkMarkRead?: () => void;
  onBulkMarkUnread?: () => void;
  filterActive?: boolean;
  onFilterClick?: (event: React.MouseEvent<HTMLElement>) => void;
  onSortClick?: (event: React.MouseEvent<HTMLElement>) => void;
}

export const WebmailToolbar: React.FC<WebmailToolbarProps> = ({
  selectedCount,
  folderName,
  searchQuery,
  onSearchChange,
  onRefresh,
  onClearSelection,
  onBulkDelete,
  onBulkArchive,
  onBulkMarkRead,
  onBulkMarkUnread,
  filterActive = false,
  onFilterClick,
  onSortClick
}) => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        p: 2,
        borderBottom: `1px solid ${theme.palette.divider}`,
        backgroundColor: theme.palette.background.paper,
        display: 'flex',
        alignItems: 'center',
        gap: 2
      }}
    >
      {/* Selection Actions */}
      {selectedCount > 0 ? (
        <>
          <Chip
            label={`${selectedCount} selected`}
            onDelete={onClearSelection}
            color="primary"
            sx={{ fontWeight: 600 }}
          />

          <Divider orientation="vertical" flexItem />

          <Tooltip title="Mark as read">
            <IconButton size="small" onClick={onBulkMarkRead}>
              <MarkReadIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Mark as unread">
            <IconButton size="small" onClick={onBulkMarkUnread}>
              <MarkUnreadIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Archive">
            <IconButton size="small" onClick={onBulkArchive}>
              <ArchiveIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Delete">
            <IconButton size="small" onClick={onBulkDelete}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Box sx={{ flex: 1 }} />

          <Button
            size="small"
            variant="outlined"
            startIcon={<CloseIcon />}
            onClick={onClearSelection}
          >
            Clear
          </Button>
        </>
      ) : (
        <>
          {/* Search Bar */}
          <TextField
            size="small"
            placeholder={`Search in ${folderName || 'folder'}...`}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            sx={{ minWidth: 300 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={() => onSearchChange('')}
                    edge="end"
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              )
            }}
          />

          <Box sx={{ flex: 1 }} />

          {/* Filter & Sort */}
          <Tooltip title="Filter">
            <IconButton
              size="small"
              onClick={onFilterClick}
              sx={{
                color: filterActive ? 'primary.main' : 'inherit',
                backgroundColor: filterActive ? alpha(theme.palette.primary.main, 0.1) : 'transparent'
              }}
            >
              <FilterIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Tooltip title="Sort">
            <IconButton size="small" onClick={onSortClick}>
              <SortIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Divider orientation="vertical" flexItem />

          {/* Refresh */}
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={onRefresh}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </>
      )}
    </Box>
  );
};

export default WebmailToolbar;
