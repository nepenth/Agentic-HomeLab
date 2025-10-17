import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  TextField,
  InputAdornment,
  IconButton,
  Button,
  Chip,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Menu,
  MenuItem,
  FormControl,
  Select,
  Checkbox,
  FormControlLabel,
  useTheme,
  alpha,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  MoreVert as MoreIcon,
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  AttachFile as AttachFileIcon,
  TaskAlt as TaskAltIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  Markunread as MarkunreadIcon,
  MarkEmailRead as MarkEmailReadIcon,
  Circle as CircleIcon,
  Reply as ReplyIcon,
  Delete as DeleteIcon,
  Drafts as DraftsIcon,
  Flag as FlagIcon,
} from '@mui/icons-material';
import { useEmail } from '../../../hooks/useEmail';
import { useTasks } from '../../../hooks/useTasks';
import { formatDistanceToNow } from 'date-fns';
import { FolderSidebar } from '../FolderSidebar';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../services/api';

interface InboxTasksTabProps {
  filters?: any;
  onFiltersChange?: (filters: any) => void;
}

export const InboxTasksTab: React.FC<InboxTasksTabProps> = ({ filters: externalFilters, onFiltersChange }) => {
  const theme = useTheme();
  const {
    emails,
    selectedEmail,
    setSelectedEmail,
    filters,
    setFilters,
    sort,
    setSort,
    searchEmails,
    markAsRead,
    markAsImportant,
    deleteEmail,
    fetchEmailDetail,
    refetchEmails,
    isFetchingDetail,
  } = useEmail();

  // Helper function to decode HTML entities if needed
  const decodeHtml = (html: string): string => {
    if (!html) return '';
    const txt = document.createElement('textarea');
    txt.innerHTML = html;
    return txt.value;
  };

  const {
    tasks,
    selectedTask,
    setSelectedTask,
    filters: taskFilters,
    setFilters: setTaskFilters,
    groupBy,
    setGroupBy,
    completeTask,
    dismissTask,
    createTask,
    refetchTasks,
  } = useTasks();

  const [view, setView] = useState<'emails' | 'tasks'>('emails');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(null);
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>('INBOX');
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);

  // Fetch email accounts to get the first account ID
  const { data: emailAccounts } = useQuery({
    queryKey: ['email-accounts'],
    queryFn: async () => {
      return await apiClient.getEmailAccounts();
    }
  });

  // Set the first account as selected if none is selected
  React.useEffect(() => {
    if (emailAccounts && emailAccounts.accounts && emailAccounts.accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(emailAccounts.accounts[0].id);
    }
  }, [emailAccounts, selectedAccountId]);

  // Apply folder filter when selected folder changes
  React.useEffect(() => {
    if (selectedFolder) {
      setFilters({ ...filters, folder_path: selectedFolder });
    }
  }, [selectedFolder]);

  // Apply external filters from navigation (e.g., from Overview metric cards)
  React.useEffect(() => {
    if (externalFilters) {
      // Switch view if specified
      if (externalFilters.view) {
        setView(externalFilters.view);
      }

      // Handle direct email selection (from Assistant tab)
      if (externalFilters.selectedEmailId) {
        const email = emails.find(e => e.email_id === externalFilters.selectedEmailId);
        if (email) {
          handleEmailSelect(email);

          // Scroll to email if requested
          if (externalFilters.scrollToEmail) {
            setTimeout(() => {
              const emailElement = document.getElementById(`email-${externalFilters.selectedEmailId}`);
              if (emailElement) {
                emailElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Add temporary highlight effect
                emailElement.style.backgroundColor = alpha(theme.palette.primary.main, 0.1);
                setTimeout(() => {
                  emailElement.style.backgroundColor = '';
                }, 2000);
              }
            }, 100);
          }
        }
      }

      // Apply filter based on type
      if (externalFilters.filter) {
        switch (externalFilters.filter) {
          case 'unread':
            setFilters({ ...filters, unread: true, important: false, hasAttachments: false });
            break;
          case 'high_priority':
            setFilters({ ...filters, important: true, unread: false, hasAttachments: false });
            break;
          case 'all':
            setFilters({ unread: false, important: false, hasAttachments: false });
            break;
          case 'today':
            setFilters({ ...filters, today: true, unread: false, important: false, hasAttachments: false });
            break;
          case 'pending_tasks':
            setTaskFilters({ ...taskFilters, status: 'pending' });
            break;
          case 'completed':
            setTaskFilters({ ...taskFilters, status: 'completed' });
            break;
          default:
            break;
        }
      }

      // Clear external filters after applying
      if (onFiltersChange) {
        onFiltersChange(null);
      }
    }
  }, [externalFilters]);

  const handleSearchSubmit = () => {
    if (searchQuery.trim()) {
      searchEmails({ query: searchQuery });
    }
  };

  const handleFilterClick = (event: React.MouseEvent<HTMLElement>) => {
    setFilterAnchorEl(event.currentTarget);
  };

  const handleSortClick = (event: React.MouseEvent<HTMLElement>) => {
    setSortAnchorEl(event.currentTarget);
  };

  const handleEmailSelect = (email: any) => {
    // Fetch full email details including body
    console.log('Fetching email details for:', email.email_id);
    fetchEmailDetail(email.email_id);
    setSelectedTask(null);
    if (!email.is_read) {
      markAsRead(email.email_id);
    }
  };

  // Debug log when selectedEmail changes
  React.useEffect(() => {
    if (selectedEmail) {
      console.log('Selected email data:', {
        has_body_html: !!selectedEmail.body_html,
        body_html_length: selectedEmail.body_html?.length,
        body_html_preview: selectedEmail.body_html?.substring(0, 200),
        has_body_text: !!selectedEmail.body_text,
        body_text_length: selectedEmail.body_text?.length,
      });
    }
  }, [selectedEmail]);

  const handleTaskSelect = (task: any) => {
    setSelectedTask(task);
    setSelectedEmail(null);
  };

  const handleCreateTaskFromEmail = () => {
    if (selectedEmail) {
      createTask({
        emailId: selectedEmail.email_id,
        taskData: {
          title: `Follow up: ${selectedEmail.subject}`,
          description: selectedEmail.body_text.substring(0, 200),
          priority: 'medium',
          status: 'pending',
        },
      });
    }
  };

  const toggleItemSelection = (id: string) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header with Search and Controls */}
      <Paper sx={{ p: 2, mb: 2, flexShrink: 0 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
          <TextField
            fullWidth
            placeholder="Search emails or use semantic search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearchSubmit()}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchQuery('')}>
                    <CloseIcon />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={handleSearchSubmit}
            disabled={!searchQuery.trim()}
          >
            Search
          </Button>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* View Toggle */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant={view === 'emails' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => setView('emails')}
            >
              Emails ({emails.length})
            </Button>
            <Button
              variant={view === 'tasks' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => setView('tasks')}
            >
              Tasks ({tasks.length})
            </Button>
          </Box>

          {/* Filter and Sort */}
          <IconButton onClick={handleFilterClick}>
            <Badge badgeContent={Object.values(filters).filter(Boolean).length} color="primary">
              <FilterIcon />
            </Badge>
          </IconButton>
          <IconButton onClick={handleSortClick}>
            <SortIcon />
          </IconButton>

          {/* Action Buttons */}
          <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
            {view === 'emails' && selectedEmail && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<TaskAltIcon />}
                onClick={handleCreateTaskFromEmail}
              >
                Create Task
              </Button>
            )}
            <IconButton onClick={() => view === 'emails' ? refetchEmails() : refetchTasks()}>
              <RefreshIcon />
            </IconButton>
          </Box>

          {/* Bulk Actions */}
          {selectedItems.length > 0 && (
            <Chip
              label={`${selectedItems.length} selected`}
              onDelete={() => setSelectedItems([])}
              color="primary"
            />
          )}
        </Box>
      </Paper>

      {/* Main Content - Split View */}
      <Grid container spacing={2} sx={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        {/* Folder Sidebar (only for emails view) */}
        {view === 'emails' && (
          <Grid item xs={12} md={2} sx={{ height: '100%', display: { xs: 'none', md: 'flex' }, minHeight: 0 }}>
            <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, width: '100%' }}>
              <FolderSidebar
                accountId={selectedAccountId}
                selectedFolder={selectedFolder}
                onFolderSelect={setSelectedFolder}
              />
            </Paper>
          </Grid>
        )}

        {/* Middle Panel - Email/Task List */}
        <Grid item xs={12} md={view === 'emails' ? 4 : 5} sx={{ height: '100%', display: 'flex', minHeight: 0 }}>
          <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, width: '100%' }}>
            <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}`, flexShrink: 0 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {view === 'emails' ? (selectedFolder || 'Inbox') : 'Tasks'}
              </Typography>
            </Box>

            <List sx={{ flex: 1, overflow: 'auto', p: 0, minHeight: 0 }}>
              {view === 'emails' ? (
                emails.length > 0 ? (
                  emails.map((email) => (
                    <React.Fragment key={email.email_id}>
                      <ListItemButton
                        id={`email-${email.email_id}`}
                        selected={selectedEmail?.email_id === email.email_id}
                        onClick={() => handleEmailSelect(email)}
                        sx={{
                          bgcolor: !email.is_read ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
                          transition: 'background-color 0.3s ease',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', width: '100%', gap: 1 }}>
                          <Checkbox
                            checked={selectedItems.includes(email.email_id)}
                            onChange={() => toggleItemSelection(email.email_id)}
                            onClick={(e) => e.stopPropagation()}
                            size="small"
                          />
                          {!email.is_read && (
                            <CircleIcon
                              sx={{
                                fontSize: 10,
                                color: theme.palette.primary.main,
                                mt: 1,
                                flexShrink: 0
                              }}
                            />
                          )}
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, minWidth: 0 }}>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontWeight: !email.is_read ? 700 : 400,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {email.sender_name || email.sender_email}
                                </Typography>
                              </Box>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                                <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                                  {formatDistanceToNow(new Date(email.sent_at || email.received_at), { addSuffix: true })}
                                </Typography>
                                <Tooltip title={email.is_read ? 'Mark as unread' : 'Mark as read'}>
                                  <IconButton
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      markAsRead(email.email_id);
                                    }}
                                    sx={{ ml: 0.5 }}
                                  >
                                    {email.is_read ? <MarkunreadIcon fontSize="small" /> : <MarkEmailReadIcon fontSize="small" />}
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            </Box>
                            <Typography
                              variant="body2"
                              sx={{
                                fontWeight: !email.is_read ? 600 : 400,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                mb: 0.5,
                              }}
                            >
                              {email.subject}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                color: theme.palette.text.secondary,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                              }}
                            >
                              {email.body_text}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
                              {/* RFC 3501 Standard Flags */}
                              {email.is_flagged && (
                                <Chip
                                  icon={<FlagIcon sx={{ fontSize: 14 }} />}
                                  label="Flagged"
                                  size="small"
                                  color="warning"
                                  sx={{ height: 18, fontSize: '0.65rem' }}
                                />
                              )}
                              {email.is_draft && (
                                <Chip
                                  icon={<DraftsIcon sx={{ fontSize: 14 }} />}
                                  label="Draft"
                                  size="small"
                                  sx={{ height: 18, fontSize: '0.65rem', backgroundColor: '#9E9E9E', color: 'white' }}
                                />
                              )}
                              {email.is_answered && (
                                <Chip
                                  icon={<ReplyIcon sx={{ fontSize: 14 }} />}
                                  label="Replied"
                                  size="small"
                                  color="success"
                                  sx={{ height: 18, fontSize: '0.65rem' }}
                                />
                              )}
                              {email.is_deleted && (
                                <Chip
                                  icon={<DeleteIcon sx={{ fontSize: 14 }} />}
                                  label="Deleted"
                                  size="small"
                                  color="error"
                                  sx={{ height: 18, fontSize: '0.65rem' }}
                                />
                              )}
                              {/* Additional Flags */}
                              {email.is_important && (
                                <Chip label="Important" size="small" color="error" sx={{ height: 18, fontSize: '0.65rem' }} />
                              )}
                              {email.is_spam && (
                                <Chip label="Spam" size="small" sx={{ height: 18, fontSize: '0.65rem', backgroundColor: '#FF6B6B', color: 'white' }} />
                              )}
                              {/* Attachments */}
                              {email.has_attachments && (
                                <Chip
                                  icon={<AttachFileIcon sx={{ fontSize: 14 }} />}
                                  label={`${email.attachment_count || ''} Attachment${email.attachment_count > 1 ? 's' : ''}`}
                                  size="small"
                                  sx={{ height: 18, fontSize: '0.65rem' }}
                                />
                              )}
                              {/* Category */}
                              {email.category && (
                                <Chip label={email.category} size="small" sx={{ height: 18, fontSize: '0.65rem' }} />
                              )}
                            </Box>
                          </Box>
                        </Box>
                      </ListItemButton>
                      <Divider />
                    </React.Fragment>
                  ))
                ) : (
                  <Box sx={{ p: 4, textAlign: 'center' }}>
                    <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                      No emails found
                    </Typography>
                  </Box>
                )
              ) : (
                tasks.length > 0 ? (
                  tasks.map((task) => (
                    <React.Fragment key={task.id}>
                      <ListItemButton
                        selected={selectedTask?.id === task.id}
                        onClick={() => handleTaskSelect(task)}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', width: '100%', gap: 1 }}>
                          <Checkbox
                            checked={selectedItems.includes(task.id)}
                            onChange={() => toggleItemSelection(task.id)}
                            onClick={(e) => e.stopPropagation()}
                            size="small"
                          />
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {task.title}
                              </Typography>
                              <Chip
                                label={task.priority}
                                size="small"
                                color={
                                  task.priority === 'high' ? 'error' :
                                  task.priority === 'medium' ? 'warning' :
                                  'default'
                                }
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                            </Box>
                            <Typography
                              variant="caption"
                              sx={{
                                color: theme.palette.text.secondary,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                              }}
                            >
                              {task.description}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 0.5, mt: 1, alignItems: 'center' }}>
                              <Chip
                                label={task.status}
                                size="small"
                                color={task.status === 'completed' ? 'success' : 'default'}
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                              {task.due_date && (
                                <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                                  Due: {new Date(task.due_date).toLocaleDateString()}
                                </Typography>
                              )}
                            </Box>
                          </Box>
                        </Box>
                      </ListItemButton>
                      <Divider />
                    </React.Fragment>
                  ))
                ) : (
                  <Box sx={{ p: 4, textAlign: 'center' }}>
                    <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                      No tasks found
                    </Typography>
                  </Box>
                )
              )}
            </List>
          </Paper>
        </Grid>

        {/* Right Panel - Detail View */}
        <Grid item xs={12} md={view === 'emails' ? 6 : 7} sx={{ height: '100%', display: 'flex', minHeight: 0 }}>
          <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, width: '100%' }}>
            {selectedEmail ? (
              <>
                {/* Email Detail Header */}
                <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}`, flexShrink: 0 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, flex: 1 }}>
                      {selectedEmail.subject}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Tooltip title={selectedEmail.is_important ? 'Remove star' : 'Add star'}>
                        <IconButton
                          size="small"
                          onClick={() => markAsImportant({ emailId: selectedEmail.email_id, important: !selectedEmail.is_important })}
                        >
                          {selectedEmail.is_important ? <StarIcon color="warning" /> : <StarBorderIcon />}
                        </IconButton>
                      </Tooltip>
                      <IconButton size="small">
                        <MoreIcon />
                      </IconButton>
                    </Box>
                  </Box>
                  <Box>
                    {/* From */}
                    <Box sx={{ mb: 1 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.text.secondary, mr: 1 }}>
                        From:
                      </Typography>
                      <Typography variant="body2" component="span" sx={{ fontWeight: 600 }}>
                        {selectedEmail.sender_name || selectedEmail.sender_email}
                      </Typography>
                      {selectedEmail.sender_name && (
                        <Typography variant="caption" component="span" sx={{ color: theme.palette.text.secondary, ml: 1 }}>
                          &lt;{selectedEmail.sender_email}&gt;
                        </Typography>
                      )}
                    </Box>

                    {/* To */}
                    {selectedEmail.to_recipients && selectedEmail.to_recipients.length > 0 && (
                      <Box sx={{ mb: 0.5 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.text.secondary, mr: 1 }}>
                          To:
                        </Typography>
                        <Typography variant="caption" component="span">
                          {selectedEmail.to_recipients.map((r: any, i: number) => (
                            <span key={i}>
                              {i > 0 && ', '}
                              {r.name || r.email}
                              {r.name && <span style={{ color: theme.palette.text.secondary }}> &lt;{r.email}&gt;</span>}
                            </span>
                          ))}
                        </Typography>
                      </Box>
                    )}

                    {/* CC */}
                    {selectedEmail.cc_recipients && selectedEmail.cc_recipients.length > 0 && (
                      <Box sx={{ mb: 0.5 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.text.secondary, mr: 1 }}>
                          CC:
                        </Typography>
                        <Typography variant="caption" component="span">
                          {selectedEmail.cc_recipients.map((r: any, i: number) => (
                            <span key={i}>
                              {i > 0 && ', '}
                              {r.name || r.email}
                              {r.name && <span style={{ color: theme.palette.text.secondary }}> &lt;{r.email}&gt;</span>}
                            </span>
                          ))}
                        </Typography>
                      </Box>
                    )}

                    {/* BCC */}
                    {selectedEmail.bcc_recipients && selectedEmail.bcc_recipients.length > 0 && (
                      <Box sx={{ mb: 0.5 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.text.secondary, mr: 1 }}>
                          BCC:
                        </Typography>
                        <Typography variant="caption" component="span">
                          {selectedEmail.bcc_recipients.map((r: any, i: number) => (
                            <span key={i}>
                              {i > 0 && ', '}
                              {r.name || r.email}
                              {r.name && <span style={{ color: theme.palette.text.secondary }}> &lt;{r.email}&gt;</span>}
                            </span>
                          ))}
                        </Typography>
                      </Box>
                    )}

                    {/* Timestamp */}
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                        {new Date(selectedEmail.sent_at || selectedEmail.received_at).toLocaleString()}
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                {/* Email Content */}
                <Box sx={{ flex: 1, overflow: 'auto', p: 3, minHeight: 0 }}>
                  {isFetchingDetail ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                      <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                        Loading email content...
                      </Typography>
                    </Box>
                  ) : selectedEmail.body_html ? (
                    <Box
                      sx={{
                        '& img': {
                          maxWidth: '100%',
                          height: 'auto',
                        },
                        '& a': {
                          color: theme.palette.primary.main,
                          textDecoration: 'underline',
                        },
                        '& table': {
                          maxWidth: '100%',
                          borderCollapse: 'collapse',
                        },
                        '& td, & th': {
                          padding: '8px',
                        },
                        '& p': {
                          margin: '0.5em 0',
                        },
                        '& blockquote': {
                          borderLeft: `3px solid ${theme.palette.divider}`,
                          paddingLeft: '1em',
                          marginLeft: 0,
                          color: theme.palette.text.secondary,
                        },
                        wordWrap: 'break-word',
                        overflowWrap: 'break-word',
                        fontSize: '14px',
                        lineHeight: 1.6,
                      }}
                      dangerouslySetInnerHTML={{ __html: decodeHtml(selectedEmail.body_html) }}
                    />
                  ) : selectedEmail.body_text ? (
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {selectedEmail.body_text}
                    </Typography>
                  ) : (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                      <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                        No content available
                      </Typography>
                    </Box>
                  )}
                </Box>

                {/* Email Actions */}
                <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}`, display: 'flex', gap: 1, flexShrink: 0 }}>
                  <Button variant="outlined" onClick={handleCreateTaskFromEmail} startIcon={<TaskAltIcon />}>
                    Create Task
                  </Button>
                  <Button variant="outlined" color="error" onClick={() => deleteEmail(selectedEmail.email_id)}>
                    Delete
                  </Button>
                </Box>
              </>
            ) : selectedTask ? (
              <>
                {/* Task Detail Header */}
                <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}`, flexShrink: 0 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, flex: 1 }}>
                      {selectedTask.title}
                    </Typography>
                    <Chip
                      label={selectedTask.priority.toUpperCase()}
                      size="small"
                      color={
                        selectedTask.priority === 'high' ? 'error' :
                        selectedTask.priority === 'medium' ? 'warning' :
                        'default'
                      }
                    />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={selectedTask.status} size="small" />
                    {selectedTask.due_date && (
                      <Chip
                        label={`Due: ${new Date(selectedTask.due_date).toLocaleDateString()}`}
                        size="small"
                        color={new Date(selectedTask.due_date) < new Date() ? 'error' : 'default'}
                      />
                    )}
                    {selectedTask.estimated_time && (
                      <Chip label={`Est: ${selectedTask.estimated_time}`} size="small" />
                    )}
                  </Box>
                </Box>

                {/* Task Content */}
                <Box sx={{ flex: 1, overflow: 'auto', p: 3, minHeight: 0 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Description
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 3, whiteSpace: 'pre-wrap' }}>
                    {selectedTask.description}
                  </Typography>

                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Related Email
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {selectedTask.email_subject}
                    </Typography>
                    <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                      From: {selectedTask.sender_name} ({selectedTask.sender_email})
                    </Typography>
                  </Paper>

                  {selectedTask.suggested_actions && selectedTask.suggested_actions.length > 0 && (
                    <>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                        Suggested Actions
                      </Typography>
                      <List dense>
                        {selectedTask.suggested_actions.map((action, index) => (
                          <ListItem key={index}>
                            <ListItemText primary={action} />
                          </ListItem>
                        ))}
                      </List>
                    </>
                  )}
                </Box>

                {/* Task Actions */}
                <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}`, display: 'flex', gap: 1, flexShrink: 0 }}>
                  {selectedTask.status !== 'completed' && (
                    <Button
                      variant="contained"
                      color="success"
                      onClick={() => completeTask(selectedTask.id)}
                      startIcon={<CheckCircleIcon />}
                    >
                      Complete
                    </Button>
                  )}
                  {selectedTask.status !== 'dismissed' && (
                    <Button variant="outlined" onClick={() => dismissTask(selectedTask.id)}>
                      Dismiss
                    </Button>
                  )}
                </Box>
              </>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
                  Select an {view === 'emails' ? 'email' : 'task'} to view details
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterAnchorEl}
        open={Boolean(filterAnchorEl)}
        onClose={() => setFilterAnchorEl(null)}
      >
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
            label="With attachments"
          />
        </MenuItem>
      </Menu>

      {/* Sort Menu */}
      <Menu
        anchorEl={sortAnchorEl}
        open={Boolean(sortAnchorEl)}
        onClose={() => setSortAnchorEl(null)}
      >
        <MenuItem onClick={() => { setSort({ field: 'received_at', direction: 'desc' }); setSortAnchorEl(null); }}>
          Newest first
        </MenuItem>
        <MenuItem onClick={() => { setSort({ field: 'received_at', direction: 'asc' }); setSortAnchorEl(null); }}>
          Oldest first
        </MenuItem>
        <MenuItem onClick={() => { setSort({ field: 'sender_name', direction: 'asc' }); setSortAnchorEl(null); }}>
          Sender A-Z
        </MenuItem>
        <MenuItem onClick={() => { setSort({ field: 'importance_score', direction: 'desc' }); setSortAnchorEl(null); }}>
          Importance
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default InboxTasksTab;
