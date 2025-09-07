import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Search,
  Article,
  Category,
  AccessTime,
  ExpandMore,
  SmartToy,
  TextFields,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  summary?: string;
  category?: string;
  tags?: string[];
  relevance_score: number;
  created_at?: string;
  metadata?: any;
}

interface KnowledgeBaseSearchProps {
  onResultSelect?: (result: SearchResult) => void;
}

const KnowledgeBaseSearch: React.FC<KnowledgeBaseSearchProps> = ({ onResultSelect }) => {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [searchType, setSearchType] = useState<'semantic' | 'keyword' | 'hybrid'>('semantic');
  const [limit, setLimit] = useState(20);

  // Search query
  const { data: searchResults, isLoading, error, refetch } = useQuery({
    queryKey: ['knowledge-search', query, category, searchType, limit],
    queryFn: () => {
      if (!query.trim()) return null;
      return apiClient.searchKnowledgeBase({
        query: query.trim(),
        category: category || undefined,
        limit,
        search_type: searchType,
      });
    },
    enabled: false, // Only run when manually triggered
  });

  // Categories query
  const { data: categories } = useQuery({
    queryKey: ['knowledge-categories'],
    queryFn: () => apiClient.getKnowledgeCategories(),
  });

  const handleSearch = () => {
    if (query.trim()) {
      refetch();
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  const handleResultClick = (result: SearchResult) => {
    if (onResultSelect) {
      onResultSelect(result);
    }
  };

  const formatRelevanceScore = (score: number) => {
    return `${(score * 100).toFixed(1)}%`;
  };

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Search Interface */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Search />
          Knowledge Base Search
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Search Query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter your search query..."
              helperText="Use natural language for semantic search"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Search Type</InputLabel>
              <Select
                value={searchType}
                label="Search Type"
                onChange={(e) => setSearchType(e.target.value as any)}
              >
                <MenuItem value="semantic">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SmartToy fontSize="small" />
                    Semantic
                  </Box>
                </MenuItem>
                <MenuItem value="keyword">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TextFields fontSize="small" />
                    Keyword
                  </Box>
                </MenuItem>
                <MenuItem value="hybrid">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Search fontSize="small" />
                    Hybrid
                  </Box>
                </MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={category}
                label="Category"
                onChange={(e) => setCategory(e.target.value)}
              >
                <MenuItem value="">
                  <em>All Categories</em>
                </MenuItem>
                {categories?.categories?.map((cat: string) => (
                  <MenuItem key={cat} value={cat}>
                    {cat}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Results</InputLabel>
              <Select
                value={limit}
                label="Results"
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={20}>20</MenuItem>
                <MenuItem value={50}>50</MenuItem>
                <MenuItem value={100}>100</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            onClick={handleSearch}
            disabled={!query.trim() || isLoading}
            startIcon={isLoading ? <CircularProgress size={20} /> : <Search />}
            sx={{ minWidth: 120 }}
          >
            {isLoading ? 'Searching...' : 'Search'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              setQuery('');
              setCategory('');
            }}
          >
            Clear
          </Button>
        </Box>

        {/* Search Tips */}
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Search Tips:</strong>
            • Use natural language for semantic search
            • Try specific terms for keyword search
            • Filter by category for more targeted results
          </Typography>
        </Alert>
      </Paper>

      {/* Search Results */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Search failed. Please try again.
        </Alert>
      )}

      {searchResults && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Search Results ({searchResults.results?.length || 0})
          </Typography>

          {searchResults.results?.length === 0 ? (
            <Alert severity="info">
              No results found for your query. Try different keywords or broaden your search.
            </Alert>
          ) : (
            <List>
              {searchResults.results.map((result: SearchResult, index: number) => (
                <React.Fragment key={result.id}>
                  <ListItem
                    sx={{
                      cursor: 'pointer',
                      '&:hover': { backgroundColor: '#f5f5f5' },
                      borderRadius: 1,
                      mb: 1,
                    }}
                    onClick={() => handleResultClick(result)}
                  >
                    <ListItemIcon>
                      <Article color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography variant="subtitle1" sx={{ flex: 1 }}>
                            {result.title}
                          </Typography>
                          <Chip
                            label={formatRelevanceScore(result.relevance_score)}
                            size="small"
                            color={getRelevanceColor(result.relevance_score) as any}
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            {result.summary || result.content.substring(0, 200) + '...'}
                          </Typography>

                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            {result.category && (
                              <Chip
                                label={result.category}
                                size="small"
                                variant="outlined"
                                icon={<Category />}
                              />
                            )}
                            {result.tags?.slice(0, 3).map((tag, tagIndex) => (
                              <Chip
                                key={tagIndex}
                                label={tag}
                                size="small"
                                variant="outlined"
                              />
                            ))}
                            {result.created_at && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <AccessTime fontSize="small" />
                                {new Date(result.created_at).toLocaleDateString()}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      }
                    />
                  </ListItem>

                  {/* Expanded Details */}
                  <Accordion sx={{ mb: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="body2" color="text.secondary">
                        View full content and details
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={12}>
                          <Typography variant="h6" gutterBottom>
                            Full Content
                          </Typography>
                          <Typography variant="body2">
                            {result.content}
                          </Typography>
                        </Grid>

                        {result.metadata && Object.keys(result.metadata).length > 0 && (
                          <Grid item xs={12}>
                            <Typography variant="h6" gutterBottom>
                              Metadata
                            </Typography>
                            <Box sx={{ backgroundColor: '#f5f5f5', p: 2, borderRadius: 1 }}>
                              <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                                {JSON.stringify(result.metadata, null, 2)}
                              </pre>
                            </Box>
                          </Grid>
                        )}
                      </Grid>
                    </AccordionDetails>
                  </Accordion>

                  {index < (searchResults.results.length - 1) && <Divider />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default KnowledgeBaseSearch;