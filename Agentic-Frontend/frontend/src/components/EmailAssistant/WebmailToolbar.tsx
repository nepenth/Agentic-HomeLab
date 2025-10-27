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
  Close as CloseIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  ViewColumn as ViewColumnIcon,
  ViewList as ViewListIcon,
  ViewModule as ViewModuleIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
  KeyboardArrowRight as KeyboardArrowRightIcon
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
  onToggleFolderCollapse?: () => void;
  isFolderCollapsed?: boolean;
  onLayoutChange?: (layout: 'three-column' | 'horizontal-split' | 'vertical-split') => void;
  currentLayout?: 'three-column' | 'horizontal-split' | 'vertical-split';
  onEmailViewerPositionChange?: (position: 'right' | 'below') => void;
  emailViewerPosition?: 'right' | 'below';
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
  onSortClick,
  onToggleFolderCollapse,
  isFolderCollapsed = false,
  onLayoutChange,
  currentLayout = 'three-column',
  onEmailViewerPositionChange,
  emailViewerPosition = 'right'
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
        gap: 2,
        borderRadius: '8px 8px 0 0',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
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

          {/* Layout Selection */}
          {onLayoutChange && (
            <>
              <Tooltip title="Three Column Layout">
                <IconButton
                  size="small"
                  onClick={() => onLayoutChange('three-column')}
                  sx={{
                    color: currentLayout === 'three-column' ? 'primary.main' : 'inherit',
                    backgroundColor: currentLayout === 'three-column' ? alpha(theme.palette.primary.main, 0.1) : 'transparent',
                    [theme.breakpoints.down('md')]: {
                      display: 'none' // Hide on mobile/tablet to save space
                    }
                  }}
                >
                  <ViewColumnIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Horizontal Split Layout">
                <IconButton
                  size="small"
                  onClick={() => onLayoutChange('horizontal-split')}
                  sx={{
                    color: currentLayout === 'horizontal-split' ? 'primary.main' : 'inherit',
                    backgroundColor: currentLayout === 'horizontal-split' ? alpha(theme.palette.primary.main, 0.1) : 'transparent',
                    [theme.breakpoints.down('md')]: {
                      display: 'none' // Hide on mobile/tablet to save space
                    }
                  }}
                >
                  <ViewListIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Vertical Split Layout">
                <IconButton
                  size="small"
                  onClick={() => onLayoutChange('vertical-split')}
                  sx={{
                    color: currentLayout === 'vertical-split' ? 'primary.main' : 'inherit',
                    backgroundColor: currentLayout === 'vertical-split' ? alpha(theme.palette.primary.main, 0.1) : 'transparent'
                  }}
                >
                  <ViewModuleIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Divider orientation="vertical" flexItem />
    
              {/* Email Viewer Position */}
              {onEmailViewerPositionChange && (
                <>
                  <Tooltip title={`Email viewer ${emailViewerPosition === 'right' ? 'below' : 'to the right'}`}>
                    <IconButton
                      size="small"
                      onClick={() => onEmailViewerPositionChange(emailViewerPosition === 'right' ? 'below' : 'right')}
                      sx={{
                        color: 'primary.main',
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        [theme.breakpoints.down('md')]: {
                          display: 'none' // Hide on mobile/tablet to save space
                        }
                      }}
                    >
                      {emailViewerPosition === 'right' ? <KeyboardArrowDownIcon fontSize="small" /> : <KeyboardArrowRightIcon fontSize="small" />}
                    </IconButton>
                  </Tooltip>
                  <Divider orientation="vertical" flexItem />
                </>
              )}
            </>
          )}

          {/* Toggle Folder Sidebar */}
          {onToggleFolderCollapse && (
            <Tooltip title={isFolderCollapsed ? "Show folders" : "Hide folders"}>
              <IconButton size="small" onClick={onToggleFolderCollapse}>
                {isFolderCollapsed ? <ChevronRightIcon fontSize="small" /> : <ChevronLeftIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          )}

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
