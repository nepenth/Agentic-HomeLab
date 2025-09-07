import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import UserManagement from '../components/UserManagement';

const UserManagementPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" mb={3}>
        User Management
      </Typography>

      <Paper sx={{ p: 3 }}>
        <UserManagement />
      </Paper>
    </Box>
  );
};

export default UserManagementPage;