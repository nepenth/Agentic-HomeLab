import React from 'react';
import { Box, GlobalStyles } from '@mui/material';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

interface LayoutProps {
  children: React.ReactNode;
  drawerWidth?: number;
}

const Layout: React.FC<LayoutProps> = ({ children, drawerWidth = 280 }) => {
  return (
    <>
      {/* Global styles to ensure proper scrolling */}
      <GlobalStyles
        styles={{
          'html, body': {
            height: '100%',
            margin: 0,
            padding: 0,
            overflow: 'hidden', // Prevent body scrolling, let main handle it
          },
          '#root': {
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          },
          // Ensure scroll bars are visible and styled consistently
          '::-webkit-scrollbar': {
            width: '12px',
            height: '12px',
          },
          '::-webkit-scrollbar-track': {
            backgroundColor: 'rgba(0, 0, 0, 0.05)',
            borderRadius: '6px',
          },
          '::-webkit-scrollbar-thumb': {
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            borderRadius: '6px',
            border: '2px solid transparent',
            backgroundClip: 'content-box',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
            },
            '&:active': {
              backgroundColor: 'rgba(0, 0, 0, 0.4)',
            },
          },
          // Firefox scrollbar styling
          '*': {
            scrollbarWidth: 'thin',
            scrollbarColor: 'rgba(0, 0, 0, 0.2) rgba(0, 0, 0, 0.05)',
          },
        }}
      />

      <Box
        sx={{
          display: 'flex',
          height: '100vh',
          overflow: 'hidden', // Container doesn't scroll, main does
        }}
      >
        <TopBar drawerWidth={drawerWidth} />
        <Sidebar drawerWidth={drawerWidth} />

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            width: { md: `calc(100% - ${drawerWidth}px)` },
            ml: { md: `${drawerWidth}px` },
            mt: '64px', // Fixed height for AppBar
            height: 'calc(100vh - 64px)',
            backgroundColor: 'background.default',
            overflow: 'auto', // Main content area handles scrolling
            // Enhanced scrollbar styling for better visibility
            '&::-webkit-scrollbar': {
              width: '12px',
              height: '12px',
            },
            '&::-webkit-scrollbar-track': {
              backgroundColor: 'rgba(0, 0, 0, 0.05)',
              borderRadius: '6px',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: 'rgba(0, 0, 0, 0.2)',
              borderRadius: '6px',
              border: '2px solid transparent',
              backgroundClip: 'content-box',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
              },
              '&:active': {
                backgroundColor: 'rgba(0, 0, 0, 0.4)',
              },
            },
            // Firefox scrollbar styling
            scrollbarWidth: 'thin',
            scrollbarColor: 'rgba(0, 0, 0, 0.2) rgba(0, 0, 0, 0.05)',
          }}
        >
          <Box
            sx={{
              p: { xs: 2, md: 3 },
              minHeight: '100%', // Ensure content takes full height for scrolling
            }}
          >
            {children}
          </Box>
        </Box>
      </Box>
    </>
  );
};

export default Layout;