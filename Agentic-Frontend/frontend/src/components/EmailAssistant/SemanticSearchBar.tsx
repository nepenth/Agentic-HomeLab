import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Typography,
  Chip,
  CircularProgress,
  alpha,
  useTheme,
  Popper,
  ClickAwayListener
} from '@mui/material';
import {
  Search as SearchIcon,
  Close as CloseIcon,
  History as HistoryIcon,
  TrendingUp as TrendingIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  Label as LabelIcon,
  Schedule as ScheduleIcon,
  AttachFile as AttachFileIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface SearchSuggestion {
  type: 'recent' | 'trending' | 'contact' | 'email' | 'category' | 'date' | 'attachment';
  text: string;
  value: string;
  count?: number;
  icon?: React.ReactNode;
}

interface SemanticSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: (query: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export const SemanticSearchBar: React.FC<SemanticSearchBarProps> = ({
  value,
  onChange,
  onSearch,
  placeholder = "Search emails...",
  disabled = false
}) => {
  const theme = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const popperRef = useRef<HTMLDivElement>(null);

  // Fetch search suggestions
  const { data: suggestions, isLoading: loadingSuggestions } = useQuery({
    queryKey: ['search-suggestions', value],
    queryFn: async () => {
      if (!value || value.length < 2) return [];
      try {
        const result = await apiClient.getEmailSearchSuggestions(value);
        return result.suggestions || [];
      } catch (error) {
        console.error('Failed to fetch search suggestions:', error);
        return [];
      }
    },
    enabled: value.length >= 2,
    staleTime: 30000
  });

  // Get recent searches from localStorage
  const getRecentSearches = (): string[] => {
    try {
      const recent = localStorage.getItem('emailRecentSearches');
      return recent ? JSON.parse(recent) : [];
    } catch {
      return [];
    }
  };

  const saveRecentSearch = (query: string) => {
    if (!query.trim()) return;
    const recent = getRecentSearches();
    const filtered = recent.filter(q => q !== query);
    filtered.unshift(query);
    localStorage.setItem('emailRecentSearches', JSON.stringify(filtered.slice(0, 10)));
  };

  // Generate suggestions based on input
  const generateSuggestions = (): SearchSuggestion[] => {
    const suggestions: SearchSuggestion[] = [];

    // Recent searches (when no input)
    if (!value) {
      const recent = getRecentSearches();
      recent.slice(0, 5).forEach(query => {
        suggestions.push({
          type: 'recent',
          text: query,
          value: query,
          icon: <HistoryIcon fontSize="small" />
        });
      });
    }

    // AI-powered suggestions from backend
    if (suggestions && suggestions.length > 0) {
      suggestions.forEach(sugg => {
        suggestions.push({
          type: sugg.type as any,
          text: sugg.text,
          value: sugg.value,
          count: sugg.count,
          icon: getSuggestionIcon(sugg.type)
        });
      });
    }

    // Quick filters based on input
    if (value) {
      // Email addresses
      if (value.includes('@')) {
        suggestions.push({
          type: 'contact',
          text: `From: ${value}`,
          value: `from:${value}`,
          icon: <PersonIcon fontSize="small" />
        });
      }

      // Categories
      const categories = ['work', 'personal', 'important', 'newsletter', 'social'];
      categories.forEach(cat => {
        if (cat.toLowerCase().includes(value.toLowerCase())) {
          suggestions.push({
            type: 'category',
            text: `Category: ${cat}`,
            value: `category:${cat}`,
            icon: <LabelIcon fontSize="small" />
          });
        }
      });

      // Date ranges
      const dateRanges = [
        { text: 'Today', value: 'date:today' },
        { text: 'Yesterday', value: 'date:yesterday' },
        { text: 'This week', value: 'date:this_week' },
        { text: 'Last week', value: 'date:last_week' },
        { text: 'This month', value: 'date:this_month' }
      ];
      dateRanges.forEach(range => {
        if (range.text.toLowerCase().includes(value.toLowerCase())) {
          suggestions.push({
            type: 'date',
            text: `Date: ${range.text}`,
            value: range.value,
            icon: <ScheduleIcon fontSize="small" />
          });
        }
      });

      // Attachments
      if (value.toLowerCase().includes('attach')) {
        suggestions.push({
          type: 'attachment',
          text: 'Has attachments',
          value: 'has:attachment',
          icon: <AttachFileIcon fontSize="small" />
        });
      }
    }

    return suggestions.slice(0, 8); // Limit to 8 suggestions
  };

  const getSuggestionIcon = (type: string) => {
    switch (type) {
      case 'recent': return <HistoryIcon fontSize="small" />;
      case 'trending': return <TrendingIcon fontSize="small" />;
      case 'contact': return <PersonIcon fontSize="small" />;
      case 'email': return <EmailIcon fontSize="small" />;
      case 'category': return <LabelIcon fontSize="small" />;
      case 'date': return <ScheduleIcon fontSize="small" />;
      case 'attachment': return <AttachFileIcon fontSize="small" />;
      default: return <SearchIcon fontSize="small" />;
    }
  };

  const allSuggestions = generateSuggestions();

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (!isOpen || allSuggestions.length === 0) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        setSelectedIndex(prev =>
          prev < allSuggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        event.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        event.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < allSuggestions.length) {
          handleSuggestionSelect(allSuggestions[selectedIndex]);
        } else {
          handleSearch();
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  const handleSuggestionSelect = (suggestion: SearchSuggestion) => {
    onChange(suggestion.value);
    setIsOpen(false);
    setSelectedIndex(-1);
    // Auto-search for suggestions
    setTimeout(() => handleSearch(suggestion.value), 100);
  };

  const handleSearch = (searchValue?: string) => {
    const query = searchValue || value;
    if (query.trim()) {
      saveRecentSearch(query);
      onSearch(query);
      setIsOpen(false);
      setSelectedIndex(-1);
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    onChange(newValue);
    setIsOpen(newValue.length > 0);
    setSelectedIndex(-1);
  };

  const handleFocus = () => {
    if (value || getRecentSearches().length > 0) {
      setIsOpen(true);
    }
  };

  const handleClear = () => {
    onChange('');
    setIsOpen(false);
    setSelectedIndex(-1);
    inputRef.current?.focus();
  };

  return (
    <ClickAwayListener onClickAway={() => setIsOpen(false)}>
      <Box sx={{ position: 'relative', width: '100%' }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          size="small"
          placeholder={placeholder}
          value={value}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                {value && (
                  <IconButton size="small" onClick={handleClear}>
                    <CloseIcon fontSize="small" />
                  </IconButton>
                )}
                {loadingSuggestions && (
                  <CircularProgress size={16} sx={{ ml: 1 }} />
                )}
              </InputAdornment>
            )
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              backgroundColor: theme.palette.background.paper,
              '&:hover': {
                backgroundColor: alpha(theme.palette.action.hover, 0.1)
              },
              '&.Mui-focused': {
                backgroundColor: theme.palette.background.paper,
                boxShadow: `0 0 0 2px ${alpha(theme.palette.primary.main, 0.2)}`
              }
            }
          }}
        />

        {/* Suggestions Popper */}
        <Popper
          open={isOpen && allSuggestions.length > 0}
          anchorEl={inputRef.current}
          placement="bottom-start"
          sx={{ zIndex: 1300, width: inputRef.current?.offsetWidth || 300 }}
        >
          <Paper
            ref={popperRef}
            elevation={8}
            sx={{
              maxHeight: 300,
              overflow: 'auto',
              borderRadius: 1,
              mt: 0.5,
              minWidth: 300
            }}
          >
            <List dense sx={{ py: 0.5 }}>
              {allSuggestions.map((suggestion, index) => (
                <ListItem key={`${suggestion.type}-${suggestion.value}`} disablePadding>
                  <ListItemButton
                    selected={selectedIndex === index}
                    onClick={() => handleSuggestionSelect(suggestion)}
                    sx={{
                      py: 1,
                      px: 2,
                      '&.Mui-selected': {
                        backgroundColor: alpha(theme.palette.primary.main, 0.1)
                      },
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.action.hover, 0.1)
                      }
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36, color: 'text.secondary' }}>
                      {suggestion.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {suggestion.text}
                        </Typography>
                      }
                      secondary={
                        suggestion.count ? (
                          <Chip
                            label={suggestion.count}
                            size="small"
                            variant="outlined"
                            sx={{ height: 16, fontSize: '0.7rem', mt: 0.25 }}
                          />
                        ) : null
                      }
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Paper>
        </Popper>
      </Box>
    </ClickAwayListener>
  );
};

export default SemanticSearchBar;