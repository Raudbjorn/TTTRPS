"""
Memory management system for optimal resource utilization across backends
"""

import gc
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from weakref import WeakSet
from ..core.result import Result

logger = logging.getLogger(__name__)


class MemoryPressure(Enum):
    """Memory pressure levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_mb: float = 0.0
    available_mb: float = 0.0
    used_mb: float = 0.0
    usage_percent: float = 0.0
    cached_mb: float = 0.0
    buffer_mb: float = 0.0
    gpu_total_mb: float = 0.0
    gpu_used_mb: float = 0.0
    gpu_free_mb: float = 0.0
    swap_total_mb: float = 0.0
    swap_used_mb: float = 0.0


@dataclass
class MemoryConfig:
    """Memory management configuration."""
    memory_limit_mb: Optional[float] = None
    high_watermark_percent: float = 80.0
    critical_watermark_percent: float = 95.0
    cleanup_interval_seconds: float = 30.0
    aggressive_cleanup_threshold: float = 85.0
    enable_monitoring: bool = True
    enable_auto_cleanup: bool = True
    cache_size_limit_mb: float = 512.0
    gpu_memory_fraction: float = 0.9
    enable_memory_mapping: bool = True
    preallocation_size_mb: float = 100.0


class MemoryManager:
    """Advanced memory management for ML/embedding workloads."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.stats = MemoryStats()
        self.pressure_level = MemoryPressure.LOW

        # Cache management
        self.cache_registry: Dict[str, Any] = {}

        # Memory monitoring
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.cleanup_callbacks: List[Callable[[], int]] = []
        self.memory_pressure_callbacks: List[Callable[[MemoryPressure], None]] = []

        # Resource tracking
        self.allocated_objects: Dict[str, Any] = {}
        self.memory_pools: Dict[str, List[Any]] = {}

        self._setup_monitoring()

    def _setup_monitoring(self):
        """Setup memory monitoring system."""
        if self.config.enable_monitoring:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
            self.monitor_thread.start()
            logger.info("Memory monitoring started")

    def _monitor_memory(self):
        """Main memory monitoring loop."""
        while self.monitoring_active:
            try:
                # Update memory statistics
                self._update_memory_stats()

                # Determine memory pressure
                old_pressure = self.pressure_level
                self.pressure_level = self._calculate_memory_pressure()

                # Notify if pressure level changed
                if old_pressure != self.pressure_level:
                    self._notify_pressure_change(self.pressure_level)

                # Auto cleanup if enabled and needed
                if self.config.enable_auto_cleanup:
                    self._auto_cleanup()

                # Sleep until next check
                time.sleep(self.config.cleanup_interval_seconds)

            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")

    def _update_memory_stats(self):
        """Update current memory statistics."""
        try:
            import psutil

            # System memory
            memory = psutil.virtual_memory()
            self.stats.total_mb = memory.total / (1024 * 1024)
            self.stats.available_mb = memory.available / (1024 * 1024)
            self.stats.used_mb = memory.used / (1024 * 1024)
            self.stats.usage_percent = memory.percent
            self.stats.cached_mb = getattr(memory, 'cached', 0) / (1024 * 1024)
            self.stats.buffer_mb = getattr(memory, 'buffers', 0) / (1024 * 1024)

            # Swap memory
            swap = psutil.swap_memory()
            self.stats.swap_total_mb = swap.total / (1024 * 1024)
            self.stats.swap_used_mb = swap.used / (1024 * 1024)

            # GPU memory (if available)
            self._update_gpu_memory_stats()

        except ImportError:
            logger.warning("psutil not available for memory monitoring")
        except Exception as e:
            logger.error(f"Failed to update memory stats: {e}")

    def _update_gpu_memory_stats(self):
        """Update GPU memory statistics."""
        try:
            # Try NVIDIA GPU first
            try:
                import pynvml
                if not hasattr(self, '_nvml_initialized'):
                    pynvml.nvmlInit()
                    self._nvml_initialized = True

                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    # Get stats for first GPU (could be extended for multi-GPU)
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                    self.stats.gpu_total_mb = mem_info.total / (1024 * 1024)
                    self.stats.gpu_used_mb = mem_info.used / (1024 * 1024)
                    self.stats.gpu_free_mb = mem_info.free / (1024 * 1024)

            except ImportError:
                # Try PyTorch CUDA
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_memory = torch.cuda.memory_stats()
                        self.stats.gpu_total_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
                        self.stats.gpu_used_mb = torch.cuda.memory_allocated() / (1024 * 1024)
                        self.stats.gpu_free_mb = self.stats.gpu_total_mb - self.stats.gpu_used_mb

                except ImportError:
                    pass

        except Exception as e:
            logger.debug(f"GPU memory stats unavailable: {e}")

    def _calculate_memory_pressure(self) -> MemoryPressure:
        """Calculate current memory pressure level."""
        usage_percent = self.stats.usage_percent

        if usage_percent >= self.config.critical_watermark_percent:
            return MemoryPressure.CRITICAL
        elif usage_percent >= self.config.high_watermark_percent:
            return MemoryPressure.HIGH
        elif usage_percent >= 60.0:
            return MemoryPressure.MEDIUM
        else:
            return MemoryPressure.LOW

    def _notify_pressure_change(self, new_pressure: MemoryPressure):
        """Notify callbacks of memory pressure change."""
        logger.info(f"Memory pressure changed to: {new_pressure.value}")

        for callback in self.memory_pressure_callbacks:
            try:
                callback(new_pressure)
            except Exception as e:
                logger.error(f"Memory pressure callback failed: {e}")

    def _auto_cleanup(self):
        """Perform automatic memory cleanup based on pressure."""
        if self.pressure_level in [MemoryPressure.HIGH, MemoryPressure.CRITICAL]:
            bytes_freed = self.cleanup_memory()
            if bytes_freed > 0:
                logger.info(f"Auto cleanup freed {bytes_freed / (1024*1024):.1f} MB")

    def cleanup_memory(self, aggressive: bool = None) -> int:
        """Perform memory cleanup and return bytes freed."""
        if aggressive is None:
            aggressive = self.pressure_level == MemoryPressure.CRITICAL

        bytes_freed = 0

        try:
            # Clear Python garbage collection
            before_gc = len(gc.get_objects())
            collected = gc.collect()
            after_gc = len(gc.get_objects())

            logger.debug(f"GC collected {collected} objects, {before_gc - after_gc} objects freed")

            # Clear registered caches
            for cache_name, cache_obj in self.cache_registry.items():
                if hasattr(cache_obj, 'clear'):
                    try:
                        cache_obj.clear()
                        logger.debug(f"Cleared cache: {cache_name}")
                    except Exception as e:
                        logger.warning(f"Failed to clear cache {cache_name}: {e}")

            # Run cleanup callbacks
            for callback in self.cleanup_callbacks:
                try:
                    freed = callback()
                    if isinstance(freed, int):
                        bytes_freed += freed
                except Exception as e:
                    logger.error(f"Cleanup callback failed: {e}")

            # Aggressive cleanup for critical pressure
            if aggressive:
                bytes_freed += self._aggressive_cleanup()

            return bytes_freed

        except Exception as e:
            logger.error(f"Memory cleanup failed: {e}")
            return 0

    def _aggressive_cleanup(self) -> int:
        """Perform aggressive memory cleanup."""
        bytes_freed = 0

        try:
            # Track memory before cleanup
            memory_before = self._get_current_memory_usage()

            # Clear PyTorch cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory_before = torch.cuda.memory_allocated()
                    torch.cuda.empty_cache()
                    gpu_memory_after = torch.cuda.memory_allocated()
                    gpu_freed = gpu_memory_before - gpu_memory_after
                    bytes_freed += max(0, gpu_freed)
                    logger.debug(f"Cleared PyTorch CUDA cache: {gpu_freed / (1024*1024):.1f}MB freed")
            except ImportError:
                pass

            # Clear TensorFlow memory if available
            try:
                import tensorflow as tf
                # Force garbage collection in TF
                tf.keras.backend.clear_session()
                logger.debug("Cleared TensorFlow session")
            except ImportError:
                pass

            # Clear object pools and track their sizes
            for pool_name, pool in self.memory_pools.items():
                pool_size = len(pool)
                pool.clear()
                # Estimate based on typical object size (rough estimate)
                estimated_pool_freed = pool_size * 1024  # 1KB per object estimate
                bytes_freed += estimated_pool_freed
                logger.debug(f"Cleared memory pool '{pool_name}': {pool_size} objects")

            # Track memory after cleanup for more accurate measurement
            memory_after = self._get_current_memory_usage()
            system_freed = max(0, memory_before - memory_after)

            # Use the larger of system measurement or component-based tracking
            total_freed = max(bytes_freed, system_freed)

            return total_freed

        except Exception as e:
            logger.error(f"Aggressive cleanup failed: {e}")
            return 0

    def _get_current_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.used
        except ImportError:
            import os
            # Fallback using os if psutil not available
            if hasattr(os, 'statvfs'):  # Unix-like systems
                return 0  # Cannot get reliable memory info without psutil
            return 0
        except Exception:
            return 0

    def register_cache(self, name: str, cache_obj: Any):
        """Register a cache for automatic cleanup."""
        self.cache_registry[name] = cache_obj
        logger.debug(f"Registered cache: {name}")

    def unregister_cache(self, name: str):
        """Unregister a cache."""
        if name in self.cache_registry:
            del self.cache_registry[name]
            logger.debug(f"Unregistered cache: {name}")

    def add_cleanup_callback(self, callback: Callable[[], int]):
        """Add cleanup callback that returns bytes freed."""
        self.cleanup_callbacks.append(callback)

    def add_pressure_callback(self, callback: Callable[[MemoryPressure], None]):
        """Add memory pressure change callback."""
        self.memory_pressure_callbacks.append(callback)

    def allocate_buffer(self, name: str, size_mb: float) -> Result[bytes, str]:
        """Allocate a managed memory buffer."""
        try:
            if not self._check_allocation_feasible(size_mb):
                return Result.Err(f"Cannot allocate {size_mb}MB - insufficient memory")

            size_bytes = int(size_mb * 1024 * 1024)
            buffer = bytearray(size_bytes)

            self.allocated_objects[name] = {
                'buffer': buffer,
                'size_mb': size_mb,
                'allocated_at': time.time()
            }

            logger.debug(f"Allocated buffer '{name}': {size_mb:.1f}MB")
            return Result.Ok(buffer)

        except Exception as e:
            return Result.Err(f"Buffer allocation failed: {str(e)}")

    def deallocate_buffer(self, name: str) -> bool:
        """Deallocate a managed memory buffer."""
        if name in self.allocated_objects:
            obj_info = self.allocated_objects[name]
            del self.allocated_objects[name]

            # Force garbage collection to free memory immediately
            gc.collect()

            logger.debug(f"Deallocated buffer '{name}': {obj_info['size_mb']:.1f}MB")
            return True
        return False

    def create_memory_pool(self, name: str, object_factory: Callable, initial_size: int = 10):
        """Create a memory pool for object reuse."""
        if name not in self.memory_pools:
            pool = [object_factory() for _ in range(initial_size)]
            self.memory_pools[name] = pool
            logger.debug(f"Created memory pool '{name}' with {initial_size} objects")

    def get_from_pool(self, name: str, factory: Callable = None):
        """Get object from memory pool."""
        if name in self.memory_pools and self.memory_pools[name]:
            return self.memory_pools[name].pop()
        elif factory:
            return factory()
        else:
            return None

    def return_to_pool(self, name: str, obj: Any):
        """Return object to memory pool."""
        if name in self.memory_pools:
            # Reset object if it has a reset method
            if hasattr(obj, 'reset'):
                try:
                    obj.reset()
                except Exception as e:
                    logger.debug(f"Failed to reset object in pool '{name}': {e}")

            self.memory_pools[name].append(obj)

    def _check_allocation_feasible(self, size_mb: float) -> bool:
        """Check if allocation is feasible given current memory state."""
        if self.pressure_level == MemoryPressure.CRITICAL:
            return False

        if self.config.memory_limit_mb:
            total_used = self.stats.used_mb + size_mb
            return total_used <= self.config.memory_limit_mb

        # Check if we have enough available memory with safety margin
        safety_margin_mb = 100  # Keep 100MB free
        return self.stats.available_mb > (size_mb + safety_margin_mb)

    def optimize_for_inference(self):
        """Optimize memory settings for inference workloads."""
        # Perform aggressive cleanup
        self.cleanup_memory(aggressive=True)

        # Disable debugging features that consume memory
        if hasattr(gc, 'set_debug'):
            gc.set_debug(0)

        # Set optimal GC thresholds
        gc.set_threshold(700, 10, 10)

        logger.info("Memory optimized for inference")

    def optimize_for_training(self):
        """Optimize memory settings for training workloads."""
        # Less aggressive cleanup for training
        self.cleanup_memory(aggressive=False)

        # Set GC thresholds for training workload
        gc.set_threshold(1000, 15, 15)

        logger.info("Memory optimized for training")

    def get_memory_info(self) -> Dict[str, Any]:
        """Get comprehensive memory information."""
        return {
            'system_memory': {
                'total_mb': self.stats.total_mb,
                'used_mb': self.stats.used_mb,
                'available_mb': self.stats.available_mb,
                'usage_percent': self.stats.usage_percent,
                'cached_mb': self.stats.cached_mb,
                'buffer_mb': self.stats.buffer_mb
            },
            'gpu_memory': {
                'total_mb': self.stats.gpu_total_mb,
                'used_mb': self.stats.gpu_used_mb,
                'free_mb': self.stats.gpu_free_mb
            },
            'swap_memory': {
                'total_mb': self.stats.swap_total_mb,
                'used_mb': self.stats.swap_used_mb
            },
            'pressure_level': self.pressure_level.value,
            'allocated_objects': len(self.allocated_objects),
            'memory_pools': {name: len(pool) for name, pool in self.memory_pools.items()},
            'registered_caches': list(self.cache_registry.keys())
        }

    def set_memory_limit(self, limit_mb: Optional[float]):
        """Set memory usage limit."""
        self.config.memory_limit_mb = limit_mb
        logger.info(f"Memory limit set to: {limit_mb}MB" if limit_mb else "Memory limit removed")

    def get_recommendations(self) -> List[str]:
        """Get memory optimization recommendations."""
        recommendations = []

        if self.pressure_level in [MemoryPressure.HIGH, MemoryPressure.CRITICAL]:
            recommendations.append("Consider reducing batch size or chunk size")
            recommendations.append("Enable aggressive memory cleanup")

        if self.stats.swap_used_mb > 0:
            recommendations.append("System is using swap memory - consider adding more RAM")

        if self.stats.gpu_used_mb > self.stats.gpu_total_mb * 0.9:
            recommendations.append("GPU memory usage is high - consider reducing model size")

        if len(self.allocated_objects) > 100:
            recommendations.append("Large number of allocated objects - consider using memory pools")

        return recommendations

    def shutdown(self):
        """Shutdown memory manager and cleanup."""
        logger.info("Shutting down MemoryManager")

        # Stop monitoring
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        # Final cleanup
        self.cleanup_memory(aggressive=True)

        # Clear all managed objects
        self.allocated_objects.clear()
        self.memory_pools.clear()
        self.cache_registry.clear()

        # Shutdown NVML if initialized
        if hasattr(self, '_nvml_initialized') and self._nvml_initialized:
            try:
                import pynvml
                pynvml.nvmlShutdown()
                self._nvml_initialized = False
                logger.debug("NVML shutdown complete")
            except Exception as e:
                logger.debug(f"NVML shutdown failed: {e}")

        logger.info("MemoryManager shutdown complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


# Global memory manager instance
global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager."""
    global global_memory_manager

    if global_memory_manager is None:
        config = MemoryConfig()
        global_memory_manager = MemoryManager(config)

    return global_memory_manager


def cleanup_memory() -> int:
    """Convenience function for global memory cleanup."""
    return get_memory_manager().cleanup_memory()


def get_memory_pressure() -> MemoryPressure:
    """Get current memory pressure level."""
    return get_memory_manager().pressure_level