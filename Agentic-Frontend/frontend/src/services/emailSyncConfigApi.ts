import apiClient from './api';

/**
 * Email Sync Configuration API
 *
 * Provides access to sync defaults, presets, and configuration options
 * for email account synchronization.
 */

export interface SyncConfigOption {
  value: number | null;
  label: string;
  description: string;
}

export interface SyncPreset {
  name: string;
  sync_days_back: number | null;
  max_emails_limit: number | null;
  description: string;
  estimated_time: string;
  use_case: string;
}

export interface SyncDefaults {
  system_defaults: {
    sync_days_back: number;
    max_emails_limit: number;
    batch_size: number;
  };
  configuration_options: {
    sync_days_back: {
      options: SyncConfigOption[];
      description: string;
    };
    max_emails_limit: {
      options: SyncConfigOption[];
      description: string;
    };
  };
  presets: {
    quick_start: SyncPreset;
    balanced: SyncPreset;
    comprehensive: SyncPreset;
    unlimited: SyncPreset;
  };
}

/**
 * Get sync configuration defaults and presets
 *
 * Returns system defaults, available configuration options, and
 * recommended presets for different use cases.
 */
export const getSyncDefaults = async (): Promise<SyncDefaults> => {
  const response = await apiClient.get('/api/v1/email-sync/defaults');
  return response.data;
};

export default {
  getSyncDefaults,
};
