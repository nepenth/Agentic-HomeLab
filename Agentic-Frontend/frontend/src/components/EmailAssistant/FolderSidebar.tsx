import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Badge,
  Divider,
  IconButton,
  Tooltip,
  Collapse,
  alpha,
  useTheme
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
  Refresh,
  ChevronRight
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface FolderSidebarProps {
  accountId: string | null;
  selectedFolder: string | null;
  onFolderSelect: (folder: string) => void;
}

interface FolderData {
  name: string;
  path: string;
  emailCount: number;
  unreadCount?: number;
  children?: FolderData[];
  isExpanded?: boolean;
}

// Icon mapping for common folders
const getFolderIcon = (folderName: string, isSelected: boolean) => {
  const name = folderName.toLowerCase();
  const color = isSelected ? 'primary' : 'inherit';

  if (name === 'inbox') return <Inbox color={color as any} />;
  if (name === 'sent' || name === 'sent items') return <Send color={color as any} />;
  if (name === 'drafts') return <Drafts color={color as any} />;
  if (name === 'trash' || name === 'deleted items' || name === 'bin') return <Delete color={color as any} />;
  if (name === 'archive') return <Archive color={color as any} />;
  if (name === 'starred' || name === 'flagged' || name === 'important') return <Star color={color as any} />;
  if (name === 'junk' || name === 'spam') return <Label color={color as any} />;

  return isSelected ? <FolderOpen color="primary" /> : <Folder />;
};

export const FolderSidebar: React.FC<FolderSidebarProps> = ({
  accountId,
  selectedFolder,
  onFolderSelect
}) => {
  const theme = useTheme();
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(new Set(['root']));

  // Fetch folder sync status to get email counts
  const { data: folderStatus, isLoading: loadingStatus, error: statusError, refetch: refetchStatus } = useQuery({
    queryKey: ['folder-status', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      console.log('[FolderSidebar] Fetching folder status for account:', accountId);
      const result = await apiClient.getFolderSyncStatus(accountId);
      console.log('[FolderSidebar] Folder status result:', result);
      return result;
    },
    enabled: !!accountId,
    refetchInterval: 30000
  });

  // Fetch available folders
  const { data: foldersData, isLoading: loadingFolders, error: foldersError, refetch: refetchFolders } = useQuery({
    queryKey: ['folders', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      console.log('[FolderSidebar] Fetching folders for account:', accountId);
      const result = await apiClient.getAccountFolders(accountId);
      console.log('[FolderSidebar] Folders result:', result);
      return result;
    },
    enabled: !!accountId
  });

  // Debug logging
  React.useEffect(() => {
    console.log('[FolderSidebar] State:', {
      accountId,
      foldersData,
      folderStatus,
      loadingFolders,
      loadingStatus,
      foldersError,
      statusError
    });
  }, [accountId, foldersData, folderStatus, loadingFolders, loadingStatus, foldersError, statusError]);

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

  // Organize folders into hierarchical structure
  const organizeFolders = (): FolderData[] => {
    if (!foldersData || !folderStatus) {
      return [];
    }

    const folderList: FolderData[] = [];
    const folderMap = new Map<string, FolderData>();

    // Create folder objects from API response
    // API returns: [{name: "INBOX", delimiter: "/", flags: [...], selectable: true, has_children: true}, ...]
    const folders = foldersData.folders || [];
    const folderStatuses = folderStatus.folders || [];

    folders.forEach((folder: any) => {
      // Extract folder name - API always returns objects with 'name' field
      const folderName = folder.name;

      // Find matching status info
      const statusInfo = folderStatuses.find((f: any) => f.folder_name === folderName);

      const folderData: FolderData = {
        name: folderName,
        path: folderName,
        emailCount: statusInfo?.email_count || 0,
        unreadCount: statusInfo?.unread_count || 0,
        children: [],
        isExpanded: expandedFolders.has(folderName)
      };

      folderMap.set(folderName, folderData);
    });

    // Build hierarchy (handle INBOX/Subfolder pattern using delimiter from API)
    folderMap.forEach((folder, path) => {
      // Check if this is a child folder (contains delimiter)
      if (path.includes('/')) {
        const parentPath = path.substring(0, path.lastIndexOf('/'));
        const parent = folderMap.get(parentPath);
        if (parent) {
          // Add to parent's children
          parent.children = parent.children || [];
          parent.children.push(folder);
        } else {
          // Parent not found, add to root
          folderList.push(folder);
        }
      } else {
        // Top-level folder
        folderList.push(folder);
      }
    });

    // Sort: common folders first, then alphabetically
    const commonFolders = ['INBOX', 'Sent', 'Drafts', 'Archive', 'Trash', 'Junk', 'Spam', 'Important'];
    folderList.sort((a, b) => {
      const aIndex = commonFolders.findIndex(cf => a.name.toUpperCase().includes(cf.toUpperCase()));
      const bIndex = commonFolders.findIndex(cf => b.name.toUpperCase().includes(cf.toUpperCase()));

      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
      if (aIndex !== -1) return -1;
      if (bIndex !== -1) return 1;
      return a.name.localeCompare(b.name);
    });

    return folderList;
  };

  const renderFolder = (folder: FolderData, depth: number = 0) => {
    const isSelected = selectedFolder === folder.path;
    const hasChildren = folder.children && folder.children.length > 0;
    const isExpanded = expandedFolders.has(folder.path);

    return (
      <React.Fragment key={folder.path}>
        <ListItem
          disablePadding
          sx={{
            pl: depth * 2,
            borderLeft: isSelected ? `3px solid ${theme.palette.primary.main}` : 'none'
          }}
        >
          <ListItemButton
            selected={isSelected}
            onClick={() => onFolderSelect(folder.path)}
            sx={{
              py: 0.75,
              px: 1.5,
              minHeight: 40,
              '&.Mui-selected': {
                backgroundColor: alpha(theme.palette.primary.main, 0.08),
                '&:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.12)
                }
              },
              '&:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.04)
              }
            }}
          >
            {hasChildren && (
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleFolder(folder.path);
                }}
                sx={{ mr: 0.5, p: 0.25 }}
              >
                {isExpanded ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
              </IconButton>
            )}

            <ListItemIcon sx={{ minWidth: 36 }}>
              {getFolderIcon(folder.name, isSelected)}
            </ListItemIcon>

            <ListItemText
              primary={folder.name.split('/').pop()}
              primaryTypographyProps={{
                sx: {
                  fontSize: '0.875rem',
                  fontWeight: isSelected ? 600 : 400,
                  color: isSelected ? 'primary.main' : 'text.primary'
                }
              }}
            />

            {/* Show unread count if there are unread emails */}
            {folder.unreadCount !== undefined && folder.unreadCount > 0 && (
              <Badge
                badgeContent={folder.unreadCount}
                color={isSelected ? 'primary' : 'default'}
                sx={{
                  '& .MuiBadge-badge': {
                    fontSize: '0.65rem',
                    height: 18,
                    minWidth: 18,
                    fontWeight: 600,
                    backgroundColor: isSelected ? theme.palette.primary.main : theme.palette.primary.light,
                    color: 'white'
                  }
                }}
              />
            )}
          </ListItemButton>
        </ListItem>

        {hasChildren && isExpanded && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            {folder.children!.map(child => renderFolder(child, depth + 1))}
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  const folders = organizeFolders();

  if (!accountId) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No email account selected
        </Typography>
      </Box>
    );
  }

  if (loadingFolders || loadingStatus) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Loading folders...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderRight: `1px solid ${theme.palette.divider}`
    }}>
      {/* Header */}
      <Box sx={{
        p: 2,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: `1px solid ${theme.palette.divider}`
      }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Folders
        </Typography>
        <Tooltip title="Refresh folders">
          <IconButton size="small" onClick={handleRefresh}>
            <Refresh fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Folder List */}
      <List sx={{ flex: 1, overflow: 'auto', py: 0.5 }}>
        {folders.map(folder => renderFolder(folder))}
      </List>

      {/* Footer Stats */}
      <Box sx={{
        p: 1.5,
        borderTop: `1px solid ${theme.palette.divider}`,
        backgroundColor: alpha(theme.palette.background.default, 0.5)
      }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
          {folders.length} folder{folders.length !== 1 ? 's' : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {folders.reduce((sum, f) => sum + f.emailCount + (f.children?.reduce((s, c) => s + c.emailCount, 0) || 0), 0)} emails total
        </Typography>
      </Box>
    </Box>
  );
};

export default FolderSidebar;
