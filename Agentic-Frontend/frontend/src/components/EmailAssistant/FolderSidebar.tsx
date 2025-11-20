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
  IconButton,
  Tooltip,
  Collapse,
  alpha,
  useTheme,
  Button,
  Divider
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
  ChevronRight,
  Edit as EditIcon,
  Add as AddIcon
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
  const sx = { fontSize: 20, color: isSelected ? 'primary.main' : 'text.secondary' };

  if (name === 'inbox') return <Inbox sx={sx} />;
  if (name === 'sent' || name === 'sent items') return <Send sx={sx} />;
  if (name === 'drafts') return <Drafts sx={sx} />;
  if (name === 'trash' || name === 'deleted items' || name === 'bin') return <Delete sx={sx} />;
  if (name === 'archive') return <Archive sx={sx} />;
  if (name === 'starred' || name === 'flagged' || name === 'important') return <Star sx={sx} />;
  if (name === 'junk' || name === 'spam') return <Label sx={sx} />;

  return <Label sx={sx} />;
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
      try {
        const result = await apiClient.getFolderSyncStatus(accountId);
        return result;
      } catch (error) {
        console.error('[FolderSidebar] Error fetching folder status:', error);
        throw error;
      }
    },
    enabled: !!accountId,
    refetchInterval: 30000,
    retry: 3,
  });

  // Fetch available folders
  const { data: foldersData, isLoading: loadingFolders, error: foldersError, refetch: refetchFolders } = useQuery({
    queryKey: ['folders', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      try {
        const result = await apiClient.getAccountFolders(accountId);
        return result;
      } catch (error) {
        console.error('[FolderSidebar] Error fetching folders:', error);
        throw error;
      }
    },
    enabled: !!accountId,
    retry: 3,
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

  // Organize folders into hierarchical structure
  const organizeFolders = (): FolderData[] => {
    // ALWAYS use folderStatus data as primary source - it's the most reliable
    if (folderStatus && folderStatus.folders && folderStatus.folders.length > 0) {
      return organizeFoldersFromStatus(folderStatus.folders || []);
    }

    // Fallback to foldersData if available and working
    if (foldersData && !foldersError) {
      return organizeFoldersFromApi(foldersData.folders || [], folderStatus?.folders || []);
    }

    return [];
  };

  const organizeFoldersFromApi = (folders: any[], folderStatuses: any[]): FolderData[] => {
    const folderList: FolderData[] = [];
    const folderMap = new Map<string, FolderData>();

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
    const folderList: FolderData[] = [];
    const folderMap = new Map<string, FolderData>();

    // First pass: Create all folder objects
    folderStatuses.forEach((status: any) => {
      const folderData: FolderData = {
        name: status.folder_name,
        path: status.folder_name,
        emailCount: status.email_count || 0,
        unreadCount: status.unread_count || 0,
        children: [],
        isExpanded: expandedFolders.has(status.folder_name)
      };
      folderMap.set(status.folder_name, folderData);
    });

    // Second pass: Build hierarchy
    // We need to handle cases where parent folders might not exist in the status list
    // but are implied by the path structure (e.g. "INBOX/Work" implies "INBOX")

    // Sort keys to ensure parents are processed before children if possible, 
    // though the map lookup handles out-of-order processing too.
    const sortedPaths = Array.from(folderMap.keys()).sort();

    sortedPaths.forEach((path) => {
      const folder = folderMap.get(path)!;

      if (path.includes('/')) {
        // It's a subfolder
        const parentPath = path.substring(0, path.lastIndexOf('/'));
        const parent = folderMap.get(parentPath);

        if (parent) {
          parent.children = parent.children || [];
          parent.children.push(folder);
        } else {
          // Parent doesn't exist in our map (maybe not returned by API?)
          // For now, treat as root level to ensure it's visible
          folderList.push(folder);
        }
      } else {
        // It's a root folder
        folderList.push(folder);
      }
    });

    return sortFolders(folderList);
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
    const folderName = folder.name.split('/').pop() || folder.name;

    return (
      <React.Fragment key={folder.path}>
        <ListItem disablePadding sx={{ mb: 0.5 }}>
          <ListItemButton
            selected={isSelected}
            onClick={() => onFolderSelect(folder.path)}
            sx={{
              pl: 2 + depth * 2,
              pr: 2,
              py: 0.75,
              mx: 1,
              borderRadius: 2,
              minHeight: 36,
              '&.Mui-selected': {
                backgroundColor: alpha(theme.palette.primary.main, 0.1),
                '&:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.15)
                }
              },
              '&:hover': {
                backgroundColor: alpha(theme.palette.text.primary, 0.04)
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
                sx={{
                  mr: 0.5,
                  p: 0.25,
                  ml: -1,
                  color: 'text.secondary',
                  transform: isExpanded ? 'rotate(90deg)' : 'none',
                  transition: 'transform 0.2s'
                }}
              >
                <ChevronRight fontSize="small" />
              </IconButton>
            )}

            <ListItemIcon sx={{ minWidth: 32, ml: hasChildren ? 0 : 2.5 }}>
              {getFolderIcon(folder.name, isSelected)}
            </ListItemIcon>

            <ListItemText
              primary={folderName}
              primaryTypographyProps={{
                sx: {
                  fontSize: '0.875rem',
                  fontWeight: isSelected ? 600 : 500,
                  color: isSelected ? 'text.primary' : 'text.secondary',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }
              }}
            />

            {/* Show unread count if there are unread emails */}
            {folder.unreadCount !== undefined && folder.unreadCount > 0 && (
              <Badge
                badgeContent={folder.unreadCount}
                color="primary"
                sx={{
                  '& .MuiBadge-badge': {
                    fontSize: '0.7rem',
                    height: 18,
                    minWidth: 18,
                    fontWeight: 600,
                    boxShadow: `0 0 0 2px ${theme.palette.background.paper}`,
                  }
                }}
              />
            )}
          </ListItemButton>
        </ListItem>

        {hasChildren && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            {folder.children!.map(child => renderFolder(child, depth + 1))}
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  const folders = organizeFolders();

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: 'transparent',
    }}>
      {/* Compose Button Area */}
      <Box sx={{ p: 2 }}>
        <Button
          variant="contained"
          fullWidth
          startIcon={<EditIcon />}
          sx={{
            py: 1.5,
            borderRadius: 3,
            textTransform: 'none',
            fontWeight: 600,
            boxShadow: theme.shadows[2],
            background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
            '&:hover': {
              boxShadow: theme.shadows[4],
            }
          }}
        >
          Compose
        </Button>
      </Box>

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

      {/* Show folders when loaded */}
      {accountId && !loadingFolders && !loadingStatus && folders.length > 0 && (
        <>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 1 }}>
              Folders
            </Typography>
          </Box>

          <List sx={{ flex: 1, overflow: 'auto', py: 0.5 }}>
            {folders.map(folder => renderFolder(folder))}
          </List>

          {/* Smart Views / Categories Section (Future) */}
          <Divider sx={{ my: 1, mx: 2 }} />

          <Box sx={{ px: 2, py: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 1 }}>
              Smart Views
            </Typography>
            <IconButton size="small" sx={{ p: 0.5 }}>
              <AddIcon fontSize="small" />
            </IconButton>
          </Box>
        </>
      )}

      {/* Show fallback error state */}
      {accountId && !loadingFolders && !loadingStatus && folders.length === 0 && !foldersError && (
        <Box sx={{ p: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No folders found
          </Typography>
        </Box>
      )}

      {/* Show error state */}
      {accountId && foldersError && !loadingFolders && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="error" sx={{ mb: 1 }}>
            Failed to load folders
          </Typography>
          <Button size="small" onClick={handleRefresh} variant="outlined" color="error">
            Retry
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default FolderSidebar;
