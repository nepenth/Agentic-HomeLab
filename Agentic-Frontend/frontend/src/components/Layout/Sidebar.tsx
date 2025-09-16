import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  IconButton,
  Avatar,
  Chip,
  Collapse,
} from '@mui/material';
import {
  Dashboard,
  SmartToy,
  Settings,
  Logout,
  Build,
  Email,
  Description,
  Menu as MenuIcon,
  ExpandLess,
  ExpandMore,
  Home,
  Speed,
  Engineering,
  Security,
  Chat,
  Memory,
  Assessment,
  Person,
  Search,
  TrendingUp,
  Audiotrack,
  Visibility,
  Psychology,
  Compare,
  Api,
  AccountTree,
  Balance,
  Group,
  Star,
} from '@mui/icons-material';
import { useAuth } from '../../hooks/useAuth';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState } from '../../store';
import { toggleSidebar } from '../../store/slices/uiSlice';

interface SidebarProps {
  drawerWidth?: number;
}

const Sidebar: React.FC<SidebarProps> = ({ drawerWidth = 280 }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { user, logout } = useAuth();
  const { sidebarOpen } = useSelector((state: RootState) => state.ui);
  
  const [workflowsOpen, setWorkflowsOpen] = React.useState(true);
  const [futureEnhancementsOpen, setFutureEnhancementsOpen] = React.useState(false);

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleToggleSidebar = () => {
    dispatch(toggleSidebar());
  };

  const handleWorkflowsToggle = () => {
    setWorkflowsOpen(!workflowsOpen);
  };

  const handleFutureEnhancementsToggle = () => {
    setFutureEnhancementsOpen(!futureEnhancementsOpen);
  };

  const isActive = (path: string) => location.pathname === path;

  const menuItems = [
    {
      type: 'item',
      path: '/dashboard',
      label: 'Dashboard',
      icon: <Dashboard />,
      primary: true,
    },
    {
      type: 'divider',
    },
    {
      type: 'item',
      path: '/system-health',
      label: 'System Health',
      icon: <Speed />,
    },
    {
      type: 'item',
      path: '/security',
      label: 'Security Center',
      icon: <Security />,
    },
    {
      type: 'item',
      path: '/agents',
      label: 'Agent Management',
      icon: <Engineering />,
    },
    {
      type: 'item',
      path: '/content-processing',
      label: 'Content Processing',
      icon: <Memory />,
    },
    {
      type: 'item',
      path: '/workflow-studio',
      label: 'Workflow Studio',
      icon: <AccountTree />,
    },
    {
      type: 'item',
      path: '/chat',
      label: 'AI Chat',
      icon: <Chat />,
    },
    {
      type: 'divider',
    },
    {
      type: 'parent',
      label: 'Future Enhancements',
      icon: <Star />,
      open: futureEnhancementsOpen,
      onToggle: handleFutureEnhancementsToggle,
      children: [
        {
          path: '/analytics',
          label: 'Analytics',
          icon: <Assessment />,
        },
        {
          path: '/personalization',
          label: 'Personalization',
          icon: <Person />,
        },
        {
          path: '/trends',
          label: 'Trends & Forecasting',
          icon: <TrendingUp />,
        },
        {
          path: '/search-intelligence',
          label: 'Search Intelligence',
          icon: <Search />,
        },
        {
          path: '/vision-studio',
          label: 'Vision AI Studio',
          icon: <Visibility />,
        },
        {
          path: '/audio-workstation',
          label: 'Audio AI Workstation',
          icon: <Audiotrack />,
        },
        {
          path: '/cross-modal-fusion',
          label: 'Cross-Modal Fusion',
          icon: <Compare />,
        },
        {
          path: '/learning-adaptation',
          label: 'Learning & Adaptation',
          icon: <Psychology />,
        },
        {
          path: '/integration-hub',
          label: 'Integration Hub',
          icon: <Api />,
        },
        {
          path: '/load-balancing',
          label: 'Load Balancing',
          icon: <Balance />,
        },
        {
          path: '/collaboration',
          label: 'Collaboration',
          icon: <Group />,
        },
      ],
    },
    {
      type: 'divider',
    },
    {
      type: 'parent',
      label: 'Workflows',
      icon: <SmartToy />,
      open: workflowsOpen,
      onToggle: handleWorkflowsToggle,
      children: [
        {
          path: '/workflows/knowledge-base',
          label: 'Knowledge Base',
          icon: <Psychology />,
        },
        {
          path: '/workflows/email-assistant',
          label: 'Email Assistant',
          icon: <Email />,
        },
        {
          path: '/workflows/document-analyzer',
          label: 'Document Analyzer',
          icon: <Description />,
          badge: 'Soon',
        },
      ],
    },
    {
      type: 'divider',
    },
    {
      type: 'item',
      path: '/utilities',
      label: 'Backend Tools',
      icon: <Build />,
    },
    {
      type: 'item',
      path: '/settings',
      label: 'Settings',
      icon: <Settings />,
    },
    ...(user?.is_superuser ? [{
      type: 'item' as const,
      path: '/user-management',
      label: 'User Management',
      icon: <Person />,
    }] : []),
  ];

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(135deg, #007AFF, #5856D6)',
          color: 'white',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.2)',
              width: 40,
              height: 40,
            }}
          >
            <Home />
          </Avatar>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
              Agentic
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, fontSize: '0.75rem' }}>
              AI Frontend
            </Typography>
          </Box>
        </Box>
        <IconButton
          onClick={handleToggleSidebar}
          sx={{ color: 'white', display: { xs: 'block', md: 'none' } }}
        >
          <MenuIcon />
        </IconButton>
      </Box>

      {/* Navigation Menu */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <List sx={{ px: 1, py: 2 }}>
          {menuItems.map((item, index) => {
            if (item.type === 'divider') {
              return <Divider key={index} sx={{ my: 1 }} />;
            }

            if (item.type === 'parent') {
              return (
                <React.Fragment key={index}>
                  <ListItem disablePadding>
                    <ListItemButton
                      onClick={item.onToggle}
                      sx={{
                        borderRadius: 2,
                        mb: 0.5,
                        '&:hover': {
                          backgroundColor: 'rgba(0, 122, 255, 0.08)',
                        },
                      }}
                    >
                      <ListItemIcon sx={{ color: 'text.secondary' }}>
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText
                        primary={item.label}
                        primaryTypographyProps={{
                          fontWeight: 500,
                          fontSize: '0.9rem',
                        }}
                      />
                      {item.open ? <ExpandLess /> : <ExpandMore />}
                    </ListItemButton>
                  </ListItem>
                  <Collapse in={item.open} timeout="auto" unmountOnExit>
                    <List component="div" sx={{ pl: 2 }}>
                      {item.children?.map((child, childIndex) => (
                        <ListItem key={childIndex} disablePadding>
                          <ListItemButton
                            onClick={() => handleNavigation(child.path)}
                            disabled={!!child.badge}
                            sx={{
                              borderRadius: 2,
                              mb: 0.5,
                              backgroundColor: isActive(child.path)
                                ? 'rgba(0, 122, 255, 0.12)'
                                : 'transparent',
                              '&:hover': {
                                backgroundColor: isActive(child.path)
                                  ? 'rgba(0, 122, 255, 0.16)'
                                  : 'rgba(0, 122, 255, 0.08)',
                              },
                              '&.Mui-disabled': {
                                opacity: 0.6,
                              },
                            }}
                          >
                            <ListItemIcon
                              sx={{
                                color: isActive(child.path)
                                  ? 'primary.main'
                                  : 'text.secondary',
                              }}
                            >
                              {child.icon}
                            </ListItemIcon>
                            <ListItemText
                              primary={child.label}
                              primaryTypographyProps={{
                                fontWeight: isActive(child.path) ? 600 : 400,
                                fontSize: '0.85rem',
                                color: isActive(child.path)
                                  ? 'primary.main'
                                  : 'text.primary',
                              }}
                            />
                            {child.badge && (
                              <Chip
                                label={child.badge}
                                size="small"
                                sx={{
                                  height: 20,
                                  fontSize: '0.7rem',
                                  backgroundColor: 'warning.light',
                                  color: 'warning.contrastText',
                                }}
                              />
                            )}
                          </ListItemButton>
                        </ListItem>
                      ))}
                    </List>
                  </Collapse>
                </React.Fragment>
              );
            }

            return (
              <ListItem key={index} disablePadding>
                <ListItemButton
                  onClick={() => item.path && handleNavigation(item.path)}
                  sx={{
                    borderRadius: 2,
                    mb: 0.5,
                    backgroundColor: item.path && isActive(item.path)
                      ? item.primary
                        ? 'linear-gradient(135deg, rgba(0, 122, 255, 0.15), rgba(88, 86, 214, 0.15))'
                        : 'rgba(0, 122, 255, 0.12)'
                      : 'transparent',
                    '&:hover': {
                      backgroundColor: item.path && isActive(item.path)
                        ? item.primary
                          ? 'linear-gradient(135deg, rgba(0, 122, 255, 0.2), rgba(88, 86, 214, 0.2))'
                          : 'rgba(0, 122, 255, 0.16)'
                        : 'rgba(0, 122, 255, 0.08)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: item.path && isActive(item.path)
                        ? 'primary.main'
                        : 'text.secondary',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{
                      fontWeight: item.path && isActive(item.path) ? 600 : 500,
                      fontSize: '0.9rem',
                      color: item.path && isActive(item.path)
                        ? 'primary.main'
                        : 'text.primary',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* User Profile & Logout */}
      <Box sx={{ borderTop: 1, borderColor: 'divider', p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Avatar sx={{ bgcolor: 'primary.main', mr: 2, width: 32, height: 32 }}>
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {user?.username || 'User'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {user?.email || 'user@example.com'}
            </Typography>
          </Box>
        </Box>
        
        <ListItemButton
          onClick={handleLogout}
          sx={{
            borderRadius: 2,
            color: 'error.main',
            '&:hover': {
              backgroundColor: 'rgba(244, 67, 54, 0.08)',
            },
          }}
        >
          <ListItemIcon sx={{ color: 'error.main' }}>
            <Logout />
          </ListItemIcon>
          <ListItemText
            primary="Logout"
            primaryTypographyProps={{
              fontWeight: 500,
              fontSize: '0.9rem',
            }}
          />
        </ListItemButton>
      </Box>
    </Box>
  );

  return (
    <>
      {/* Mobile drawer */}
      <Drawer
        variant="temporary"
        open={sidebarOpen}
        onClose={handleToggleSidebar}
        ModalProps={{
          keepMounted: true, // Better mobile performance
        }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
            border: 'none',
          },
        }}
      >
        {drawer}
      </Drawer>

      {/* Desktop drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
            border: 'none',
          },
        }}
        open
      >
        {drawer}
      </Drawer>
    </>
  );
};

export default Sidebar;