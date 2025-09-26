import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Grid,
  Alert
} from '@mui/material';
import {
  Email,
  ExpandMore,
  ExpandLess,
  Person,
  Schedule,
  Task,
  Add,
  Link,
  Star,
  StarBorder
} from '@mui/icons-material';

interface EmailReference {
  email_id: string;
  subject: string;
  sender: string;
  sent_at: string;
  similarity_score: number;
}

interface TaskCreated {
  title: string;
  description: string;
  priority: number;
  estimated_duration: number;
  auto_generated: boolean;
}

interface EmailReferencesProps {
  emailReferences: EmailReference[];
  tasksCreated: TaskCreated[];
  metadata?: any;
}

const EmailReferences: React.FC<EmailReferencesProps> = ({
  emailReferences,
  tasksCreated,
  metadata
}) => {
  const [expandedEmails, setExpandedEmails] = useState(false);
  const [expandedTasks, setExpandedTasks] = useState(false);
  const [showTaskDialog, setShowTaskDialog] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({
    description: '',
    type: 'general',
    priority: 3,
    due_date: ''
  });

  const handleCreateTask = async (emailId: string) => {
    try {
      const response = await fetch('/api/v1/email/tasks/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
          email_id: emailId,
          task_description: newTask.description,
          task_type: newTask.type,
          priority: newTask.priority,
          due_date: newTask.due_date ? new Date(newTask.due_date).toISOString() : undefined
        })
      });

      if (response.ok) {
        setShowTaskDialog(false);
        setNewTask({ description: '', type: 'general', priority: 3, due_date: '' });
        // Show success message or refresh data
      }
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority <= 2) return 'error';
    if (priority === 3) return 'warning';
    return 'success';
  };

  const getPriorityLabel = (priority: number) => {
    if (priority <= 2) return 'High';
    if (priority === 3) return 'Medium';
    return 'Low';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const datePart = date.toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric'
    });
    const timePart = date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
    return `${datePart} ${timePart}`;
  };

  if (emailReferences.length === 0 && tasksCreated.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 2 }}>
      {/* Email References */}
      {emailReferences.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Email color="primary" />
                <Typography variant="h6">
                  Referenced Emails ({emailReferences.length})
                </Typography>
              </Box>
              <IconButton
                onClick={() => setExpandedEmails(!expandedEmails)}
                size="small"
              >
                {expandedEmails ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>

            <Collapse in={expandedEmails}>
              <List dense>
                {emailReferences.map((email, index) => (
                  <React.Fragment key={email.email_id}>
                    <ListItem>
                      <ListItemIcon>
                        <Email />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" fontWeight="bold">
                              {email.subject || 'No Subject'}
                            </Typography>
                            <Chip
                              label={`${(email.similarity_score * 100).toFixed(0)}% match`}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Person fontSize="small" />
                              <Typography variant="caption">{email.sender}</Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Schedule fontSize="small" />
                              <Typography variant="caption">
                                {formatDate(email.sent_at)}
                              </Typography>
                            </Box>
                          </Box>
                        }
                      />
                      <Button
                        size="small"
                        startIcon={<Add />}
                        onClick={() => {
                          setSelectedEmail(email.email_id);
                          setShowTaskDialog(true);
                        }}
                      >
                        Create Task
                      </Button>
                    </ListItem>
                    {index < emailReferences.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Tasks Created */}
      {tasksCreated.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Task color="success" />
                <Typography variant="h6">
                  Tasks Created ({tasksCreated.length})
                </Typography>
              </Box>
              <IconButton
                onClick={() => setExpandedTasks(!expandedTasks)}
                size="small"
              >
                {expandedTasks ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>

            <Collapse in={expandedTasks}>
              <List dense>
                {tasksCreated.map((task, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemIcon>
                        <Task />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" fontWeight="bold">
                              {task.title}
                            </Typography>
                            <Chip
                              label={getPriorityLabel(task.priority)}
                              size="small"
                              color={getPriorityColor(task.priority)}
                            />
                            {task.auto_generated && (
                              <Chip
                                label="AI Generated"
                                size="small"
                                variant="outlined"
                                color="info"
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" display="block">
                              {task.description}
                            </Typography>
                            {task.estimated_duration > 0 && (
                              <Typography variant="caption" color="text.secondary">
                                Estimated: {task.estimated_duration} minutes
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < tasksCreated.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </Collapse>
          </CardContent>
        </Card>
      )}

      {/* Processing Metadata */}
      {metadata && (metadata.emails_searched > 0 || metadata.processing_time_ms) && (
        <Alert severity="info" sx={{ mt: 1 }}>
          <Typography variant="caption">
            {metadata.emails_searched > 0 && `Searched ${metadata.emails_searched} emails. `}
            {metadata.emails_referenced > 0 && `Referenced ${metadata.emails_referenced} emails. `}
            {metadata.processing_time_ms && `Processed in ${metadata.processing_time_ms}ms.`}
          </Typography>
        </Alert>
      )}

      {/* Create Task Dialog */}
      <Dialog
        open={showTaskDialog}
        onClose={() => setShowTaskDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create Task from Email</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                label="Task Description"
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                fullWidth
                multiline
                rows={3}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                select
                label="Task Type"
                value={newTask.type}
                onChange={(e) => setNewTask({ ...newTask, type: e.target.value })}
                fullWidth
              >
                <MenuItem value="general">General</MenuItem>
                <MenuItem value="follow_up">Follow Up</MenuItem>
                <MenuItem value="meeting">Meeting</MenuItem>
                <MenuItem value="review">Review</MenuItem>
                <MenuItem value="research">Research</MenuItem>
                <MenuItem value="action_required">Action Required</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                select
                label="Priority"
                value={newTask.priority}
                onChange={(e) => setNewTask({ ...newTask, priority: parseInt(e.target.value) })}
                fullWidth
              >
                <MenuItem value={1}>High Priority</MenuItem>
                <MenuItem value={2}>High</MenuItem>
                <MenuItem value={3}>Medium</MenuItem>
                <MenuItem value={4}>Low</MenuItem>
                <MenuItem value={5}>Low Priority</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                type="datetime-local"
                label="Due Date (Optional)"
                value={newTask.due_date}
                onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTaskDialog(false)}>Cancel</Button>
          <Button
            onClick={() => selectedEmail && handleCreateTask(selectedEmail)}
            variant="contained"
            disabled={!newTask.description.trim()}
          >
            Create Task
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EmailReferences;