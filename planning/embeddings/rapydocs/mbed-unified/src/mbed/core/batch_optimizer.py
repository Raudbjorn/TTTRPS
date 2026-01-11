"""
Dynamic batch size optimization for MBED backends (T132)

This module provides intelligent batch size optimization based on:
- Hardware capabilities (VRAM, CPU cores, memory)
- Model characteristics (size, complexity)
- Performance metrics (throughput, latency)
- Resource utilization feedback
"""

import time
import logging
import psutil
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from pathlib import Path
import json
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategies for batch sizing"""
    THROUGHPUT = "throughput"  # Maximize documents/second
    LATENCY = "latency"       # Minimize response time
    MEMORY = "memory"         # Minimize memory usage
    BALANCED = "balanced"     # Balance all factors


@dataclass
class BatchSizeResult:
    """Result from batch size testing"""
    batch_size: int
    duration_ms: float
    throughput_docs_per_sec: float
    memory_mb: float
    gpu_memory_mb: Optional[float] = None
    utilization: Optional[float] = None
    error_occurred: bool = False
    error_message: Optional[str] = None
    error_type: Optional[str] = None  # Added for better error classification


@dataclass
class OptimizationConfig:
    """Configuration for batch size optimization"""
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    min_batch_size: int = 1
    max_batch_size: int = 1024
    test_iterations: int = 3
    memory_safety_factor: float = 0.8  # Use 80% of available memory
    target_latency_ms: Optional[float] = None
    target_throughput_docs_per_sec: Optional[float] = None
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if self.min_batch_size <= 0:
            raise ValueError("min_batch_size must be greater than 0")
        if self.max_batch_size <= 0:
            raise ValueError("max_batch_size must be greater than 0")
        if self.min_batch_size > self.max_batch_size:
            raise ValueError("min_batch_size must be less than or equal to max_batch_size")
        if self.test_iterations <= 0:
            raise ValueError("test_iterations must be greater than 0")
        if not (0.0 < self.memory_safety_factor <= 1.0):
            raise ValueError("memory_safety_factor must be between 0.0 and 1.0")
        if self.target_latency_ms is not None and self.target_latency_ms <= 0:
            raise ValueError("target_latency_ms must be positive")
        if self.target_throughput_docs_per_sec is not None and self.target_throughput_docs_per_sec <= 0:
            raise ValueError("target_throughput_docs_per_sec must be positive")


class DynamicBatchOptimizer:
    """
    Dynamic batch size optimizer for MBED backends
    
    Features:
    - Hardware-aware optimization
    - Performance testing with multiple strategies
    - Memory safety checks
    - Persistent optimization cache
    - Real-time adaptation
    """
    
    def __init__(
        self,
        backend_type: str,
        model_name: str,
        config: Optional[OptimizationConfig] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize batch optimizer
        
        Args:
            backend_type: Type of backend (cuda, cpu, openvino, mps)
            model_name: Name of the model being optimized
            config: Optional OptimizationConfig object for optimizer settings
            cache_dir: Directory to cache optimization results
        """
        self.backend_type = backend_type.lower()
        self.model_name = model_name
        self.config = config or OptimizationConfig()
        self.cache_dir = cache_dir or Path("./cache/batch_optimization")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file for optimization results
        self.cache_file = self.cache_dir / f"{backend_type}_{model_name}_batch_opt.json"
        
        # Load cached results
        self.cache = self._load_cache()
        
        # Hardware detection
        self.hardware_info = self._detect_hardware()
        
        logger.debug(f"Batch optimizer initialized for {backend_type}/{model_name}")
    
    def _detect_hardware(self) -> Dict[str, Any]:
        """Detect hardware capabilities"""
        info = {
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "total_memory_gb": psutil.virtual_memory().total / (1024**3),
            "available_memory_gb": psutil.virtual_memory().available / (1024**3),
        }
        
        # GPU detection for different backends
        if self.backend_type == "cuda":
            info.update(self._detect_cuda_hardware())
        elif self.backend_type == "openvino":
            info.update(self._detect_openvino_hardware())
        elif self.backend_type == "mps":
            info.update(self._detect_mps_hardware())
        
        return info
    
    def _detect_cuda_hardware(self) -> Dict[str, Any]:
        """Detect CUDA hardware capabilities"""
        info = {}
        try:
            import torch
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                props = torch.cuda.get_device_properties(device)
                info.update({
                    "gpu_name": props.name,
                    "gpu_memory_gb": props.total_memory / (1024**3),
                    "gpu_compute_capability": f"{props.major}.{props.minor}",
                    "gpu_multiprocessors": props.multi_processor_count,
                })
        except Exception as e:
            logger.debug(f"Could not detect CUDA hardware: {e}")
        
        return info
    
    def _detect_openvino_hardware(self) -> Dict[str, Any]:
        """Detect OpenVINO hardware capabilities"""
        info = {}
        try:
            from openvino.runtime import Core
            core = Core()
            devices = core.available_devices
            
            info["openvino_devices"] = devices
            
            # Get GPU info if available
            gpu_devices = [d for d in devices if d.startswith("GPU")]
            if gpu_devices:
                gpu_device = gpu_devices[0]
                gpu_name = core.get_property(gpu_device, "FULL_DEVICE_NAME")
                info.update({
                    "gpu_name": gpu_name,
                    "gpu_device": gpu_device,
                })
                
        except Exception as e:
            logger.debug(f"Could not detect OpenVINO hardware: {e}")
        
        return info
    
    def _detect_mps_hardware(self) -> Dict[str, Any]:
        """Detect MPS (Apple Silicon) hardware capabilities"""
        info = {}
        try:
            import torch
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                # Apple Silicon unified memory
                import subprocess
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"], 
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    # Parse unified memory size
                    for line in result.stdout.split('\n'):
                        if 'Memory:' in line:
                            memory_info = line.split(':')[1].strip()
                            info["unified_memory"] = memory_info
                            break
        except Exception as e:
            logger.debug(f"Could not detect MPS hardware: {e}")
        
        return info
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load optimization cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    cache = json.load(f)
                logger.debug(f"Loaded batch optimization cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Could not load optimization cache: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save optimization cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save optimization cache: {e}")
    
    def calculate_optimal_batch_size(self, 
                                   backend,
                                   config: OptimizationConfig,
                                   sample_texts: Optional[List[str]] = None) -> int:
        """
        Calculate optimal batch size for given backend and configuration
        
        Args:
            backend: Backend instance to optimize
            config: Optimization configuration
            sample_texts: Sample texts for testing (generated if None)
            
        Returns:
            Optimal batch size
        """
        cache_key = self._get_cache_key(config)
        
        # Check cache first
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            logger.info(f"Using cached optimal batch size: {cached_result['optimal_batch_size']}")
            return cached_result['optimal_batch_size']
        
        logger.info(f"Optimizing batch size for {self.backend_type} backend...")
        
        # Generate test data if not provided
        if sample_texts is None:
            sample_texts = self._generate_test_texts(max(config.max_batch_size, 100))
        
        # Determine batch sizes to test
        test_sizes = self._generate_test_batch_sizes(config)
        
        # Test different batch sizes
        results = []
        for batch_size in test_sizes:
            logger.debug(f"Testing batch size: {batch_size}")
            
            result = self._test_batch_size(
                backend, batch_size, sample_texts, config.test_iterations
            )
            results.append(result)
            
            # Early stopping if we hit memory limits
            if result.error_occurred and result.error_type == "memory":
                logger.warning(f"Memory limit reached at batch size {batch_size}")
                break
        
        # Select optimal batch size
        optimal_size = self._select_optimal_batch_size(results, config)
        
        # Cache results
        self.cache[cache_key] = {
            "optimal_batch_size": optimal_size,
            "hardware_info": self.hardware_info,
            "test_results": [self._result_to_dict(r) for r in results],
            "timestamp": time.time()
        }
        self._save_cache()
        
        logger.info(f"Optimal batch size determined: {optimal_size}")
        return optimal_size
    
    def _get_cache_key(self, config: OptimizationConfig) -> str:
        """Generate cache key for configuration"""
        key_data = {
            "backend_type": self.backend_type,
            "model_name": self.model_name,
            "strategy": config.strategy.value,
            "hardware_hash": hash(str(sorted(self.hardware_info.items())))
        }
        return str(hash(str(sorted(key_data.items()))))
    
    def _generate_test_texts(self, count: int) -> List[str]:
        """Generate test texts for optimization"""
        import random
        
        # Template sentences of various lengths
        templates = [
            "This is a short test sentence.",
            "This is a medium length test sentence that contains a bit more content for testing purposes.",
            "This is a longer test sentence that contains significantly more content and is designed to test how the system handles various text lengths during batch processing optimization.",
            "Brief text.",
            "Moderately sized text content that should provide a good balance for testing.",
        ]
        
        texts = []
        for i in range(count):
            # Mix of different lengths
            template = random.choice(templates)
            # Add some variation
            texts.append(f"{template} Document {i}.")
        
        return texts
    
    def _generate_test_batch_sizes(self, config: OptimizationConfig) -> List[int]:
        """Generate list of batch sizes to test"""
        sizes = []
        
        # Always test the boundaries
        sizes.extend([config.min_batch_size, config.max_batch_size])
        
        # Add powers of 2 (common for GPU optimization)
        power = 1
        while power <= config.max_batch_size:
            if config.min_batch_size <= power <= config.max_batch_size:
                sizes.append(power)
            power *= 2
        
        # Add some intermediate values
        for multiplier in [4, 8, 16, 32, 64, 128, 256, 512]:
            if config.min_batch_size <= multiplier <= config.max_batch_size:
                sizes.append(multiplier)
        
        # Hardware-specific optimization
        if self.backend_type == "cuda" and "gpu_memory_gb" in self.hardware_info:
            # CUDA: Test batch sizes based on VRAM
            gpu_memory_gb = self.hardware_info["gpu_memory_gb"]
            estimated_max = min(int(gpu_memory_gb * 64), config.max_batch_size)  # Rough estimate
            for size in [estimated_max // 4, estimated_max // 2, estimated_max]:
                if config.min_batch_size <= size <= config.max_batch_size:
                    sizes.append(size)
        
        elif self.backend_type == "cpu":
            # CPU: Test batch sizes based on core count
            cpu_cores = self.hardware_info.get("cpu_cores", 4)
            for multiplier in [cpu_cores, cpu_cores * 2, cpu_cores * 4, cpu_cores * 8]:
                if config.min_batch_size <= multiplier <= config.max_batch_size:
                    sizes.append(multiplier)
        
        # Remove duplicates and sort
        sizes = sorted(list(set(sizes)))
        
        logger.debug(f"Testing batch sizes: {sizes}")
        return sizes
    
    def _test_batch_size(self, 
                        backend,
                        batch_size: int, 
                        sample_texts: List[str], 
                        iterations: int) -> BatchSizeResult:
        """Test a specific batch size"""
        durations = []
        memory_usage = []
        gpu_memory_usage = []
        
        try:
            # Ensure we have enough test data
            if not sample_texts or len(sample_texts) == 0:
                raise ValueError("sample_texts cannot be empty")
            
            # Safely calculate repetition count to avoid division by zero
            sample_len = len(sample_texts)
            if sample_len == 0:  # Extra safety check
                raise ValueError("sample_texts cannot be empty")
            
            # Calculate how many times to repeat the sample texts to reach batch_size
            repetitions = (batch_size // sample_len) + 1
            test_texts = (sample_texts * repetitions)[:batch_size]
            
            for _ in range(iterations):
                # Measure memory before
                memory_before = psutil.Process().memory_info().rss / (1024 * 1024)
                gpu_memory_before = None
                
                if self.backend_type == "cuda":
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.synchronize()
                            gpu_memory_before = torch.cuda.memory_allocated() / (1024 * 1024)
                    except Exception:
                        pass
                
                # Run inference
                start_time = time.perf_counter()
                embeddings = backend.generate_embeddings(test_texts)
                end_time = time.perf_counter()
                
                duration_ms = (end_time - start_time) * 1000
                durations.append(duration_ms)
                
                # Measure memory after
                memory_after = psutil.Process().memory_info().rss / (1024 * 1024)
                memory_usage.append(memory_after - memory_before)
                
                if gpu_memory_before is not None:
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.synchronize()
                            gpu_memory_after = torch.cuda.memory_allocated() / (1024 * 1024)
                            gpu_memory_usage.append(gpu_memory_after - gpu_memory_before)
                    except Exception:
                        pass
                
                # Verify output shape
                expected_shape = (batch_size, backend.get_embedding_dimension())
                if embeddings.shape != expected_shape:
                    raise ValueError(f"Unexpected embedding shape: {embeddings.shape} vs {expected_shape}")
            
            # Calculate averages
            avg_duration = sum(durations) / len(durations)
            throughput = batch_size / (avg_duration / 1000)  # docs per second
            avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0
            avg_gpu_memory = sum(gpu_memory_usage) / len(gpu_memory_usage) if gpu_memory_usage else None
            
            return BatchSizeResult(
                batch_size=batch_size,
                duration_ms=avg_duration,
                throughput_docs_per_sec=throughput,
                memory_mb=avg_memory,
                gpu_memory_mb=avg_gpu_memory
            )
            
        except Exception as e:
            logger.debug(f"Error testing batch size {batch_size}: {e}")
            
            # Classify error type based on exception type and message
            error_type = "unknown"
            error_msg = str(e).lower()
            
            if isinstance(e, MemoryError) or "out of memory" in error_msg or "oom" in error_msg:
                error_type = "memory"
            elif "cuda" in error_msg and "memory" in error_msg:
                error_type = "memory"  # CUDA OOM
            elif "timeout" in error_msg or "time" in error_msg:
                error_type = "timeout"
            elif isinstance(e, ValueError):
                error_type = "validation"
            elif isinstance(e, RuntimeError):
                error_type = "runtime"
            
            return BatchSizeResult(
                batch_size=batch_size,
                duration_ms=float('inf'),
                throughput_docs_per_sec=0,
                memory_mb=0,
                error_occurred=True,
                error_message=str(e),
                error_type=error_type
            )
    
    def _select_optimal_batch_size(self, 
                                 results: List[BatchSizeResult],
                                 config: OptimizationConfig) -> int:
        """Select optimal batch size based on strategy"""
        # Filter out failed results
        valid_results = [r for r in results if not r.error_occurred]
        
        if not valid_results:
            logger.warning("No valid batch size results, using minimum")
            return config.min_batch_size
        
        if config.strategy == OptimizationStrategy.THROUGHPUT:
            # Maximize throughput
            optimal = max(valid_results, key=lambda r: r.throughput_docs_per_sec)
        
        elif config.strategy == OptimizationStrategy.LATENCY:
            # Minimize latency (duration per document)
            optimal = min(valid_results, key=lambda r: r.duration_ms / r.batch_size)
        
        elif config.strategy == OptimizationStrategy.MEMORY:
            # Minimize memory usage while maintaining reasonable throughput
            # Filter results by memory threshold
            memory_threshold = self.hardware_info["available_memory_gb"] * 1024 * config.memory_safety_factor
            memory_efficient = [r for r in valid_results if r.memory_mb < memory_threshold]
            
            if memory_efficient:
                optimal = max(memory_efficient, key=lambda r: r.throughput_docs_per_sec)
            else:
                optimal = min(valid_results, key=lambda r: r.memory_mb)
        
        else:  # BALANCED
            # Balance throughput, latency, and memory usage
            scores = []
            for result in valid_results:
                # Normalize metrics (higher is better)
                throughput_score = result.throughput_docs_per_sec
                latency_score = 1000 / (result.duration_ms / result.batch_size) if result.duration_ms > 0 and result.batch_size > 0 else 0  # Invert latency
                memory_score = 1000 / max(result.memory_mb, 1)  # Invert memory usage
                
                # Combined score (can be weighted)
                combined_score = (throughput_score * 0.4 + 
                                latency_score * 0.3 + 
                                memory_score * 0.3)
                scores.append(combined_score)
            
            max_score_idx = scores.index(max(scores))
            optimal = valid_results[max_score_idx]
        
        logger.info(f"Selected batch size {optimal.batch_size} "
                   f"(throughput: {optimal.throughput_docs_per_sec:.1f} docs/sec, "
                   f"latency: {optimal.duration_ms/optimal.batch_size:.2f}ms/doc, "
                   f"memory: {optimal.memory_mb:.1f}MB)")
        
        return optimal.batch_size
    
    def _result_to_dict(self, result: BatchSizeResult) -> Dict[str, Any]:
        """Convert BatchSizeResult to dictionary"""
        return {
            "batch_size": result.batch_size,
            "duration_ms": result.duration_ms,
            "throughput_docs_per_sec": result.throughput_docs_per_sec,
            "memory_mb": result.memory_mb,
            "gpu_memory_mb": result.gpu_memory_mb,
            "utilization": result.utilization,
            "error_occurred": result.error_occurred,
            "error_message": result.error_message
        }
    
    def get_cached_optimization(self, strategy: OptimizationStrategy) -> Optional[int]:
        """
        Get cached optimization result for given strategy
        
        Args:
            strategy: Optimization strategy
            
        Returns:
            Cached optimal batch size or None
        """
        config = OptimizationConfig(strategy=strategy)
        cache_key = self._get_cache_key(config)
        
        if cache_key in self.cache:
            return self.cache[cache_key]["optimal_batch_size"]
        
        return None
    
    def clear_cache(self):
        """Clear optimization cache"""
        self.cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Batch optimization cache cleared")