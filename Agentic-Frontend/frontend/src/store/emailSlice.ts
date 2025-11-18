import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

interface Email {
  email_id: string;
  subject: string;
  sender_email: string;
  sender_name: string;
  body_text: string;
  sent_at: string;
  received_at: string;
  is_read: boolean;
  is_important: boolean;
  is_flagged: boolean;
  is_draft: boolean;
  is_answered: boolean;
  is_deleted: boolean;
  is_spam: boolean;
  has_attachments: boolean;
  attachment_count?: number;
  category?: string;
  folder_path?: string;
  importance_score?: number;
  thread_id?: string;
}

interface EmailAccount {
  account_id: string;
  email_address: string;
  display_name: string;
  account_type: string;
  sync_status: string;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  next_sync_at: string | null;
  total_emails_synced: number;
  embedding_model: string | null;
  last_error: string | null;
}

interface EmailState {
  emails: Email[];
  selectedEmail: Email | null;
  accounts: EmailAccount[];
  selectedAccount: EmailAccount | null;
  filters: {
    search: string;
    unread: boolean;
    important: boolean;
    dateRange: string;
    sender: string;
    hasAttachments: boolean;
    folder_path?: string;
  };
  sort: {
    field: string;
    direction: 'asc' | 'desc';
  };
  view: 'email' | 'task';
  loading: boolean;
  error: string | null;
}

const initialState: EmailState = {
  emails: [],
  selectedEmail: null,
  accounts: [],
  selectedAccount: null,
  filters: {
    search: '',
    unread: false,
    important: false,
    dateRange: 'last7days',
    sender: '',
    hasAttachments: false,
  },
  sort: {
    field: 'received_at',
    direction: 'desc',
  },
  view: 'email',
  loading: false,
  error: null,
};

const emailSlice = createSlice({
  name: 'email',
  initialState,
  reducers: {
    setEmails(state, action: PayloadAction<Email[]>) {
      state.emails = action.payload;
    },
    addEmail(state, action: PayloadAction<Email>) {
      state.emails.unshift(action.payload);
    },
    updateEmail(state, action: PayloadAction<Email>) {
      const index = state.emails.findIndex(e => e.email_id === action.payload.email_id);
      if (index !== -1) {
        state.emails[index] = action.payload;
      }
    },
    removeEmail(state, action: PayloadAction<string>) {
      state.emails = state.emails.filter(e => e.email_id !== action.payload);
    },
    setSelectedEmail(state, action: PayloadAction<Email | null>) {
      state.selectedEmail = action.payload;
    },
    setAccounts(state, action: PayloadAction<EmailAccount[]>) {
      state.accounts = action.payload;
    },
    addAccount(state, action: PayloadAction<EmailAccount>) {
      state.accounts.push(action.payload);
    },
    updateAccount(state, action: PayloadAction<EmailAccount>) {
      const index = state.accounts.findIndex(a => a.account_id === action.payload.account_id);
      if (index !== -1) {
        state.accounts[index] = action.payload;
      }
    },
    removeAccount(state, action: PayloadAction<string>) {
      state.accounts = state.accounts.filter(a => a.account_id !== action.payload);
    },
    setSelectedAccount(state, action: PayloadAction<EmailAccount | null>) {
      state.selectedAccount = action.payload;
    },
    setFilters(state, action: PayloadAction<Partial<EmailState['filters']>>) {
      state.filters = { ...state.filters, ...action.payload };
    },
    resetFilters(state) {
      state.filters = initialState.filters;
    },
    setSort(state, action: PayloadAction<{ field: string; direction: 'asc' | 'desc' }>) {
      state.sort = action.payload;
    },
    setView(state, action: PayloadAction<'email' | 'task'>) {
      state.view = action.payload;
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
  setEmails,
  addEmail,
  updateEmail,
  removeEmail,
  setSelectedEmail,
  setAccounts,
  addAccount,
  updateAccount,
  removeAccount,
  setSelectedAccount,
  setFilters,
  resetFilters,
  setSort,
  setView,
  setLoading,
  setError,
} = emailSlice.actions;

export default emailSlice.reducer;
