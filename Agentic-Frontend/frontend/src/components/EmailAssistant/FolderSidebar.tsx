import React, { useState, useEffect } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Chip,
  Divider,
  CircularProgress,
  Collapse,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Inbox,
  Send,
  Drafts,
  Delete,
  Archive,
  Star,
  Label,
  ExpandMore,
  ExpandLess,
  Folder,
  FolderOpen,
  Refresh
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface FolderSidebarProps {
  accountId: string | null;
  selectedFolder: string | null;
  onFolderSelect: (folder: string) => void;
}

interface FolderItem {
  name: string;
  path: string;
  emailCount: number;
  unreadCount?: number;
}

// Icon mapping for common folders
const getFolderIcon = (folderName: string) => {
  const name = folderName.toLowerCase();
  if (name === 'inbox') return <Inbox />;
  if (name === 'sent' || name === 'sent items') return <Send />;
  if (name === 'drafts') return <Drafts />;
  if (name === 'trash' || name === 'deleted items' || name === 'bin') return <Delete />;
  if (name === 'archive') return <Archive />;
  if (name === 'starred' || name === 'flagged') return <Star />;
  if (name === 'junk' || name === 'spam') return <Label />;
  return <Folder />;
};

export const FolderSidebar: React.FC<FolderSidebarProps> = ({
  accountId,
  selectedFolder,
  onFolderSelect
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['root']));

  // Fetch folder sync status to get email counts
  const { data: folderStatus, isLoading: loadingStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['folder-status', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      return await apiClient.getFolderSyncStatus(accountId);
    },
    enabled: !!accountId,
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Fetch available folders
  const { data: foldersData, isLoading: loadingFolders, refetch: refetchFolders } = useQuery({
    queryKey: ['folders', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      return await apiClient.getAccountFolders(accountId);
    },
    enabled: !!accountId
  });

  const handleRefresh = () => {
    refetchStatus();
    refetchFolders();
  };

  const toggleFolder = (folderPath: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderPath)) {
      newExpanded.delete(folderPath);
    } else {
      newExpanded.add(folderPath);
    }
    setExpandedFolders(newExpanded);
  };

  // Organize folders into a tree structure
  const organizeFolders = (): FolderItem[] => {
    if (!foldersData?.folders || !folderStatus?.folders) {
      return [];
    }

    const folderList: FolderItem[] = foldersData.folders.map((folder: any) => {
      const statusInfo = folderStatus.folders.find((f: any) => f.folder_name === folder.name || f.folder_name === folder);
      const folderName = typeof folder === 'string' ? folder : folder.name;

      return {
        name: folderName,
        path: folderName,
        emailCount: statusInfo?.email_count || 0,
        unreadCount: 0 // TODO: Add unread count from backend
      };
    });

    // Sort folders: common folders first, then alphabetically
    const commonFolders = ['INBOX', 'Sent', 'Drafts', 'Archive', 'Trash', 'Junk', 'Spam'];
    folderList.sort((a, b) => {
      const aIndex = commonFolders.findIndex(cf => a.name.toLowerCase().includes(cf.toLowerCase()));
      const bIndex = commonFolders.findIndex(cf => b.name.toLowerCase().includes(cf.toLowerCase()));

      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
      if (aIndex !== -1) return -1;
      if (bIndex !== -1) return 1;
      return a.name.localeCompare(b.name);
    });

    return folderList;
  };

  const folders = organizeFolders();

  if (!accountId) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Select an email account to view folders
        </Typography>
      </Box>
    );
  }

  if (loadingFolders || loadingStatus) {
    return (
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600 }}>
          Folders
        </Typography>
        <Tooltip title="Refresh folders">
          <IconButton size="small" onClick={handleRefresh}>
            <Refresh fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Divider />

      {/* Folder List */}
      <List sx={{ flex: 1, overflow: 'auto', py: 0 }}>
        {folders.map((folder) => (
          <ListItem key={folder.path} disablePadding>
            <ListItemButton
              selected={selectedFolder === folder.path}
              onClick={() => onFolderSelect(folder.path)}
              sx={{
                py: 1,
                px: 2,
                '&.Mui-selected': {
                  backgroundColor: 'primary.light',
                  '&:hover': {
                    backgroundColor: 'primary.light'
                  }
                }
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                {selectedFolder === folder.path ?
                  React.cloneElement(getFolderIcon(folder.name), { color: 'primary' }) :
                  getFolderIcon(folder.name)
                }
              </ListItemIcon>
              <ListItemText
                primary={folder.name}
                primaryTypographyProps={{
                  sx: {
                    fontSize: '0.9rem',
                    fontWeight: selectedFolder === folder.path ? 600 : 400
                  }
                }}
              />
              {folder.emailCount > 0 && (
                <Chip
                  label={folder.emailCount}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    backgroundColor: selectedFolder === folder.path ? 'primary.main' : 'grey.300',
                    color: selectedFolder === folder.path ? 'white' : 'text.primary'
                  }}
                />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      {/* Footer Info */}
      <Divider />
      <Box sx={{ p: 1.5, backgroundColor: 'background.default' }}>
        <Typography variant="caption" color="text.secondary">
          {folders.length} folder{folders.length !== 1 ? 's' : ''} •
          {' '}{folders.reduce((sum, f) => sum + f.emailCount, 0)} emails
        </Typography>
      </Box>
    </Box>
  );
};

export default FolderSidebar;
