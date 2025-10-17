import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { SearchType, SortOrder, SearchResult, EmailThread } from '../services/emailSearchApi';

interface SearchFilters {
  dateFrom: string | null;
  dateTo: string | null;
  sender: string | null;
  categories: string[];
  minImportance: number | null;
  hasAttachments: boolean | null;
  threadId: string | null;
}

interface SearchState {
  searchType: SearchType;
  sortOrder: SortOrder;
  filters: SearchFilters;
  results: SearchResult[];
  totalCount: number;
  suggestions: string[];
  facets: Record<string, any>;
  threads: EmailThread[];
  currentThread: EmailThread | null;
  isSearching: boolean;
  error: string | null;
  lastQuery: string | null;
}

const initialState: SearchState = {
  searchType: 'semantic',
  sortOrder: 'relevance',
  filters: {
    dateFrom: null,
    dateTo: null,
    sender: null,
    categories: [],
    minImportance: null,
    hasAttachments: null,
    threadId: null,
  },
  results: [],
  totalCount: 0,
  suggestions: [],
  facets: {},
  threads: [],
  currentThread: null,
  isSearching: false,
  error: null,
  lastQuery: null,
};

export const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setSearchType: (state, action: PayloadAction<SearchType>) => {
      state.searchType = action.payload;
    },
    setSortOrder: (state, action: PayloadAction<SortOrder>) => {
      state.sortOrder = action.payload;
    },
    setFilter: (state, action: PayloadAction<{ key: keyof SearchFilters; value: any }>) => {
      state.filters[action.payload.key] = action.payload.value;
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    setResults: (state, action: PayloadAction<SearchResult[]>) => {
      state.results = action.payload;
    },
    setTotalCount: (state, action: PayloadAction<number>) => {
      state.totalCount = action.payload;
    },
    setSuggestions: (state, action: PayloadAction<string[]>) => {
      state.suggestions = action.payload;
    },
    setFacets: (state, action: PayloadAction<Record<string, any>>) => {
      state.facets = action.payload;
    },
    setThreads: (state, action: PayloadAction<EmailThread[]>) => {
      state.threads = action.payload;
    },
    setCurrentThread: (state, action: PayloadAction<EmailThread | null>) => {
      state.currentThread = action.payload;
    },
    setIsSearching: (state, action: PayloadAction<boolean>) => {
      state.isSearching = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setLastQuery: (state, action: PayloadAction<string | null>) => {
      state.lastQuery = action.payload;
    },
    clearSearch: (state) => {
      state.results = [];
      state.totalCount = 0;
      state.suggestions = [];
      state.facets = {};
      state.lastQuery = null;
      state.error = null;
    },
  },
});

export const {
  setSearchType,
  setSortOrder,
  setFilter,
  clearFilters,
  setResults,
  setTotalCount,
  setSuggestions,
  setFacets,
  setThreads,
  setCurrentThread,
  setIsSearching,
  setError,
  setLastQuery,
  clearSearch,
} = searchSlice.actions;

export default searchSlice.reducer;
