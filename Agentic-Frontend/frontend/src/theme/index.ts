import { createTheme } from '@mui/material/styles';
import type { ThemeOptions } from '@mui/material/styles';

const themeOptions: ThemeOptions = {
  palette: {
    mode: 'light',
    primary: {
      main: '#007AFF', // iOS blue
      light: '#5AC8FA',
      dark: '#0051D5',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#5856D6', // iOS purple
      light: '#AF52DE',
      dark: '#3A3A9C',
      contrastText: '#FFFFFF',
    },
    error: {
      main: '#FF3B30', // iOS red
      light: '#FF6961',
      dark: '#D70015',
    },
    warning: {
      main: '#FF9500', // iOS orange
      light: '#FFCC02',
      dark: '#FF6D00',
    },
    success: {
      main: '#34C759', // iOS green
      light: '#30D158',
      dark: '#248A3D',
    },
    info: {
      main: '#007AFF',
      light: '#5AC8FA',
      dark: '#0051D5',
    },
    background: {
      default: '#F2F2F7', // iOS light gray background
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1D1D1F', // Apple's dark text
      secondary: '#86868B', // Apple's secondary text
    },
    grey: {
      50: '#F2F2F7',
      100: '#E5E5EA',
      200: '#D1D1D6',
      300: '#C7C7CC',
      400: '#AEAEB2',
      500: '#8E8E93',
      600: '#636366',
      700: '#48484A',
      800: '#3A3A3C',
      900: '#1D1D1F',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", system-ui, sans-serif',
    h1: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      fontWeight: 700,
      fontSize: '2.125rem',
      lineHeight: 1.2,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      fontWeight: 600,
      fontSize: '1.75rem',
      lineHeight: 1.3,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.3,
      letterSpacing: '-0.01em',
    },
    h4: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.4,
    },
    h5: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      fontWeight: 600,
      fontSize: '1.125rem',
      lineHeight: 1.4,
    },
    h6: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      fontWeight: 600,
      fontSize: '1rem',
      lineHeight: 1.4,
    },
    body1: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
      fontWeight: 400,
      fontSize: '1rem',
      lineHeight: 1.5,
    },
    body2: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
      fontWeight: 400,
      fontSize: '0.875rem',
      lineHeight: 1.43,
    },
    button: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
      fontWeight: 500,
      fontSize: '0.875rem',
      textTransform: 'none',
      letterSpacing: 0,
    },
  },
  shape: {
    borderRadius: 12, // Apple's rounded corners
  },
  shadows: [
    'none',
    '0px 1px 3px rgba(0, 0, 0, 0.12), 0px 1px 2px rgba(0, 0, 0, 0.24)', // subtle shadow
    '0px 3px 6px rgba(0, 0, 0, 0.15), 0px 2px 4px rgba(0, 0, 0, 0.12)',
    '0px 6px 12px rgba(0, 0, 0, 0.15), 0px 4px 6px rgba(0, 0, 0, 0.12)',
    '0px 10px 20px rgba(0, 0, 0, 0.15), 0px 6px 10px rgba(0, 0, 0, 0.12)',
    '0px 15px 25px rgba(0, 0, 0, 0.15), 0px 8px 12px rgba(0, 0, 0, 0.12)',
    '0px 20px 30px rgba(0, 0, 0, 0.15), 0px 10px 15px rgba(0, 0, 0, 0.12)',
    '0px 25px 35px rgba(0, 0, 0, 0.15), 0px 12px 18px rgba(0, 0, 0, 0.12)',
    '0px 30px 40px rgba(0, 0, 0, 0.15), 0px 15px 20px rgba(0, 0, 0, 0.12)',
    '0px 35px 45px rgba(0, 0, 0, 0.15), 0px 18px 22px rgba(0, 0, 0, 0.12)',
    '0px 40px 50px rgba(0, 0, 0, 0.15), 0px 20px 25px rgba(0, 0, 0, 0.12)',
    '0px 45px 55px rgba(0, 0, 0, 0.15), 0px 22px 28px rgba(0, 0, 0, 0.12)',
    '0px 50px 60px rgba(0, 0, 0, 0.15), 0px 25px 30px rgba(0, 0, 0, 0.12)',
    '0px 55px 65px rgba(0, 0, 0, 0.15), 0px 28px 32px rgba(0, 0, 0, 0.12)',
    '0px 60px 70px rgba(0, 0, 0, 0.15), 0px 30px 35px rgba(0, 0, 0, 0.12)',
    '0px 65px 75px rgba(0, 0, 0, 0.15), 0px 32px 38px rgba(0, 0, 0, 0.12)',
    '0px 70px 80px rgba(0, 0, 0, 0.15), 0px 35px 40px rgba(0, 0, 0, 0.12)',
    '0px 75px 85px rgba(0, 0, 0, 0.15), 0px 38px 42px rgba(0, 0, 0, 0.12)',
    '0px 80px 90px rgba(0, 0, 0, 0.15), 0px 40px 45px rgba(0, 0, 0, 0.12)',
    '0px 85px 95px rgba(0, 0, 0, 0.15), 0px 42px 48px rgba(0, 0, 0, 0.12)',
    '0px 90px 100px rgba(0, 0, 0, 0.15), 0px 45px 50px rgba(0, 0, 0, 0.12)',
    '0px 95px 105px rgba(0, 0, 0, 0.15), 0px 48px 52px rgba(0, 0, 0, 0.12)',
    '0px 100px 110px rgba(0, 0, 0, 0.15), 0px 50px 55px rgba(0, 0, 0, 0.12)',
    '0px 105px 115px rgba(0, 0, 0, 0.15), 0px 52px 58px rgba(0, 0, 0, 0.12)',
    '0px 110px 120px rgba(0, 0, 0, 0.15), 0px 55px 60px rgba(0, 0, 0, 0.12)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '10px 20px',
          fontWeight: 500,
          textTransform: 'none',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.2)',
            transform: 'translateY(-1px)',
            transition: 'all 0.2s ease-in-out',
          },
        },
        contained: {
          '&:hover': {
            boxShadow: '0px 4px 8px rgba(0, 0, 0, 0.25)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.12), 0px 1px 2px rgba(0, 0, 0, 0.24)',
          border: 'none',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.15), 0px 2px 6px rgba(0, 0, 0, 0.12)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backgroundImage: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRadius: 0,
          border: 'none',
          boxShadow: '0px 0px 20px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '&:hover fieldset': {
              borderColor: '#007AFF',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          fontWeight: 500,
        },
      },
    },
  },
  transitions: {
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
    },
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195,
    },
  },
};

// Light theme
export const lightTheme = createTheme(themeOptions);

// Dark theme
export const darkTheme = createTheme({
  ...themeOptions,
  palette: {
    ...themeOptions.palette,
    mode: 'dark',
    primary: {
      main: '#0A84FF', // iOS blue for dark mode
      light: '#5AC8FA',
      dark: '#007AFF',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#000000', // iOS dark background
      paper: '#1C1C1E', // iOS dark card background
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#EBEBF5', // iOS secondary text in dark mode
    },
    grey: {
      50: '#1C1C1E',
      100: '#2C2C2E',
      200: '#3A3A3C',
      300: '#48484A',
      400: '#636366',
      500: '#8E8E93',
      600: '#AEAEB2',
      700: '#C7C7CC',
      800: '#D1D1D6',
      900: '#E5E5EA',
    },
  },
});

// Function to get theme based on mode
export const getTheme = (mode: 'light' | 'dark') => {
  return mode === 'dark' ? darkTheme : lightTheme;
};

export const theme = lightTheme;
export default theme;