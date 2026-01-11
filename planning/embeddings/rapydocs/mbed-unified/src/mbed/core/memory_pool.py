"""
Memory pooling implementation for MBED system (T133)

This module provides efficient memory management through pooling:
- Tensor memory pools for embedding operations
- Buffer pools for I/O operations
- Automatic memory reuse and garbage collection
- Thread-safe pool management
"""

import gc
import weakref
import threading
import logging
import psutil
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)


@dataclass
class PoolStats:
    """Statistics for memory pool usage"""
    total_allocations: int = 0
    total_deallocations: int = 0
    current_allocated: int = 0
    peak_allocated: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_bytes_allocated: int = 0
    total_bytes_reused: int = 0


class TensorPool:
    """
    Memory pool for tensor/array allocations
    
    Reduces allocation overhead by reusing memory buffers
    """
    
    def __init__(self,
                 max_pool_size: int = 100,
                 enable_stats: bool = True):
        """
        Initialize tensor pool
        
        Args:
            max_pool_size: Maximum number of tensors to keep in pool
            enable_stats: Enable statistics tracking
        """
        self.max_pool_size = max_pool_size
        self.enable_stats = enable_stats
        
        # Pool storage by shape and dtype
        self._pools: Dict[Tuple[Tuple[int, ...], np.dtype], List[np.ndarray]] = defaultdict(list)
        self._torch_pools: Dict[Tuple[Tuple[int, ...], torch.dtype, str], List[torch.Tensor]] = defaultdict(list)
        
        # Statistics
        self.stats = PoolStats() if enable_stats else None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Track allocations for cleanup (use list since numpy arrays aren't hashable)
        self._allocations: List = []
    
    def get_numpy_array(self,
                        shape: Tuple[int, ...],
                        dtype: np.dtype = np.float32,
                        zero: bool = True) -> np.ndarray:
        """
        Get a numpy array from pool or allocate new
        
        Args:
            shape: Array shape
            dtype: Data type
            zero: Whether to zero the array
            
        Returns:
            Numpy array
        """
        key = (shape, dtype)
        
        with self._lock:
            # Try to get from pool
            if self._pools[key]:
                array = self._pools[key].pop()
                if self.stats:
                    self.stats.cache_hits += 1
                    self.stats.total_bytes_reused += array.nbytes
            else:
                # Allocate new
                array = np.empty(shape, dtype=dtype)
                if self.stats:
                    self.stats.cache_misses += 1
                    self.stats.total_allocations += 1
                    self.stats.total_bytes_allocated += array.nbytes
            
            # Track allocation
            self._allocations.append(array)
            
            if self.stats:
                self.stats.current_allocated += 1
                self.stats.peak_allocated = max(self.stats.peak_allocated, 
                                               self.stats.current_allocated)
            
            # Zero if requested
            if zero:
                array.fill(0)
            
            return array
    
    def get_torch_tensor(self,
                        shape: Tuple[int, ...],
                        dtype: torch.dtype = None,
                        device: Union[str, torch.device] = "cpu",
                        zero: bool = True) -> Optional[torch.Tensor]:
        """
        Get a PyTorch tensor from pool or allocate new
        
        Args:
            shape: Tensor shape
            dtype: Data type (defaults to torch.float32)
            device: Device to allocate on
            zero: Whether to zero the tensor
            
        Returns:
            PyTorch tensor or None if torch not available
        """
        if not HAS_TORCH:
            return None
        
        if dtype is None:
            dtype = torch.float32
        
        device_str = str(device)
        key = (shape, dtype, device_str)
        
        with self._lock:
            # Try to get from pool
            if self._torch_pools[key]:
                tensor = self._torch_pools[key].pop()
                if self.stats:
                    self.stats.cache_hits += 1
                    self.stats.total_bytes_reused += tensor.element_size() * tensor.nelement()
            else:
                # Allocate new
                tensor = torch.empty(shape, dtype=dtype, device=device)
                if self.stats:
                    self.stats.cache_misses += 1
                    self.stats.total_allocations += 1
                    self.stats.total_bytes_allocated += tensor.element_size() * tensor.nelement()
            
            # Track allocation  
            self._allocations.append(tensor)
            
            if self.stats:
                self.stats.current_allocated += 1
                self.stats.peak_allocated = max(self.stats.peak_allocated,
                                               self.stats.current_allocated)
            
            # Zero if requested
            if zero:
                tensor.zero_()
            
            return tensor
    
    def return_numpy_array(self, array: np.ndarray):
        """
        Return numpy array to pool
        
        Args:
            array: Array to return
        """
        if not isinstance(array, np.ndarray):
            return
        
        key = (array.shape, array.dtype)
        
        with self._lock:
            # Remove from active allocations tracking
            if array in self._allocations:
                self._allocations.remove(array)
            
            # Check pool size limit
            if len(self._pools[key]) < self.max_pool_size:
                self._pools[key].append(array)
            
            if self.stats:
                self.stats.current_allocated -= 1
                self.stats.total_deallocations += 1
    
    def return_torch_tensor(self, tensor: torch.Tensor):
        """
        Return PyTorch tensor to pool
        
        Args:
            tensor: Tensor to return
        """
        if not HAS_TORCH or not isinstance(tensor, torch.Tensor):
            return
        
        key = (tuple(tensor.shape), tensor.dtype, str(tensor.device))
        
        with self._lock:
            # Remove from active allocations tracking
            if tensor in self._allocations:
                self._allocations.remove(tensor)
            
            # Check pool size limit
            if len(self._torch_pools[key]) < self.max_pool_size:
                self._torch_pools[key].append(tensor)
            
            if self.stats:
                self.stats.current_allocated -= 1
                self.stats.total_deallocations += 1
    
    @contextmanager
    def numpy_array(self, *args, **kwargs):
        """
        Context manager for numpy array allocation
        
        Example:
            with pool.numpy_array((1024, 768)) as array:
                # Use array
                pass
            # Array automatically returned to pool
        """
        array = self.get_numpy_array(*args, **kwargs)
        try:
            yield array
        finally:
            self.return_numpy_array(array)
    
    @contextmanager
    def torch_tensor(self, *args, **kwargs):
        """
        Context manager for torch tensor allocation
        
        Example:
            with pool.torch_tensor((32, 512, 768), device="cuda") as tensor:
                # Use tensor
                pass
            # Tensor automatically returned to pool
        """
        tensor = self.get_torch_tensor(*args, **kwargs)
        try:
            yield tensor
        finally:
            if tensor is not None:
                self.return_torch_tensor(tensor)
    
    def clear_pool(self, force_gc: bool = False):
        """
        Clear all pooled memory
        
        Args:
            force_gc: Force garbage collection
        """
        with self._lock:
            self._pools.clear()
            self._torch_pools.clear()
            
            if force_gc:
                gc.collect()
                if HAS_TORCH and torch.cuda.is_available():
                    torch.cuda.empty_cache()
    
    def get_pool_info(self) -> Dict[str, Any]:
        """
        Get information about pool state
        
        Returns:
            Pool information dictionary
        """
        with self._lock:
            numpy_shapes = list(self._pools.keys())
            torch_shapes = list(self._torch_pools.keys())
            
            numpy_count = sum(len(pool) for pool in self._pools.values())
            torch_count = sum(len(pool) for pool in self._torch_pools.values())
            
            numpy_bytes = sum(
                sum(arr.nbytes for arr in pool)
                for pool in self._pools.values()
            )
            
            torch_bytes = 0
            if HAS_TORCH:
                torch_bytes = sum(
                    sum(t.element_size() * t.nelement() for t in pool)
                    for pool in self._torch_pools.values()
                )
            
            info = {
                "numpy_shapes": len(numpy_shapes),
                "torch_shapes": len(torch_shapes),
                "numpy_arrays_pooled": numpy_count,
                "torch_tensors_pooled": torch_count,
                "numpy_bytes_pooled": numpy_bytes,
                "torch_bytes_pooled": torch_bytes,
                "total_bytes_pooled": numpy_bytes + torch_bytes
            }
            
            if self.stats:
                info["stats"] = {
                    "total_allocations": self.stats.total_allocations,
                    "total_deallocations": self.stats.total_deallocations,
                    "current_allocated": self.stats.current_allocated,
                    "peak_allocated": self.stats.peak_allocated,
                    "cache_hit_rate": self.stats.cache_hits / max(1, self.stats.cache_hits + self.stats.cache_misses),
                    "total_bytes_allocated": self.stats.total_bytes_allocated,
                    "total_bytes_reused": self.stats.total_bytes_reused,
                    "reuse_rate": self.stats.total_bytes_reused / max(1, self.stats.total_bytes_allocated)
                }
            
            return info


class BufferPool:
    """
    Memory pool for byte buffers (I/O operations)
    """
    
    def __init__(self,
                 buffer_sizes: List[int] = None,
                 max_buffers_per_size: int = 10):
        """
        Initialize buffer pool
        
        Args:
            buffer_sizes: List of buffer sizes to pool
            max_buffers_per_size: Maximum buffers per size
        """
        self.buffer_sizes = buffer_sizes or [
            1024,        # 1KB
            4096,        # 4KB
            16384,       # 16KB
            65536,       # 64KB
            262144,      # 256KB
            1048576,     # 1MB
            4194304,     # 4MB
        ]
        self.max_buffers_per_size = max_buffers_per_size
        
        # Pool storage
        self._pools: Dict[int, List[bytearray]] = defaultdict(list)
        self._lock = threading.RLock()
        self.stats = PoolStats()
    
    def get_buffer(self, size: int) -> bytearray:
        """
        Get a buffer of at least the requested size
        
        Args:
            size: Minimum buffer size needed
            
        Returns:
            Bytearray buffer
        """
        # Find appropriate buffer size
        buffer_size = size
        for pool_size in self.buffer_sizes:
            if pool_size >= size:
                buffer_size = pool_size
                break
        
        with self._lock:
            # Try to get from pool
            if self._pools[buffer_size]:
                buffer = self._pools[buffer_size].pop()
                self.stats.cache_hits += 1
                self.stats.total_bytes_reused += len(buffer)
            else:
                # Allocate new
                buffer = bytearray(buffer_size)
                self.stats.cache_misses += 1
                self.stats.total_allocations += 1
                self.stats.total_bytes_allocated += buffer_size
            
            self.stats.current_allocated += 1
            self.stats.peak_allocated = max(self.stats.peak_allocated,
                                           self.stats.current_allocated)
            
            return buffer
    
    def return_buffer(self, buffer: bytearray):
        """
        Return buffer to pool
        
        Args:
            buffer: Buffer to return
        """
        if not isinstance(buffer, bytearray):
            return
        
        size = len(buffer)
        
        with self._lock:
            # Only pool standard sizes
            if size in self.buffer_sizes and len(self._pools[size]) < self.max_buffers_per_size:
                # Clear buffer for security
                buffer[:] = b'\x00' * size  # Clear entire buffer
                self._pools[size].append(buffer)
            
            self.stats.current_allocated -= 1
            self.stats.total_deallocations += 1
    
    @contextmanager
    def buffer(self, size: int):
        """
        Context manager for buffer allocation
        
        Example:
            with pool.buffer(8192) as buf:
                # Use buffer
                pass
            # Buffer automatically returned
        """
        buf = self.get_buffer(size)
        try:
            yield buf
        finally:
            self.return_buffer(buf)
    
    def clear_pool(self):
        """Clear all pooled buffers"""
        with self._lock:
            self._pools.clear()


class MemoryPoolManager:
    """
    Global memory pool manager
    
    Coordinates multiple pools and provides unified interface
    """
    
    def __init__(self,
                 enable_tensor_pool: bool = True,
                 enable_buffer_pool: bool = True,
                 max_pool_size: int = 100):
        """
        Initialize memory pool manager
        
        Args:
            enable_tensor_pool: Enable tensor/array pooling
            enable_buffer_pool: Enable buffer pooling
            max_pool_size: Maximum items per pool
        """
        self.tensor_pool = TensorPool(max_pool_size) if enable_tensor_pool else None
        self.buffer_pool = BufferPool() if enable_buffer_pool else None
        
        # Periodic cleanup
        self._cleanup_counter = 0
        self._cleanup_interval = 1000
    
    def get_array(self, *args, **kwargs) -> np.ndarray:
        """Get numpy array from pool"""
        if self.tensor_pool:
            self._check_cleanup()
            return self.tensor_pool.get_numpy_array(*args, **kwargs)
        return np.empty(*args, **kwargs)
    
    def get_tensor(self, *args, **kwargs) -> Optional[torch.Tensor]:
        """Get torch tensor from pool"""
        if self.tensor_pool:
            self._check_cleanup()
            return self.tensor_pool.get_torch_tensor(*args, **kwargs)
        if HAS_TORCH:
            return torch.empty(*args, **kwargs)
        return None
    
    def get_buffer(self, size: int) -> bytearray:
        """Get buffer from pool"""
        if self.buffer_pool:
            return self.buffer_pool.get_buffer(size)
        return bytearray(size)
    
    def return_array(self, array: np.ndarray):
        """Return array to pool"""
        if self.tensor_pool:
            self.tensor_pool.return_numpy_array(array)
    
    def return_tensor(self, tensor: torch.Tensor):
        """Return tensor to pool"""
        if self.tensor_pool:
            self.tensor_pool.return_torch_tensor(tensor)
    
    def return_buffer(self, buffer: bytearray):
        """Return buffer to pool"""
        if self.buffer_pool:
            self.buffer_pool.return_buffer(buffer)
    
    @contextmanager
    def array(self, *args, **kwargs):
        """Context manager for array allocation"""
        array = self.get_array(*args, **kwargs)
        try:
            yield array
        finally:
            self.return_array(array)
    
    @contextmanager
    def tensor(self, *args, **kwargs):
        """Context manager for tensor allocation"""
        tensor = self.get_tensor(*args, **kwargs)
        try:
            yield tensor
        finally:
            if tensor is not None:
                self.return_tensor(tensor)
    
    @contextmanager
    def buffer(self, size: int):
        """Context manager for buffer allocation"""
        buf = self.get_buffer(size)
        try:
            yield buf
        finally:
            self.return_buffer(buf)
    
    def _check_cleanup(self):
        """Periodically cleanup pools"""
        self._cleanup_counter += 1
        if self._cleanup_counter >= self._cleanup_interval:
            self._cleanup_counter = 0
            self.cleanup_pools(aggressive=False)
    
    def cleanup_pools(self, aggressive: bool = False):
        """
        Cleanup memory pools
        
        Args:
            aggressive: Perform aggressive cleanup with GC
        """
        if self.tensor_pool:
            # Reduce pool sizes if memory pressure
            mem = psutil.virtual_memory()
            if mem.percent > 80:  # High memory usage
                logger.info("High memory usage detected, reducing pool sizes")
                self.tensor_pool.max_pool_size = max(10, self.tensor_pool.max_pool_size // 2)
                self.tensor_pool.clear_pool(force_gc=aggressive)
        
        if aggressive:
            gc.collect()
            if HAS_TORCH and torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        stats = {}
        
        if self.tensor_pool:
            stats["tensor_pool"] = self.tensor_pool.get_pool_info()
        
        if self.buffer_pool and self.buffer_pool.stats:
            stats["buffer_pool"] = {
                "allocations": self.buffer_pool.stats.total_allocations,
                "deallocations": self.buffer_pool.stats.total_deallocations,
                "cache_hit_rate": self.buffer_pool.stats.cache_hits / max(1, self.buffer_pool.stats.cache_hits + self.buffer_pool.stats.cache_misses),
                "bytes_allocated": self.buffer_pool.stats.total_bytes_allocated,
                "bytes_reused": self.buffer_pool.stats.total_bytes_reused
            }
        
        return stats


# Global pool manager instance
_pool_manager: Optional[MemoryPoolManager] = None


def get_pool_manager() -> MemoryPoolManager:
    """Get global memory pool manager"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = MemoryPoolManager()
    return _pool_manager


# Convenience functions
def get_pooled_array(*args, **kwargs) -> np.ndarray:
    """Get pooled numpy array"""
    return get_pool_manager().get_array(*args, **kwargs)


def get_pooled_tensor(*args, **kwargs) -> Optional[torch.Tensor]:
    """Get pooled torch tensor"""
    return get_pool_manager().get_tensor(*args, **kwargs)


def get_pooled_buffer(size: int) -> bytearray:
    """Get pooled buffer"""
    return get_pool_manager().get_buffer(size)


@contextmanager
def pooled_array(*args, **kwargs):
    """Context manager for pooled array"""
    with get_pool_manager().array(*args, **kwargs) as arr:
        yield arr


@contextmanager
def pooled_tensor(*args, **kwargs):
    """Context manager for pooled tensor"""
    with get_pool_manager().tensor(*args, **kwargs) as t:
        yield t


@contextmanager
def pooled_buffer(size: int):
    """Context manager for pooled buffer"""
    with get_pool_manager().buffer(size) as buf:
        yield buf