import psutil
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import math

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    pynvml = None


class SystemMetricsService:
    """Service for collecting system utilization metrics."""

    def __init__(self):
        self.nvml_initialized = False
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
            except Exception as e:
                print(f"Failed to initialize NVML: {e}")

    def __del__(self):
        if self.nvml_initialized and NVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except:
                pass

    def get_cpu_metrics(self) -> Dict[str, Any]:
        """Get CPU utilization metrics."""
        try:
            # Get CPU usage percentage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Get CPU frequency
            cpu_freq = psutil.cpu_freq()
            current_freq = cpu_freq.current if cpu_freq and cpu_freq.current else None
            min_freq = cpu_freq.min if cpu_freq and cpu_freq.min else None
            max_freq = cpu_freq.max if cpu_freq and cpu_freq.max else None

            # Handle case where current frequency is very low (container issue)
            if current_freq and current_freq < 100:  # Less than 100 MHz is likely incorrect
                current_freq = None

            # Get CPU times
            cpu_times = psutil.cpu_times_percent(interval=0.1)

            # Get CPU count
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)

            # Get CPU temperature (if available)
            cpu_temp = None
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    coretemp = temps['coretemp']
                    if coretemp:
                        cpu_temp = round(coretemp[0].current, 1)
                elif 'cpu_thermal' in temps:
                    cpu_thermal = temps['cpu_thermal']
                    if cpu_thermal:
                        cpu_temp = round(cpu_thermal[0].current, 1)
            except:
                pass

            # Calculate GHz values (handle None values)
            current_ghz = round(current_freq / 1000, 1) if current_freq and current_freq >= 100 else None
            min_ghz = round(min_freq / 1000, 1) if min_freq else None
            max_ghz = round(max_freq / 1000, 1) if max_freq else None

            return {
                "usage_percent": round(cpu_percent, 2),
                "frequency_ghz": {
                    "current": current_ghz,
                    "min": min_ghz,
                    "max": max_ghz
                },
                "frequency_mhz": {
                    "current": round(current_freq, 0) if current_freq and current_freq >= 100 else None,
                    "min": round(min_freq, 0) if min_freq else None,
                    "max": round(max_freq, 0) if max_freq else None
                },
                "temperature_celsius": cpu_temp,
                "temperature_fahrenheit": round((cpu_temp * 9/5) + 32, 1) if cpu_temp else None,
                "times_percent": {
                    "user": round(cpu_times.user, 2),
                    "system": round(cpu_times.system, 2),
                    "idle": round(cpu_times.idle, 2),
                    "nice": round(cpu_times.nice, 2) if hasattr(cpu_times, 'nice') else 0,
                    "iowait": round(cpu_times.iowait, 2) if hasattr(cpu_times, 'iowait') else 0,
                    "irq": round(cpu_times.irq, 2) if hasattr(cpu_times, 'irq') else 0,
                    "softirq": round(cpu_times.softirq, 2) if hasattr(cpu_times, 'softirq') else 0
                },
                "count": {
                    "physical": cpu_count,
                    "logical": cpu_count_logical
                }
            }
        except Exception as e:
            return {"error": f"Failed to get CPU metrics: {str(e)}"}

    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory utilization metrics."""
        try:
            memory = psutil.virtual_memory()

            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.free / (1024**3), 2),
                "usage_percent": round(memory.percent, 2),
                "buffers_gb": round(getattr(memory, 'buffers', 0) / (1024**3), 2),
                "cached_gb": round(getattr(memory, 'cached', 0) / (1024**3), 2),
                "shared_gb": round(getattr(memory, 'shared', 0) / (1024**3), 2)
            }
        except Exception as e:
            return {"error": f"Failed to get memory metrics: {str(e)}"}

    def get_disk_metrics(self) -> Dict[str, Any]:
        """Get disk utilization metrics."""
        try:
            # Get disk usage for root filesystem
            disk_usage = psutil.disk_usage('/')

            # Get disk I/O statistics
            disk_io = psutil.disk_io_counters()

            return {
                "usage": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "usage_percent": round(disk_usage.percent, 2)
                },
                "io": {
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0,
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_time_ms": disk_io.read_time if disk_io else 0,
                    "write_time_ms": disk_io.write_time if disk_io else 0
                } if disk_io else None
            }
        except Exception as e:
            return {"error": f"Failed to get disk metrics: {str(e)}"}

    def get_network_metrics(self) -> Dict[str, Any]:
        """Get network utilization metrics."""
        try:
            # Get network I/O statistics
            net_io = psutil.net_io_counters()

            # Get network interfaces
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()

            interfaces = []
            for interface_name, addrs in net_if_addrs.items():
                if interface_name in net_if_stats:
                    stats = net_if_stats[interface_name]
                    interfaces.append({
                        "name": interface_name,
                        "isup": stats.isup,
                        "speed_mbps": stats.speed if stats.speed > 0 else None,
                        "mtu": stats.mtu
                    })

            # Calculate network speeds (bytes per second) - this is an approximation
            # In a real implementation, you'd track previous values and calculate rates
            network_speeds = None
            if net_io:
                # These are cumulative counters, not rates
                # For actual speeds, you'd need to sample over time
                network_speeds = {
                    "bytes_sent_per_sec": net_io.bytes_sent,  # Placeholder - would need time-based calculation
                    "bytes_recv_per_sec": net_io.bytes_recv,  # Placeholder - would need time-based calculation
                    "packets_sent_per_sec": net_io.packets_sent,  # Placeholder
                    "packets_recv_per_sec": net_io.packets_recv   # Placeholder
                }

            return {
                "io": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout
                } if net_io else None,
                "speeds": network_speeds,
                "interfaces": interfaces
            }
        except Exception as e:
            return {"error": f"Failed to get network metrics: {str(e)}"}

    def get_load_average(self) -> Dict[str, Any]:
        """Get system load average metrics."""
        try:
            load_avg = psutil.getloadavg()
            return {
                "1m": round(load_avg[0], 2),
                "5m": round(load_avg[1], 2),
                "15m": round(load_avg[2], 2)
            }
        except Exception as e:
            return {"error": f"Failed to get load average: {str(e)}"}

    def get_swap_metrics(self) -> Dict[str, Any]:
        """Get swap memory utilization metrics."""
        try:
            swap = psutil.swap_memory()
            return {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2),
                "usage_percent": round(swap.percent, 2),
                "sin": swap.sin,  # Pages swapped in
                "sout": swap.sout  # Pages swapped out
            }
        except Exception as e:
            return {"error": f"Failed to get swap metrics: {str(e)}"}

    def get_system_info(self) -> Dict[str, Any]:
        """Get general system information."""
        try:
            # Get system uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_days = int(uptime_seconds // (24 * 3600))
            uptime_hours = int((uptime_seconds % (24 * 3600)) // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)

            # Get process count
            process_count = len(psutil.pids())

            return {
                "uptime": {
                    "seconds": int(uptime_seconds),
                    "formatted": f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
                },
                "processes": {
                    "total_count": process_count
                },
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat() + "Z"
            }
        except Exception as e:
            return {"error": f"Failed to get system info: {str(e)}"}

    def get_gpu_metrics(self) -> List[Dict[str, Any]]:
        """Get GPU utilization metrics for NVIDIA GPUs."""
        if not NVML_AVAILABLE:
            return [{"error": "pynvml library not available. Install with: pip install pynvml"}]

        # Try to initialize NVML if not already done
        if not self.nvml_initialized:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
            except Exception as e:
                return [{"error": f"Failed to initialize NVML: {str(e)}. Make sure NVIDIA drivers are installed and GPU is accessible."}]

        try:
            gpu_metrics = []
            device_count = pynvml.nvmlDeviceGetCount()

            if device_count == 0:
                return [{"error": "No NVIDIA GPUs detected"}]

            for i in range(device_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                    # Get GPU name
                    name = pynvml.nvmlDeviceGetName(handle)

                    # Get utilization rates
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

                    # Get memory info
                    memory = pynvml.nvmlDeviceGetMemoryInfo(handle)

                    # Get temperature
                    temperature_f = None
                    try:
                        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        # Convert Celsius to Fahrenheit
                        temperature_f = round((temperature * 9/5) + 32, 1)
                    except Exception as e:
                        print(f"Warning: Could not get temperature for GPU {i}: {e}")

                    # Get clock frequencies
                    graphics_clock = None
                    memory_clock = None
                    try:
                        graphics_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
                        memory_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
                    except Exception as e:
                        print(f"Warning: Could not get clock info for GPU {i}: {e}")

                    # Get power usage
                    power_usage = None
                    power_limit = None
                    try:
                        power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                        power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
                    except Exception as e:
                        print(f"Warning: Could not get power info for GPU {i}: {e}")

                    gpu_metrics.append({
                        "index": i,
                        "name": name.decode('utf-8') if isinstance(name, bytes) else str(name),
                        "utilization": {
                            "gpu_percent": utilization.gpu,
                            "memory_percent": utilization.memory
                        },
                        "memory": {
                            "total_mb": memory.total // (1024 * 1024),
                            "used_mb": memory.used // (1024 * 1024),
                            "free_mb": memory.free // (1024 * 1024)
                        },
                        "temperature_fahrenheit": temperature_f,
                        "clocks": {
                            "graphics_mhz": graphics_clock,
                            "memory_mhz": memory_clock
                        },
                        "power": {
                            "usage_watts": round(power_usage, 2) if power_usage else None,
                            "limit_watts": round(power_limit, 2) if power_limit else None
                        }
                    })
                except Exception as e:
                    gpu_metrics.append({
                        "index": i,
                        "error": f"Failed to get metrics for GPU {i}: {str(e)}"
                    })

            return gpu_metrics
        except Exception as e:
            return [{"error": f"Failed to get GPU metrics: {str(e)}"}]

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all system utilization metrics."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cpu": self.get_cpu_metrics(),
            "memory": self.get_memory_metrics(),
            "disk": self.get_disk_metrics(),
            "network": self.get_network_metrics(),
            "gpu": self.get_gpu_metrics(),
            "load_average": self.get_load_average(),
            "swap": self.get_swap_metrics(),
            "system": self.get_system_info()
        }


# Global instance
system_metrics_service = SystemMetricsService()