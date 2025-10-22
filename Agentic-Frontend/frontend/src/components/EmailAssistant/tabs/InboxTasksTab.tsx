import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  useTheme,
  Menu,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Typography
} from '@mui/material';
import { useEmail } from '../../../hooks/useEmail';
import { FolderSidebar } from '../FolderSidebar';
import { EmailListPanel } from '../EmailListPanel';
import { EmailDetailPanel } from '../EmailDetailPanel';
import { WebmailToolbar } from '../WebmailToolbar';

// Global flag to verify new code is loaded
console.log('🔵 InboxTasksTab MODULE LOADED - BUILD VERSION: 2024-10-20-v3');
(window as any).__INBOX_TASKS_TAB_VERSION = '2024-10-20-v3';

interface InboxTasksTabProps {
  filters?: any;
  onFiltersChange?: (filters: any) => void;
}

export const InboxTasksTab: React.FC<InboxTasksTabProps> = ({
  filters: externalFilters,
  onFiltersChange
}) => {
  console.log('===== InboxTasksTab COMPONENT MOUNTED ===== VERSION 2.0 - ' + new Date().toISOString());
  const theme = useTheme();
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
  } = useEmail();

  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(null);
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);

  // Resizable columns state
  const [folderWidth, setFolderWidth] = useState(250);
  const [emailListWidth, setEmailListWidth] = useState(400);
  const [isDraggingFolder, setIsDraggingFolder] = useState(false);
  const [isDraggingList, setIsDraggingList] = useState(false);

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
      setFilters({ ...filters, folder_path: selectedFolder, search: searchQuery });
      setSelectedItems([]); // Clear selection when changing folders
    }
  }, [selectedFolder, selectedAccountId]);

  // Apply search filter
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery !== filters.search) {
        setFilters({ ...filters, search: searchQuery });
      }
    }, 300); // Debounce search

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

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

  const handleEmailSelect = (email: any) => {
    fetchEmailDetail(email.email_id);
    if (!email.is_read) {
      markAsRead(email.email_id);
    }
  };

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

    const handleMouseMove = (e: MouseEvent) => {
      e.preventDefault();

      if (isDraggingFolder) {
        // Calculate new width based on mouse position
        const newWidth = e.clientX - 24; // Subtract padding
        if (newWidth >= 200 && newWidth <= 500) {
          setFolderWidth(newWidth);
        }
      }
      if (isDraggingList) {
        // Calculate new width for email list
        const newWidth = e.clientX - folderWidth - 28; // Subtract folder width and handles
        if (newWidth >= 300 && newWidth <= 700) {
          setEmailListWidth(newWidth);
        }
      }
    };

    const handleMouseUp = () => {
      setIsDraggingFolder(false);
      setIsDraggingList(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDraggingFolder, isDraggingList, folderWidth]);

  const filterActive = filters.unread || filters.important || filters.hasAttachments;

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
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
      />

      {/* Main Content - 3 Column Layout */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
        {/* Folder Sidebar */}
        <Box
          sx={{
            width: folderWidth,
            flexShrink: 0,
            overflow: 'hidden',
            backgroundColor: theme.palette.background.paper,
            position: 'relative'
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

        {/* Email List */}
        <Paper
          elevation={0}
          sx={{
            width: emailListWidth,
            flexShrink: 0,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative'
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

        {/* Email Detail */}
        <Paper
          elevation={0}
          sx={{
            flex: 1,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
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
    </Box>
  );
};

export default InboxTasksTab;
