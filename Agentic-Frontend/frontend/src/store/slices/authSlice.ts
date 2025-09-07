import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { User } from '../../types';
import apiClient from '../../services/api';
import webSocketService from '../../services/websocket';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean; // To track if the initial auth check has been performed
}

const initialState: AuthState = {
  user: null,
  isLoading: false,
  error: null,
  isAuthenticated: false,
  isInitialized: false,
};

// Async thunks
export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async ({ username, password }: { username: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await apiClient.login(username, password);
      
      // Connect WebSocket after successful login
      webSocketService.connect('logs', apiClient.getAuthToken() || undefined);
      
      return {
        user: {
          id: response.user_id || username,
          username,
          email: response.email,
          isAuthenticated: true,
        },
        token: response.access_token,
      };
    } catch (error: any) {
      return rejectWithValue(error.detail || 'Login failed');
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, { dispatch }) => {
    try {
      await apiClient.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local state and disconnect WebSocket
      webSocketService.disconnect();
      dispatch(clearAuth());
    }
  }
);

export const checkAuthStatus = createAsyncThunk(
  'auth/checkAuthStatus',
  async (_, { rejectWithValue }) => {
    try {
      const token = apiClient.getAuthToken();
      if (!token) {
        throw new Error('No token found');
      }

      // Verify token by making a request to a protected endpoint
      await apiClient.getHealth();
      
      // If successful, connect WebSocket
      webSocketService.connect('logs', token);
      
      // For now, create a basic user object from stored data
      // In a real app, you'd fetch user data from an endpoint
      return {
        user: {
          id: 'current-user',
          username: 'User',
          isAuthenticated: true,
        },
      };
    } catch (error: any) {
      apiClient.clearAuthToken();
      return rejectWithValue('Token invalid');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearAuth: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      state.error = null;
      state.isLoading = false;
    },
    updateUser: (state, action: PayloadAction<Partial<User>>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.isAuthenticated = false;
      })
      
      // Logout
      .addCase(logoutUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
        state.error = null;
      })
      
      // Check auth status
      .addCase(checkAuthStatus.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(checkAuthStatus.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.error = null;
        state.isInitialized = true;
      })
      .addCase(checkAuthStatus.rejected, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
        state.isInitialized = true;
      });
  },
});

export const { clearError, clearAuth, updateUser } = authSlice.actions;
export default authSlice.reducer;