import React from 'react';
import type { ReactNode } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Chip,
  Alert,
  IconButton,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  ArrowBack,
  Settings,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface WorkflowTemplateProps {
  title: string;
  description: string;
  status: 'active' | 'inactive' | 'coming-soon';
  icon?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

const WorkflowTemplate: React.FC<WorkflowTemplateProps> = ({
  title,
  description,
  status,
  icon,
  children,
  actions,
  breadcrumbs,
}) => {
  const navigate = useNavigate();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'warning';
      case 'coming-soon':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return 'Active';
      case 'inactive':
        return 'Inactive';
      case 'coming-soon':
        return 'Coming Soon';
      default:
        return 'Unknown';
    }
  };

  const defaultBreadcrumbs = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Workflows', href: '/workflows' },
    { label: title },
  ];

  const finalBreadcrumbs = breadcrumbs || defaultBreadcrumbs;

  return (
    <Box>
      {/* Header Section */}
      <Box sx={{ mb: 3 }}>
        {/* Back Button */}
        <Box sx={{ mb: 2 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/dashboard')}
            variant="text"
            color="inherit"
          >
            Back to Dashboard
          </Button>
        </Box>

        {/* Breadcrumbs */}
        <Breadcrumbs sx={{ mb: 2 }}>
          {finalBreadcrumbs.map((crumb, index) => (
            <span key={index}>
              {crumb.href && index < finalBreadcrumbs.length - 1 ? (
                <Link
                  color="inherit"
                  href={crumb.href}
                  onClick={(e) => {
                    e.preventDefault();
                    navigate(crumb.href!);
                  }}
                  sx={{ cursor: 'pointer', textDecoration: 'none' }}
                >
                  {crumb.label}
                </Link>
              ) : (
                <Typography color="text.primary">{crumb.label}</Typography>
              )}
            </span>
          ))}
        </Breadcrumbs>

        {/* Title Section */}
        <Paper
          elevation={0}
          sx={{
            p: 3,
            background: 'linear-gradient(135deg, rgba(0, 122, 255, 0.1), rgba(88, 86, 214, 0.1))',
            border: 1,
            borderColor: 'divider',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {icon && (
                <Box sx={{ mr: 2, fontSize: '2.5rem', color: 'primary.main' }}>
                  {icon}
                </Box>
              )}
              <Box>
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                  {title}
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                  {description}
                </Typography>
                <Chip
                  label={getStatusText(status)}
                  color={getStatusColor(status) as any}
                  sx={{ fontWeight: 600 }}
                />
              </Box>
            </Box>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              {actions}
              <IconButton color="primary">
                <Settings />
              </IconButton>
            </Box>
          </Box>
        </Paper>
      </Box>

      {/* Status Alerts */}
      {status === 'coming-soon' && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            This workflow is currently under development. Check back soon for updates!
          </Typography>
        </Alert>
      )}

      {status === 'inactive' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="body2">
            This workflow is currently inactive. Contact your administrator to enable it.
          </Typography>
        </Alert>
      )}

      {/* Main Content */}
      <Box>
        {children}
      </Box>
    </Box>
  );
};

export default WorkflowTemplate;