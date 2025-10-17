import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import uiSlice from './slices/uiSlice';
import emailSlice from './emailSlice';
import taskSlice from './taskSlice';
import assistantSlice from './assistantSlice';
import workflowSlice from './workflowSlice';
import searchSlice from './searchSlice';
import syncConfigSlice from './syncConfigSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    ui: uiSlice,
    email: emailSlice,
    task: taskSlice,
    assistant: assistantSlice,
    workflow: workflowSlice,
    search: searchSlice,
    syncConfig: syncConfigSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;