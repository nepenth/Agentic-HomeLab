import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  Chip,
  IconButton,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from '@mui/material';
import {
  Close,
  Add,
  Delete,
} from '@mui/icons-material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';

interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  summary?: string;
  category?: string;
  tags?: string[];
  metadata?: any;
  created_at?: string;
  updated_at?: string;
}

interface ItemEditorProps {
  open: boolean;
  onClose: () => void;
  item: KnowledgeItem | null;
}

const ItemEditor: React.FC<ItemEditorProps> = ({ open, onClose, item }) => {
  const [formData, setFormData] = useState<Partial<KnowledgeItem>>({});
  const [newTag, setNewTag] = useState('');
  const queryClient = useQueryClient();

  // Reset form when item changes
  useEffect(() => {
    if (item) {
      setFormData({
        title: item.title || '',
        content: item.content || '',
        summary: item.summary || '',
        category: item.category || '',
        tags: item.tags || [],
        metadata: item.metadata || {},
      });
    } else {
      setFormData({
        title: '',
        content: '',
        summary: '',
        category: '',
        tags: [],
        metadata: {},
      });
    }
  }, [item]);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<KnowledgeItem>) =>
      apiClient.updateKnowledgeItem(item!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-items'] });
      onClose();
    },
  });

  const handleSave = () => {
    if (!item) return;

    updateMutation.mutate({
      title: formData.title,
      content: formData.content,
      summary: formData.summary,
      category: formData.category,
      tags: formData.tags,
      metadata: formData.metadata,
    });
  };

  const handleAddTag = () => {
    if (newTag.trim() && !formData.tags?.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), newTag.trim()]
      }));
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags?.filter(tag => tag !== tagToRemove) || []
    }));
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAddTag();
    }
  };

  if (!item) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Edit Knowledge Item
          </Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Grid container spacing={3}>
            {/* Basic Information */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                Basic Information
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Title"
                value={formData.title || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Summary"
                value={formData.summary || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, summary: e.target.value }))}
                variant="outlined"
                multiline
                rows={2}
                helperText="Brief summary of the content"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={formData.category || ''}
                  label="Category"
                  onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                >
                  <MenuItem value="">
                    <em>None</em>
                  </MenuItem>
                  <MenuItem value="Technology">Technology</MenuItem>
                  <MenuItem value="Science">Science</MenuItem>
                  <MenuItem value="Business">Business</MenuItem>
                  <MenuItem value="Health">Health</MenuItem>
                  <MenuItem value="Education">Education</MenuItem>
                  <MenuItem value="Entertainment">Entertainment</MenuItem>
                  <MenuItem value="Sports">Sports</MenuItem>
                  <MenuItem value="Politics">Politics</MenuItem>
                  <MenuItem value="Environment">Environment</MenuItem>
                  <MenuItem value="Other">Other</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Tags */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                Tags
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                {formData.tags?.map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag}
                    onDelete={() => handleRemoveTag(tag)}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  size="small"
                  placeholder="Add a tag..."
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyPress={handleKeyPress}
                  sx={{ flex: 1 }}
                />
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleAddTag}
                  disabled={!newTag.trim()}
                  startIcon={<Add />}
                >
                  Add
                </Button>
              </Box>
            </Grid>

            {/* Content */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                Content
              </Typography>
              <TextField
                fullWidth
                label="Full Content"
                value={formData.content || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                variant="outlined"
                multiline
                rows={8}
                helperText="The complete content of this knowledge item"
              />
            </Grid>

            {/* Metadata */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                Metadata
              </Typography>
              <TextField
                fullWidth
                label="Metadata (JSON)"
                value={JSON.stringify(formData.metadata || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const metadata = JSON.parse(e.target.value);
                    setFormData(prev => ({ ...prev, metadata }));
                  } catch (error) {
                    // Invalid JSON, keep the string value for now
                  }
                }}
                variant="outlined"
                multiline
                rows={4}
                helperText="Additional metadata in JSON format"
              />
            </Grid>

            {/* Timestamps */}
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, color: 'text.secondary' }}>
                <Typography variant="caption">
                  Created: {item.created_at ? new Date(item.created_at).toLocaleString() : 'Unknown'}
                </Typography>
                <Typography variant="caption">
                  Last Updated: {item.updated_at ? new Date(item.updated_at).toLocaleString() : 'Never'}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={updateMutation.isPending}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={updateMutation.isPending}
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogActions>

      {updateMutation.isError && (
        <Box sx={{ px: 3, pb: 2 }}>
          <Alert severity="error">
            Failed to save changes. Please try again.
          </Alert>
        </Box>
      )}
    </Dialog>
  );
};

export default ItemEditor;