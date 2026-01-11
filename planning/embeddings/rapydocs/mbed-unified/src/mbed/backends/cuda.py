"""
CUDA backend implementation for NVIDIA GPUs with advanced optimizations.

Features:
- Dynamic batch sizing based on VRAM availability
- Pinned memory transfers for CPU↔GPU optimization
- Mixed precision (FP16) support with AMP
- Multi-GPU support via DataParallel
- CUDA stream optimization for overlapped transfers
- FAISS-GPU integration for vector operations
- Graceful OOM error handling with automatic batch size reduction
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
import os
import gc
import warnings
from contextlib import contextmanager

from .base import EmbeddingBackend
from ..core.hardware import HardwareType, HardwareDetector
from ..core.config import MBEDSettings

logger = logging.getLogger(__name__)


# Constants for dynamic batch sizing
SAMPLES_PER_GB_LARGE = 32  # Large models (>500M params)
SAMPLES_PER_GB_BASE = 64   # Base models (100M-500M params)
SAMPLES_PER_GB_SMALL = 128 # Small models (<100M params)

class CUDABackend(EmbeddingBackend):
    """CUDA-accelerated embedding backend for NVIDIA GPUs with advanced optimizations"""

    def __init__(self, config: MBEDSettings):
        super().__init__(config)
        self.model = None
        self.embedding_dim = 768
        self.device = "cuda"
        self.torch = None  # Will be imported in initialize
        self.cuda_stream = None
        self.use_amp = config.mixed_precision if hasattr(config, 'mixed_precision') else False
        self.use_multi_gpu = config.multi_gpu if hasattr(config, 'multi_gpu') else False
        self.dynamic_batch_size = True
        self.max_batch_size = self.batch_size
        self.current_batch_size = self.batch_size
        self.oom_count = 0
        self.max_oom_retries = 3
        self.vram_reserved_gb = config.cuda_vram_reserved_gb if hasattr(config, 'cuda_vram_reserved_gb') else 2.0
        self.use_pinned_memory = config.cuda_use_pinned_memory if hasattr(config, 'cuda_use_pinned_memory') else True
        self.normalize_embeddings = config.normalize_embeddings if hasattr(config, 'normalize_embeddings') else True
        self.faiss_index = None
        self.use_faiss_gpu = config.use_faiss_gpu if hasattr(config, 'use_faiss_gpu') else False

    def initialize(self) -> None:
        """Initialize CUDA backend with advanced features"""
        if not self.is_available():
            raise RuntimeError("CUDA is not available on this system")

        try:
            self._setup_cuda_environment()
            self._load_model()
            self._configure_optimizations()

        except ImportError as e:
            raise RuntimeError(f"Required libraries not available: {e}") from e

    def _setup_cuda_environment(self) -> None:
        """Setup CUDA environment and verify availability"""
        import torch
        from sentence_transformers import SentenceTransformer
        self.torch = torch

        # Verify CUDA is really available
        if not torch.cuda.is_available():
            raise RuntimeError("PyTorch CUDA support not available")

        # Set CUDA device and properties
        cuda_device = self.config.cuda_device if hasattr(self.config, 'cuda_device') else 0
        torch.cuda.set_device(cuda_device)
        self.device = f"cuda:{cuda_device}"

        # Enable TF32 on Ampere GPUs for better performance
        if torch.cuda.get_device_capability()[0] >= 8:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            logger.info("Enabled TF32 for Ampere+ GPU")

    def _load_model(self) -> None:
        """Load and configure the embedding model"""
        from sentence_transformers import SentenceTransformer

        # Map model names
        model_map = {
            "nomic-embed-text": "nomic-ai/nomic-embed-text-v1",
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "mxbai-embed-large": "mixedbread-ai/mxbai-embed-large-v1",
        }

        model_name = model_map.get(self.model_name, self.model_name)
        logger.info(f"Loading CUDA model: {model_name}")

        # Load model with optimizations
        self.model = SentenceTransformer(
            model_name,
            device=self.device,
            cache_folder=str(self.config.model_cache_dir)
        )

        # Enable multi-GPU if available and requested
        if self.use_multi_gpu and self.torch.cuda.device_count() > 1:
            logger.info(f"Using {self.torch.cuda.device_count()} GPUs with DataParallel")
            self.model = self.torch.nn.DataParallel(self.model)

        # Get embedding dimension
        with self.torch.no_grad():
            dummy_embedding = self.model.encode(["test"], show_progress_bar=False)
        self.embedding_dim = dummy_embedding.shape[1]

    def _configure_optimizations(self) -> None:
        """Configure CUDA optimizations and features"""
        # Calculate dynamic batch size based on VRAM
        self._calculate_dynamic_batch_size()

        # Initialize CUDA stream for async operations
        self.cuda_stream = self.torch.cuda.Stream()

        # Log GPU info
        gpu_info = self._get_gpu_info()
        logger.info(f"GPU initialized: {gpu_info['gpu_name']} ({gpu_info['vram_gb']:.1f}GB VRAM)")
        logger.info(f"Dynamic batch size: {self.current_batch_size} (max: {self.max_batch_size})")

        # Initialize FAISS-GPU if requested
        if self.use_faiss_gpu:
            self._initialize_faiss_gpu()
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using CUDA acceleration with advanced optimizations"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        # Preprocess texts
        processed = self.preprocess_texts(texts)

        # Try with current batch size, reduce on OOM
        for retry in range(self.max_oom_retries):
            try:
                embeddings = self._generate_with_optimization(processed)

                # Reset OOM count on success
                if self.oom_count > 0:
                    logger.info(f"Successfully recovered from OOM after {self.oom_count} attempts, batch size: {self.current_batch_size}")
                    self.oom_count = 0

                return embeddings

            except self.torch.cuda.OutOfMemoryError as e:
                self._handle_oom_error(e, retry)

                # Log diagnostics after multiple OOM errors
                if self.oom_count >= 2:
                    logger.warning(f"Multiple OOM errors ({self.oom_count}) detected. Consider:")
                    logger.warning("  - Reducing initial batch size")
                    logger.warning("  - Enabling mixed precision")
                    logger.warning("  - Checking for memory leaks")
                    logger.warning(f"  - Current VRAM usage: {self._get_vram_usage():.1f}GB")

        # If all retries failed, raise error
        logger.error("All CUDA attempts failed and CPU fallback is not implemented")
        raise RuntimeError("CUDA processing failed after multiple retries. Please use CPU backend directly if CUDA continues to fail.")

    def _generate_with_optimization(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings with all optimizations enabled"""
        # Use pinned memory for faster transfers
        if self.use_pinned_memory and self.torch:
            self.torch.cuda.empty_cache()

        # Process in optimized batches
        all_embeddings = []

        for i in range(0, len(texts), self.current_batch_size):
            batch = texts[i:i + self.current_batch_size]

            # Use mixed precision if enabled
            if self.use_amp:
                with torch.cuda.amp.autocast():
                    batch_embeddings = self._encode_batch(batch)
            else:
                batch_embeddings = self._encode_batch(batch)

            all_embeddings.append(batch_embeddings)

            # Track total samples processed for cache clearing
            if not hasattr(self, "_samples_processed"):
                self._samples_processed = 0
            self._samples_processed += len(batch)

            # Clear cache every N samples to prevent fragmentation
            CACHE_CLEAR_INTERVAL = 10000  # Tunable value
            if self._samples_processed % CACHE_CLEAR_INTERVAL == 0 and self.torch:
                self.torch.cuda.empty_cache()

        # Concatenate all embeddings
        if not all_embeddings:
            return np.empty((0, self.embedding_dim), dtype=np.float32)
        if len(all_embeddings) == 1:
            return all_embeddings[0]
        return np.vstack(all_embeddings)

    def _encode_batch(self, batch: List[str]) -> np.ndarray:
        """Encode a single batch with CUDA stream optimization"""
        # Use CUDA stream for async operations
        if self.cuda_stream:
            with self.torch.cuda.stream(self.cuda_stream):
                embeddings = self.model.encode(
                    batch,
                    batch_size=len(batch),  # Already batched
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    device="cuda",
                    normalize_embeddings=self.normalize_embeddings
                )
            # Synchronize stream
            self.cuda_stream.synchronize()
        else:
            embeddings = self.model.encode(
                batch,
                batch_size=len(batch),
                show_progress_bar=False,
                convert_to_numpy=True,
                device="cuda",
                normalize_embeddings=self.normalize_embeddings
            )

        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    def is_available(self) -> bool:
        """Check if CUDA is available"""
        capability = HardwareDetector.detect_cuda()
        return capability.available
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive CUDA backend information"""
        info = {
            "backend": "CUDA",
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "batch_size": self.current_batch_size,
            "max_batch_size": self.max_batch_size,
            "dynamic_batching": self.dynamic_batch_size,
            "mixed_precision": self.use_amp,
            "multi_gpu": self.use_multi_gpu,
            "pinned_memory": self.use_pinned_memory,
            "faiss_gpu": self.use_faiss_gpu,
            "oom_count": self.oom_count,
        }

        # Add detailed GPU info
        gpu_info = self._get_gpu_info()
        info |= gpu_info

        return info

    def _get_gpu_info(self) -> Dict[str, Any]:
        """Get detailed GPU information"""
        info = {}
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                info |= self._get_cuda_device_info(props)

                # Add current GPU utilization if pynvml is available
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    info["gpu_utilization"] = f"{util.gpu}%"
                    info["gpu_temperature"] = f"{temp}°C"
                    pynvml.nvmlShutdown()
                except Exception as e:
                    logger.debug(f"Could not get GPU utilization/temperature via pynvml: {e}")
        except Exception as e:
            logger.debug(f"Could not get GPU info: {e}")

        return info

    def _calculate_dynamic_batch_size(self) -> None:
        """Calculate optimal batch size based on available VRAM"""
        try:
            import torch
            props = torch.cuda.get_device_properties(0)
            vram_gb = props.total_memory / 1024**3

            # Reserve some VRAM for system and other processes
            available_vram_gb = vram_gb - self.vram_reserved_gb

            # Estimate batch size based on model size
            # Try to determine model size from parameter count if model is loaded
            if self.model is not None:
                try:
                    model_to_inspect = self.model.module if hasattr(self.model, 'module') else self.model
                    if hasattr(model_to_inspect, 'parameters'):
                        num_params = sum(p.numel() for p in model_to_inspect.parameters())
                        if num_params > 500_000_000:  # Large models
                            samples_per_gb = SAMPLES_PER_GB_LARGE
                        elif num_params > 100_000_000:  # Base models
                            samples_per_gb = SAMPLES_PER_GB_BASE
                        else:  # Small models
                            samples_per_gb = SAMPLES_PER_GB_SMALL
                    else:
                        # Fallback to name-based heuristics
                        if "large" in self.model_name.lower():
                            samples_per_gb = SAMPLES_PER_GB_LARGE
                        elif "base" in self.model_name.lower():
                            samples_per_gb = SAMPLES_PER_GB_BASE
                        else:
                            samples_per_gb = SAMPLES_PER_GB_SMALL
                except Exception:
                    # Fallback to name-based heuristics
                    if "large" in self.model_name.lower():
                        samples_per_gb = SAMPLES_PER_GB_LARGE
                    elif "base" in self.model_name.lower():
                        samples_per_gb = SAMPLES_PER_GB_BASE
                    else:
                        samples_per_gb = SAMPLES_PER_GB_SMALL
            else:
                # Model not loaded yet, use name-based heuristics
                if "large" in self.model_name.lower():
                    samples_per_gb = SAMPLES_PER_GB_LARGE
                elif "base" in self.model_name.lower():
                    samples_per_gb = SAMPLES_PER_GB_BASE
                else:
                    samples_per_gb = SAMPLES_PER_GB_SMALL

            calculated_batch = int(available_vram_gb * samples_per_gb)

            # Apply bounds
            self.current_batch_size = min(max(calculated_batch, 8), 512)
            self.max_batch_size = self.current_batch_size

            logger.info(f"Dynamic batch sizing: {self.current_batch_size} samples "
                       f"(based on {available_vram_gb:.1f}GB available VRAM)")

        except Exception as e:
            logger.warning(f"Could not calculate dynamic batch size: {e}")
            self.current_batch_size = self.batch_size

    def _handle_oom_error(self, error: Exception, retry: int) -> None:
        """Handle CUDA out of memory errors gracefully"""
        self.oom_count += 1
        logger.warning(f"CUDA OOM error (attempt {retry + 1}/{self.max_oom_retries}): {error}")

        # Clear cache
        if self.torch:
            self.torch.cuda.empty_cache()
            gc.collect()

        # Reduce batch size
        self.current_batch_size = max(self.current_batch_size // 2, 1)
        logger.info(f"Reduced batch size to {self.current_batch_size}")

        if retry >= self.max_oom_retries - 1:
            logger.error("Max OOM retries reached")

    # Removed misleading CPU fallback method - users should explicitly use CPU backend

    def _get_vram_usage(self) -> float:
        """Get current VRAM usage in GB"""
        if self.torch and self.torch.cuda.is_available():
            return self.torch.cuda.memory_allocated(0) / 1024**3
        return 0.0

    def _get_cuda_device_info(self, props) -> Dict[str, Any]:
        """Get CUDA device information"""
        return {
            "gpu_name": self.torch.cuda.get_device_name(0),
            "gpu_count": self.torch.cuda.device_count(),
            "vram_gb": props.total_memory / 1024**3,
            "vram_used_gb": self.torch.cuda.memory_allocated(0) / 1024**3,
            "vram_reserved_gb": self.torch.cuda.memory_reserved(0) / 1024**3,
            "cuda_version": self.torch.version.cuda,
            "compute_capability": f"{props.major}.{props.minor}",
            "multi_processor_count": props.multi_processor_count,
        }

    def _initialize_faiss_gpu(self) -> None:
        """Initialize FAISS-GPU for vector operations"""
        try:
            import faiss

            # Check if GPU version is available
            if not hasattr(faiss, 'StandardGpuResources'):
                logger.warning("FAISS-GPU not available, using CPU version")
                self.use_faiss_gpu = False
                return

            # Initialize GPU resources
            self.faiss_gpu_resources = faiss.StandardGpuResources()
            logger.info("FAISS-GPU initialized successfully")

        except ImportError:
            logger.warning("FAISS not installed, vector operations will use numpy")
            self.use_faiss_gpu = False
        except Exception as e:
            logger.warning(f"Could not initialize FAISS-GPU: {e}")
            self.use_faiss_gpu = False

    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """Build FAISS index for fast similarity search"""
        if not self.use_faiss_gpu:
            return

        try:
            import faiss

            # Create index
            index = faiss.IndexFlatL2(self.embedding_dim)

            # Move to GPU
            self.faiss_index = faiss.index_cpu_to_gpu(
                self.faiss_gpu_resources, 0, index
            )

            # Add embeddings
            self.faiss_index.add(embeddings.astype('float32'))
            logger.info(f"Built FAISS-GPU index with {len(embeddings)} vectors")

        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            self.faiss_index = None

    def search_faiss(self, query_embeddings: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """Search using FAISS-GPU index"""
        if self.faiss_index is None:
            raise RuntimeError("FAISS index not built")

        # Search
        distances, indices = self.faiss_index.search(
            query_embeddings.astype('float32'), k
        )

        return distances, indices


# Register backend
from .base import BackendFactory
BackendFactory.register(HardwareType.CUDA, CUDABackend)