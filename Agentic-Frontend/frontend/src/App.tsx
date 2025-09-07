import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { Provider, useSelector } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { store } from './store';
import { getTheme } from './theme';
import type { RootState } from './store';

// Components
import Layout from './components/Layout/Layout';
import PrivateRoute from './components/PrivateRoute';
import WorkflowList from './components/WorkflowList';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import SystemHealth from './pages/SystemHealth';
import Security from './pages/Security';
import AgentManagement from './pages/AgentManagement';
import Chat from './pages/Chat';
import Utilities from './pages/Utilities';
import Settings from './pages/Settings';
import WorkflowTemplate from './pages/WorkflowTemplate';
import ContentProcessing from './pages/ContentProcessing';
import Analytics from './pages/Analytics';
import Personalization from './pages/Personalization';
import Trends from './pages/Trends';
import SearchIntelligence from './pages/SearchIntelligence';
import VisionStudio from './pages/VisionStudio';
import AudioWorkstation from './pages/AudioWorkstation';
import CrossModalFusion from './pages/CrossModalFusion';
import LearningAdaptation from './pages/LearningAdaptation';
import WorkflowStudio from './pages/WorkflowStudio';
import IntegrationHub from './pages/IntegrationHub';
import LoadBalancing from './pages/LoadBalancing';
import Collaboration from './pages/Collaboration';
import UserManagement from './pages/UserManagement';

// Workflow modules
import EmailAssistant from './modules/email-assistant/EmailAssistant';
import DocumentAnalyzer from './modules/document-analyzer/DocumentAnalyzer';

// Knowledge Base
import KnowledgeBase from './pages/KnowledgeBase';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Themed App Routes component that uses the UI state for theme
const ThemedAppRoutes: React.FC = () => {
  const { theme: themeMode } = useSelector((state: RootState) => state.ui);
  const currentTheme = getTheme(themeMode);

  return (
    <ThemeProvider theme={currentTheme}>
      <CssBaseline />
      <Router>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />

              {/* Protected routes with layout */}
              <Route
                path="/dashboard"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Dashboard />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/system-health"
                element={
                  <PrivateRoute>
                    <Layout>
                      <SystemHealth />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/security"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Security />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/agents"
                element={
                  <PrivateRoute>
                    <Layout>
                      <AgentManagement />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/content-processing"
                element={
                  <PrivateRoute>
                    <Layout>
                      <ContentProcessing />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/analytics"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Analytics />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/personalization"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Personalization />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/trends"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Trends />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/search-intelligence"
                element={
                  <PrivateRoute>
                    <Layout>
                      <SearchIntelligence />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/vision-studio"
                element={
                  <PrivateRoute>
                    <Layout>
                      <VisionStudio />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/audio-workstation"
                element={
                  <PrivateRoute>
                    <Layout>
                      <AudioWorkstation />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/cross-modal-fusion"
                element={
                  <PrivateRoute>
                    <Layout>
                      <CrossModalFusion />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/learning-adaptation"
                element={
                  <PrivateRoute>
                    <Layout>
                      <LearningAdaptation />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/workflow-studio"
                element={
                  <PrivateRoute>
                    <Layout>
                      <WorkflowStudio />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/integration-hub"
                element={
                  <PrivateRoute>
                    <Layout>
                      <IntegrationHub />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/load-balancing"
                element={
                  <PrivateRoute>
                    <Layout>
                      <LoadBalancing />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/collaboration"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Collaboration />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/user-management"
                element={
                  <PrivateRoute>
                    <Layout>
                      <UserManagement />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/chat"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Chat />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/utilities"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Utilities />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <PrivateRoute>
                    <Layout>
                      <Settings />
                    </Layout>
                  </PrivateRoute>
                }
              />

              {/* Workflow routes */}
              <Route
                path="/workflows"
                element={
                  <PrivateRoute>
                    <Layout>
                      <WorkflowTemplate
                        title="Workflows"
                        description="Select and manage your AI workflows"
                        status="active"
                      >
                        <WorkflowList />
                      </WorkflowTemplate>
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/workflows/knowledge-base"
                element={
                  <PrivateRoute>
                    <Layout>
                      <KnowledgeBase />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/workflows/email-assistant"
                element={
                  <PrivateRoute>
                    <Layout>
                      <EmailAssistant />
                    </Layout>
                  </PrivateRoute>
                }
              />
              <Route
                path="/workflows/document-analyzer"
                element={
                  <PrivateRoute>
                    <Layout>
                      <DocumentAnalyzer />
                    </Layout>
                  </PrivateRoute>
                }
              />

              {/* Default redirects */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Router>
    </ThemeProvider>
  );
};

// Main App component with providers
const App: React.FC = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemedAppRoutes />
      </QueryClientProvider>
    </Provider>
  );
};

export default App;
