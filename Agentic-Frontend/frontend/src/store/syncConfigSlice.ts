import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { SyncDefaults, SyncPreset } from '../services/emailSyncConfigApi';

interface SyncConfigState {
  syncDefaults: SyncDefaults | null;
  selectedPreset: string | null;
  customConfig: {
    syncDaysBack: number | null;
    maxEmailsLimit: number | null;
    foldersToSync: string[];
    syncAttachments: boolean;
    includeSpam: boolean;
    includeTrash: boolean;
  };
  isLoading: boolean;
  error: string | null;
}

const initialState: SyncConfigState = {
  syncDefaults: null,
  selectedPreset: null,
  customConfig: {
    syncDaysBack: null,
    maxEmailsLimit: null,
    foldersToSync: ['INBOX'],
    syncAttachments: true,
    includeSpam: false,
    includeTrash: false,
  },
  isLoading: false,
  error: null,
};

export const syncConfigSlice = createSlice({
  name: 'syncConfig',
  initialState,
  reducers: {
    setSyncDefaults: (state, action: PayloadAction<SyncDefaults>) => {
      state.syncDefaults = action.payload;
    },
    setSelectedPreset: (state, action: PayloadAction<string | null>) => {
      state.selectedPreset = action.payload;

      // Apply preset values to custom config
      if (action.payload && state.syncDefaults?.presets) {
        const preset = state.syncDefaults.presets[action.payload as keyof typeof state.syncDefaults.presets];
        if (preset) {
          state.customConfig.syncDaysBack = preset.sync_days_back;
          state.customConfig.maxEmailsLimit = preset.max_emails_limit;
        }
      }
    },
    setCustomConfig: (state, action: PayloadAction<Partial<typeof initialState.customConfig>>) => {
      state.customConfig = { ...state.customConfig, ...action.payload };
      // Clear preset selection when custom values change
      state.selectedPreset = null;
    },
    setSyncDaysBack: (state, action: PayloadAction<number | null>) => {
      state.customConfig.syncDaysBack = action.payload;
      state.selectedPreset = null;
    },
    setMaxEmailsLimit: (state, action: PayloadAction<number | null>) => {
      state.customConfig.maxEmailsLimit = action.payload;
      state.selectedPreset = null;
    },
    setFoldersToSync: (state, action: PayloadAction<string[]>) => {
      state.customConfig.foldersToSync = action.payload;
    },
    toggleSyncAttachments: (state) => {
      state.customConfig.syncAttachments = !state.customConfig.syncAttachments;
    },
    toggleIncludeSpam: (state) => {
      state.customConfig.includeSpam = !state.customConfig.includeSpam;
    },
    toggleIncludeTrash: (state) => {
      state.customConfig.includeTrash = !state.customConfig.includeTrash;
    },
    resetCustomConfig: (state) => {
      state.customConfig = initialState.customConfig;
      state.selectedPreset = null;
    },
    setIsLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setSyncDefaults,
  setSelectedPreset,
  setCustomConfig,
  setSyncDaysBack,
  setMaxEmailsLimit,
  setFoldersToSync,
  toggleSyncAttachments,
  toggleIncludeSpam,
  toggleIncludeTrash,
  resetCustomConfig,
  setIsLoading,
  setError,
} = syncConfigSlice.actions;

export default syncConfigSlice.reducer;
