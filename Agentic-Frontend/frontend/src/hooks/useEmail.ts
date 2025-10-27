import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RootState } from '../store';
import {
  setEmails,
  setAccounts,
  setSelectedEmail,
  setSelectedAccount,
  setFilters,
  setSort,
  setLoading,
  setError,
} from '../store/emailSlice';
import apiClient from '../services/api';

export const useEmail = (pagination?: { currentPage: number; emailsPerPage: number }) => {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  const {
    emails,
    selectedEmail,
    accounts,
    selectedAccount,
    filters,
    sort,
    loading,
    error,
  } = useSelector((state: RootState) => state.email);

  // Fetch email accounts
  const { data: accountsData, isLoading: accountsLoading, refetch: refetchAccounts } = useQuery({
    queryKey: ['email-accounts'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/email-sync/accounts');
      return response.data.accounts;
    },
  });

  // Update Redux when accounts data changes
  React.useEffect(() => {
    if (accountsData) {
      dispatch(setAccounts(accountsData));
    }
  }, [accountsData, dispatch]);

  // Auto-select first account if none selected
  React.useEffect(() => {
    if (accounts && accounts.length > 0 && !selectedAccount) {
      console.log('[useEmail] Auto-selecting first account:', accounts[0]);
      dispatch(setSelectedAccount(accounts[0]));
    }
  }, [accounts, selectedAccount, dispatch]);

  // Fetch emails with filters and pagination
  const { data: emailsData, isLoading: emailsLoading, refetch: refetchEmails } = useQuery({
    queryKey: ['emails', filters, sort, selectedAccount?.account_id, pagination?.currentPage || 1],
    queryFn: async () => {
      const params: any = {
        limit: pagination?.emailsPerPage || 100,
        offset: ((pagination?.currentPage || 1) - 1) * (pagination?.emailsPerPage || 100),
        sort_by: sort.field,
        sort_order: sort.direction,
      };

      if (selectedAccount) {
        params.account_id = selectedAccount.account_id;
      }

      if (filters.search) {
        params.search_query = filters.search;
      }

      if (filters.unread) {
        params.is_read = false;
      }

      if (filters.important) {
        params.is_important = true;
      }

      if (filters.hasAttachments) {
        params.has_attachments = true;
      }

      if (filters.sender) {
        params.sender_email = filters.sender;
      }

      if (filters.folder_path) {
        params.folder_path = filters.folder_path;
      }

      if (filters.dateRange && filters.dateRange !== 'all') {
        const now = new Date();
        let startDate: Date;

        switch (filters.dateRange) {
          case 'today':
            startDate = new Date(now.setHours(0, 0, 0, 0));
            break;
          case 'last7days':
            startDate = new Date(now.setDate(now.getDate() - 7));
            break;
          case 'last30days':
            startDate = new Date(now.setDate(now.getDate() - 30));
            break;
          case 'last90days':
            startDate = new Date(now.setDate(now.getDate() - 90));
            break;
          default:
            startDate = new Date(0);
        }

        params.start_date = startDate.toISOString();
      }

      const response = await apiClient.get('/api/v1/email-sync/emails', { params });
      return response.data.emails;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: accounts.length > 0,
  });

  // Update Redux when emails data changes
  React.useEffect(() => {
    if (emailsData) {
      dispatch(setEmails(emailsData));
    }
  }, [emailsData, dispatch]);

  // Sync emails mutation - now uses V2 UID-based sync
  const syncMutation = useMutation({
    mutationFn: async ({ accountIds }: { accountIds?: string[] } = {}) => {
      dispatch(setLoading(true));
      const response = await apiClient.post('/api/v1/email-sync/v2/sync', {
        account_ids: accountIds || accounts.map(a => a.account_id),
        force_full_sync: false, // V2 UID-based sync handles incremental automatically
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
      dispatch(setLoading(false));
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to sync emails'));
      dispatch(setLoading(false));
    },
  });

  // Semantic search mutation
  const searchMutation = useMutation({
    mutationFn: async ({ query, accountId }: { query: string; accountId?: string }) => {
      const params: any = {
        query,
        limit: 50,
      };

      if (accountId) {
        params.account_id = accountId;
      }

      const response = await apiClient.get('/api/v1/email-sync/search', { params });
      return response.data.results;
    },
    onSuccess: (data) => {
      dispatch(setEmails(data));
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Search failed'));
    },
  });

  // Mark email as read mutation
  const markAsReadMutation = useMutation({
    mutationFn: async (emailId: string) => {
      const response = await apiClient.patch(`/api/v1/email-sync/emails/${emailId}`, {
        is_read: true,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
    },
  });

  // Mark email as important mutation
  const markAsImportantMutation = useMutation({
    mutationFn: async ({ emailId, important }: { emailId: string; important: boolean }) => {
      const response = await apiClient.patch(`/api/v1/email-sync/emails/${emailId}`, {
        is_important: important,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
    },
  });

  // Delete email mutation
  const deleteEmailMutation = useMutation({
    mutationFn: async (emailId: string) => {
      await apiClient.delete(`/api/v1/email-sync/emails/${emailId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] });
    },
  });

  // Add email account mutation
  const addAccountMutation = useMutation({
    mutationFn: async (accountData: any) => {
      const response = await apiClient.post('/api/v1/email-sync/accounts', accountData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
    },
  });

  // Update email account mutation
  const updateAccountMutation = useMutation({
    mutationFn: async ({ accountId, data }: { accountId: string; data: any }) => {
      const response = await apiClient.put(`/api/v1/email-sync/accounts/${accountId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
    },
  });

  // Delete email account mutation
  const deleteAccountMutation = useMutation({
    mutationFn: async (accountId: string) => {
      await apiClient.delete(`/api/v1/email-sync/accounts/${accountId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-accounts'] });
    },
  });

  // Fetch full email details mutation
  const fetchEmailDetailMutation = useMutation({
    mutationFn: async (emailId: string) => {
      const response = await apiClient.get(`/api/v1/email-sync/emails/${emailId}`);
      return response.data.email;
    },
    onSuccess: (emailData) => {
      dispatch(setSelectedEmail(emailData));
    },
    onError: (error: any) => {
      dispatch(setError(error.message || 'Failed to load email details'));
    },
  });

  return {
    // State
    emails,
    selectedEmail,
    accounts,
    selectedAccount,
    filters,
    sort,
    loading: loading || accountsLoading || emailsLoading,
    error,

    // Actions
    setSelectedEmail: (email: any) => dispatch(setSelectedEmail(email)),
    setSelectedAccount: (account: any) => dispatch(setSelectedAccount(account)),
    setFilters: (newFilters: any) => dispatch(setFilters(newFilters)),
    setSort: (newSort: any) => dispatch(setSort(newSort)),

    // Mutations
    syncEmails: syncMutation.mutate,
    searchEmails: searchMutation.mutate,
    markAsRead: markAsReadMutation.mutate,
    markAsImportant: markAsImportantMutation.mutate,
    deleteEmail: deleteEmailMutation.mutate,
    addAccount: addAccountMutation.mutate,
    updateAccount: updateAccountMutation.mutate,
    deleteAccount: deleteAccountMutation.mutate,
    fetchEmailDetail: fetchEmailDetailMutation.mutate,

    // Refetch functions
    refetchEmails,
    refreshAccounts: refetchAccounts,

    // Loading states
    isSyncing: syncMutation.isPending,
    isSearching: searchMutation.isPending,
    isFetchingDetail: fetchEmailDetailMutation.isPending,
  };
};
