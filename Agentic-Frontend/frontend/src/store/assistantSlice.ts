import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    model?: string;
    generation_time?: number;
    thinking_content?: string;
    actions_performed?: any[];
    email_references?: any[];
    task_suggestions?: any[];
  };
}

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  model_name: string;
}

interface AssistantState {
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  messages: Message[];
  selectedModel: string;
  isStreaming: boolean;
  streamingEnabled: boolean;
  quickActions: any[];
  context: {
    currentEmail?: string;
    currentTask?: string;
    lastSearch?: string;
  };
  loading: boolean;
  error: string | null;
}

const initialState: AssistantState = {
  currentSession: null,
  sessions: [],
  messages: [],
  selectedModel: 'qwen3:30b-a3b-thinking-2507-q8_0',
  isStreaming: false,
  streamingEnabled: true,
  quickActions: [],
  context: {},
  loading: false,
  error: null,
};

const assistantSlice = createSlice({
  name: 'assistant',
  initialState,
  reducers: {
    setCurrentSession(state, action: PayloadAction<ChatSession | null>) {
      state.currentSession = action.payload;
    },
    setSessions(state, action: PayloadAction<ChatSession[]>) {
      state.sessions = action.payload;
    },
    addSession(state, action: PayloadAction<ChatSession>) {
      state.sessions.unshift(action.payload);
    },
    removeSession(state, action: PayloadAction<string>) {
      state.sessions = state.sessions.filter(s => s.id !== action.payload);
      if (state.currentSession?.id === action.payload) {
        state.currentSession = null;
        state.messages = [];
      }
    },
    setMessages(state, action: PayloadAction<Message[]>) {
      state.messages = action.payload;
    },
    addMessage(state, action: PayloadAction<Message>) {
      state.messages.push(action.payload);
    },
    updateLastMessage(state, action: PayloadAction<Partial<Message>>) {
      if (state.messages.length > 0) {
        const lastMessage = state.messages[state.messages.length - 1];
        state.messages[state.messages.length - 1] = { ...lastMessage, ...action.payload };
      }
    },
    clearMessages(state) {
      state.messages = [];
    },
    setSelectedModel(state, action: PayloadAction<string>) {
      state.selectedModel = action.payload;
    },
    setIsStreaming(state, action: PayloadAction<boolean>) {
      state.isStreaming = action.payload;
    },
    setStreamingEnabled(state, action: PayloadAction<boolean>) {
      state.streamingEnabled = action.payload;
    },
    setQuickActions(state, action: PayloadAction<any[]>) {
      state.quickActions = action.payload;
    },
    setContext(state, action: PayloadAction<Partial<AssistantState['context']>>) {
      state.context = { ...state.context, ...action.payload };
    },
    clearContext(state) {
      state.context = {};
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
  },
});

export const {
  setCurrentSession,
  setSessions,
  addSession,
  removeSession,
  setMessages,
  addMessage,
  updateLastMessage,
  clearMessages,
  setSelectedModel,
  setIsStreaming,
  setStreamingEnabled,
  setQuickActions,
  setContext,
  clearContext,
  setLoading,
  setError,
} = assistantSlice.actions;

export default assistantSlice.reducer;
