import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  Workflow,
  WorkflowStatus,
  WorkflowSettings,
  WorkflowDashboardStats,
} from '../services/emailWorkflowApi';

interface WorkflowState {
  workflows: WorkflowStatus[];
  currentWorkflow: WorkflowStatus | null;
  workflowSettings: WorkflowSettings[];
  defaultSettings: WorkflowSettings | null;
  dashboardStats: WorkflowDashboardStats | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: WorkflowState = {
  workflows: [],
  currentWorkflow: null,
  workflowSettings: [],
  defaultSettings: null,
  dashboardStats: null,
  isLoading: false,
  error: null,
};

export const workflowSlice = createSlice({
  name: 'workflow',
  initialState,
  reducers: {
    setWorkflows: (state, action: PayloadAction<WorkflowStatus[]>) => {
      state.workflows = action.payload;
    },
    addWorkflow: (state, action: PayloadAction<WorkflowStatus>) => {
      state.workflows.unshift(action.payload);
    },
    updateWorkflow: (state, action: PayloadAction<WorkflowStatus>) => {
      const index = state.workflows.findIndex(w => w.workflow_id === action.payload.workflow_id);
      if (index !== -1) {
        state.workflows[index] = action.payload;
      }
      if (state.currentWorkflow?.workflow_id === action.payload.workflow_id) {
        state.currentWorkflow = action.payload;
      }
    },
    setCurrentWorkflow: (state, action: PayloadAction<WorkflowStatus | null>) => {
      state.currentWorkflow = action.payload;
    },
    removeWorkflow: (state, action: PayloadAction<string>) => {
      state.workflows = state.workflows.filter(w => w.workflow_id !== action.payload);
      if (state.currentWorkflow?.workflow_id === action.payload) {
        state.currentWorkflow = null;
      }
    },
    setWorkflowSettings: (state, action: PayloadAction<WorkflowSettings[]>) => {
      state.workflowSettings = action.payload;
    },
    addWorkflowSetting: (state, action: PayloadAction<WorkflowSettings>) => {
      state.workflowSettings.push(action.payload);
    },
    updateWorkflowSetting: (state, action: PayloadAction<WorkflowSettings>) => {
      const index = state.workflowSettings.findIndex(s => s.id === action.payload.id);
      if (index !== -1) {
        state.workflowSettings[index] = action.payload;
      }
    },
    removeWorkflowSetting: (state, action: PayloadAction<string>) => {
      state.workflowSettings = state.workflowSettings.filter(s => s.id !== action.payload);
    },
    setDefaultSettings: (state, action: PayloadAction<WorkflowSettings | null>) => {
      state.defaultSettings = action.payload;
    },
    setDashboardStats: (state, action: PayloadAction<WorkflowDashboardStats>) => {
      state.dashboardStats = action.payload;
    },
    setIsLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
});

export const {
  setWorkflows,
  addWorkflow,
  updateWorkflow,
  setCurrentWorkflow,
  removeWorkflow,
  setWorkflowSettings,
  addWorkflowSetting,
  updateWorkflowSetting,
  removeWorkflowSetting,
  setDefaultSettings,
  setDashboardStats,
  setIsLoading,
  setError,
  clearError,
} = workflowSlice.actions;

export default workflowSlice.reducer;
