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
import { QuickActionsToolbar } from '../QuickActionsToolbar';
import { BulkOperationsDialog } from '../BulkOperationsDialog';
import { WebmailLayout } from '../WebmailLayout';
import { CreateTaskDialog } from '../CreateTaskDialog';

// Global flag to verify new code is loaded
console.log('🔵 InboxTasksTab MODULE LOADED - BUILD VERSION: 2024-10-20-v6-FORCE-REFRESH');
(window as any).__INBOX_TASKS_TAB_VERSION = '2024-10-20-v6-FORCE-REFRESH';

interface InboxTasksTabProps {
  filters?: any;
  onFiltersChange?: (filters: any) => void;
}

const InboxTasksTabBase: React.FC<InboxTasksTabProps> = ({
  filters: externalFilters,
  onFiltersChange
}) => {
  const theme = useTheme();
  const componentId = React.useRef(`inbox-tasks-${Date.now()}`);

  console.log('===== InboxTasksTab COMPONENT MOUNTED =====', componentId.current, '- VERSION 2.1 - ' + new Date().toISOString());

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

  // Advanced filtering state
  const [advancedFilters, setAdvancedFilters] = useState<any>({});

  // Bulk operations state
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkOperationType, setBulkOperationType] = useState<string>('');
  const [bulkOperations, setBulkOperations] = useState<any[]>([]);

  // Collapsible sidebar state
  const [isFolderCollapsed, setIsFolderCollapsed] = useState(false);

  // Layout selection state with memoization
  const [layoutMode, setLayoutMode] = useState<'three-column' | 'horizontal-split' | 'vertical-split'>('three-column');
  const [emailViewerPosition, setEmailViewerPosition] = useState<'right' | 'below'>('right');

  // Load saved preferences from localStorage (only once)
  React.useEffect(() => {
    const savedLayout = localStorage.getItem('emailLayoutMode');
    const savedPosition = localStorage.getItem('emailViewerPosition');
    const savedCollapsed = localStorage.getItem('folderSidebarCollapsed');

    console.log('[InboxTasksTab] Loading preferences:', { savedLayout, savedPosition, savedCollapsed });

    if (savedLayout && ['three-column', 'horizontal-split', 'vertical-split'].includes(savedLayout)) {
      setLayoutMode(savedLayout as 'three-column' | 'horizontal-split' | 'vertical-split');
    }
    if (savedPosition && ['right', 'below'].includes(savedPosition)) {
      setEmailViewerPosition(savedPosition as 'right' | 'below');
    }
    if (savedCollapsed) {
      setIsFolderCollapsed(savedCollapsed === 'true');
    }

    console.log('[InboxTasksTab] Preferences loaded - layout:', layoutMode, 'position:', emailViewerPosition, 'collapsed:', isFolderCollapsed);
  }, []);

  // Save preferences to localStorage
  React.useEffect(() => {
    console.log('[InboxTasksTab] Saving layout mode to localStorage:', layoutMode);
    localStorage.setItem('emailLayoutMode', layoutMode);
  }, [layoutMode]);

  React.useEffect(() => {
    console.log('[InboxTasksTab] Saving viewer position to localStorage:', emailViewerPosition);
    localStorage.setItem('emailViewerPosition', emailViewerPosition);
  }, [emailViewerPosition]);

  React.useEffect(() => {
    console.log('[InboxTasksTab] Saving folder collapsed state to localStorage:', isFolderCollapsed);
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
      setFilters((prevFilters) => ({
        ...prevFilters,
        folder_path: selectedFolder,
        search: searchQuery,
        ...advancedFilters // Include advanced filters
      }));
      setSelectedItems([]); // Clear selection when changing folders
    }
  }, [selectedFolder, selectedAccountId, searchQuery, advancedFilters, setFilters]);

  // Apply search filter
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setFilters((prevFilters) => {
        if (searchQuery !== prevFilters.search) {
          return { ...prevFilters, search: searchQuery, ...advancedFilters };
        }
        return prevFilters;
      });
    }, 300); // Debounce search

    return () => clearTimeout(timeoutId);
  }, [searchQuery, advancedFilters, setFilters]);

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
    if (selectedItems.length === 0) return;

    const operations = selectedItems.map(id => {
      const email = emails.find(e => e.email_id === id);
      return {
        id: `mark-read-${id}`,
        type: 'mark_read' as const,
        emailId: id,
        emailSubject: email?.subject || '(No subject)',
        status: 'pending' as const
      };
    });

    setBulkOperations(operations);
    setBulkOperationType('mark_read');
    setShowBulkDialog(true);
  };

  const handleBulkMarkUnread = () => {
    if (selectedItems.length === 0) return;

    const operations = selectedItems.map(id => {
      const email = emails.find(e => e.email_id === id);
      return {
        id: `mark-unread-${id}`,
        type: 'mark_unread' as const,
        emailId: id,
        emailSubject: email?.subject || '(No subject)',
        status: 'pending' as const
      };
    });

    setBulkOperations(operations);
    setBulkOperationType('mark_unread');
    setShowBulkDialog(true);
  };

  const handleBulkDelete = () => {
    if (selectedItems.length === 0) return;

    const operations = selectedItems.map(id => {
      const email = emails.find(e => e.email_id === id);
      return {
        id: `delete-${id}`,
        type: 'delete' as const,
        emailId: id,
        emailSubject: email?.subject || '(No subject)',
        status: 'pending' as const
      };
    });

    setBulkOperations(operations);
    setBulkOperationType('delete');
    setShowBulkDialog(true);
  };

  const handleBulkArchive = () => {
    if (selectedItems.length === 0) return;

    const operations = selectedItems.map(id => {
      const email = emails.find(e => e.email_id === id);
      return {
        id: `archive-${id}`,
        type: 'archive' as const,
        emailId: id,
        emailSubject: email?.subject || '(No subject)',
        status: 'pending' as const
      };
    });

    setBulkOperations(operations);
    setBulkOperationType('archive');
    setShowBulkDialog(true);
  };

  const handleToggleFolderCollapse = () => {
    setIsFolderCollapsed(!isFolderCollapsed);
  };

  const handleLayoutChange = (newLayout: 'three-column' | 'horizontal-split' | 'vertical-split') => {
    console.log('[InboxTasksTab] Layout change requested:', newLayout, 'current:', layoutMode);

    // Force a re-render by using functional state updates
    setLayoutMode(prevLayout => {
      console.log('[InboxTasksTab] Setting layout from', prevLayout, 'to', newLayout);
      return newLayout;
    });

    // Auto-adjust email viewer position based on layout using functional updates
    setEmailViewerPosition(prevPosition => {
      let newPosition = prevPosition;
      if (newLayout === 'vertical-split' || newLayout === 'horizontal-split') {
        newPosition = 'below';
      } else if (newLayout === 'three-column' && prevPosition === 'below') {
        newPosition = 'right';
      }
      console.log('[InboxTasksTab] Auto-adjusting viewer position from', prevPosition, 'to', newPosition, 'for layout:', newLayout);
      return newPosition;
    });
  };

  const handleEmailViewerPositionChange = (position: 'right' | 'below') => {
    console.log('[InboxTasksTab] Email viewer position change requested:', position, 'current:', emailViewerPosition, 'layout:', layoutMode);

    setEmailViewerPosition(prevPosition => {
      console.log('[InboxTasksTab] Setting viewer position from', prevPosition, 'to', position);
      return position;
    });

    // Adjust layout mode if needed using functional update
    setLayoutMode(prevLayout => {
      let newLayout = prevLayout;
      if (position === 'below' && prevLayout === 'three-column') {
        newLayout = 'vertical-split';
      } else if (position === 'right' && prevLayout === 'vertical-split') {
        newLayout = 'three-column';
      }
      if (newLayout !== prevLayout) {
        console.log('[InboxTasksTab] Auto-adjusting layout from', prevLayout, 'to', newLayout, 'for position:', position);
      }
      return newLayout;
    });
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

  const handleBulkOperationConfirm = async () => {
    // Process bulk operations
    for (const operation of bulkOperations) {
      try {
        switch (operation.type) {
          case 'delete':
            await deleteEmail(operation.emailId);
            break;
          case 'archive':
            // TODO: Implement archive API call
            console.log('Archive email:', operation.emailId);
            break;
          case 'mark_read':
            await markAsRead(operation.emailId);
            break;
          case 'mark_unread':
            // TODO: Implement mark as unread
            console.log('Mark as unread:', operation.emailId);
            break;
          default:
            console.log('Unknown operation:', operation.type);
        }

        // Update operation status
        setBulkOperations(prev =>
          prev.map(op =>
            op.id === operation.id
              ? { ...op, status: 'completed' as const }
              : op
          )
        );
      } catch (error) {
        console.error(`Failed to ${operation.type} email ${operation.emailId}:`, error);
        setBulkOperations(prev =>
          prev.map(op =>
            op.id === operation.id
              ? { ...op, status: 'failed' as const, error: 'Operation failed' }
              : op
          )
        );
      }
    }

    setSelectedItems([]);
  };

  const handleBulkOperationCancel = () => {
    setShowBulkDialog(false);
    setBulkOperations([]);
    setBulkOperationType('');
  };

  const filterActive = filters.unread || filters.important || filters.hasAttachments;

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Error Alert */}
      {error && (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => setError(null)}>
              Dismiss
            </Button>
          }
          sx={{ m: 2 }}
        >
          {error}
        </Alert>
      )}

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
        filters={advancedFilters}
        onFiltersChange={setAdvancedFilters}
        availableCategories={[]} // TODO: Fetch from API
        availableFolders={[]} // TODO: Fetch from API
        onExport={() => { }} // TODO: Implement export functionality
        totalResults={emails.length}
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

      {/* Main Content - Webmail Layout */}
      <WebmailLayout
        layoutMode={layoutMode}
        emailViewerPosition={emailViewerPosition}
        isSidebarCollapsed={isFolderCollapsed}
        onToggleSidebar={handleToggleFolderCollapse}
        sidebar={
          accountsLoading ? (
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
          )
        }
        emailList={
          <EmailListPanel
            emails={emails}
            selectedEmailId={selectedEmail?.email_id || null}
            selectedItems={selectedItems}
            onEmailSelect={handleEmailSelect}
            onToggleSelection={handleToggleSelection}
            onToggleImportant={handleToggleImportant}
            onMarkAsRead={markAsRead}
            isLoading={loading || accountsLoading}
          />
        }
        emailDetail={
          <EmailDetailPanel
            email={selectedEmail}
            isLoading={isFetchingDetail}
            onToggleImportant={(important) =>
              selectedEmail && handleToggleImportant(selectedEmail.email_id, important)
            }
            onDelete={() => selectedEmail && deleteEmail(selectedEmail.email_id)}
            onArchive={() => {
              // TODO: Implement archive
              console.log('Archive email');
            }}
            onCreateTask={handleCreateTask}
          />
        }
      />
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

      {/* Bulk Operations Dialog */}
      {showBulkDialog && (
        <BulkOperationsDialog
          open={showBulkDialog}
          onClose={handleBulkOperationCancel}
          operations={bulkOperations}
          operationType={bulkOperationType}
          totalCount={selectedItems.length}
          onConfirm={handleBulkOperationConfirm}
          onCancel={handleBulkOperationCancel}
        />
      )}

      {/* Quick Actions Toolbar */}
      <QuickActionsToolbar
        selectedEmail={selectedEmail}
        selectedCount={selectedItems.length}
        onReply={() => {
          // TODO: Implement reply functionality
          console.log('Reply to email:', selectedEmail?.email_id);
        }}
        onReplyAll={() => {
          // TODO: Implement reply all functionality
          console.log('Reply all to email:', selectedEmail?.email_id);
        }}
        onForward={() => {
          // TODO: Implement forward functionality
          console.log('Forward email:', selectedEmail?.email_id);
        }}
        onDelete={handleBulkDelete}
        onArchive={handleBulkArchive}
        onToggleImportant={(important) => {
          if (selectedEmail) {
            handleToggleImportant(selectedEmail.email_id, important);
          }
        }}
        onToggleFlag={(flagged) => {
          // TODO: Implement flag functionality
          console.log('Toggle flag:', selectedEmail?.email_id, flagged);
        }}
        onMarkAsRead={() => {
          if (selectedEmail) {
            markAsRead(selectedEmail.email_id);
          }
        }}
        onMarkAsUnread={handleBulkMarkUnread}
        onCreateTask={handleCreateTask}
        onMove={() => {
          // TODO: Implement move functionality
          console.log('Move emails:', selectedItems);
        }}
        onLabel={() => {
          // TODO: Implement label functionality
          console.log('Label emails:', selectedItems);
        }}
        onDownload={() => {
          // TODO: Implement download functionality
          console.log('Download emails:', selectedItems);
        }}
        onPrint={() => {
          // TODO: Implement print functionality
          console.log('Print email:', selectedEmail?.email_id);
        }}
        onBlock={() => {
          // TODO: Implement block functionality
          console.log('Block sender:', selectedEmail?.sender_email);
        }}
        onSnooze={() => {
          // TODO: Implement snooze functionality
          console.log('Snooze email:', selectedEmail?.email_id);
        }}
      />
    </Box>
  );
};

export const InboxTasksTab = React.memo(InboxTasksTabBase);
export default InboxTasksTab;
