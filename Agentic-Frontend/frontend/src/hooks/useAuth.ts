import { useSelector, useDispatch } from 'react-redux';
import { useEffect, useCallback } from 'react';
import type { RootState, AppDispatch } from '../store';
import { loginUser, logoutUser, checkAuthStatus, clearError } from '../store/slices/authSlice';

export const useAuth = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { user, isLoading, error, isAuthenticated, isInitialized } = useSelector(
    (state: RootState) => state.auth
  );

  useEffect(() => {
    // Only run the initial auth check if it hasn't been done yet.
    if (!isInitialized) {
      dispatch(checkAuthStatus());
    }
  }, [dispatch, isInitialized]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await dispatch(loginUser({ username, password }));
    return result.type === 'auth/loginUser/fulfilled';
  }, [dispatch]);

  const logout = useCallback(async () => {
    await dispatch(logoutUser());
  }, [dispatch]);

  const clearAuthError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    isInitialized,
    login,
    logout,
    clearAuthError,
  };
};