import React, { useState } from 'react';
import {
  Box,
  Container,
  Paper,
  Tabs,
  Tab,
  useTheme,
  alpha,
  Badge,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Inbox as InboxIcon,
  Chat as ChatIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { OverviewTab } from './tabs/OverviewTab';
import { InboxTasksTab } from './tabs/InboxTasksTab';
import { AssistantTab } from './tabs/AssistantTab';
import { SettingsTab } from './tabs/SettingsTab';
import { useEmail } from '../../hooks/useEmail';
import { useTasks } from '../../hooks/useTasks';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`email-assistant-tabpanel-${index}`}
      aria-labelledby={`email-assistant-tab-${index}`}
      style={{ height: '100%' }}
    >
      {value === index && <Box sx={{ height: '100%', p: 0 }}>{children}</Box>}
    </div>
  );
};

export const EmailAssistantComponent: React.FC = () => {
  const theme = useTheme();
  const [currentTab, setCurrentTab] = useState(0);
  const [inboxFilters, setInboxFilters] = useState<any>(null);
  const { emails } = useEmail();
  const { tasks } = useTasks();

  // Calculate badge counts
  const unreadCount = emails.filter(e => !e.is_read).length;
  const pendingTasksCount = tasks.filter(t => t.status === 'pending' || t.status === 'in_progress').length;

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
    // Clear filters when manually switching tabs
    if (newValue !== 1) {
      setInboxFilters(null);
    }
  };

  const handleNavigate = (tab: string, options?: any) => {
    switch (tab) {
      case 'inbox':
        if (options) {
          setInboxFilters(options);
        }
        setCurrentTab(1);
        break;
      case 'assistant':
        setCurrentTab(2);
        break;
      case 'settings':
        setCurrentTab(3);
        break;
      default:
        setCurrentTab(0);
    }
  };

  const handleNavigateToEmail = (emailId: string) => {
    // Navigate to inbox tab with specific email selected
    setInboxFilters({
      view: 'emails',
      selectedEmailId: emailId,
      scrollToEmail: true,
    });
    setCurrentTab(1);
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header with Tabs */}
      <Paper
        elevation={1}
        sx={{
          borderRadius: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
          mb: 2,
        }}
      >
        <Container maxWidth="xl" sx={{ px: 0 }}>
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            aria-label="email assistant tabs"
            sx={{
              '& .MuiTab-root': {
                minHeight: 64,
                textTransform: 'none',
                fontSize: '0.95rem',
                fontWeight: 600,
              },
            }}
          >
            <Tab
              icon={<DashboardIcon />}
              iconPosition="start"
              label="Overview"
              id="email-assistant-tab-0"
              aria-controls="email-assistant-tabpanel-0"
            />
            <Tab
              icon={
                <Badge badgeContent={unreadCount + pendingTasksCount} color="error" max={99}>
                  <InboxIcon />
                </Badge>
              }
              iconPosition="start"
              label="Inbox & Tasks"
              id="email-assistant-tab-1"
              aria-controls="email-assistant-tabpanel-1"
            />
            <Tab
              icon={<ChatIcon />}
              iconPosition="start"
              label="Assistant"
              id="email-assistant-tab-2"
              aria-controls="email-assistant-tabpanel-2"
            />
            <Tab
              icon={<SettingsIcon />}
              iconPosition="start"
              label="Settings"
              id="email-assistant-tab-3"
              aria-controls="email-assistant-tabpanel-3"
            />
          </Tabs>
        </Container>
      </Paper>

      {/* Tab Content */}
      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0, pb: 2 }}>
        <Container maxWidth="xl" sx={{ flex: 1, display: 'flex', flexDirection: 'column', px: 0, overflow: 'hidden', minHeight: 0 }}>
          <TabPanel value={currentTab} index={0}>
            <OverviewTab onNavigate={handleNavigate} />
          </TabPanel>
          <TabPanel value={currentTab} index={1}>
            <InboxTasksTab filters={inboxFilters} onFiltersChange={setInboxFilters} />
          </TabPanel>
          <TabPanel value={currentTab} index={2}>
            <AssistantTab onNavigateToEmail={handleNavigateToEmail} />
          </TabPanel>
          <TabPanel value={currentTab} index={3}>
            <SettingsTab />
          </TabPanel>
        </Container>
      </Box>
    </Box>
  );
};

export default EmailAssistantComponent;
