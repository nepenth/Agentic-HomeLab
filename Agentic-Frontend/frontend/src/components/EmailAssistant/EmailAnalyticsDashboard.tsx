import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Button,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  alpha,
  useTheme
} from '@mui/material';
import {
  Email as EmailIcon,
  Send as SendIcon,
  Reply as ReplyIcon,
  Archive as ArchiveIcon,
  Delete as DeleteIcon,
  Star as StarIcon,
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Schedule as TimeIcon,
  Person as PersonIcon,
  Folder as FolderIcon,
  BarChart as ChartIcon,
  Refresh as RefreshIcon,
  DateRange as DateRangeIcon,
  MoreVert as MoreIcon
} from '@mui/icons-material';
import { format, subDays, startOfDay, endOfDay } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../services/api';

interface EmailStats {
  totalEmails: number;
  unreadEmails: number;
  sentEmails: number;
  receivedEmails: number;
  archivedEmails: number;
  deletedEmails: number;
  importantEmails: number;
  repliedEmails: number;
  emailsWithAttachments: number;
}

interface ProductivityMetrics {
  averageResponseTime: number; // minutes
  emailsPerDay: number;
  peakEmailHours: number[];
  mostActiveDay: string;
  topSenders: Array<{ email: string; name: string; count: number }>;
  topFolders: Array<{ folder: string; count: number }>;
  searchQueriesCount: number;
  bulkOperationsCount: number;
}

interface SearchAnalytics {
  totalSearches: number;
  popularQueries: Array<{ query: string; count: number }>;
  searchSuccessRate: number;
  averageSearchTime: number;
  mostSearchedTerms: Array<{ term: string; count: number }>;
  searchByCategory: Record<string, number>;
}

interface TimeRange {
  label: string;
  value: string;
  days: number;
}

export const EmailAnalyticsDashboard: React.FC = () => {
  const theme = useTheme();
  const [timeRange, setTimeRange] = useState<string>('7d');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const timeRanges: TimeRange[] = [
    { label: 'Last 24 hours', value: '1d', days: 1 },
    { label: 'Last 7 days', value: '7d', days: 7 },
    { label: 'Last 30 days', value: '30d', days: 30 },
    { label: 'Last 90 days', value: '90d', days: 90 }
  ];

  const selectedTimeRange = timeRanges.find(tr => tr.value === timeRange) || timeRanges[1];

  // Fetch email statistics
  const { data: emailStats, isLoading: loadingStats, refetch: refetchStats } = useQuery({
    queryKey: ['email-stats', timeRange],
    queryFn: async () => {
      const endDate = new Date();
      const startDate = subDays(endDate, selectedTimeRange.days);

      try {
        const response = await apiClient.get('/api/v1/analytics/email/stats', {
          params: {
            start_date: startOfDay(startDate).toISOString(),
            end_date: endOfDay(endDate).toISOString()
          }
        });
        return response.data as EmailStats;
      } catch (error) {
        console.error('Failed to fetch email stats:', error);
        return null;
      }
    }
  });

  // Fetch productivity metrics
  const { data: productivityMetrics, isLoading: loadingProductivity, refetch: refetchProductivity } = useQuery({
    queryKey: ['productivity-metrics', timeRange],
    queryFn: async () => {
      const endDate = new Date();
      const startDate = subDays(endDate, selectedTimeRange.days);

      try {
        const response = await apiClient.get('/api/v1/analytics/email/productivity', {
          params: {
            start_date: startOfDay(startDate).toISOString(),
            end_date: endOfDay(endDate).toISOString()
          }
        });
        return response.data as ProductivityMetrics;
      } catch (error) {
        console.error('Failed to fetch productivity metrics:', error);
        return null;
      }
    }
  });

  // Fetch search analytics
  const { data: searchAnalytics, isLoading: loadingSearch, refetch: refetchSearch } = useQuery({
    queryKey: ['search-analytics', timeRange],
    queryFn: async () => {
      const endDate = new Date();
      const startDate = subDays(endDate, selectedTimeRange.days);

      try {
        const response = await apiClient.get('/api/v1/analytics/email/search', {
          params: {
            start_date: startOfDay(startDate).toISOString(),
            end_date: endOfDay(endDate).toISOString()
          }
        });
        return response.data as SearchAnalytics;
      } catch (error) {
        console.error('Failed to fetch search analytics:', error);
        return null;
      }
    }
  });

  const handleRefresh = () => {
    refetchStats();
    refetchProductivity();
    refetchSearch();
  };

  const handleTimeRangeChange = (event: SelectChangeEvent) => {
    setTimeRange(event.target.value);
  };

  const formatTime = (minutes: number) => {
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ReactNode;
    color?: string;
    subtitle?: string;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
  }> = ({ title, value, icon, color = 'primary', subtitle, trend, trendValue }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ color: `${color}.main` }}>{icon}</Box>
          {trend && trendValue && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {trend === 'up' ? (
                <TrendingUpIcon sx={{ color: 'success.main', fontSize: 16 }} />
              ) : trend === 'down' ? (
                <TrendingDownIcon sx={{ color: 'error.main', fontSize: 16 }} />
              ) : null}
              <Typography variant="caption" color={trend === 'up' ? 'success.main' : trend === 'down' ? 'error.main' : 'text.secondary'}>
                {trendValue}
              </Typography>
            </Box>
          )}
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 0.5 }}>
          {typeof value === 'number' ? formatNumber(value) : value}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: subtitle ? 0.5 : 0 }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
            Email Analytics Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Insights into your email usage and productivity patterns
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={handleTimeRangeChange}
            >
              {timeRanges.map(range => (
                <MenuItem key={range.value} value={range.value}>
                  {range.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Tooltip title="Refresh data">
            <IconButton onClick={handleRefresh}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Email Statistics */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Email Statistics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Emails"
            value={emailStats?.totalEmails || 0}
            icon={<EmailIcon />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Unread Emails"
            value={emailStats?.unreadEmails || 0}
            icon={<EmailIcon />}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Sent Emails"
            value={emailStats?.sentEmails || 0}
            icon={<SendIcon />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Important Emails"
            value={emailStats?.importantEmails || 0}
            icon={<StarIcon />}
            color="error"
          />
        </Grid>
      </Grid>

      {/* Productivity Metrics */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Productivity Metrics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Average Response Time"
            value={formatTime(productivityMetrics?.averageResponseTime || 0)}
            icon={<TimeIcon />}
            subtitle="Time to reply to emails"
            color="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Emails Per Day"
            value={Math.round(productivityMetrics?.emailsPerDay || 0)}
            icon={<ChartIcon />}
            subtitle="Average daily email volume"
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Search Queries"
            value={productivityMetrics?.searchQueriesCount || 0}
            icon={<SearchIcon />}
            subtitle="Total searches performed"
            color="primary"
          />
        </Grid>
      </Grid>

      {/* Top Senders and Folders */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              Top Email Senders
            </Typography>
            {productivityMetrics?.topSenders?.slice(0, 5).map((sender, index) => (
              <Box
                key={sender.email}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  py: 1,
                  borderBottom: index < 4 ? `1px solid ${alpha(theme.palette.divider, 0.3)}` : 'none'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <PersonIcon sx={{ color: 'text.secondary' }} />
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {sender.name || sender.email}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {sender.email}
                    </Typography>
                  </Box>
                </Box>
                <Chip
                  label={sender.count}
                  size="small"
                  variant="outlined"
                />
              </Box>
            )) || (
              <Typography variant="body2" color="text.secondary">
                No sender data available
              </Typography>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              Most Active Folders
            </Typography>
            {productivityMetrics?.topFolders?.slice(0, 5).map((folder, index) => (
              <Box
                key={folder.folder}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  py: 1,
                  borderBottom: index < 4 ? `1px solid ${alpha(theme.palette.divider, 0.3)}` : 'none'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <FolderIcon sx={{ color: 'text.secondary' }} />
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {folder.folder}
                  </Typography>
                </Box>
                <Chip
                  label={folder.count}
                  size="small"
                  variant="outlined"
                />
              </Box>
            )) || (
              <Typography variant="body2" color="text.secondary">
                No folder data available
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Search Analytics */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Search Analytics
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Total Searches"
            value={searchAnalytics?.totalSearches || 0}
            icon={<SearchIcon />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Success Rate"
            value={`${Math.round((searchAnalytics?.searchSuccessRate || 0) * 100)}%`}
            icon={<TrendingUpIcon />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Avg Search Time"
            value={`${Math.round(searchAnalytics?.averageSearchTime || 0)}ms`}
            icon={<TimeIcon />}
            color="info"
          />
        </Grid>
      </Grid>

      {/* Popular Search Terms */}
      {searchAnalytics?.popularQueries && searchAnalytics.popularQueries.length > 0 && (
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Popular Search Queries
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {searchAnalytics.popularQueries.slice(0, 10).map((query, index) => (
              <Chip
                key={index}
                label={`${query.query} (${query.count})`}
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default EmailAnalyticsDashboard;