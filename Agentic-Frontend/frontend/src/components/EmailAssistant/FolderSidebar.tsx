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
  useTheme,
  Button
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
  // Cache-busting timestamp
  const forceRefresh = React.useMemo(() => Date.now(), []);
  
  const theme = useTheme();
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(new Set(['root']));

  // Fetch folder sync status to get email counts
  const { data: folderStatus, isLoading: loadingStatus, error: statusError, refetch: refetchStatus } = useQuery({
    queryKey: ['folder-status', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      console.log('[FolderSidebar] Fetching folder status for account:', accountId);
      try {
        const result = await apiClient.getFolderSyncStatus(accountId);
        console.log('[FolderSidebar] Folder status result:', result);
        return result;
      } catch (error) {
        console.error('[FolderSidebar] Error fetching folder status:', error);
        throw error;
      }
    },
    enabled: !!accountId,
    refetchInterval: 30000,
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Fetch available folders
  const { data: foldersData, isLoading: loadingFolders, error: foldersError, refetch: refetchFolders } = useQuery({
    queryKey: ['folders', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      console.log('[FolderSidebar] Fetching folders for account:', accountId);
      try {
        const result = await apiClient.getAccountFolders(accountId);
        console.log('[FolderSidebar] Folders result:', result);
        return result;
      } catch (error) {
        console.error('[FolderSidebar] Error fetching folders:', error);
        throw error;
      }
    },
    enabled: !!accountId,
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
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

    if (foldersError) {
      console.error('[FolderSidebar] Folders error details:', foldersError);
    }
    if (statusError) {
      console.error('[FolderSidebar] Status error details:', statusError);
    }
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
    console.log('[FolderSidebar] organizeFolders called:', {
      hasFoldersData: !!foldersData,
      hasFolderStatus: !!folderStatus,
      hasFoldersError: !!foldersError,
      hasStatusError: !!statusError,
      foldersLength: folderStatus?.folders?.length || 0
    });

    // ALWAYS use folderStatus data as primary source - it's the most reliable
    if (folderStatus && folderStatus.folders && folderStatus.folders.length > 0) {
      console.log('[FolderSidebar] Using FOLDER STATUS data as primary - folders:', folderStatus.folders.length);
      return organizeFoldersFromStatus(folderStatus.folders || []);
    }

    // Fallback to foldersData if available and working
    if (foldersData && !foldersError) {
      console.log('[FolderSidebar] Using primary folders data as fallback');
      return organizeFoldersFromApi(foldersData.folders || [], folderStatus?.folders || []);
    }

    console.log('[FolderSidebar] organizeFolders: No usable data available');
    return [];
  };

  const organizeFoldersFromApi = (folders: any[], folderStatuses: any[]): FolderData[] => {
    const folderList: FolderData[] = [];
    const folderMap = new Map<string, FolderData>();

    console.log('[FolderSidebar] Processing', folders.length, 'API folders and', folderStatuses.length, 'statuses');

    folders.forEach((folder: any) => {
      const folderName = folder.name;
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

    // Build hierarchy
    folderMap.forEach((folder, path) => {
      if (path.includes('/')) {
        const parentPath = path.substring(0, path.lastIndexOf('/'));
        const parent = folderMap.get(parentPath);
        if (parent) {
          parent.children = parent.children || [];
          parent.children.push(folder);
        } else {
          folderList.push(folder);
        }
      } else {
        folderList.push(folder);
      }
    });

    return sortFolders(folderList);
  };

  const organizeFoldersFromStatus = (folderStatuses: any[]): FolderData[] => {
    console.log('[FolderSidebar] Processing', folderStatuses.length, 'status-only folders');
    console.log('[FolderSidebar] Folder names:', folderStatuses.map(f => f.folder_name));

    const result = folderStatuses.map((status: any) => {
      const folderData = {
        name: status.folder_name,
        path: status.folder_name,
        emailCount: status.email_count || 0,
        unreadCount: status.unread_count || 0,
        children: [],
        isExpanded: expandedFolders.has(status.folder_name)
      };
      console.log('[FolderSidebar] Mapped folder:', folderData.name, 'emails:', folderData.emailCount);
      return folderData;
    });

    console.log('[FolderSidebar] Final organized folders count:', result.length);
    return result;
  };

  const sortFolders = (folderList: FolderData[]): FolderData[] => {
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

  console.log('[FolderSidebar] Final folders array length:', folders.length, 'folders:', folders.map(f => f.name));

  // Conditional rendering within single return statement
  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderRight: `1px solid ${theme.palette.divider}`,
      backgroundColor: theme.palette.background.paper,
      borderRadius: '8px 0 0 8px'
    }}>
      {/* Show "no account" message */}
      {!accountId && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No email account selected
          </Typography>
        </Box>
      )}

      {/* Show loading state */}
      {accountId && (loadingFolders || loadingStatus) && (
        <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Loading folders...
          </Typography>
        </Box>
      )}

      {/* Show folders when loaded - ALWAYS show if we have account and not loading */}
      {accountId && !loadingFolders && !loadingStatus && folders.length > 0 && (
        <>
          {/* Header */}
          <Box sx={{
            p: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: `1px solid ${theme.palette.divider}`,
            backgroundColor: alpha(theme.palette.primary.main, 0.02),
            borderRadius: '8px 0 0 0'
          }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Folders{foldersError ? ' (Fallback)' : ''}
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
              {foldersError ? ' (using fallback)' : ''}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {folders.reduce((sum, f) => sum + f.emailCount + (f.children?.reduce((s, c) => s + c.emailCount, 0) || 0), 0)} emails total
            </Typography>
          </Box>
        </>
      )}

      {/* Show fallback error state when we have no folders but have tried to load */}
      {accountId && !loadingFolders && !loadingStatus && folders.length === 0 && !foldersError && (
        <Box sx={{ p: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No folders found
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Try refreshing or check your account settings
          </Typography>
          <Typography variant="caption" color="error" sx={{ display: 'block', mt: 1 }}>
            Debug: folders.length = {folders.length}, foldersError = {foldersError ? 'present' : 'none'}
          </Typography>
        </Box>
      )}

      {/* Show error state */}
      {accountId && foldersError && !loadingFolders && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="error" sx={{ mb: 1 }}>
            Failed to load folders
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
            {foldersError.message || 'Unknown error occurred'}
          </Typography>
          <Button size="small" onClick={handleRefresh} variant="outlined">
            Retry
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default FolderSidebar;
