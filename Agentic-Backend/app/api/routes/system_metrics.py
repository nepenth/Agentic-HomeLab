from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.services.system_metrics_service import system_metrics_service

router = APIRouter()


@router.get("/system/metrics", summary="Get System Utilization Metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """
    Get comprehensive system utilization metrics including CPU, memory, disk, network, and GPU.

    Returns detailed metrics for:
    - CPU: usage percentage, frequency, times breakdown
    - Memory: total, used, available, usage percentage
    - Disk: usage statistics and I/O metrics
    - Network: I/O statistics and interface information
    - GPU: utilization, memory, temperature (Fahrenheit), clocks, power (for NVIDIA GPUs)

    This endpoint is useful for monitoring system performance and resource utilization.
    """
    try:
        return system_metrics_service.get_all_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system metrics: {str(e)}"
        )


@router.get("/system/metrics/cpu", summary="Get CPU Metrics")
async def get_cpu_metrics() -> Dict[str, Any]:
    """Get CPU utilization and performance metrics."""
    try:
        return system_metrics_service.get_cpu_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve CPU metrics: {str(e)}"
        )


@router.get("/system/metrics/memory", summary="Get Memory Metrics")
async def get_memory_metrics() -> Dict[str, Any]:
    """Get memory utilization metrics."""
    try:
        return system_metrics_service.get_memory_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve memory metrics: {str(e)}"
        )


@router.get("/system/metrics/disk", summary="Get Disk Metrics")
async def get_disk_metrics() -> Dict[str, Any]:
    """Get disk utilization and I/O metrics."""
    try:
        return system_metrics_service.get_disk_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve disk metrics: {str(e)}"
        )


@router.get("/system/metrics/network", summary="Get Network Metrics")
async def get_network_metrics() -> Dict[str, Any]:
    """Get network I/O and interface metrics."""
    try:
        return system_metrics_service.get_network_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve network metrics: {str(e)}"
        )


@router.get("/system/metrics/gpu", summary="Get GPU Metrics")
async def get_gpu_metrics() -> List[Dict[str, Any]]:
    """
    Get GPU utilization metrics for NVIDIA GPUs.

    Returns metrics for Tesla P40 GPUs including:
    - GPU utilization percentage
    - Memory usage and frequency
    - Temperature in Fahrenheit
    - Clock frequencies
    - Power consumption
    """
    try:
        gpu_data = system_metrics_service.get_gpu_metrics()
        return gpu_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve GPU metrics: {str(e)}"
        )


@router.get("/system/metrics/load", summary="Get System Load Average")
async def get_load_average() -> Dict[str, Any]:
    """Get system load average metrics for 1, 5, and 15 minute periods."""
    try:
        return system_metrics_service.get_load_average()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve load average metrics: {str(e)}"
        )


@router.get("/system/metrics/swap", summary="Get Swap Memory Metrics")
async def get_swap_metrics() -> Dict[str, Any]:
    """Get swap memory utilization metrics."""
    try:
        return system_metrics_service.get_swap_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve swap metrics: {str(e)}"
        )


@router.get("/system/info", summary="Get System Information")
async def get_system_info() -> Dict[str, Any]:
    """
    Get general system information including uptime and process count.

    Returns:
    - System uptime in seconds and formatted string
    - Total process count
    - System boot time
    """
    try:
        return system_metrics_service.get_system_info()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system info: {str(e)}"
        )