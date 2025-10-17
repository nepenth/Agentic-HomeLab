import React, { useState } from 'react';
import {
  Paper,
  TextField,
  IconButton,
  Box,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Chip,
  useTheme,
  alpha,
} from '@mui/material';
import { Send as SendIcon, Close as CloseIcon } from '@mui/icons-material';
import { useAssistant } from '../../../hooks/useAssistant';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../services/api';
import ReactMarkdown from 'react-markdown';

export const QuickChat: React.FC = () => {
  const theme = useTheme();
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { selectedModel, updateModel } = useAssistant();

  // Fetch available models
  const { data: modelsData } = useQuery({
    queryKey: ['chat-models'],
    queryFn: async () => {
      const response = await apiClient.getChatModels();
      return response;
    },
    staleTime: 5 * 60 * 1000,
  });

  const availableModels = modelsData?.models || [];

  const handleSend = async () => {
    if (!message.trim() || isLoading) return;

    setIsLoading(true);
    try {
      // Create a quick session for this message
      const sessionResponse = await apiClient.post('/api/v1/email-assistant/sessions', {
        title: 'Quick Chat',
        model_name: selectedModel || availableModels[0],
      });

      const sessionId = sessionResponse.data.id;

      // Send message
      const messageResponse = await apiClient.post(
        `/api/v1/email-assistant/sessions/${sessionId}/chat`,
        {
          message,
          model_name: selectedModel || availableModels[0],
        }
      );

      setResponse(messageResponse.data.message.content);
      setMessage('');
    } catch (error: any) {
      console.error('Quick chat error:', error);
      setResponse('Error: Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Paper
      sx={{
        p: 2,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 2,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
          Quick Chat
        </Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel sx={{ fontSize: '0.875rem' }}>Model</InputLabel>
          <Select
            value={selectedModel || (availableModels[0] || '')}
            onChange={(e) => updateModel(e.target.value)}
            label="Model"
            sx={{ fontSize: '0.875rem' }}
          >
            {availableModels.map((model: string) => (
              <MenuItem key={model} value={model} sx={{ fontSize: '0.875rem' }}>
                {model}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {response && (
        <Paper
          variant="outlined"
          sx={{
            p: 2,
            mb: 2,
            minHeight: 200,
            maxHeight: 500,
            overflow: 'auto',
            bgcolor: alpha(theme.palette.grey[500], 0.03),
            position: 'relative',
          }}
        >
          <IconButton
            size="small"
            onClick={() => setResponse('')}
            sx={{
              position: 'absolute',
              top: 4,
              right: 4,
              bgcolor: 'background.paper',
              '&:hover': {
                bgcolor: alpha(theme.palette.error.main, 0.1),
              },
            }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
          <Box sx={{ '& p:last-child': { mb: 0 }, fontSize: '0.875rem' }}>
            <ReactMarkdown>{response}</ReactMarkdown>
          </Box>
        </Paper>
      )}

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Ask a quick question about your emails..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          multiline
          maxRows={3}
          disabled={isLoading}
          sx={{
            '& .MuiInputBase-input': {
              fontSize: '0.875rem',
            },
          }}
        />
        <IconButton
          color="primary"
          onClick={handleSend}
          disabled={isLoading || !message.trim()}
          sx={{
            bgcolor: isLoading || !message.trim() ? 'transparent' : alpha(theme.palette.primary.main, 0.1),
            '&:hover': {
              bgcolor: alpha(theme.palette.primary.main, 0.2),
            },
          }}
        >
          {isLoading ? <CircularProgress size={24} /> : <SendIcon />}
        </IconButton>
      </Box>

      <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
        {['Summarize unread', 'Find urgent emails', 'Show today\'s tasks'].map((prompt) => (
          <Chip
            key={prompt}
            label={prompt}
            size="small"
            onClick={() => setMessage(prompt)}
            sx={{
              fontSize: '0.7rem',
              height: 22,
              cursor: 'pointer',
              '&:hover': {
                bgcolor: alpha(theme.palette.primary.main, 0.1),
              },
            }}
          />
        ))}
      </Box>
    </Paper>
  );
};

export default QuickChat;
