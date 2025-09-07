import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  Alert,
  Skeleton,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Avatar,
  Divider,
  Tabs,
  Tab,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Fab,
  Tooltip,
  Drawer,
  CircularProgress,
} from '@mui/material';
import {
  People,
  Message,
  Share,
  Comment,
  Edit,
  Visibility,
  Notifications,
  NotificationsOff,
  Group,
  PersonAdd,
  Forum,
  ChatBubble,
  ThumbUp,
  Reply,
  Send,
  ExpandMore,
  Refresh,
  Assessment,
  Timeline,
  TrendingUp,
  Speed,
  Memory,
  AccessTime,
  CallReceived,
  CallMade,
  Http,
  Security,
  Route,
  Transform,
  Send as SendIcon,
  NotificationsActive,
  NotificationsNone,
  GroupWork,
  WorkspacePremium,
  LiveHelp,
  Help,
  Support,
  ContactSupport,
  CheckCircle,
  SmartToy,
  Add,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

// Define collaboration types locally for now
interface CollaborationSession {
  id: string;
  name: string;
  type: 'workflow' | 'agent' | 'analysis' | 'general';
  participants: Participant[];
  status: 'active' | 'inactive' | 'archived';
  created_at: string;
  last_activity: string;
  metadata: {
    total_messages: number;
    total_participants: number;
    duration_minutes: number;
  };
}

interface Participant {
  id: string;
  name: string;
  avatar?: string;
  role: 'owner' | 'editor' | 'viewer';
  status: 'online' | 'away' | 'offline';
  joined_at: string;
  last_seen: string;
}

interface Message {
  id: string;
  session_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  type: 'text' | 'system' | 'file' | 'annotation';
  timestamp: string;
  reactions: Reaction[];
  replies: Reply[];
  metadata?: any;
}

interface Reaction {
  emoji: string;
  count: number;
  users: string[];
}

interface Reply {
  id: string;
  content: string;
  sender_id: string;
  sender_name: string;
  timestamp: string;
}

interface Notification {
  id: string;
  type: 'mention' | 'reply' | 'invitation' | 'update' | 'system';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  action_url?: string;
  metadata?: any;
}

interface CollaborationStats {
  total_sessions: number;
  active_sessions: number;
  total_participants: number;
  online_participants: number;
  total_messages: number;
  average_session_duration: number;
  collaboration_efficiency: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`collaboration-tabpanel-${index}`}
      aria-labelledby={`collaboration-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Collaboration: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [selectedSession, setSelectedSession] = useState<CollaborationSession | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [showMessageDialog, setShowMessageDialog] = useState(false);
  const [currentMessage, setCurrentMessage] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  // Collaboration Stats Query
  const {
    data: collaborationStats,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery<CollaborationStats>({
    queryKey: ['collaboration-stats'],
    queryFn: async () => {
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 1000));
      return {
        total_sessions: 24,
        active_sessions: 8,
        total_participants: 156,
        online_participants: 42,
        total_messages: 2847,
        average_session_duration: 45,
        collaboration_efficiency: 0.87
      };
    },
  });

  // Collaboration Sessions Query
  const {
    data: collaborationSessions,
    isLoading: sessionsLoading,
    refetch: refetchSessions,
  } = useQuery<CollaborationSession[]>({
    queryKey: ['collaboration-sessions'],
    queryFn: async () => {
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 1200));
      return [
        {
          id: 'session_001',
          name: 'Workflow Optimization Review',
          type: 'workflow',
          participants: [
            {
              id: 'user_001',
              name: 'Alice Johnson',
              role: 'owner',
              status: 'online',
              joined_at: '2024-01-01T09:00:00Z',
              last_seen: '2024-01-01T10:30:00Z'
            },
            {
              id: 'user_002',
              name: 'Bob Smith',
              role: 'editor',
              status: 'online',
              joined_at: '2024-01-01T09:15:00Z',
              last_seen: '2024-01-01T10:25:00Z'
            }
          ],
          status: 'active',
          created_at: '2024-01-01T09:00:00Z',
          last_activity: '2024-01-01T10:30:00Z',
          metadata: {
            total_messages: 45,
            total_participants: 2,
            duration_minutes: 90
          }
        },
        {
          id: 'session_002',
          name: 'AI Model Performance Analysis',
          type: 'analysis',
          participants: [
            {
              id: 'user_003',
              name: 'Carol Davis',
              role: 'owner',
              status: 'away',
              joined_at: '2024-01-01T08:30:00Z',
              last_seen: '2024-01-01T10:15:00Z'
            }
          ],
          status: 'active',
          created_at: '2024-01-01T08:30:00Z',
          last_activity: '2024-01-01T10:15:00Z',
          metadata: {
            total_messages: 23,
            total_participants: 1,
            duration_minutes: 105
          }
        }
      ];
    },
  });

  // Messages Query
  const {
    data: messages,
    isLoading: messagesLoading,
    refetch: refetchMessages,
  } = useQuery<Message[]>({
    queryKey: ['session-messages', selectedSession?.id],
    queryFn: async () => {
      if (!selectedSession) return [];
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 800));
      return [
        {
          id: 'msg_001',
          session_id: selectedSession.id,
          sender_id: 'user_001',
          sender_name: 'Alice Johnson',
          content: 'I think we should optimize the data processing step in the workflow',
          type: 'text',
          timestamp: '2024-01-01T10:00:00Z',
          reactions: [
            { emoji: '👍', count: 2, users: ['user_001', 'user_002'] }
          ],
          replies: [
            {
              id: 'reply_001',
              content: 'Agreed, the current implementation is inefficient',
              sender_id: 'user_002',
              sender_name: 'Bob Smith',
              timestamp: '2024-01-01T10:05:00Z'
            }
          ]
        },
        {
          id: 'msg_002',
          session_id: selectedSession.id,
          sender_id: 'user_002',
          sender_name: 'Bob Smith',
          content: 'Let me share the performance metrics for comparison',
          type: 'text',
          timestamp: '2024-01-01T10:10:00Z',
          reactions: [],
          replies: []
        }
      ];
    },
    enabled: !!selectedSession,
  });

  // Notifications Query
  const {
    data: notifications,
    isLoading: notificationsLoading,
    refetch: refetchNotifications,
  } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      // Placeholder implementation
      await new Promise(resolve => setTimeout(resolve, 600));
      return [
        {
          id: 'notif_001',
          type: 'mention',
          title: 'You were mentioned',
          message: 'Alice Johnson mentioned you in "Workflow Optimization Review"',
          timestamp: '2024-01-01T10:30:00Z',
          read: false,
          action_url: '/collaboration/session_001'
        },
        {
          id: 'notif_002',
          type: 'invitation',
          title: 'New collaboration invitation',
          message: 'You have been invited to join "AI Model Analysis Session"',
          timestamp: '2024-01-01T10:15:00Z',
          read: true,
          action_url: '/collaboration/session_003'
        }
      ];
    },
  });

  // Mutations
  const createSessionMutation = useMutation({
    mutationFn: (session: Partial<CollaborationSession>) => Promise.resolve(session),
    onSuccess: () => {
      setShowCreateDialog(false);
      refetchSessions();
      refetchStats();
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: (message: Partial<Message>) => Promise.resolve(message),
    onSuccess: () => {
      setCurrentMessage('');
      refetchMessages();
    },
  });

  const inviteParticipantMutation = useMutation({
    mutationFn: (invitation: any) => Promise.resolve(invitation),
    onSuccess: () => {
      setShowInviteDialog(false);
      refetchSessions();
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSendMessage = () => {
    if (!currentMessage.trim() || !selectedSession) return;

    sendMessageMutation.mutate({
      session_id: selectedSession.id,
      sender_id: 'current-user', // Would come from auth context
      sender_name: 'Current User', // Would come from auth context
      content: currentMessage,
      type: 'text',
      timestamp: new Date().toISOString(),
      reactions: [],
      replies: []
    });
  };

  const handleCreateSession = () => {
    createSessionMutation.mutate({
      id: `session_${Date.now()}`,
      name: 'New Collaboration Session',
      type: 'general',
      participants: [],
      status: 'active',
      created_at: new Date().toISOString(),
      last_activity: new Date().toISOString(),
      metadata: {
        total_messages: 0,
        total_participants: 0,
        duration_minutes: 0
      }
    });
  };

  const handleInviteParticipant = (email: string) => {
    inviteParticipantMutation.mutate({
      session_id: selectedSession?.id,
      email,
      role: 'viewer'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'success';
      case 'away':
        return 'warning';
      case 'offline':
        return 'default';
      case 'active':
        return 'primary';
      case 'inactive':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircle sx={{ fontSize: 12 }} />;
      case 'away':
        return <AccessTime sx={{ fontSize: 12 }} />;
      case 'offline':
        return <NotificationsOff sx={{ fontSize: 12 }} />;
      default:
        return null;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'workflow':
        return <Timeline />;
      case 'agent':
        return <SmartToy />;
      case 'analysis':
        return <Assessment />;
      case 'general':
        return <Forum />;
      default:
        return <Group />;
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'mention':
        return <NotificationsActive color="primary" />;
      case 'reply':
        return <Reply color="secondary" />;
      case 'invitation':
        return <PersonAdd color="success" />;
      case 'update':
        return <Edit color="info" />;
      case 'system':
        return <Notifications color="warning" />;
      default:
        return <Notifications />;
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Real-time Collaboration Hub
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Connect, collaborate, and create together in real-time with live features and shared workspaces.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControlLabel
            control={
              <Switch
                checked={notificationsEnabled}
                onChange={(e) => setNotificationsEnabled(e.target.checked)}
              />
            }
            label="Notifications"
          />
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowCreateDialog(true)}
          >
            New Session
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => {
              refetchStats();
              refetchSessions();
              refetchMessages();
              refetchNotifications();
            }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Key Metrics */}
      {collaborationStats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                  {collaborationStats.active_sessions}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Sessions
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                  {collaborationStats.online_participants}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Online Participants
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                  {collaborationStats.total_messages}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Messages
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                  {(collaborationStats.collaboration_efficiency * 100).toFixed(0)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Efficiency
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card elevation={0}>
        <CardContent sx={{ pb: 0 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="collaboration tabs">
            <Tab icon={<Group />} label="Sessions" />
            <Tab icon={<Forum />} label="Messages" />
            <Tab icon={<Notifications />} label="Notifications" />
            <Tab icon={<Assessment />} label="Analytics" />
          </Tabs>
        </CardContent>

        {/* Sessions Tab */}
        <TabPanel value={tabValue} index={0}>
          {sessionsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : collaborationSessions ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Collaboration Sessions ({collaborationSessions.length})
                </Typography>
              </Grid>

              {collaborationSessions.map((session) => (
                <Grid item xs={12} md={6} lg={4} key={session.id}>
                  <Card elevation={1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            {getTypeIcon(session.type)}
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {session.name}
                            </Typography>
                          </Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            {session.type} • {session.metadata.total_participants} participants
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Last activity: {new Date(session.last_activity).toLocaleString()}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                          <Chip
                            label={session.status}
                            color={getStatusColor(session.status) as any}
                          />
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <IconButton size="small" onClick={() => setSelectedSession(session)}>
                              <Visibility />
                            </IconButton>
                            <IconButton size="small" onClick={() => setShowInviteDialog(true)}>
                              <PersonAdd />
                            </IconButton>
                          </Box>
                        </Box>
                      </Box>

                      {/* Participants */}
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Participants:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          {session.participants.slice(0, 3).map((participant) => (
                            <Box key={participant.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Badge
                                overlap="circular"
                                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                                badgeContent={getStatusIcon(participant.status)}
                              >
                                <Avatar sx={{ width: 24, height: 24 }}>
                                  {participant.name.charAt(0)}
                                </Avatar>
                              </Badge>
                              <Typography variant="body2">{participant.name}</Typography>
                            </Box>
                          ))}
                          {session.participants.length > 3 && (
                            <Typography variant="body2" color="text.secondary">
                              +{session.participants.length - 3} more
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      {/* Session Stats */}
                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Session Stats:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          <Chip
                            label={`${session.metadata.total_messages} messages`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${session.metadata.duration_minutes} min`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {collaborationSessions.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <Group sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No collaboration sessions
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Create your first session to start collaborating
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No collaboration sessions available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Messages Tab */}
        <TabPanel value={tabValue} index={1}>
          {selectedSession ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Messages - {selectedSession.name}
                  </Typography>
                  <Button
                    variant="outlined"
                    startIcon={<Message />}
                    onClick={() => setShowMessageDialog(true)}
                  >
                    New Message
                  </Button>
                </Box>
              </Grid>

              <Grid item xs={12} md={8}>
                <Card elevation={1}>
                  <CardContent>
                    {messagesLoading ? (
                      <Box>
                        <Skeleton variant="rectangular" width="100%" height={300} sx={{ borderRadius: 1 }} />
                      </Box>
                    ) : messages ? (
                      <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                        {messages.map((message) => (
                          <Box key={message.id} sx={{ mb: 3 }}>
                            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                              <Avatar sx={{ width: 32, height: 32 }}>
                                {message.sender_name.charAt(0)}
                              </Avatar>
                              <Box sx={{ flex: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                    {message.sender_name}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {new Date(message.timestamp).toLocaleString()}
                                  </Typography>
                                </Box>
                                <Typography variant="body1" sx={{ mb: 1 }}>
                                  {message.content}
                                </Typography>

                                {/* Reactions */}
                                {message.reactions.length > 0 && (
                                  <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                                    {message.reactions.map((reaction) => (
                                      <Chip
                                        key={reaction.emoji}
                                        label={`${reaction.emoji} ${reaction.count}`}
                                        size="small"
                                        variant="outlined"
                                      />
                                    ))}
                                  </Box>
                                )}

                                {/* Replies */}
                                {message.replies.length > 0 && (
                                  <Box sx={{ ml: 4, mt: 1 }}>
                                    {message.replies.map((reply) => (
                                      <Box key={reply.id} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                                        <Avatar sx={{ width: 24, height: 24 }}>
                                          {reply.sender_name.charAt(0)}
                                        </Avatar>
                                        <Box>
                                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                            {reply.sender_name}
                                          </Typography>
                                          <Typography variant="body2" color="text.secondary">
                                            {reply.content}
                                          </Typography>
                                        </Box>
                                      </Box>
                                    ))}
                                  </Box>
                                )}
                              </Box>
                            </Box>
                          </Box>
                        ))}
                      </Box>
                    ) : (
                      <Box sx={{ textAlign: 'center', py: 4 }}>
                        <Typography variant="body1" color="text.secondary">
                          No messages in this session
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card elevation={1}>
                  <CardContent>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                      Participants ({selectedSession.participants.length})
                    </Typography>
                    <List>
                      {selectedSession.participants.map((participant) => (
                        <ListItem key={participant.id}>
                          <ListItemIcon>
                            <Badge
                              overlap="circular"
                              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                              badgeContent={getStatusIcon(participant.status)}
                            >
                              <Avatar>
                                {participant.name.charAt(0)}
                              </Avatar>
                            </Badge>
                          </ListItemIcon>
                          <ListItemText
                            primary={participant.name}
                            secondary={`${participant.role} • ${participant.status}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Forum sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Select a session to view messages
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Choose a collaboration session from the Sessions tab
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Notifications Tab */}
        <TabPanel value={tabValue} index={2}>
          {notificationsLoading ? (
            <Box>
              <Skeleton variant="rectangular" width="100%" height={400} sx={{ borderRadius: 1 }} />
            </Box>
          ) : notifications ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Notifications ({notifications.filter(n => !n.read).length} unread)
                </Typography>
              </Grid>

              {notifications.map((notification) => (
                <Grid item xs={12} key={notification.id}>
                  <Card elevation={notification.read ? 0 : 1}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                        {getNotificationIcon(notification.type)}
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {notification.title}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {new Date(notification.timestamp).toLocaleString()}
                            </Typography>
                          </Box>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            {notification.message}
                          </Typography>
                          {notification.action_url && (
                            <Button size="small" variant="outlined">
                              View
                            </Button>
                          )}
                        </Box>
                        {!notification.read && (
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'primary.main' }} />
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {notifications.length === 0 && (
                <Grid item xs={12}>
                  <Box sx={{ textAlign: 'center', py: 8 }}>
                    <NotificationsNone sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No notifications
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      You're all caught up!
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No notifications available
              </Typography>
            </Box>
          )}
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={1}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                    Collaboration Performance Analytics
                  </Typography>

                  <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Collaboration analytics visualization would be implemented here
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Create Session Dialog */}
      <Dialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Group sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Create Collaboration Session</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Session Name"
                placeholder="Enter session name"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Session Type</InputLabel>
                <Select defaultValue="general">
                  <MenuItem value="general">General Discussion</MenuItem>
                  <MenuItem value="workflow">Workflow Collaboration</MenuItem>
                  <MenuItem value="agent">Agent Development</MenuItem>
                  <MenuItem value="analysis">Data Analysis</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                placeholder="Describe the purpose of this collaboration session"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)}>Cancel</Button>
          <Button
            onClick={handleCreateSession}
            variant="contained"
            disabled={createSessionMutation.isPending}
          >
            {createSessionMutation.isPending ? 'Creating...' : 'Create Session'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Invite Participant Dialog */}
      <Dialog
        open={showInviteDialog}
        onClose={() => setShowInviteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <PersonAdd sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Invite Participant</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Email Address"
                placeholder="user@example.com"
                type="email"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Role</InputLabel>
                <Select defaultValue="viewer">
                  <MenuItem value="viewer">Viewer</MenuItem>
                  <MenuItem value="editor">Editor</MenuItem>
                  <MenuItem value="owner">Owner</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowInviteDialog(false)}>Cancel</Button>
          <Button
            onClick={() => handleInviteParticipant('user@example.com')}
            variant="contained"
            disabled={inviteParticipantMutation.isPending}
          >
            {inviteParticipantMutation.isPending ? 'Inviting...' : 'Send Invitation'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* New Message Dialog */}
      <Dialog
        open={showMessageDialog}
        onClose={() => setShowMessageDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Message sx={{ color: 'primary.main' }} />
            <Typography variant="h6">Send Message</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Message"
                placeholder="Type your message here..."
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowMessageDialog(false)}>Cancel</Button>
          <Button
            onClick={handleSendMessage}
            variant="contained"
            disabled={sendMessageMutation.isPending || !currentMessage.trim()}
            startIcon={<Send />}
          >
            {sendMessageMutation.isPending ? 'Sending...' : 'Send Message'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Collaboration;