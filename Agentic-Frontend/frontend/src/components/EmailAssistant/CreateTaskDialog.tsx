import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Box,
    Typography,
    Chip,
    CircularProgress,
    Alert
} from '@mui/material';
import {
    Assignment as TaskIcon,
    SmartToy as AgentIcon,
    Email as EmailIcon
} from '@mui/icons-material';
import apiClient from '../../services/api';
import type { Agent } from '../../types';

interface CreateTaskDialogProps {
    open: boolean;
    onClose: () => void;
    email: {
        id: string;
        subject: string;
        sender: string;
        body_text?: string;
    } | null;
    onTaskCreated: () => void;
}

export const CreateTaskDialog: React.FC<CreateTaskDialogProps> = ({
    open,
    onClose,
    email,
    onTaskCreated
}) => {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loadingAgents, setLoadingAgents] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [taskDescription, setTaskDescription] = useState('');
    const [selectedAgentId, setSelectedAgentId] = useState('');

    useEffect(() => {
        if (open) {
            fetchAgents();
            if (email) {
                setTaskDescription(`Task from email: ${email.subject}\n\nContext:\nFrom: ${email.sender}\n\n${email.body_text?.substring(0, 200)}...`);
            }
        }
    }, [open, email]);

    const fetchAgents = async () => {
        setLoadingAgents(true);
        try {
            const fetchedAgents = await apiClient.getAgents();
            setAgents(fetchedAgents);
            if (fetchedAgents.length > 0) {
                setSelectedAgentId(fetchedAgents[0].id);
            }
        } catch (err) {
            console.error('Failed to fetch agents:', err);
            setError('Failed to load available agents.');
        } finally {
            setLoadingAgents(false);
        }
    };

    const handleSubmit = async () => {
        if (!selectedAgentId || !taskDescription) return;

        setSubmitting(true);
        setError(null);

        try {
            await apiClient.runTask({
                agent_id: selectedAgentId,
                input: {
                    description: taskDescription,
                    source: 'email_assistant',
                    email_context: email ? {
                        subject: email.subject,
                        sender: email.sender,
                        id: email.id
                    } : undefined
                },
                email_id: email?.id,
                email_sender: email?.sender,
                email_subject: email?.subject
            });

            onTaskCreated();
            onClose();
        } catch (err) {
            console.error('Failed to create task:', err);
            setError('Failed to create task. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TaskIcon color="primary" />
                Create Task from Email
            </DialogTitle>
            <DialogContent dividers>
                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}

                <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Source Email
                    </Typography>
                    <Box sx={{
                        p: 1.5,
                        bgcolor: 'action.hover',
                        borderRadius: 1,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1
                    }}>
                        <EmailIcon fontSize="small" color="action" />
                        <Typography variant="body2" noWrap sx={{ fontWeight: 500 }}>
                            {email?.subject || '(No Subject)'}
                        </Typography>
                    </Box>
                </Box>

                <FormControl fullWidth sx={{ mb: 3 }}>
                    <InputLabel id="agent-select-label">Assign to Agent</InputLabel>
                    <Select
                        labelId="agent-select-label"
                        value={selectedAgentId}
                        label="Assign to Agent"
                        onChange={(e) => setSelectedAgentId(e.target.value)}
                        disabled={loadingAgents}
                        startAdornment={<AgentIcon fontSize="small" sx={{ ml: 1, mr: 0.5, color: 'action.active' }} />}
                    >
                        {loadingAgents ? (
                            <MenuItem disabled>
                                <CircularProgress size={20} sx={{ mr: 1 }} /> Loading agents...
                            </MenuItem>
                        ) : (
                            agents.map((agent) => (
                                <MenuItem key={agent.id} value={agent.id}>
                                    {agent.name}
                                </MenuItem>
                            ))
                        )}
                    </Select>
                </FormControl>

                <TextField
                    fullWidth
                    label="Task Description"
                    multiline
                    rows={4}
                    value={taskDescription}
                    onChange={(e) => setTaskDescription(e.target.value)}
                    placeholder="Describe what the agent should do..."
                    helperText="Provide clear instructions for the AI agent."
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={submitting}>
                    Cancel
                </Button>
                <Button
                    onClick={handleSubmit}
                    variant="contained"
                    disabled={submitting || !selectedAgentId || !taskDescription}
                    startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <TaskIcon />}
                >
                    {submitting ? 'Creating...' : 'Create Task'}
                </Button>
            </DialogActions>
        </Dialog>
    );
};
