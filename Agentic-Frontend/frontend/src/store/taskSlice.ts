import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Task {
  id: string;
  email_id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed';
  priority: 'low' | 'medium' | 'high';
  due_date: string | null;
  estimated_time: string | null;
  sender_email: string;
  sender_name: string;
  email_subject: string;
  importance_score: number;
  suggested_actions: string[];
  created_at: string;
  completed_at: string | null;
}

interface TaskState {
  tasks: Task[];
  selectedTask: Task | null;
  filters: {
    status: string[];
    priority: string[];
    search: string;
  };
  groupBy: 'priority' | 'status' | 'due_date' | 'none';
  sort: {
    field: string;
    direction: 'asc' | 'desc';
  };
  loading: boolean;
  error: string | null;
}

const initialState: TaskState = {
  tasks: [],
  selectedTask: null,
  filters: {
    status: ['pending', 'in_progress'],
    priority: [],
    search: '',
  },
  groupBy: 'priority',
  sort: {
    field: 'created_at',
    direction: 'desc',
  },
  loading: false,
  error: null,
};

const taskSlice = createSlice({
  name: 'task',
  initialState,
  reducers: {
    setTasks(state, action: PayloadAction<Task[]>) {
      state.tasks = action.payload;
    },
    addTask(state, action: PayloadAction<Task>) {
      state.tasks.unshift(action.payload);
    },
    updateTask(state, action: PayloadAction<Task>) {
      const index = state.tasks.findIndex(t => t.id === action.payload.id);
      if (index !== -1) {
        state.tasks[index] = action.payload;
      }
    },
    removeTask(state, action: PayloadAction<string>) {
      state.tasks = state.tasks.filter(t => t.id !== action.payload);
    },
    setSelectedTask(state, action: PayloadAction<Task | null>) {
      state.selectedTask = action.payload;
    },
    completeTask(state, action: PayloadAction<string>) {
      const task = state.tasks.find(t => t.id === action.payload);
      if (task) {
        task.status = 'completed';
        task.completed_at = new Date().toISOString();
      }
    },
    dismissTask(state, action: PayloadAction<string>) {
      const task = state.tasks.find(t => t.id === action.payload);
      if (task) {
        task.status = 'dismissed';
      }
    },
    setFilters(state, action: PayloadAction<Partial<TaskState['filters']>>) {
      state.filters = { ...state.filters, ...action.payload };
    },
    resetFilters(state) {
      state.filters = initialState.filters;
    },
    setGroupBy(state, action: PayloadAction<TaskState['groupBy']>) {
      state.groupBy = action.payload;
    },
    setSort(state, action: PayloadAction<{ field: string; direction: 'asc' | 'desc' }>) {
      state.sort = action.payload;
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
  setTasks,
  addTask,
  updateTask,
  removeTask,
  setSelectedTask,
  completeTask,
  dismissTask,
  setFilters,
  resetFilters,
  setGroupBy,
  setSort,
  setLoading,
  setError,
} = taskSlice.actions;

export default taskSlice.reducer;
