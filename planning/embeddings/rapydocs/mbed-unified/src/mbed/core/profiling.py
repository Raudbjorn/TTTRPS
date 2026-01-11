"""
Performance profiling infrastructure for MBED system (T131)

This module provides comprehensive profiling capabilities including:
- CPU profiling with cProfile/py-spy integration
- Memory profiling with tracemalloc/memray
- GPU profiling with NVIDIA nsys integration  
- Custom performance metrics and monitoring
"""

import time
import cProfile
import pstats
import io
import functools
import tracemalloc
import psutil
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
import json

logger = logging.getLogger(__name__)


@dataclass
class ProfileMetrics:
    """Container for profiling metrics"""
    name: str
    duration_ms: float
    peak_memory_mb: float
    avg_memory_mb: float
    cpu_percent: float
    gpu_utilization: Optional[float] = None
    gpu_memory_mb: Optional[float] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class PerformanceProfiler:
    """
    Comprehensive performance profiler for MBED system
    
    Features:
    - Automatic CPU/memory profiling
    - GPU metrics collection (NVIDIA)
    - Custom metric tracking
    - Report generation
    - Integration with py-spy and memray
    """
    
    def __init__(self, 
                 enable_memory_profiling: bool = True,
                 enable_gpu_profiling: bool = True,
                 profile_dir: Optional[Path] = None):
        """
        Initialize profiler
        
        Args:
            enable_memory_profiling: Enable memory usage tracking
            enable_gpu_profiling: Enable GPU metrics (requires pynvml)
            profile_dir: Directory to save profile reports
        """
        self.enable_memory_profiling = enable_memory_profiling
        self.enable_gpu_profiling = enable_gpu_profiling
        self.profile_dir = profile_dir or Path("./profiles")
        self.profile_dir.mkdir(exist_ok=True)
        
        self._metrics: List[ProfileMetrics] = []
        self._lock = Lock()
        self._start_times: Dict[str, float] = {}
        
        # Initialize memory profiling
        if self.enable_memory_profiling:
            try:
                tracemalloc.start()
                logger.debug("Memory profiling enabled")
            except Exception as e:
                logger.warning(f"Could not start memory profiling: {e}")
                self.enable_memory_profiling = False
        
        # Initialize GPU profiling
        self.gpu_available = False
        if self.enable_gpu_profiling:
            try:
                import pynvml
                pynvml.nvmlInit()
                self.gpu_available = True
                logger.debug("GPU profiling enabled")
            except ImportError:
                logger.debug("pynvml not available, GPU profiling disabled")
            except Exception as e:
                logger.warning(f"Could not initialize GPU profiling: {e}")
    
    def profile_function(self, name: Optional[str] = None):
        """
        Decorator to profile a function
        
        Args:
            name: Custom name for the profile (defaults to function name)
            
        Example:
            @profiler.profile_function("embedding_generation")
            def generate_embeddings(self, texts):
                # function code
                return embeddings
        """
        def decorator(func: Callable) -> Callable:
            profile_name = name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.profile_context(profile_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @contextmanager
    def profile_context(self, name: str):
        """
        Context manager for profiling code blocks
        
        Args:
            name: Name for this profiling session
            
        Example:
            with profiler.profile_context("batch_processing"):
                # code to profile
                results = process_batch(data)
        """
        start_time = time.perf_counter()
        start_memory = 0
        gpu_start = {}
        
        # Get initial memory usage
        if self.enable_memory_profiling:
            try:
                _, start_memory = tracemalloc.get_traced_memory()
                start_memory = start_memory / (1024 * 1024)  # MB
            except Exception:
                start_memory = 0
        
        # Get initial GPU state
        if self.gpu_available:
            gpu_start = self._get_gpu_metrics()
        
        # Get initial CPU usage
        cpu_start = psutil.cpu_percent(interval=None)
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            # Calculate memory usage
            peak_memory = avg_memory = start_memory
            if self.enable_memory_profiling:
                try:
                    current, peak = tracemalloc.get_traced_memory()
                    peak_memory = peak / (1024 * 1024)  # MB
                    avg_memory = (start_memory + current / (1024 * 1024)) / 2
                except Exception:
                    pass
            
            # Get final CPU usage
            cpu_end = psutil.cpu_percent(interval=None)
            cpu_percent = (cpu_start + cpu_end) / 2
            
            # Calculate GPU metrics
            gpu_utilization = None
            gpu_memory = None
            if self.gpu_available and gpu_start:
                gpu_end = self._get_gpu_metrics()
                gpu_utilization = (gpu_start.get("utilization", 0) + 
                                  gpu_end.get("utilization", 0)) / 2
                gpu_memory = max(gpu_start.get("memory_used_mb", 0),
                                gpu_end.get("memory_used_mb", 0))
            
            # Create metrics object
            metrics = ProfileMetrics(
                name=name,
                duration_ms=duration_ms,
                peak_memory_mb=peak_memory,
                avg_memory_mb=avg_memory,
                cpu_percent=cpu_percent,
                gpu_utilization=gpu_utilization,
                gpu_memory_mb=gpu_memory
            )
            
            # Store metrics
            with self._lock:
                self._metrics.append(metrics)
            
            logger.debug(f"Profile [{name}]: {duration_ms:.2f}ms, "
                        f"{peak_memory:.1f}MB peak memory")
    
    def _get_gpu_metrics(self, device_id: int = 0) -> Dict[str, float]:
        """Get current GPU metrics
        
        Args:
            device_id: GPU device index to query (default: 0)
        
        Returns:
            Dictionary of GPU metrics
        """
        metrics = {}
        try:
            import pynvml
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            
            # Get utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            metrics["utilization"] = util.gpu
            
            # Get memory info
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics["memory_used_mb"] = meminfo.used / (1024 * 1024)
            metrics["memory_total_mb"] = meminfo.total / (1024 * 1024)
            
        except Exception as e:
            logger.debug(f"Could not get GPU metrics: {e}")
        
        return metrics
    
    def add_custom_metric(self, name: str, key: str, value: Any):
        """
        Add custom metric to the most recent profile
        
        Args:
            name: Profile name to add metric to
            key: Metric key
            value: Metric value
        """
        with self._lock:
            for metric in reversed(self._metrics):
                if metric.name == name:
                    metric.custom_metrics[key] = value
                    break
    
    def get_metrics(self, name_filter: Optional[str] = None) -> List[ProfileMetrics]:
        """
        Get collected metrics
        
        Args:
            name_filter: Filter metrics by name pattern
            
        Returns:
            List of ProfileMetrics
        """
        with self._lock:
            if name_filter:
                return [m for m in self._metrics if name_filter in m.name]
            return self._metrics.copy()
    
    def generate_report(self, 
                       output_file: Optional[Path] = None,
                       format: str = "json") -> str:
        """
        Generate performance report
        
        Args:
            output_file: File to save report to
            format: Report format ("json", "text")
            
        Returns:
            Report content as string
        """
        metrics = self.get_metrics()
        
        if format == "json":
            report_data = {
                "summary": self._generate_summary(metrics),
                "profiles": [self._metric_to_dict(m) for m in metrics]
            }
            report = json.dumps(report_data, indent=2)
        else:
            report = self._generate_text_report(metrics)
        
        if output_file:
            output_file.write_text(report)
            logger.info(f"Performance report saved to {output_file}")
        
        return report
    
    def _generate_summary(self, metrics: List[ProfileMetrics]) -> Dict[str, Any]:
        """Generate summary statistics"""
        if not metrics:
            return {}
        
        durations = [m.duration_ms for m in metrics]
        memories = [m.peak_memory_mb for m in metrics]
        
        return {
            "total_profiles": len(metrics),
            "total_duration_ms": sum(durations),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "avg_memory_mb": sum(memories) / len(memories),
            "peak_memory_mb": max(memories)
        }
    
    def _metric_to_dict(self, metric: ProfileMetrics) -> Dict[str, Any]:
        """Convert ProfileMetrics to dictionary"""
        return {
            "name": metric.name,
            "duration_ms": metric.duration_ms,
            "peak_memory_mb": metric.peak_memory_mb,
            "avg_memory_mb": metric.avg_memory_mb,
            "cpu_percent": metric.cpu_percent,
            "gpu_utilization": metric.gpu_utilization,
            "gpu_memory_mb": metric.gpu_memory_mb,
            "custom_metrics": metric.custom_metrics,
            "timestamp": metric.timestamp
        }
    
    def _generate_text_report(self, metrics: List[ProfileMetrics]) -> str:
        """Generate human-readable text report"""
        lines = ["Performance Report", "=" * 50, ""]
        
        summary = self._generate_summary(metrics)
        lines.extend([
            f"Total Profiles: {summary.get('total_profiles', 0)}",
            f"Total Duration: {summary.get('total_duration_ms', 0):.2f}ms",
            f"Average Duration: {summary.get('avg_duration_ms', 0):.2f}ms",
            f"Peak Memory: {summary.get('peak_memory_mb', 0):.1f}MB",
            ""
        ])
        
        lines.append("Detailed Results:")
        lines.append("-" * 30)
        
        for metric in metrics:
            lines.extend([
                f"Profile: {metric.name}",
                f"  Duration: {metric.duration_ms:.2f}ms",
                f"  Memory: {metric.peak_memory_mb:.1f}MB (peak), {metric.avg_memory_mb:.1f}MB (avg)",
                f"  CPU: {metric.cpu_percent:.1f}%",
            ])
            
            if metric.gpu_utilization is not None:
                lines.append(f"  GPU: {metric.gpu_utilization:.1f}% util, {metric.gpu_memory_mb:.1f}MB mem")
            
            if metric.custom_metrics:
                lines.append(f"  Custom: {metric.custom_metrics}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        with self._lock:
            self._metrics.clear()
    
    def profile_with_cprofile(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run function with detailed cProfile profiling
        
        Args:
            func: Function to profile
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
        """
        pr = cProfile.Profile()
        pr.enable()
        
        try:
            result = func(*args, **kwargs)
        finally:
            pr.disable()
        
        # Save profile data
        profile_file = self.profile_dir / f"cprofile_{func.__name__}_{int(time.time())}.prof"
        pr.dump_stats(str(profile_file))
        
        # Generate text report
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        
        report_file = profile_file.with_suffix('.txt')
        report_file.write_text(s.getvalue())
        
        logger.info(f"cProfile results saved to {profile_file} and {report_file}")
        
        return result


# Global profiler instance
_profiler: Optional[PerformanceProfiler] = None


def get_profiler(
    enable_memory_profiling: bool = True,
    enable_gpu_profiling: bool = True,
    profile_dir: Optional[Path] = None
) -> PerformanceProfiler:
    """
    Get or create global profiler instance
    
    Args:
        enable_memory_profiling: Enable memory usage tracking
        enable_gpu_profiling: Enable GPU metrics
        profile_dir: Directory for profile reports
        
    Returns:
        PerformanceProfiler instance
    """
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler(
            enable_memory_profiling=enable_memory_profiling,
            enable_gpu_profiling=enable_gpu_profiling,
            profile_dir=profile_dir
        )
    return _profiler


# Convenience functions for common profiling tasks
def profile_function(name: Optional[str] = None):
    """Decorator to profile a function using global profiler"""
    return get_profiler().profile_function(name)


@contextmanager
def profile_context(name: str):
    """Context manager for profiling using global profiler"""
    with get_profiler().profile_context(name):
        yield


def benchmark_function(func: Callable, iterations: int = 10, *args, **kwargs) -> Dict[str, float]:
    """
    Benchmark a function with multiple iterations
    
    Args:
        func: Function to benchmark
        iterations: Number of iterations to run
        *args, **kwargs: Function arguments
        
    Returns:
        Dictionary with benchmark statistics
    """
    profiler = get_profiler()
    name = f"benchmark_{func.__name__}"
    
    # Clear previous metrics
    profiler.clear_metrics()
    
    # Run iterations
    for i in range(iterations):
        with profiler.profile_context(f"{name}_iter_{i}"):
            func(*args, **kwargs)
    
    # Calculate statistics
    metrics = profiler.get_metrics(name)
    durations = [m.duration_ms for m in metrics]
    memories = [m.peak_memory_mb for m in metrics]
    
    return {
        "iterations": iterations,
        "avg_duration_ms": sum(durations) / len(durations),
        "min_duration_ms": min(durations),
        "max_duration_ms": max(durations),
        "std_duration_ms": np.std(durations),
        "avg_memory_mb": sum(memories) / len(memories),
        "peak_memory_mb": max(memories)
    }