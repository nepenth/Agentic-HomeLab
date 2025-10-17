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
import { FolderSidebarEnhanced } from '../FolderSidebarEnhanced';
import { EmailListPanel } from '../EmailListPanel';
import { EmailDetailPanel } from '../EmailDetailPanel';
import { WebmailToolbar } from '../WebmailToolbar';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../services/api';

interface InboxTasksTabV2Props {
  filters?: any;
  onFiltersChange?: (filters: any) => void;
}

export const InboxTasksTabV2: React.FC<InboxTasksTabV2Props> = ({
  filters: externalFilters,
  onFiltersChange
}) => {
  console.log('===== InboxTasksTabV2 COMPONENT MOUNTED =====');
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
  } = useEmail();

  const [selectedFolder, setSelectedFolder] = useState<string>('INBOX');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(null);
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);

  // Fetch email accounts to get the first account ID
  const { data: emailAccountsData, isLoading: accountsLoading, error: accountsError } = useQuery({
    queryKey: ['email-accounts'],
    queryFn: async () => {
      console.log('[InboxTasksTabV2] Fetching email accounts...');
      const response = await apiClient.get('/api/v1/email-sync/accounts');
      console.log('[InboxTasksTabV2] API Response:', response);
      console.log('[InboxTasksTabV2] Response data:', response.data);
      return response.data;
    },
    retry: false,
  });

  const selectedAccountId = emailAccountsData?.accounts?.[0]?.account_id || null;

  // Debug logging
  React.useEffect(() => {
    console.log('[InboxTasksTabV2] Email Accounts Data:', emailAccountsData);
    console.log('[InboxTasksTabV2] Accounts Array:', emailAccountsData?.accounts);
    console.log('[InboxTasksTabV2] Accounts Length:', emailAccountsData?.accounts?.length);
    console.log('[InboxTasksTabV2] First Account:', emailAccountsData?.accounts?.[0]);
    console.log('[InboxTasksTabV2] Selected Account ID:', selectedAccountId);
    console.log('[InboxTasksTabV2] Accounts Loading:', accountsLoading);
    console.log('[InboxTasksTabV2] Accounts Error:', accountsError);
  }, [emailAccountsData, selectedAccountId, accountsLoading, accountsError]);

  // Apply folder filter when selected folder changes
  useEffect(() => {
    if (selectedFolder) {
      setFilters({ ...filters, folder_path: selectedFolder, search: searchQuery });
      setSelectedItems([]); // Clear selection when changing folders
    }
  }, [selectedFolder]);

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
            width: 250,
            flexShrink: 0,
            borderRight: `1px solid ${theme.palette.divider}`,
            overflow: 'hidden',
            backgroundColor: theme.palette.background.paper
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
                Accounts: {emailAccountsData?.accounts?.length || 0}
              </Typography>
            </Box>
          ) : (
            <FolderSidebarEnhanced
              accountId={selectedAccountId}
              selectedFolder={selectedFolder}
              onFolderSelect={setSelectedFolder}
            />
          )}
        </Box>

        {/* Email List */}
        <Paper
          elevation={0}
          sx={{
            width: 400,
            flexShrink: 0,
            borderRight: `1px solid ${theme.palette.divider}`,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
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

export default InboxTasksTabV2;
