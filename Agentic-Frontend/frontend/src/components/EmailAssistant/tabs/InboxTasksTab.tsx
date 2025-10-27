import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  useTheme,
  Menu,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Typography,
  Alert,
  Skeleton,
  Snackbar,
  Button
} from '@mui/material';
import { useEmail } from '../../../hooks/useEmail';
import { FolderSidebar } from '../FolderSidebar';
import { EmailListPanel } from '../EmailListPanel';
import { EmailDetailPanel } from '../EmailDetailPanel';
import { WebmailToolbar } from '../WebmailToolbar';

// Global flag to verify new code is loaded
console.log('🔵 InboxTasksTab MODULE LOADED - BUILD VERSION: 2024-10-20-v4');
(window as any).__INBOX_TASKS_TAB_VERSION = '2024-10-20-v4';

interface InboxTasksTabProps {
  filters?: any;
  onFiltersChange?: (filters: any) => void;
}

export const InboxTasksTab: React.FC<InboxTasksTabProps> = ({
  filters: externalFilters,
  onFiltersChange
}) => {
  console.log('===== InboxTasksTab COMPONENT MOUNTED ===== VERSION 2.1 - ' + new Date().toISOString());
  const theme = useTheme();

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const emailsPerPage = 50;

  const {
    emails,
    selectedEmail,
    setSelectedEmail,
    filters,
    setFilters,
    sort,
    setSort,
    markAsRead,
    markAsImportant,
    deleteEmail,
    fetchEmailDetail,
    refetchEmails,
    isFetchingDetail,
    accounts,
    selectedAccount,
    loading,
  } = useEmail({ currentPage, emailsPerPage });

  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(null);
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  // Resizable columns state
  const [folderWidth, setFolderWidth] = useState(250);
  const [emailListWidth, setEmailListWidth] = useState(400);
  const [isDraggingFolder, setIsDraggingFolder] = useState(false);
  const [isDraggingList, setIsDraggingList] = useState(false);

  // Collapsible sidebar state
  const [isFolderCollapsed, setIsFolderCollapsed] = useState(false);

  // Layout selection state
  const [layoutMode, setLayoutMode] = useState<'three-column' | 'horizontal-split' | 'vertical-split'>('three-column');
  const [emailViewerPosition, setEmailViewerPosition] = useState<'right' | 'below'>('right');

  // Load saved preferences from localStorage
  React.useEffect(() => {
    const savedLayout = localStorage.getItem('emailLayoutMode');
    const savedPosition = localStorage.getItem('emailViewerPosition');
    const savedCollapsed = localStorage.getItem('folderSidebarCollapsed');

    if (savedLayout && ['three-column', 'horizontal-split', 'vertical-split'].includes(savedLayout)) {
      setLayoutMode(savedLayout as 'three-column' | 'horizontal-split' | 'vertical-split');
    }
    if (savedPosition && ['right', 'below'].includes(savedPosition)) {
      setEmailViewerPosition(savedPosition as 'right' | 'below');
    }
    if (savedCollapsed) {
      setIsFolderCollapsed(savedCollapsed === 'true');
    }
  }, []);

  // Save preferences to localStorage
  React.useEffect(() => {
    localStorage.setItem('emailLayoutMode', layoutMode);
  }, [layoutMode]);

  React.useEffect(() => {
    localStorage.setItem('emailViewerPosition', emailViewerPosition);
  }, [emailViewerPosition]);

  React.useEffect(() => {
    localStorage.setItem('folderSidebarCollapsed', isFolderCollapsed.toString());
  }, [isFolderCollapsed]);

  // Use the selected account from Redux store
  const selectedAccountId = selectedAccount?.account_id || null;
  const accountsLoading = loading;

  // Debug logging
  React.useEffect(() => {
    console.log('[InboxTasksTab] Accounts from Redux:', accounts);
    console.log('[InboxTasksTab] Accounts Length:', accounts?.length);
    console.log('[InboxTasksTab] Selected Account:', selectedAccount);
    console.log('[InboxTasksTab] Selected Account ID:', selectedAccountId);
    console.log('[InboxTasksTab] Accounts Loading:', accountsLoading);
  }, [accounts, selectedAccount, selectedAccountId, accountsLoading]);

  // Set initial folder to INBOX once account is loaded
  useEffect(() => {
    if (selectedAccountId && !selectedFolder) {
      console.log('[InboxTasksTab] Setting initial folder to INBOX');
      setSelectedFolder('INBOX');
    }
  }, [selectedAccountId, selectedFolder]);

  // Apply folder filter when selected folder changes
  useEffect(() => {
    if (selectedFolder && selectedAccountId) {
      console.log('[InboxTasksTab] Applying folder filter:', selectedFolder);
      setFilters((prevFilters) => ({ ...prevFilters, folder_path: selectedFolder, search: searchQuery }));
      setSelectedItems([]); // Clear selection when changing folders
    }
  }, [selectedFolder, selectedAccountId, searchQuery, setFilters]);

  // Apply search filter
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setFilters((prevFilters) => {
        if (searchQuery !== prevFilters.search) {
          return { ...prevFilters, search: searchQuery };
        }
        return prevFilters;
      });
    }, 300); // Debounce search

    return () => clearTimeout(timeoutId);
  }, [searchQuery, setFilters]);

  const handleEmailSelect = useCallback((email: any) => {
    fetchEmailDetail(email.email_id);
    if (!email.is_read) {
      markAsRead(email.email_id);
    }
  }, [fetchEmailDetail, markAsRead]);

  // Handle external filters from navigation
  useEffect(() => {
    if (externalFilters) {
      if (externalFilters.selectedEmailId) {
        const email = emails.find(e => e.email_id === externalFilters.selectedEmailId);
        if (email) {
          handleEmailSelect(email);
        }
      }

      if (externalFilters.filter) {
        switch (externalFilters.filter) {
          case 'unread':
            setFilters({ ...filters, unread: true, important: false });
            break;
          case 'high_priority':
            setFilters({ ...filters, important: true, unread: false });
            break;
          case 'all':
            setFilters({ ...filters, unread: false, important: false });
            break;
          default:
            break;
        }
      }

      if (onFiltersChange) {
        onFiltersChange(null);
      }
    }
  }, [externalFilters]);


  const handleToggleSelection = (id: string) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleClearSelection = () => {
    setSelectedItems([]);
  };

  const handleToggleImportant = (emailId: string, important: boolean) => {
    markAsImportant({ emailId, important });
  };

  const handleBulkMarkRead = () => {
    selectedItems.forEach(id => markAsRead(id));
    setSelectedItems([]);
  };

  const handleBulkMarkUnread = () => {
    selectedItems.forEach(id => markAsRead(id)); // Toggle
    setSelectedItems([]);
  };

  const handleBulkDelete = () => {
    if (window.confirm(`Delete ${selectedItems.length} email(s)?`)) {
      selectedItems.forEach(id => deleteEmail(id));
      setSelectedItems([]);
    }
  };

  const handleBulkArchive = () => {
    // TODO: Implement archive functionality
    console.log('Archive', selectedItems);
    setSelectedItems([]);
  };

  const handleToggleFolderCollapse = () => {
    setIsFolderCollapsed(!isFolderCollapsed);
  };

  const handleLayoutChange = (newLayout: 'three-column' | 'horizontal-split' | 'vertical-split') => {
    setLayoutMode(newLayout);
    // Auto-adjust email viewer position based on layout
    if (newLayout === 'vertical-split') {
      setEmailViewerPosition('below');
    } else if (newLayout === 'horizontal-split') {
      setEmailViewerPosition('below');
    } else {
      // For three-column, keep current position or default to right
      if (emailViewerPosition === 'below') {
        setEmailViewerPosition('right');
      }
    }
  };

  const handleEmailViewerPositionChange = (position: 'right' | 'below') => {
    setEmailViewerPosition(position);
    // Adjust layout mode if needed
    if (position === 'below' && layoutMode === 'three-column') {
      setLayoutMode('vertical-split');
    } else if (position === 'right' && layoutMode === 'vertical-split') {
      setLayoutMode('three-column');
    }
  };

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle shortcuts when not typing in input fields
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (event.key) {
        case 'ArrowUp':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Navigate to previous email
            if (emails.length > 0) {
              const currentIndex = selectedEmail ? emails.findIndex(e => e.email_id === selectedEmail.email_id) : -1;
              const prevIndex = Math.max(0, currentIndex - 1);
              if (prevIndex !== currentIndex) {
                handleEmailSelect(emails[prevIndex]);
              }
            }
          }
          break;
        case 'ArrowDown':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Navigate to next email
            if (emails.length > 0) {
              const currentIndex = selectedEmail ? emails.findIndex(e => e.email_id === selectedEmail.email_id) : -1;
              const nextIndex = Math.min(emails.length - 1, currentIndex + 1);
              if (nextIndex !== currentIndex) {
                handleEmailSelect(emails[nextIndex]);
              }
            }
          }
          break;
        case 'Enter':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Mark as read/unread toggle
            if (selectedEmail) {
              markAsRead(selectedEmail.email_id);
            }
          }
          break;
        case 'Delete':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Delete selected email
            if (selectedEmail) {
              deleteEmail(selectedEmail.email_id);
            }
          }
          break;
        case 's':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Toggle star/important
            if (selectedEmail) {
              handleToggleImportant(selectedEmail.email_id, !selectedEmail.is_important);
            }
          }
          break;
        case 'f':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Toggle folder sidebar
            handleToggleFolderCollapse();
          }
          break;
        case 'r':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            // Refresh emails
            refetchEmails();
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [emails, selectedEmail, handleEmailSelect, markAsRead, deleteEmail, handleToggleImportant, handleToggleFolderCollapse, refetchEmails]);

  const handleFilterClick = (event: React.MouseEvent<HTMLElement>) => {
    setFilterAnchorEl(event.currentTarget);
  };

  const handleSortClick = (event: React.MouseEvent<HTMLElement>) => {
    setSortAnchorEl(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterAnchorEl(null);
  };

  const handleSortClose = () => {
    setSortAnchorEl(null);
  };

  const handleCreateTask = () => {
    if (selectedEmail) {
      // TODO: Implement task creation
      console.log('Create task from email:', selectedEmail.email_id);
    }
  };

  // Resize handlers
  const handleFolderResizeStart = React.useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingFolder(true);
  }, []);

  const handleListResizeStart = React.useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingList(true);
  }, []);

  React.useEffect(() => {
    if (!isDraggingFolder && !isDraggingList) return;

    let animationFrameId: number | null = null;
    let lastMouseX = 0;

    const handleMouseMove = (e: MouseEvent) => {
      lastMouseX = e.clientX;

      // Use requestAnimationFrame for smooth 60fps updates
      if (animationFrameId === null) {
        animationFrameId = requestAnimationFrame(() => {
          const containerRect = document.querySelector('[data-inbox-container]')?.getBoundingClientRect();
          const containerLeft = containerRect?.left || 0;

          if (isDraggingFolder) {
            const newWidth = lastMouseX - containerLeft;
            if (newWidth >= 200 && newWidth <= 500) {
              setFolderWidth(newWidth);
            }
          }
          if (isDraggingList) {
            const newWidth = lastMouseX - containerLeft - folderWidth - 4;
            if (newWidth >= 300 && newWidth <= 700) {
              setEmailListWidth(newWidth);
            }
          }

          animationFrameId = null;
        });
      }
    };

    const handleMouseUp = () => {
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }
      setIsDraggingFolder(false);
      setIsDraggingList(false);
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDraggingFolder, isDraggingList, folderWidth]);

  const filterActive = filters.unread || filters.important || filters.hasAttachments;

  // Show error state
  if (error) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => setError(null)}>
              Dismiss
            </Button>
          }
        >
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      backgroundColor: theme.palette.background.default,
      borderRadius: 2,
      border: `1px solid ${theme.palette.divider}`
    }}>
      {/* Toolbar */}
      <WebmailToolbar
        selectedCount={selectedItems.length}
        folderName={selectedFolder}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onRefresh={refetchEmails}
        onClearSelection={handleClearSelection}
        onBulkDelete={handleBulkDelete}
        onBulkArchive={handleBulkArchive}
        onBulkMarkRead={handleBulkMarkRead}
        onBulkMarkUnread={handleBulkMarkUnread}
        filterActive={filterActive}
        onFilterClick={handleFilterClick}
        onSortClick={handleSortClick}
        onToggleFolderCollapse={handleToggleFolderCollapse}
        isFolderCollapsed={isFolderCollapsed}
        onLayoutChange={handleLayoutChange}
        currentLayout={layoutMode}
        onEmailViewerPositionChange={handleEmailViewerPositionChange}
        emailViewerPosition={emailViewerPosition}
      />

      {/* Loading skeleton */}
      {loading && emails.length === 0 && (
        <Box sx={{ p: 2 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Box key={i} sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2 }} />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="60%" height={20} />
                <Skeleton variant="text" width="40%" height={16} />
              </Box>
              <Skeleton variant="text" width={80} height={16} />
            </Box>
          ))}
        </Box>
      )}

      {/* Main Content - Dynamic Layout */}
      <Box sx={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
        minHeight: 0,
        backgroundColor: theme.palette.background.paper,
        borderRadius: '0 0 8px 8px',
        flexDirection: (layoutMode === 'vertical-split' || emailViewerPosition === 'below') ? 'column' : 'row',
        [theme.breakpoints.down('md')]: {
          flexDirection: 'column',
          // On mobile/tablet, always show email viewer below list for better UX
          '& > *:nth-of-type(2)': {
            order: 2,
            height: 'auto !important',
            minHeight: '300px'
          },
          '& > *:nth-of-type(3)': {
            order: 3,
            height: 'auto !important',
            minHeight: '400px'
          }
        },
        [theme.breakpoints.down('sm')]: {
          // Extra mobile optimizations
          '& > *:nth-of-type(1)': {
            width: '100% !important',
            height: '150px !important'
          }
        }
      }} data-inbox-container>
        {/* Folder Sidebar */}
        <Box
          sx={{
            width: isFolderCollapsed ? 0 : folderWidth,
            flexShrink: 0,
            overflow: 'hidden',
            backgroundColor: theme.palette.background.paper,
            position: 'relative',
            transition: isDraggingFolder ? 'none' : 'width 0.1s ease-out',
            [theme.breakpoints.down('md')]: {
              width: '100%',
              height: '200px',
              borderBottom: `1px solid ${theme.palette.divider}`
            }
          }}
        >
          {accountsLoading ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Loading accounts...
              </Typography>
            </Box>
          ) : !selectedAccountId ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="error">
                No email account found. Please add an account in Settings.
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Accounts: {accounts?.length || 0}
              </Typography>
            </Box>
          ) : (
            <FolderSidebar
              accountId={selectedAccountId}
              selectedFolder={selectedFolder}
              onFolderSelect={setSelectedFolder}
            />
          )}
        </Box>

        {/* Resize Handle for Folder */}
        {!isFolderCollapsed && (
          <Box
            onMouseDown={handleFolderResizeStart}
            sx={{
              width: 4,
              cursor: 'col-resize',
              backgroundColor: 'transparent',
              '&:hover': {
                backgroundColor: theme.palette.primary.main,
                opacity: 0.3
              },
              transition: 'background-color 0.2s',
              flexShrink: 0
            }}
          />
        )}

        {/* Email List */}
        <Paper
          elevation={0}
          sx={{
            width: (layoutMode === 'vertical-split' || emailViewerPosition === 'below') ? '100%' : emailListWidth,
            height: (layoutMode === 'vertical-split' || emailViewerPosition === 'below') ? '50%' : 'auto',
            flexShrink: 0,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            transition: isDraggingList ? 'none' : 'width 0.1s ease-out',
            borderLeft: `1px solid ${theme.palette.divider}`,
            borderRight: (layoutMode === 'three-column' && emailViewerPosition === 'right') ? `1px solid ${theme.palette.divider}` : 'none',
            borderBottom: (layoutMode === 'vertical-split' || emailViewerPosition === 'below') ? `1px solid ${theme.palette.divider}` : 'none',
            backgroundColor: theme.palette.background.paper,
            [theme.breakpoints.down('md')]: {
              width: '100%',
              height: '300px',
              borderLeft: 'none',
              borderRight: 'none',
              borderBottom: `1px solid ${theme.palette.divider}`
            }
          }}
        >
          <EmailListPanel
            emails={emails}
            selectedEmailId={selectedEmail?.email_id || null}
            selectedItems={selectedItems}
            onEmailSelect={handleEmailSelect}
            onToggleSelection={handleToggleSelection}
            onToggleImportant={handleToggleImportant}
            onMarkAsRead={markAsRead}
            isLoading={false}
          />
        </Paper>

        {/* Resize Handle for Email List */}
        {layoutMode === 'three-column' && emailViewerPosition === 'right' && (
          <Box
            onMouseDown={handleListResizeStart}
            sx={{
              width: 4,
              cursor: 'col-resize',
              backgroundColor: 'transparent',
              '&:hover': {
                backgroundColor: theme.palette.primary.main,
                opacity: 0.3
              },
              transition: 'background-color 0.2s',
              flexShrink: 0
            }}
          />
        )}

        {/* Email Detail */}
        {layoutMode !== 'horizontal-split' && (
          <Paper
            elevation={0}
            sx={{
              flex: 1,
              height: (layoutMode === 'vertical-split' || emailViewerPosition === 'below') ? '50%' : 'auto',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              [theme.breakpoints.down('md')]: {
                height: 'calc(100vh - 500px)',
                minHeight: '300px'
              }
            }}
          >
            <EmailDetailPanel
              email={selectedEmail}
              isLoading={isFetchingDetail}
              onToggleImportant={(important) => {
                if (selectedEmail) {
                  handleToggleImportant(selectedEmail.email_id, important);
                }
              }}
              onDelete={() => {
                if (selectedEmail) {
                  deleteEmail(selectedEmail.email_id);
                }
              }}
              onArchive={() => {
                // TODO: Implement archive
                console.log('Archive email');
              }}
              onCreateTask={handleCreateTask}
            />
          </Paper>
        )}
      </Box>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterAnchorEl}
        open={Boolean(filterAnchorEl)}
        onClose={handleFilterClose}
      >
        <MenuItem sx={{ minWidth: 200 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', color: 'text.secondary' }}>
            Filters
          </Typography>
        </MenuItem>
        <MenuItem>
          <FormControlLabel
            control={
              <Checkbox
                checked={filters.unread}
                onChange={(e) => setFilters({ ...filters, unread: e.target.checked })}
              />
            }
            label="Unread only"
          />
        </MenuItem>
        <MenuItem>
          <FormControlLabel
            control={
              <Checkbox
                checked={filters.important}
                onChange={(e) => setFilters({ ...filters, important: e.target.checked })}
              />
            }
            label="Important only"
          />
        </MenuItem>
        <MenuItem>
          <FormControlLabel
            control={
              <Checkbox
                checked={filters.hasAttachments}
                onChange={(e) => setFilters({ ...filters, hasAttachments: e.target.checked })}
              />
            }
            label="Has attachments"
          />
        </MenuItem>
      </Menu>

      {/* Sort Menu */}
      <Menu
        anchorEl={sortAnchorEl}
        open={Boolean(sortAnchorEl)}
        onClose={handleSortClose}
      >
        <MenuItem sx={{ minWidth: 200 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', color: 'text.secondary' }}>
            Sort By
          </Typography>
        </MenuItem>
        <MenuItem
          selected={sort.field === 'received_at' && sort.direction === 'desc'}
          onClick={() => {
            setSort({ field: 'received_at', direction: 'desc' });
            handleSortClose();
          }}
        >
          Newest first
        </MenuItem>
        <MenuItem
          selected={sort.field === 'received_at' && sort.direction === 'asc'}
          onClick={() => {
            setSort({ field: 'received_at', direction: 'asc' });
            handleSortClose();
          }}
        >
          Oldest first
        </MenuItem>
        <MenuItem
          selected={sort.field === 'sender_name'}
          onClick={() => {
            setSort({ field: 'sender_name', direction: 'asc' });
            handleSortClose();
          }}
        >
          By sender
        </MenuItem>
        <MenuItem
          selected={sort.field === 'importance_score'}
          onClick={() => {
            setSort({ field: 'importance_score', direction: 'desc' });
            handleSortClose();
          }}
        >
          By importance
        </MenuItem>
      </Menu>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbarOpen(false)}
          severity="success"
          sx={{ width: '100%' }}
        >
          Operation completed successfully
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default InboxTasksTab;
