import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Chip,
  IconButton,
  Divider,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Send,
  SmartToy,
  Person,
  ExpandMore,
  Psychology,
  Search,
  Article,
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import apiClient from '../services/api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{
    id: string;
    title: string;
    relevance_score: number;
    excerpt?: string;
  }>;
  metadata?: any;
}

interface KnowledgeBaseChatProps {
  initialQuery?: string;
  onMessageSent?: (message: ChatMessage) => void;
}

const KnowledgeBaseChat: React.FC<KnowledgeBaseChatProps> = ({
  initialQuery,
  onMessageSent,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState(initialQuery || '');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Chat mutation
  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      // First, search the knowledge base for relevant content
      const searchResults = await apiClient.searchKnowledgeBase({
        query: message,
        limit: 5,
        search_type: 'semantic',
      });

      // Then send to chat API with context
      const chatResponse = await apiClient.sendChatMessage('knowledge-base-session', {
        message,
        context: {
          knowledge_base_results: searchResults.results || [],
          mode: 'knowledge_base_assistant',
        },
      });

      return {
        searchResults: searchResults.results || [],
        chatResponse,
      };
    },
    onSuccess: (data) => {
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.chatResponse.response,
        timestamp: new Date(),
        sources: data.searchResults.map((result: any) => ({
          id: result.id,
          title: result.title,
          relevance_score: result.relevance_score,
          excerpt: result.summary || result.content?.substring(0, 200) + '...',
        })),
        metadata: data.chatResponse.performance_metrics,
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);

      if (onMessageSent) {
        onMessageSent(assistantMessage);
      }
    },
    onError: (error) => {
      console.error('Chat error:', error);
      setIsTyping(false);

      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    },
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle initial query
  useEffect(() => {
    if (initialQuery && messages.length === 0) {
      handleSendMessage();
    }
  }, [initialQuery]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isTyping) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    if (onMessageSent) {
      onMessageSent(userMessage);
    }

    // Send to API
    chatMutation.mutate(inputMessage.trim());
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Chat Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Psychology color="primary" />
          <Typography variant="h6">
            Knowledge Base Assistant
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Ask questions about your knowledge base. I'll search through your content and provide relevant answers.
        </Typography>
      </Paper>

      {/* Messages Area */}
      <Box sx={{ flex: 1, overflow: 'auto', mb: 2, minHeight: 400 }}>
        {messages.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <SmartToy sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Start a conversation
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ask me anything about your knowledge base content
            </Typography>
          </Box>
        ) : (
          <List>
            {messages.map((message, index) => (
              <React.Fragment key={message.id}>
                <ListItem sx={{ alignItems: 'flex-start' }}>
                  <ListItemAvatar>
                    <Avatar sx={{
                      bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main'
                    }}>
                      {message.role === 'user' ? <Person /> : <SmartToy />}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Typography variant="subtitle2">
                          {message.role === 'user' ? 'You' : 'Knowledge Assistant'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatTimestamp(message.timestamp)}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                          {message.content}
                        </Typography>

                        {/* Sources for assistant messages */}
                        {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Search fontSize="small" />
                              Sources ({message.sources.length})
                            </Typography>

                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                              {message.sources.map((source, sourceIndex) => (
                                <Chip
                                  key={sourceIndex}
                                  label={`${source.title} (${(source.relevance_score * 100).toFixed(0)}%)`}
                                  size="small"
                                  color={getRelevanceColor(source.relevance_score) as any}
                                  variant="outlined"
                                  icon={<Article />}
                                />
                              ))}
                            </Box>

                            {/* Expandable source details */}
                            <Accordion sx={{ mt: 1 }}>
                              <AccordionSummary expandIcon={<ExpandMore />}>
                                <Typography variant="caption">
                                  View source details
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                {message.sources.map((source, sourceIndex) => (
                                  <Box key={sourceIndex} sx={{ mb: 2 }}>
                                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                      {source.title}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      Relevance: {(source.relevance_score * 100).toFixed(1)}%
                                    </Typography>
                                    {source.excerpt && (
                                      <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                                        "{source.excerpt}"
                                      </Typography>
                                    )}
                                  </Box>
                                ))}
                              </AccordionDetails>
                            </Accordion>
                          </Box>
                        )}

                        {/* Performance metrics for assistant messages */}
                        {message.role === 'assistant' && message.metadata && (
                          <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid #e0e0e0' }}>
                            <Typography variant="caption" color="text.secondary">
                              Response time: {message.metadata.response_time_seconds?.toFixed(2)}s •
                              Tokens: {message.metadata.total_tokens}
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < messages.length - 1 && <Divider />}
              </React.Fragment>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <ListItem>
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: 'secondary.main' }}>
                    <SmartToy />
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary="Knowledge Assistant is thinking..."
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={16} />
                      <Typography variant="caption" color="text.secondary">
                        Searching knowledge base...
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            )}

            <div ref={messagesEndRef} />
          </List>
        )}
      </Box>

      {/* Input Area */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your knowledge base..."
            disabled={isTyping}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />
          <Button
            variant="contained"
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isTyping}
            sx={{ minWidth: 60, borderRadius: 2 }}
          >
            <Send />
          </Button>
        </Box>

        <Box sx={{ mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Press Enter to send, Shift+Enter for new line
          </Typography>
        </Box>
      </Paper>

      {/* Error Alert */}
      {chatMutation.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to send message. Please check your connection and try again.
        </Alert>
      )}
    </Box>
  );
};

export default KnowledgeBaseChat;