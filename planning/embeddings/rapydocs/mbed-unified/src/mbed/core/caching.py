"""
Multi-level caching system for MBED (T136)

This module provides a sophisticated caching hierarchy:
- L1 Cache: In-memory LRU cache for hot embeddings
- L2 Cache: Persistent disk cache with compression
- L3 Cache: Distributed cache (Redis/Memcached) for clusters
- Smart cache warming and prefetching
- Cache invalidation and consistency management
"""

import os
import time
import hashlib
import logging
import pickle
import gzip
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import Lock, RLock
from functools import wraps
import numpy as np
from abc import ABC, abstractmethod

from ..utils.cache_utils import create_cache_key

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    avg_access_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size_bytes": self.size_bytes,
            "hit_rate": self.hit_rate,
            "avg_access_time_ms": self.avg_access_time_ms
        }


class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        pass


class LRUMemoryCache(CacheBackend):
    """
    L1 Cache: High-speed in-memory LRU cache
    
    Features:
    - Least Recently Used eviction policy
    - Thread-safe operations
    - Automatic size management
    - Fast O(1) access patterns
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 512):
        """
        Initialize LRU cache
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict = OrderedDict()
        self.lock = RLock()
        self.stats = CacheStats()
        
        logger.debug(f"LRU cache initialized: {max_size} entries, {max_memory_mb}MB")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, updating access order"""
        start_time = time.perf_counter()
        
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.stats.hits += 1
                
                access_time = (time.perf_counter() - start_time) * 1000
                self._update_avg_access_time(access_time)
                
                return value
            else:
                self.stats.misses += 1
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with automatic eviction"""
        try:
            # Estimate memory size of value
            value_size = self._estimate_size(value)
            
            with self.lock:
                # Remove existing entry if present
                if key in self.cache:
                    old_size = self._estimate_size(self.cache[key])
                    self.stats.size_bytes -= old_size
                    del self.cache[key]
                
                # Check if we need to evict entries
                self._evict_if_needed(value_size)
                
                # Add new entry
                self.cache[key] = value
                self.stats.size_bytes += value_size
                
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                value_size = self._estimate_size(self.cache[key])
                del self.cache[key]
                self.stats.size_bytes -= value_size
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.stats.size_bytes = 0
            logger.debug("LRU cache cleared")
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        with self.lock:
            stats_copy = CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                size_bytes=self.stats.size_bytes,
                avg_access_time_ms=self.stats.avg_access_time_ms
            )
            return stats_copy
    
    def _evict_if_needed(self, new_value_size: int):
        """Evict entries if necessary to make room"""
        # Check size limit
        while (len(self.cache) >= self.max_size or 
               self.stats.size_bytes + new_value_size > self.max_memory_bytes):
            
            if not self.cache:
                break
                
            # Remove least recently used (first item)
            oldest_key, oldest_value = self.cache.popitem(last=False)
            old_size = self._estimate_size(oldest_value)
            self.stats.size_bytes -= old_size
            self.stats.evictions += 1
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value"""
        try:
            if isinstance(value, np.ndarray):
                return value.nbytes
            elif isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, dict):
                return len(str(value))  # Rough approximation
            else:
                return len(pickle.dumps(value, protocol=-1))
        except Exception:
            return 1024  # Default estimate
    
    def _update_avg_access_time(self, access_time_ms: float):
        """Update running average of access times"""
        total_accesses = self.stats.hits + self.stats.misses
        if total_accesses <= 1:
            self.stats.avg_access_time_ms = access_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.avg_access_time_ms = (
                alpha * access_time_ms + 
                (1 - alpha) * self.stats.avg_access_time_ms
            )


class DiskCache(CacheBackend):
    """
    L2 Cache: Persistent disk cache with compression
    
    Features:
    - SQLite-based metadata management
    - Compressed storage with gzip
    - TTL support with automatic cleanup
    - Size limits with LRU eviction
    """
    
    def __init__(self, 
                 cache_dir: Path = Path("./cache/disk"), 
                 max_size_gb: int = 10,
                 compression_level: int = 6,
                 cleanup_interval_hours: int = 24):
        """
        Initialize disk cache
        
        Args:
            cache_dir: Directory for cache storage
            max_size_gb: Maximum disk usage in GB
            compression_level: gzip compression level (1-9)
            cleanup_interval_hours: Hours between cleanup runs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        self.compression_level = compression_level
        self.cleanup_interval = cleanup_interval_hours * 3600
        
        # SQLite database for metadata
        self.db_path = self.cache_dir / "cache_metadata.db"
        self.lock = Lock()
        self.stats = CacheStats()
        
        self._init_database()
        self._last_cleanup = time.time()
        
        logger.debug(f"Disk cache initialized: {cache_dir}, {max_size_gb}GB limit")
    
    def _init_database(self):
        """Initialize SQLite database for metadata"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    expires_at REAL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
            """)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        start_time = time.perf_counter()
        
        # Check if cleanup is needed
        if time.time() - self._last_cleanup > self.cleanup_interval:
            await self._cleanup_expired()
        
        with self.lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute(
                        "SELECT file_path, expires_at FROM cache_entries WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        self.stats.misses += 1
                        return None
                    
                    file_path, expires_at = row
                    
                    # Check expiration
                    if expires_at and time.time() > expires_at:
                        await self._delete_entry(key, file_path)
                        self.stats.misses += 1
                        return None
                    
                    # Load and decompress data
                    file_path = self.cache_dir / file_path
                    if not file_path.exists():
                        # File missing, clean up metadata
                        conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                        self.stats.misses += 1
                        return None
                    
                    with gzip.open(file_path, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Update access statistics
                    conn.execute(
                        "UPDATE cache_entries SET accessed_at = ?, access_count = access_count + 1 WHERE key = ?",
                        (time.time(), key)
                    )
                    
                    self.stats.hits += 1
                    access_time = (time.perf_counter() - start_time) * 1000
                    self._update_avg_access_time(access_time)
                    
                    return data
                    
            except Exception as e:
                logger.error(f"Error getting cache entry {key}: {e}")
                self.stats.misses += 1
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in disk cache"""
        try:
            # Serialize and compress data
            data = pickle.dumps(value, protocol=-1)
            compressed_data = gzip.compress(data, compresslevel=self.compression_level)
            
            # Generate unique filename
            key_hash = hashlib.md5(key.encode()).hexdigest()
            file_name = f"{key_hash}.cache"
            file_path = self.cache_dir / file_name
            
            # Calculate sizes
            original_size = len(data)
            compressed_size = len(compressed_data)
            
            with self.lock:
                # Check if we need to evict entries
                await self._evict_if_needed(compressed_size)
                
                # Write compressed data
                with open(file_path, 'wb') as f:
                    f.write(compressed_data)
                
                # Update metadata
                expires_at = time.time() + ttl if ttl else None
                
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO cache_entries 
                           (key, file_path, size_bytes, created_at, accessed_at, expires_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (key, file_name, compressed_size, time.time(), time.time(), expires_at)
                    )
                
                self.stats.size_bytes += compressed_size
                
                logger.debug(f"Cached {key}: {original_size} -> {compressed_size} bytes "
                           f"({compressed_size/original_size:.1%} compression)")
                
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from disk cache"""
        with self.lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute(
                        "SELECT file_path, size_bytes FROM cache_entries WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        return False
                    
                    file_path, size_bytes = row
                    
                    # Delete file and metadata
                    await self._delete_entry(key, file_path)
                    self.stats.size_bytes -= size_bytes
                    
                    return True
                    
            except Exception as e:
                logger.error(f"Error deleting cache entry {key}: {e}")
                return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute("SELECT file_path FROM cache_entries")
                    files = [row[0] for row in cursor.fetchall()]
                    
                    # Delete all files
                    for file_name in files:
                        file_path = self.cache_dir / file_name
                        if file_path.exists():
                            file_path.unlink()
                    
                    # Clear metadata
                    conn.execute("DELETE FROM cache_entries")
                
                self.stats.size_bytes = 0
                logger.debug("Disk cache cleared")
                
            except Exception as e:
                logger.error(f"Error clearing disk cache: {e}")
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        with self.lock:
            # Update current size from database
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
                    result = cursor.fetchone()
                    if result and result[0]:
                        self.stats.size_bytes = int(result[0])
            except Exception:
                pass
                
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                size_bytes=self.stats.size_bytes,
                avg_access_time_ms=self.stats.avg_access_time_ms
            )
    
    async def _evict_if_needed(self, new_entry_size: int):
        """Evict old entries if needed"""
        if self.stats.size_bytes + new_entry_size <= self.max_size_bytes:
            return
        
        # Evict least recently used entries
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT key, file_path, size_bytes FROM cache_entries ORDER BY accessed_at ASC"
            )
            
            for key, file_path, size_bytes in cursor:
                if self.stats.size_bytes + new_entry_size <= self.max_size_bytes:
                    break
                
                await self._delete_entry(key, file_path)
                self.stats.size_bytes -= size_bytes
                self.stats.evictions += 1
    
    async def _delete_entry(self, key: str, file_path: str):
        """Delete cache entry file and metadata"""
        try:
            # Delete file
            full_path = self.cache_dir / file_path
            if full_path.exists():
                full_path.unlink()
            
            # Delete metadata
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                
        except Exception as e:
            logger.error(f"Error deleting cache entry {key}: {e}")
    
    async def _cleanup_expired(self):
        """Clean up expired entries"""
        try:
            current_time = time.time()
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    "SELECT key, file_path, size_bytes FROM cache_entries WHERE expires_at < ?",
                    (current_time,)
                )
                
                expired_entries = cursor.fetchall()
                
                for key, file_path, size_bytes in expired_entries:
                    await self._delete_entry(key, file_path)
                    self.stats.size_bytes -= size_bytes
                
                if expired_entries:
                    logger.debug(f"Cleaned up {len(expired_entries)} expired entries")
            
            self._last_cleanup = current_time
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def _update_avg_access_time(self, access_time_ms: float):
        """Update running average of access times"""
        total_accesses = self.stats.hits + self.stats.misses
        if total_accesses <= 1:
            self.stats.avg_access_time_ms = access_time_ms
        else:
            alpha = 0.1
            self.stats.avg_access_time_ms = (
                alpha * access_time_ms + 
                (1 - alpha) * self.stats.avg_access_time_ms
            )


class RedisCache(CacheBackend):
    """
    L3 Cache: Distributed Redis cache for clusters
    
    Features:
    - Network-based distributed caching
    - Automatic serialization/deserialization
    - TTL support with Redis expiration
    - Connection pooling and failover
    """
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 key_prefix: str = "mbed:",
                 connection_pool_size: int = 10):
        """
        Initialize Redis cache
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (if required)
            key_prefix: Prefix for all cache keys
            connection_pool_size: Connection pool size
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self.connection_pool_size = connection_pool_size
        
        self.redis = None
        self.stats = CacheStats()
        
        # Try to initialize Redis connection
        self._init_redis()
        
        logger.debug(f"Redis cache initialized: {host}:{port}/{db}")
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            from redis import ConnectionPool
            
            pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.connection_pool_size,
                decode_responses=False  # We'll handle binary data
            )
            
            self.redis = redis.Redis(connection_pool=pool)
            
            # Test connection
            self.redis.ping()
            
        except ImportError:
            logger.warning("redis-py not installed, Redis cache disabled")
            self.redis = None
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}")
            self.redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.redis:
            self.stats.misses += 1
            return None
        
        start_time = time.perf_counter()
        
        try:
            redis_key = f"{self.key_prefix}{key}"
            data = self.redis.get(redis_key)
            
            if data is None:
                self.stats.misses += 1
                return None
            
            # Deserialize data
            value = pickle.loads(data)
            
            self.stats.hits += 1
            access_time = (time.perf_counter() - start_time) * 1000
            self._update_avg_access_time(access_time)
            
            return value
            
        except Exception as e:
            logger.error(f"Error getting Redis cache entry {key}: {e}")
            self.stats.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        if not self.redis:
            return False
        
        try:
            # Serialize data
            data = pickle.dumps(value, protocol=-1)
            redis_key = f"{self.key_prefix}{key}"
            
            # Set with optional TTL
            if ttl:
                result = self.redis.setex(redis_key, ttl, data)
            else:
                result = self.redis.set(redis_key, data)
            
            if result:
                self.stats.size_bytes += len(data)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error setting Redis cache entry {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.redis:
            return False
        
        try:
            redis_key = f"{self.key_prefix}{key}"
            result = self.redis.delete(redis_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting Redis cache entry {key}: {e}")
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries with our prefix"""
        if not self.redis:
            return
        
        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys_to_delete = []
            for key in self.redis.scan_iter(pattern):
                keys_to_delete.append(key)
            
            if keys_to_delete:
                self.redis.delete(*keys_to_delete)
                logger.debug(f"Cleared {len(keys_to_delete)} Redis cache entries")
            
            self.stats.size_bytes = 0
            
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        # Note: Redis doesn't easily provide size information
        # We track approximate size based on operations
        return CacheStats(
            hits=self.stats.hits,
            misses=self.stats.misses,
            evictions=self.stats.evictions,
            size_bytes=self.stats.size_bytes,
            avg_access_time_ms=self.stats.avg_access_time_ms
        )
    
    def _update_avg_access_time(self, access_time_ms: float):
        """Update running average of access times"""
        total_accesses = self.stats.hits + self.stats.misses
        if total_accesses <= 1:
            self.stats.avg_access_time_ms = access_time_ms
        else:
            alpha = 0.1
            self.stats.avg_access_time_ms = (
                alpha * access_time_ms + 
                (1 - alpha) * self.stats.avg_access_time_ms
            )


class CacheHierarchy:
    """
    Multi-level cache hierarchy coordinator
    
    Features:
    - Automatic cache level promotion/demotion
    - Smart cache warming and prefetching
    - Consistency management across levels
    - Performance optimization based on access patterns
    """
    
    def __init__(self, 
                 l1_cache: Optional[CacheBackend] = None,
                 l2_cache: Optional[CacheBackend] = None,
                 l3_cache: Optional[CacheBackend] = None,
                 enable_prefetching: bool = True,
                 promotion_threshold: int = 3):
        """
        Initialize cache hierarchy
        
        Args:
            l1_cache: L1 (memory) cache backend
            l2_cache: L2 (disk) cache backend  
            l3_cache: L3 (distributed) cache backend
            enable_prefetching: Enable smart prefetching
            promotion_threshold: Access count threshold for cache promotion
        """
        # Initialize default caches if not provided
        self.l1_cache = l1_cache or LRUMemoryCache()
        self.l2_cache = l2_cache or DiskCache()
        self.l3_cache = l3_cache  # Optional
        
        self.enable_prefetching = enable_prefetching
        self.promotion_threshold = promotion_threshold
        
        # Track access patterns for smart prefetching
        self.access_patterns: Dict[str, int] = {}
        self.related_keys: Dict[str, List[str]] = {}
        
        self.caches = [self.l1_cache, self.l2_cache]
        if self.l3_cache:
            self.caches.append(self.l3_cache)
        
        logger.info(f"Cache hierarchy initialized with {len(self.caches)} levels")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache hierarchy
        
        Checks L1 -> L2 -> L3 and promotes successful hits
        """
        # Track access pattern
        self.access_patterns[key] = self.access_patterns.get(key, 0) + 1
        
        # Try each cache level
        for level, cache in enumerate(self.caches):
            value = await cache.get(key)
            
            if value is not None:
                # Cache hit - promote to higher levels if needed
                await self._promote_to_higher_levels(key, value, level)
                
                # Trigger prefetching if enabled
                if self.enable_prefetching:
                    await self._prefetch_related(key)
                
                return value
        
        # Cache miss at all levels
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache hierarchy
        
        Sets in all available cache levels
        """
        success = True
        
        # Set in all cache levels
        for cache in self.caches:
            try:
                result = await cache.set(key, value, ttl)
                success = success and result
            except Exception as e:
                logger.error(f"Error setting cache entry in {cache.__class__.__name__}: {e}")
                success = False
        
        # Update access pattern
        self.access_patterns[key] = self.access_patterns.get(key, 0) + 1
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels"""
        success = True
        
        for cache in self.caches:
            try:
                result = await cache.delete(key)
                success = success and result
            except Exception as e:
                logger.error(f"Error deleting cache entry from {cache.__class__.__name__}: {e}")
                success = False
        
        # Clean up access patterns
        self.access_patterns.pop(key, None)
        self.related_keys.pop(key, None)
        
        return success
    
    async def clear(self) -> None:
        """Clear all cache levels"""
        for cache in self.caches:
            try:
                await cache.clear()
            except Exception as e:
                logger.error(f"Error clearing {cache.__class__.__name__}: {e}")
        
        # Clear access patterns
        self.access_patterns.clear()
        self.related_keys.clear()
        
        logger.info("Cache hierarchy cleared")
    
    async def warm_cache(self, key_value_pairs: List[Tuple[str, Any]]):
        """
        Warm cache with pre-computed values
        
        Args:
            key_value_pairs: List of (key, value) tuples to cache
        """
        logger.info(f"Warming cache with {len(key_value_pairs)} entries")
        
        for key, value in key_value_pairs:
            await self.set(key, value)
        
        logger.info("Cache warming completed")
    
    async def _promote_to_higher_levels(self, key: str, value: Any, hit_level: int):
        """Promote cache entry to higher (faster) levels"""
        # Only promote if accessed frequently enough
        access_count = self.access_patterns.get(key, 0)
        if access_count < self.promotion_threshold:
            return
        
        # Promote to all higher levels
        for level in range(hit_level):
            try:
                cache = self.caches[level]
                await cache.set(key, value)
                logger.debug(f"Promoted {key} to L{level+1} cache")
            except Exception as e:
                logger.error(f"Error promoting {key} to L{level+1}: {e}")
    
    async def _prefetch_related(self, key: str):
        """Prefetch related cache entries based on access patterns"""
        if not self.enable_prefetching:
            return
        
        # Get related keys (simple implementation)
        related = self.related_keys.get(key, [])
        
        # Also consider keys with similar prefixes
        key_prefix = key.split(':')[0] if ':' in key else key[:10]
        similar_keys = [k for k in self.access_patterns.keys() 
                       if k.startswith(key_prefix) and k != key]
        
        related.extend(similar_keys[:3])  # Limit prefetching
        
        # Prefetch related entries
        for related_key in related[:5]:  # Limit to avoid overloading
            if related_key not in self.access_patterns:
                continue
                
            # Check if already in L1 cache
            l1_value = await self.l1_cache.get(related_key)
            if l1_value is not None:
                continue
                
            # Try to load from lower levels and promote
            for level, cache in enumerate(self.caches[1:], 1):
                value = await cache.get(related_key)
                if value is not None:
                    await self.l1_cache.set(related_key, value)
                    logger.debug(f"Prefetched {related_key} from L{level+1} to L1")
                    break
    
    def add_key_relationship(self, key1: str, key2: str):
        """
        Add relationship between keys for smart prefetching
        
        Args:
            key1: First key
            key2: Related key
        """
        if key1 not in self.related_keys:
            self.related_keys[key1] = []
        if key2 not in self.related_keys:
            self.related_keys[key2] = []
        
        if key2 not in self.related_keys[key1]:
            self.related_keys[key1].append(key2)
        if key1 not in self.related_keys[key2]:
            self.related_keys[key2].append(key1)
    
    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics from all cache levels"""
        stats = {}
        
        for i, cache in enumerate(self.caches):
            level_name = f"L{i+1}"
            if isinstance(cache, LRUMemoryCache):
                level_name += "_Memory"
            elif isinstance(cache, DiskCache):
                level_name += "_Disk"
            elif isinstance(cache, RedisCache):
                level_name += "_Redis"
            
            stats[level_name] = cache.get_stats()
        
        return stats
    
    def get_access_patterns(self) -> Dict[str, int]:
        """Get current access patterns"""
        return self.access_patterns.copy()


def cache_embeddings(ttl: Optional[int] = 3600, 
                    cache_hierarchy: Optional[CacheHierarchy] = None):
    """
    Decorator for caching embedding generation results
    
    Args:
        ttl: Time to live in seconds
        cache_hierarchy: Cache hierarchy to use (creates default if None)
        
    Example:
        @cache_embeddings(ttl=7200)
        def generate_embeddings(self, texts: List[str]) -> np.ndarray:
            # Expensive embedding generation
            return embeddings
    """
    if cache_hierarchy is None:
        cache_hierarchy = CacheHierarchy()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function arguments
            cache_key = create_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = await cache_hierarchy.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - compute result
            result = func(*args, **kwargs)
            
            # Handle async functions
            if hasattr(result, '__await__'):
                result = await result
            
            # Cache the result
            await cache_hierarchy.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator




# Global cache hierarchy instance
_global_cache: Optional[CacheHierarchy] = None


def get_global_cache() -> CacheHierarchy:
    """Get or create global cache hierarchy"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheHierarchy()
    return _global_cache


def configure_global_cache(l1_cache: Optional[CacheBackend] = None,
                          l2_cache: Optional[CacheBackend] = None,
                          l3_cache: Optional[CacheBackend] = None) -> CacheHierarchy:
    """
    Configure global cache hierarchy
    
    Args:
        l1_cache: L1 cache backend
        l2_cache: L2 cache backend
        l3_cache: L3 cache backend
        
    Returns:
        Configured cache hierarchy
    """
    global _global_cache
    _global_cache = CacheHierarchy(
        l1_cache=l1_cache,
        l2_cache=l2_cache,
        l3_cache=l3_cache
    )
    return _global_cache