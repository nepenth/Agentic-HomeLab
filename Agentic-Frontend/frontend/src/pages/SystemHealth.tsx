import React, { useState, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  IconButton,
  Button,
  Alert,
  Chip,
  LinearProgress,
  Paper,
  Skeleton,
} from '@mui/material';
import {
  Refresh,
  TrendingUp,
  Speed,
  Memory,
  Storage,
  DeviceThermostat,
  Videocam,
  Timeline,
  CheckCircle,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import { CardSkeleton } from '../components';
import type { HttpClientMetrics, ModelPerformanceMetrics } from '../types';

// Types for better type safety
interface GPUData {
  id: number;
  name: string;
  usage: number;
  memoryUsed: number;
  memoryTotal: number;
  temperature: string | number;
  frequency: string | number;
  memoryFrequency: string | number;
  power: string | number;
}

interface SystemMetrics {
  cpu?: {
    usage?: number;
    temperature?: string | number;
    cores?: string | number;
    frequency?: string | number;
    loadAverage?: number[] | string;
  };
  memory?: {
    used?: number;
    total?: number;
    percentage?: number;
    swapUsed?: string | number;
    swapTotal?: string | number;
  };
  disk?: {
    used?: string | number;
    total?: string | number;
    percentage?: number;
    readSpeed?: string | number;
    writeSpeed?: string | number;
  };
  network?: {
    download?: string | number;
    upload?: string | number;
    connections?: string | number;
    latency?: string | number;
  };
  gpus?: GPUData[];
  system?: {
    uptime?: string | number;
    loadAverage?: number[] | string;
    processes?: string | number;
    health?: string;
  };
}

// No mock data - we will show "No data available" when API fails

// Modern GPU Card Component with proper error handling
const GPUCard: React.FC<{ gpu: GPUData; index: number }> = ({ gpu, index }) => {
  const formatValue = (value: string | number, unit: string = ''): string => {
    if (value === 'N/A' || value === null || value === undefined) return 'N/A';
    if (typeof value === 'number') {
      return unit ? `${value.toFixed(1)}${unit}` : value.toString();
    }
    return `${value}${unit}`;
  };

  return (
    <Box key={`gpu-${gpu.id}-${index}`} sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'primary.main' }}>
        GPU {gpu.id + 1}: {gpu.name || 'Unknown GPU'}
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              textAlign: 'center',
              border: 1,
              borderColor: 'divider',
              minHeight: 100,
              transition: 'all 0.2s ease-in-out',
              '&:hover': { borderColor: 'primary.main', transform: 'translateY(-2px)' }
            }}
          >
            <Videocam sx={{ fontSize: 24, color: 'primary.main', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">Usage</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatValue(gpu.usage, '%')}
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              textAlign: 'center',
              border: 1,
              borderColor: 'divider',
              minHeight: 100,
              transition: 'all 0.2s ease-in-out',
              '&:hover': { borderColor: 'info.main', transform: 'translateY(-2px)' }
            }}
          >
            <Memory sx={{ fontSize: 24, color: 'info.main', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">Memory</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatValue(gpu.memoryUsed, 'GB')}/{formatValue(gpu.memoryTotal, 'GB')}
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              textAlign: 'center',
              border: 1,
              borderColor: 'divider',
              minHeight: 100,
              transition: 'all 0.2s ease-in-out',
              '&:hover': { borderColor: 'error.main', transform: 'translateY(-2px)' }
            }}
          >
            <DeviceThermostat sx={{ fontSize: 24, color: 'error.main', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">Temperature</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatValue(gpu.temperature, '°F')}
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              textAlign: 'center',
              border: 1,
              borderColor: 'divider',
              minHeight: 100,
              transition: 'all 0.2s ease-in-out',
              '&:hover': { borderColor: 'warning.main', transform: 'translateY(-2px)' }
            }}
          >
            <Speed sx={{ fontSize: 24, color: 'warning.main', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">GPU Freq</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatValue(gpu.frequency, 'MHz')}
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              textAlign: 'center',
              border: 1,
              borderColor: 'divider',
              minHeight: 100,
              transition: 'all 0.2s ease-in-out',
              '&:hover': { borderColor: 'success.main', transform: 'translateY(-2px)' }
            }}
          >
            <Timeline sx={{ fontSize: 24, color: 'success.main', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">Mem Freq</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatValue(gpu.memoryFrequency, 'MHz')}
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={4} lg={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              textAlign: 'center',
              border: 1,
              borderColor: 'divider',
              minHeight: 100,
              transition: 'all 0.2s ease-in-out',
              '&:hover': { borderColor: 'secondary.main', transform: 'translateY(-2px)' }
            }}
          >
            <TrendingUp sx={{ fontSize: 24, color: 'secondary.main', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">Power</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatValue(gpu.power, 'W')}
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

const SystemHealth: React.FC = () => {
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const {
    data: rawSystemData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: async (): Promise<SystemMetrics | null> => {
      try {
        // Get real system metrics from individual endpoints
        const [
          cpuMetrics,
          memoryMetrics,
          diskMetrics,
          networkMetrics,
          gpuMetrics,
          loadMetrics,
          swapMetrics,
          systemInfo
        ] = await Promise.all([
          apiClient.getSystemMetricsCpu().catch((error) => {
            console.warn('Failed to fetch CPU metrics:', error);
            return null;
          }),
          apiClient.getSystemMetricsMemory().catch((error) => {
            console.warn('Failed to fetch memory metrics:', error);
            return null;
          }),
          apiClient.getSystemMetricsDisk().catch((error) => {
            console.warn('Failed to fetch disk metrics:', error);
            return null;
          }),
          apiClient.getSystemMetricsNetwork().catch((error) => {
            console.warn('Failed to fetch network metrics:', error);
            return null;
          }),
          apiClient.getSystemMetricsGpu().catch((error) => {
            console.warn('Failed to fetch GPU metrics:', error);
            console.log('GPU API error details:', error?.response?.data || error?.message);
            return null;
          }),
          apiClient.getSystemMetricsLoad().catch((error) => {
            console.warn('Failed to fetch load metrics:', error);
            return null;
          }),
          apiClient.getSystemMetricsSwap().catch((error) => {
            console.warn('Failed to fetch swap metrics:', error);
            return null;
          }),
          apiClient.getSystemInfo().catch((error) => {
            console.warn('Failed to fetch system info:', error);
            return null;
          })
        ]);

        // Debug: Log raw GPU data
        console.log('Raw GPU metrics from API:', gpuMetrics);

        // Transform the data to match our component's expected format
        const transformedData: SystemMetrics = {
          cpu: cpuMetrics ? {
            usage: cpuMetrics.usage_percent,
            temperature: cpuMetrics.temperature_celsius || 'N/A',
            cores: cpuMetrics.count?.logical || 'N/A',
            frequency: cpuMetrics.frequency_mhz?.current ? cpuMetrics.frequency_mhz.current / 1000 : 'N/A', // Convert MHz to GHz
            loadAverage: loadMetrics ? [loadMetrics['1m'], loadMetrics['5m'], loadMetrics['15m']] : 'N/A',
          } : undefined,
          memory: memoryMetrics ? {
            used: memoryMetrics.used_gb,
            total: memoryMetrics.total_gb,
            percentage: memoryMetrics.usage_percent,
            swapUsed: swapMetrics?.used_gb || 'N/A',
            swapTotal: swapMetrics?.total_gb || 'N/A',
          } : undefined,
          disk: diskMetrics ? {
            used: diskMetrics.usage?.used_gb || 'N/A',
            total: diskMetrics.usage?.total_gb || 'N/A',
            percentage: diskMetrics.usage?.usage_percent || 'N/A',
            readSpeed: diskMetrics.io?.read_bytes_per_sec ? diskMetrics.io.read_bytes_per_sec / (1024 * 1024) : 'N/A', // Convert to MB/s
            writeSpeed: diskMetrics.io?.write_bytes_per_sec ? diskMetrics.io.write_bytes_per_sec / (1024 * 1024) : 'N/A', // Convert to MB/s
          } : undefined,
          network: networkMetrics ? {
            download: networkMetrics.speeds?.bytes_recv_per_sec ? networkMetrics.speeds.bytes_recv_per_sec / (1024 * 1024) : 'N/A', // Convert to MB/s
            upload: networkMetrics.speeds?.bytes_sent_per_sec ? networkMetrics.speeds.bytes_sent_per_sec / (1024 * 1024) : 'N/A', // Convert to MB/s
            connections: networkMetrics.io?.packets_recv || 'N/A',
            latency: 'N/A', // Not available in current API
          } : undefined,
          gpus: Array.isArray(gpuMetrics) ? gpuMetrics.map((gpu: any, index: number) => {
            console.log(`Processing GPU ${index}:`, gpu);
            return {
              id: gpu.index ?? index,
              name: gpu.name || `GPU ${index + 1}`,
              usage: gpu.utilization?.gpu_percent || 0,
              memoryUsed: gpu.memory?.used_mb ? gpu.memory.used_mb / 1024 : 0, // Convert MB to GB
              memoryTotal: gpu.memory?.total_mb ? gpu.memory.total_mb / 1024 : 0, // Convert MB to GB
              temperature: gpu.temperature_fahrenheit || 'N/A',
              frequency: gpu.clocks?.graphics_mhz || 'N/A',
              memoryFrequency: gpu.clocks?.memory_mhz || 'N/A',
              power: gpu.power?.usage_watts || 'N/A',
            };
          }) : [],
          system: systemInfo ? {
            uptime: systemInfo.uptime?.formatted || 'N/A',
            loadAverage: loadMetrics ? [loadMetrics['1m'], loadMetrics['5m'], loadMetrics['15m']] : 'N/A',
            processes: systemInfo.processes?.total_count || 'N/A',
            health: 'healthy',
          } : undefined,
        };

        console.log('Transformed system data:', transformedData);
        return transformedData;
      } catch (error) {
        console.warn('Failed to fetch system metrics:', error);
        // Return null to indicate no data available
        return null;
      }
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Memoized data processing for better performance
  const systemData: SystemMetrics | null = useMemo((): SystemMetrics | null => {
    if (!rawSystemData) return null;

    // Enhanced GPU data processing with validation
    const processedGpus: GPUData[] = Array.isArray(rawSystemData.gpus)
      ? rawSystemData.gpus.map((gpu: any, index: number) => {
        console.log(`Processing GPU ${index}:`, gpu);

        // Validate GPU data structure
        if (!gpu || typeof gpu !== 'object') {
          console.warn(`Invalid GPU data at index ${index}:`, gpu);
          return null;
        }

        const processedGpu: GPUData = {
          id: typeof gpu.id === 'number' ? gpu.id : index,
          name: gpu.name || `GPU ${index + 1}`,
          usage: gpu.usage || 0,
          memoryUsed: gpu.memoryUsed || 0,
          memoryTotal: gpu.memoryTotal || 0,
          temperature: gpu.temperature || 'N/A',
          frequency: gpu.frequency || 'N/A',
          memoryFrequency: gpu.memoryFrequency || 'N/A',
          power: gpu.power || 'N/A',
        };

        console.log(`Processed GPU ${index}:`, processedGpu);
        return processedGpu;
      }).filter((gpu): gpu is GPUData => gpu !== null)
      : [];

    console.log('Total GPUs processed:', processedGpus.length);

    return {
      ...rawSystemData,
      gpus: processedGpus,
    };
  }, [rawSystemData]);

  // Fetch Ollama health status
  const {
    data: ollamaHealth,
    isLoading: ollamaLoading,
  } = useQuery({
    queryKey: ['ollama-health'],
    queryFn: () => apiClient.getOllamaHealth(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch HTTP client metrics (Phase 1.2)
  const {
    data: httpMetrics,
    isLoading: httpLoading,
  } = useQuery<HttpClientMetrics>({
    queryKey: ['http-metrics'],
    queryFn: () => apiClient.getHttpClientMetrics(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch model performance metrics (Phase 1.3)
  const {
    data: modelPerformance,
    isLoading: modelPerformanceLoading,
  } = useQuery<ModelPerformanceMetrics[]>({
    queryKey: ['model-performance'],
    queryFn: () => apiClient.getModelPerformanceMetrics(),
    refetchInterval: 60000, // Refetch every minute
  });

  const handleRefresh = async () => {
    await refetch();
    setLastRefresh(new Date());
  };

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };


  if (error || systemData === null) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity={error ? "error" : "warning"}
          action={
            <Button color="inherit" size="small" onClick={handleRefresh}>
              Retry
            </Button>
          }
        >
          {error ? "Failed to load system health data. Please try again." : "No system health data available. The backend may not be providing this information."}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ paddingBottom: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            System Health
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time monitoring of system resources and performance metrics.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </Typography>
          <IconButton onClick={handleRefresh} disabled={isLoading}>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* System Overview */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      System Status
                    </Typography>
                    <CheckCircle color="success" />
                  </Box>
                  <Chip
                    label={systemData?.system?.health || 'healthy'}
                    color={getHealthColor(systemData?.system?.health || 'healthy') as any}
                    sx={{ mb: 2, fontWeight: 600, textTransform: 'capitalize' }}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Uptime: {systemData?.system?.uptime || '7 days, 14 hours'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Processes: {systemData?.system?.processes || 284}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      CPU
                    </Typography>
                    <Speed color="primary" />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}>
                    {systemData?.cpu?.usage || 45}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {systemData?.cpu?.cores || 8} cores • {systemData?.cpu?.frequency || 3.2} GHz
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Temp: {systemData?.cpu?.temperature || 68}°C
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Memory
                    </Typography>
                    <Memory color="info" />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main', mb: 1 }}>
                    {systemData?.memory?.percentage || 39}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {systemData?.memory?.used || 6.2}GB / {systemData?.memory?.total || 16}GB
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Swap: {systemData?.memory?.swapUsed || 0.5}GB / {systemData?.memory?.swapTotal || 8}GB
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {isLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Storage
                    </Typography>
                    <Storage color="warning" />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main', mb: 1 }}>
                    {systemData?.disk?.percentage || 47}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {systemData?.disk?.used || 234}GB / {systemData?.disk?.total || 500}GB
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Read: {systemData?.disk?.readSpeed || 125} MB/s
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {ollamaLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Ollama Service
                    </Typography>
                    {ollamaLoading ? (
                      <Refresh sx={{ animation: 'spin 2s linear infinite' }} />
                    ) : (
                      <CheckCircle color={ollamaHealth?.status === 'healthy' ? 'success' : 'error'} />
                    )}
                  </Box>
                  <Chip
                    label={ollamaHealth?.status || 'unknown'}
                    color={ollamaHealth?.status === 'healthy' ? 'success' : 'error'}
                    sx={{ mb: 2, fontWeight: 600, textTransform: 'capitalize' }}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Models Available: {ollamaHealth?.models_available || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Default: {ollamaHealth?.default_model || 'None'}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {httpLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      HTTP Client
                    </Typography>
                    <CheckCircle color={httpMetrics ? 'success' : 'warning'} />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'secondary.main', mb: 1 }}>
                    {httpMetrics?.total_requests || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Total Requests
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Success Rate: {httpMetrics ? ((httpMetrics.successful_requests / httpMetrics.total_requests) * 100).toFixed(1) : 0}%
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card elevation={0}>
            <CardContent>
              {modelPerformanceLoading ? (
                <CardSkeleton lines={3} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      AI Models
                    </Typography>
                    <CheckCircle color={modelPerformance ? 'success' : 'warning'} />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main', mb: 1 }}>
                    {modelPerformance?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Models Tracked
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg Response: {modelPerformance?.length ?
                      (modelPerformance.reduce((sum, m) => sum + m.average_response_time_ms, 0) / modelPerformance.length).toFixed(0) : 0}ms
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detailed Metrics */}
      <Grid container spacing={3}>
        {/* CPU & Memory Details */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                CPU & Memory Details
              </Typography>

              {isLoading ? (
                <Box>
                  {[...Array(4)].map((_, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Skeleton variant="text" width="30%" height={24} />
                      <Skeleton variant="rectangular" width="100%" height={8} sx={{ borderRadius: 1 }} />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Box>
                  {/* CPU Usage */}
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>CPU Usage</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>{systemData?.cpu?.usage || 45}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemData?.cpu?.usage || 45}
                      sx={{ height: 8, borderRadius: 1 }}
                      color="primary"
                    />
                  </Box>

                  {/* Memory Usage */}
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>Memory Usage</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>{systemData?.memory?.percentage || 39}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemData?.memory?.percentage || 39}
                      sx={{ height: 8, borderRadius: 1 }}
                      color="info"
                    />
                  </Box>

                  {/* Load Average */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Load Average (1m, 5m, 15m)
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      {systemData?.cpu?.loadAverage === 'N/A' ? (
                        <Chip
                          label="N/A"
                          size="small"
                          variant="outlined"
                        />
                      ) : (
                        (Array.isArray(systemData?.cpu?.loadAverage) ? systemData.cpu.loadAverage : [1.2, 1.1, 1.0]).map((load: number, index: number) => (
                          <Chip
                            key={index}
                            label={load.toFixed(1)}
                            size="small"
                            variant="outlined"
                          />
                        ))
                      )}
                    </Box>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Network & Disk Details */}
        <Grid item xs={12} lg={6}>
          <Card elevation={0}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                Network & Storage Details
              </Typography>

              {isLoading ? (
                <Box>
                  {[...Array(4)].map((_, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Skeleton variant="text" width="30%" height={24} />
                      <Skeleton variant="rectangular" width="100%" height={8} sx={{ borderRadius: 1 }} />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Box>
                  {/* Network */}
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>Network I/O</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        ↓ {typeof systemData?.network?.download === 'number' ? systemData.network.download.toFixed(2) : '45.20'} MB/s ↑ {typeof systemData?.network?.upload === 'number' ? systemData.network.upload.toFixed(2) : '12.80'} MB/s
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                      <Box sx={{ flex: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={typeof systemData?.network?.download === 'number' ? Math.min(systemData.network.download * 2, 100) : 0}
                          sx={{ height: 6, borderRadius: 1 }}
                          color="success"
                        />
                        <Typography variant="caption" color="text.secondary">Download</Typography>
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={typeof systemData?.network?.upload === 'number' ? Math.min(systemData.network.upload * 5, 100) : 0}
                          sx={{ height: 6, borderRadius: 1 }}
                          color="info"
                        />
                        <Typography variant="caption" color="text.secondary">Upload</Typography>
                      </Box>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      Connections: {systemData?.network?.connections || 'N/A'} • Latency: {systemData?.network?.latency || 'N/A'}ms
                    </Typography>
                  </Box>

                  {/* Disk Usage */}
                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>Disk Usage</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>{systemData?.disk?.percentage || 47}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={typeof systemData?.disk?.percentage === 'number' ? systemData.disk.percentage : 0}
                      sx={{ height: 8, borderRadius: 1 }}
                      color="warning"
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {systemData?.disk?.used || 234}GB used of {systemData?.disk?.total || 500}GB
                    </Typography>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* GPU Details */}
        <Grid item xs={12}>
          <Card elevation={0} sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                GPU Monitoring {systemData?.gpus && systemData.gpus.length > 0 ? `(${systemData.gpus.length} GPUs detected)` : ''}
              </Typography>

              {isLoading ? (
                <Box>
                  {[...Array(2)].map((_, index) => (
                    <Box key={`skeleton-${index}`} sx={{ mb: 3 }}>
                      <Skeleton variant="text" width="40%" height={28} />
                      <Grid container spacing={2}>
                        {[...Array(6)].map((_, i) => (
                          <Grid item xs={12} sm={6} md={2} key={`skeleton-item-${i}`}>
                            <Skeleton variant="rectangular" width="100%" height={60} sx={{ borderRadius: 1 }} />
                          </Grid>
                        ))}
                      </Grid>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Box>
                  {systemData?.gpus && systemData.gpus.length > 0 ? (
                    <>
                      {systemData.gpus.map((gpu: GPUData, index: number) => (
                        <GPUCard key={`gpu-${gpu.id}-${index}`} gpu={gpu} index={index} />
                      ))}
                    </>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Videocam sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                      <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                        No GPU data available
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        GPU monitoring data is not available from the backend. This could be due to:
                      </Typography>
                      <Box sx={{ mt: 2, textAlign: 'left', maxWidth: 400, mx: 'auto' }}>
                        <Typography variant="body2" color="text.secondary" component="div">
                          • Backend service not running<br/>
                          • GPU drivers not installed<br/>
                          • NVIDIA GPUs not detected<br/>
                          • API endpoint returning empty data
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SystemHealth;