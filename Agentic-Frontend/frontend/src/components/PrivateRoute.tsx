import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LoadingSpinner } from './LoadingSpinner';

interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, isInitialized } = useAuth();
  const location = useLocation();

  // Show loading spinner if auth state is still being determined
  if (!isInitialized || isLoading) {
    return <LoadingSpinner fullScreen message="Checking authentication..." />;
  }

  // If initialization is complete and user is not authenticated, redirect
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default PrivateRoute;