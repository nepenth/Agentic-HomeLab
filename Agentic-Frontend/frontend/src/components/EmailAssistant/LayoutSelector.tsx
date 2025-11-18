import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Popover,
  Button,
  Divider,
  alpha,
  useTheme
} from '@mui/material';
import {
  ViewColumn as ThreeColumnIcon,
  ViewList as HorizontalSplitIcon,
  ViewModule as VerticalSplitIcon,
  KeyboardArrowDown as ArrowIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';

interface LayoutOption {
  id: 'three-column' | 'horizontal-split' | 'vertical-split';
  name: string;
  description: string;
  icon: React.ReactNode;
  preview: string;
}

interface LayoutSelectorProps {
  currentLayout: 'three-column' | 'horizontal-split' | 'vertical-split';
  currentEmailViewerPosition: 'right' | 'below';
  onLayoutChange: (layout: 'three-column' | 'horizontal-split' | 'vertical-split') => void;
  onEmailViewerPositionChange: (position: 'right' | 'below') => void;
}

export const LayoutSelector: React.FC<LayoutSelectorProps> = ({
  currentLayout,
  currentEmailViewerPosition,
  onLayoutChange,
  onEmailViewerPositionChange
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const layoutOptions: LayoutOption[] = [
    {
      id: 'three-column',
      name: 'Three Column',
      description: 'Folders, email list, and viewer side by side',
      icon: <ThreeColumnIcon />,
      preview: '📁 | 📧📧📧 | 📄'
    },
    {
      id: 'horizontal-split',
      name: 'Horizontal Split',
      description: 'Email list and viewer stacked horizontally',
      icon: <HorizontalSplitIcon />,
      preview: '📧📧📧\n📄📄📄'
    },
    {
      id: 'vertical-split',
      name: 'Vertical Split',
      description: 'Email list and viewer stacked vertically',
      icon: <VerticalSplitIcon />,
      preview: '📧📧📧\n📄📄📄'
    }
  ];

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLayoutSelect = (layoutId: 'three-column' | 'horizontal-split' | 'vertical-split') => {
    onLayoutChange(layoutId);
    handleClose();
  };

  const handlePositionToggle = () => {
    onEmailViewerPositionChange(currentEmailViewerPosition === 'right' ? 'below' : 'right');
  };

  const currentLayoutOption = layoutOptions.find(option => option.id === currentLayout);

  return (
    <>
      <Tooltip title="Change layout">
        <IconButton
          onClick={handleClick}
          sx={{
            color: 'text.secondary',
            '&:hover': {
              backgroundColor: alpha(theme.palette.primary.main, 0.1),
              color: 'primary.main'
            }
          }}
        >
          <SettingsIcon />
        </IconButton>
      </Tooltip>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: { minWidth: 320, p: 1 }
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Layout Options
          </Typography>

          {/* Current Layout Display */}
          <Box sx={{ mb: 2, p: 1.5, backgroundColor: alpha(theme.palette.primary.main, 0.05), borderRadius: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5 }}>
              Current: {currentLayoutOption?.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {currentLayoutOption?.description}
            </Typography>
          </Box>

          {/* Layout Options */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
            {layoutOptions.map((option) => (
              <Button
                key={option.id}
                variant={currentLayout === option.id ? 'contained' : 'outlined'}
                onClick={() => handleLayoutSelect(option.id)}
                sx={{
                  justifyContent: 'flex-start',
                  textAlign: 'left',
                  p: 1.5,
                  height: 'auto',
                  '& .MuiButton-startIcon': {
                    mr: 1.5
                  }
                }}
                startIcon={option.icon}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.25 }}>
                    {option.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                    {option.description}
                  </Typography>
                  <Box
                    sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      color: 'text.secondary',
                      backgroundColor: alpha(theme.palette.background.default, 0.5),
                      p: 0.5,
                      borderRadius: 0.5,
                      display: 'inline-block',
                      whiteSpace: 'pre-line',
                      textAlign: 'center'
                    }}
                  >
                    {option.preview}
                  </Box>
                </Box>
              </Button>
            ))}
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Email Viewer Position Toggle */}
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
              Email Viewer Position
            </Typography>
            <Button
              variant="outlined"
              onClick={handlePositionToggle}
              sx={{
                width: '100%',
                justifyContent: 'flex-start',
                textTransform: 'none'
              }}
              startIcon={<ArrowIcon sx={{
                transform: currentEmailViewerPosition === 'right' ? 'rotate(90deg)' : 'rotate(-90deg)',
                transition: 'transform 0.2s'
              }} />}
            >
              <Box sx={{ textAlign: 'left' }}>
                <Typography variant="body2">
                  Viewer {currentEmailViewerPosition === 'right' ? 'on the right' : 'below'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Click to toggle position
                </Typography>
              </Box>
            </Button>
          </Box>

          {/* Layout Tips */}
          <Box sx={{ mt: 2, p: 1.5, backgroundColor: alpha(theme.palette.info.main, 0.05), borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              💡 Layout Tips:
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.4 }}>
              • Three Column: Best for wide screens<br/>
              • Horizontal Split: Good for medium screens<br/>
              • Vertical Split: Optimized for mobile
            </Typography>
          </Box>
        </Box>
      </Popover>
    </>
  );
};

export default LayoutSelector;