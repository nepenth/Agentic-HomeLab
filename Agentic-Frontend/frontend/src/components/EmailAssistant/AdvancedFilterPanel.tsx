import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Switch,
  FormControlLabel,
  Divider,
  IconButton,
  Collapse,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  alpha,
  useTheme
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Close as CloseIcon,
  FilterList as FilterIcon,
  Save as SaveIcon,
  Clear as ClearIcon,
  DateRange as DateRangeIcon,
  Person as PersonIcon,
  Label as LabelIcon,
  Star as StarIcon,
  AttachFile as AttachFileIcon
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format, subDays, startOfDay, endOfDay } from 'date-fns';

interface FilterCriteria {
  query?: string;
  search_type?: 'semantic' | 'keyword' | 'hybrid';
  date_from?: Date;
  date_to?: Date;
  sender?: string;
  sender_domain?: string;
  categories?: string[];
  min_importance?: number;
  has_attachments?: boolean;
  is_read?: boolean;
  is_important?: boolean;
  is_flagged?: boolean;
  folder_path?: string;
  attachment_types?: string[];
}

interface SavedFilter {
  id: string;
  name: string;
  criteria: FilterCriteria;
  created_at: string;
}

interface AdvancedFilterPanelProps {
  open: boolean;
  onClose: () => void;
  filters: FilterCriteria;
  onFiltersChange: (filters: FilterCriteria) => void;
  onApplyFilters: () => void;
  onClearFilters: () => void;
  availableCategories?: string[];
  availableFolders?: string[];
}

export const AdvancedFilterPanel: React.FC<AdvancedFilterPanelProps> = ({
  open,
  onClose,
  filters,
  onFiltersChange,
  onApplyFilters,
  onClearFilters,
  availableCategories = [],
  availableFolders = []
}) => {
  const theme = useTheme();
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [filterName, setFilterName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Load saved filters from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('emailSavedFilters');
    if (saved) {
      try {
        setSavedFilters(JSON.parse(saved));
      } catch (error) {
        console.error('Failed to load saved filters:', error);
      }
    }
  }, []);

  const handleFilterChange = (key: keyof FilterCriteria, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  const handleCategoryToggle = (category: string) => {
    const currentCategories = filters.categories || [];
    const newCategories = currentCategories.includes(category)
      ? currentCategories.filter(c => c !== category)
      : [...currentCategories, category];

    handleFilterChange('categories', newCategories);
  };

  const handleAttachmentTypeToggle = (type: string) => {
    const currentTypes = filters.attachment_types || [];
    const newTypes = currentTypes.includes(type)
      ? currentTypes.filter(t => t !== type)
      : [...currentTypes, type];

    handleFilterChange('attachment_types', newTypes);
  };

  const handleQuickDateRange = (days: number) => {
    const to = endOfDay(new Date());
    const from = startOfDay(subDays(to, days));
    onFiltersChange({
      ...filters,
      date_from: from,
      date_to: to
    });
  };

  const handleSaveFilter = () => {
    if (!filterName.trim()) return;

    const newFilter: SavedFilter = {
      id: Date.now().toString(),
      name: filterName.trim(),
      criteria: { ...filters },
      created_at: new Date().toISOString()
    };

    const updatedFilters = [...savedFilters, newFilter];
    setSavedFilters(updatedFilters);
    localStorage.setItem('emailSavedFilters', JSON.stringify(updatedFilters));

    setFilterName('');
    setShowSaveDialog(false);
  };

  const handleLoadFilter = (filter: SavedFilter) => {
    onFiltersChange({ ...filter.criteria });
  };

  const handleDeleteFilter = (filterId: string) => {
    const updatedFilters = savedFilters.filter(f => f.id !== filterId);
    setSavedFilters(updatedFilters);
    localStorage.setItem('emailSavedFilters', JSON.stringify(updatedFilters));
  };

  const hasActiveFilters = Object.keys(filters).some(key => {
    const value = filters[key as keyof FilterCriteria];
    if (Array.isArray(value)) return value.length > 0;
    return value !== undefined && value !== null && value !== '';
  });

  const quickDateRanges = [
    { label: 'Today', days: 0 },
    { label: 'Last 3 days', days: 3 },
    { label: 'Last week', days: 7 },
    { label: 'Last 2 weeks', days: 14 },
    { label: 'Last month', days: 30 },
    { label: 'Last 3 months', days: 90 }
  ];

  const attachmentTypes = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'rtf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'zip', 'rar'
  ];

  if (!open) return null;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Paper
        sx={{
          position: 'absolute',
          top: 60,
          right: 16,
          width: 400,
          maxHeight: '80vh',
          overflow: 'auto',
          zIndex: 1300,
          boxShadow: theme.shadows[8],
          border: `1px solid ${theme.palette.divider}`
        }}
      >
        {/* Header */}
        <Box sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: alpha(theme.palette.primary.main, 0.02)
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterIcon color="primary" />
            <Typography variant="h6">Advanced Filters</Typography>
          </Box>
          <IconButton size="small" onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ p: 2 }}>
          {/* Search Query */}
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Search Query
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Enter search terms..."
                value={filters.query || ''}
                onChange={(e) => handleFilterChange('query', e.target.value)}
                sx={{ mb: 2 }}
              />

              <FormControl fullWidth size="small">
                <InputLabel>Search Type</InputLabel>
                <Select
                  value={filters.search_type || 'hybrid'}
                  onChange={(e) => handleFilterChange('search_type', e.target.value)}
                >
                  <MenuItem value="semantic">Semantic Search</MenuItem>
                  <MenuItem value="keyword">Keyword Search</MenuItem>
                  <MenuItem value="hybrid">Hybrid Search</MenuItem>
                </Select>
              </FormControl>
            </AccordionDetails>
          </Accordion>

          {/* Date Range */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Date Range
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  Quick Ranges
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                  {quickDateRanges.map((range) => (
                    <Chip
                      key={range.days}
                      label={range.label}
                      size="small"
                      variant="outlined"
                      onClick={() => handleQuickDateRange(range.days)}
                      sx={{ fontSize: '0.7rem' }}
                    />
                  ))}
                </Box>
              </Box>

              <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                <DatePicker
                  label="From"
                  value={filters.date_from || null}
                  onChange={(date) => handleFilterChange('date_from', date)}
                  slotProps={{ textField: { size: 'small', fullWidth: true } }}
                />
                <DatePicker
                  label="To"
                  value={filters.date_to || null}
                  onChange={(date) => handleFilterChange('date_to', date)}
                  slotProps={{ textField: { size: 'small', fullWidth: true } }}
                />
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Sender Filters */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Sender
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <TextField
                fullWidth
                size="small"
                label="Sender Email"
                placeholder="john@example.com"
                value={filters.sender || ''}
                onChange={(e) => handleFilterChange('sender', e.target.value)}
                sx={{ mb: 2 }}
              />

              <TextField
                fullWidth
                size="small"
                label="Domain"
                placeholder="example.com"
                value={filters.sender_domain || ''}
                onChange={(e) => handleFilterChange('sender_domain', e.target.value)}
              />
            </AccordionDetails>
          </Accordion>

          {/* Categories */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Categories
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {availableCategories.map((category) => (
                  <Chip
                    key={category}
                    label={category}
                    size="small"
                    variant={(filters.categories || []).includes(category) ? "filled" : "outlined"}
                    onClick={() => handleCategoryToggle(category)}
                    sx={{ fontSize: '0.7rem' }}
                  />
                ))}
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Status & Flags */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Status & Flags
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={filters.is_read === true}
                      onChange={(e) => handleFilterChange('is_read', e.target.checked ? true : undefined)}
                    />
                  }
                  label="Read only"
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={filters.is_read === false}
                      onChange={(e) => handleFilterChange('is_read', e.target.checked ? false : undefined)}
                    />
                  }
                  label="Unread only"
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={filters.is_important || false}
                      onChange={(e) => handleFilterChange('is_important', e.target.checked)}
                    />
                  }
                  label="Important only"
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={filters.is_flagged || false}
                      onChange={(e) => handleFilterChange('is_flagged', e.target.checked)}
                    />
                  }
                  label="Flagged only"
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={filters.has_attachments || false}
                      onChange={(e) => handleFilterChange('has_attachments', e.target.checked)}
                    />
                  }
                  label="Has attachments"
                />
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Importance Score */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Minimum Importance
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Box sx={{ px: 2 }}>
                <Slider
                  value={filters.min_importance || 0}
                  onChange={(_, value) => handleFilterChange('min_importance', value as number)}
                  min={0}
                  max={1}
                  step={0.1}
                  marks={[
                    { value: 0, label: '0' },
                    { value: 0.5, label: '0.5' },
                    { value: 1, label: '1' }
                  ]}
                  valueLabelDisplay="auto"
                />
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Attachments */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Attachment Types
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {attachmentTypes.map((type) => (
                  <Chip
                    key={type}
                    label={type.toUpperCase()}
                    size="small"
                    variant={(filters.attachment_types || []).includes(type) ? "filled" : "outlined"}
                    onClick={() => handleAttachmentTypeToggle(type)}
                    sx={{ fontSize: '0.7rem' }}
                  />
                ))}
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Folder */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Folder
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Folder</InputLabel>
                <Select
                  value={filters.folder_path || ''}
                  onChange={(e) => handleFilterChange('folder_path', e.target.value)}
                >
                  <MenuItem value="">
                    <em>All folders</em>
                  </MenuItem>
                  {availableFolders.map((folder) => (
                    <MenuItem key={folder} value={folder}>
                      {folder}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </AccordionDetails>
          </Accordion>

          {/* Saved Filters */}
          {savedFilters.length > 0 && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Saved Filters
                </Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ pt: 0 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {savedFilters.map((filter) => (
                    <Box key={filter.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        fullWidth
                        onClick={() => handleLoadFilter(filter)}
                        sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                      >
                        {filter.name}
                      </Button>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteFilter(filter.id)}
                        sx={{ color: 'error.main' }}
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Save Current Filter */}
          <Collapse in={showSaveDialog}>
            <Box sx={{ mt: 2, p: 2, border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>
              <TextField
                fullWidth
                size="small"
                label="Filter Name"
                value={filterName}
                onChange={(e) => setFilterName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSaveFilter()}
                sx={{ mb: 1 }}
              />
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button size="small" onClick={handleSaveFilter} disabled={!filterName.trim()}>
                  Save
                </Button>
                <Button size="small" onClick={() => setShowSaveDialog(false)}>
                  Cancel
                </Button>
              </Box>
            </Box>
          </Collapse>
        </Box>

        {/* Footer Actions */}
        <Box sx={{
          p: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          gap: 1,
          backgroundColor: alpha(theme.palette.background.default, 0.5)
        }}>
          <Button
            variant="contained"
            size="small"
            onClick={onApplyFilters}
            disabled={!hasActiveFilters}
          >
            Apply Filters
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={onClearFilters}
            disabled={!hasActiveFilters}
          >
            Clear All
          </Button>
          <Button
            variant="text"
            size="small"
            startIcon={<SaveIcon />}
            onClick={() => setShowSaveDialog(!showSaveDialog)}
            disabled={!hasActiveFilters}
          >
            Save
          </Button>
        </Box>
      </Paper>
    </LocalizationProvider>
  );
};

export default AdvancedFilterPanel;