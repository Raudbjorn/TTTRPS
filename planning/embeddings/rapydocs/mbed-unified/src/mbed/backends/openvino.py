"""
OpenVINO backend implementation for Intel GPUs

This module provides hardware-accelerated embedding generation using Intel's OpenVINO
toolkit, supporting Intel GPUs (Arc, Iris Xe, integrated graphics) and CPUs with
SIMD optimizations.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import json

from .base import EmbeddingBackend
from ..core.hardware import HardwareType, HardwareDetector
from ..core.config import MBEDSettings

logger = logging.getLogger(__name__)

# Constants for configuration
DEFAULT_MAX_SEQUENCE_LENGTH = 512
DEFAULT_MIN_BATCH_SIZE = 1 
DEFAULT_MAX_BATCH_SIZE = 128
MAX_WORKERS_MULTI_GPU = 16
MAX_WORKERS_CPU = 8
MAX_WORKERS_ABSOLUTE = 32
MAX_BATCH_SIZE_ABSOLUTE = 1024
MEMORY_BASELINE_GB = 8.0


class OpenVINOBackend(EmbeddingBackend):
    """
    OpenVINO-accelerated embedding backend for Intel GPUs
    
    Supports:
    - Intel Arc GPUs (A770, A750, A380)
    - Intel Iris Xe Graphics
    - Intel UHD Graphics
    - CPU with AVX2/AVX512 optimizations
    - AUTO device selection for optimal performance
    - INT8 quantization for 2x throughput improvement
    - Dynamic batching and async inference
    
    Device Options:
    - "AUTO" - Automatically select best available device
    - "GPU" - Use primary GPU
    - "GPU.0", "GPU.1" - Use specific GPU by index
    - "CPU" - Use CPU with optimizations
    - "AUTO:GPU,CPU" - Use GPU with CPU fallback
    - "AUTO:GPU.0,GPU.1,CPU" - Multi-device with priority order
    
    The device string format follows OpenVINO conventions:
    https://docs.openvino.ai/latest/openvino_docs_OV_UG_Working_with_devices.html
    """
    
    def __init__(self, config: MBEDSettings):
        """
        Initialize OpenVINO backend
        
        Args:
            config: MBEDSettings configuration object
        """
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.core = None
        self.compiled_model = None
        self.embedding_dim = 768
        self.device = "GPU"  # Default device, will be updated in initialize()
        self.use_quantization = getattr(config, 'openvino_quantize', False)
        self.performance_hint = getattr(config, 'openvino_performance_hint', 'THROUGHPUT')
        self.cache_dir = Path(getattr(config, 'openvino_cache_dir', config.model_cache_dir / 'openvino'))
        
        # Async processing
        self.async_processor = None
        
    def initialize(self) -> None:
        """
        Initialize OpenVINO backend with hardware detection and model loading
        
        Raises:
            RuntimeError: If OpenVINO is not available or initialization fails
        """
        if not self.is_available():
            raise RuntimeError("OpenVINO is not available on this system")
        
        try:
            from openvino.runtime import Core
            from optimum.intel import OVModelForFeatureExtraction
            from transformers import AutoTokenizer
            
            logger.info(f"Initializing OpenVINO backend for model: {self.model_name}")
            
            # Initialize OpenVINO runtime
            self.core = Core()
            
            # Detect and select optimal device
            self.device = self._select_device()
            logger.info(f"Selected device: {self.device}")
            
            # Log device information
            if "GPU" in self.device:
                try:
                    # Extract base device name (handles AUTO:GPU,CPU format)
                    base_device = self._get_base_gpu_device(self.device)
                    gpu_name = self.core.get_property(base_device, "FULL_DEVICE_NAME")
                    logger.info(f"🚀 Using GPU: {gpu_name}")
                except Exception as e:
                    logger.debug(f"Could not get GPU name: {e}")
            
            # Map model names to Hugging Face models
            model_map = {
                "nomic-embed-text": "nomic-ai/nomic-embed-text-v1",
                "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
                "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
                "e5-large-v2": "intfloat/e5-large-v2",
            }
            
            model_name = model_map.get(self.model_name, self.model_name)
            
            # Create cache directory if it doesn't exist
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Load tokenizer
            logger.info(f"Loading tokenizer: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=str(self.config.model_cache_dir)
            )
            
            # Configure compilation options based on device and performance hints
            compile_config = self._get_compile_config()
            
            # Load OpenVINO optimized model
            logger.info(f"Loading OpenVINO model with device: {self.device}")
            self.model = OVModelForFeatureExtraction.from_pretrained(
                model_name,
                export=True,  # Export to OpenVINO format if needed
                device=self.device,
                cache_dir=str(self.config.model_cache_dir),
                compile=True,
                ov_config=compile_config
            )
            
            # Get actual embedding dimension from model config
            self._detect_embedding_dimension(model_name)
            
            # Initialize async processor
            self._initialize_async_processor()
            
            logger.info(f"✅ OpenVINO backend initialized on {self.device}")
            logger.info(f"   Embedding dimension: {self.embedding_dim}")
            logger.info(f"   Quantization: {'Enabled' if self.use_quantization else 'Disabled'}")
            logger.info(f"   Performance hint: {self.performance_hint}")
            logger.info(f"   Async processor: Ready")
            
        except ImportError as e:
            raise RuntimeError(
                f"OpenVINO libraries not available. Install with: "
                f"pip install openvino>=2024.0 openvino-dev>=2024.0 optimum[openvino]. Error: {e}"
            )
        except Exception as e:
            logger.exception("Failed to initialize OpenVINO backend")
            raise RuntimeError(f"OpenVINO initialization failed: {e}") from e
    
    def _initialize_async_processor(self) -> None:
        """Initialize persistent async processor"""
        try:
            from .openvino_async import create_async_pipeline
            
            # Create dynamic async pipeline config based on MBEDSettings and hardware
            config = self._get_async_pipeline_config()
            
            self.async_processor = create_async_pipeline(self, config)
            logger.debug(f"Async processor initialized with {config['num_workers']} workers")
            
        except Exception as e:
            logger.warning(f"Could not initialize async processor: {e}")
            self.async_processor = None
    
    def _get_base_gpu_device(self, device_string: str) -> str:
        """
        Extract base GPU device name from complex device strings
        
        Args:
            device_string: Device string like "AUTO:GPU,CPU" or "GPU.0" or "GPU"
            
        Returns:
            Base device name like "GPU" or "GPU.0"
        """
        base_device = device_string
        if ':' in base_device:
            # For "AUTO:GPU,CPU" format, get the part after ':'
            device_list = base_device.split(':', 1)[1]
            # Get first device from comma-separated list
            base_device = device_list.split(',')[0]
        return base_device
    
    def _select_device(self) -> str:
        """
        Select optimal device based on availability and configuration
        
        Returns:
            Device string for OpenVINO (e.g., "GPU", "CPU", "AUTO:GPU,CPU")
        """
        available_devices = self.core.available_devices
        logger.debug(f"Available OpenVINO devices: {available_devices}")
        
        # Check configuration for device preference
        device_config = getattr(self.config, 'openvino_device', 'AUTO')
        
        if device_config == "AUTO":
            return self._select_device_auto(available_devices)
        
        elif device_config in available_devices:
            return device_config
        
        else:
            # Requested device not available, fall back to AUTO
            logger.warning(f"Requested device {device_config} not available, using AUTO mode")
            return self._select_device_auto(available_devices)
    
    def _select_device_auto(self, available_devices: List[str]) -> str:
        """
        Helper to select device in AUTO mode
        
        Args:
            available_devices: List of available OpenVINO devices
            
        Returns:
            AUTO device string
        """
        gpu_devices = [d for d in available_devices if d.startswith('GPU')]
        
        if gpu_devices:
            # Multiple GPUs available
            if len(gpu_devices) > 1:
                return f"AUTO:{','.join(gpu_devices)},CPU"
            else:
                return "AUTO:GPU,CPU"
        else:
            logger.warning("No Intel GPU detected, falling back to CPU")
            return "CPU"
    
    def _get_compile_config(self) -> Dict[str, Any]:
        """
        Get compilation configuration based on device and settings
        
        Returns:
            Dictionary of OpenVINO compilation options
        """
        config = {
            "PERFORMANCE_HINT": self.performance_hint,
        }
        
        if "GPU" in self.device:
            # GPU-specific optimizations
            config |= {
                "GPU_THROUGHPUT_STREAMS": "AUTO",
                "CACHE_DIR": str(self.cache_dir),
            }
            
            if self.use_quantization:
                # Validate INT8 compatibility before setting precision hint
                try:
                    # Extract base GPU device name for property queries
                    gpu_device = self._get_base_gpu_device(self.device)
                    
                    # Check if the device supports INT8 inference
                    supported_props = self.core.get_property(gpu_device, "OPTIMIZATION_CAPABILITIES")
                    if "INT8" in supported_props or "WINOGRAD" in supported_props:
                        config["INFERENCE_PRECISION_HINT"] = "u8"
                        logger.info(f"INT8 inference enabled for {gpu_device}")
                    else:
                        logger.warning(f"INT8 not supported on {gpu_device}, using default precision")
                except Exception as e:
                    logger.debug(f"Could not validate INT8 support: {e}, using default precision")
        
        elif "CPU" in self.device:
            # CPU-specific optimizations
            config |= {
                "CPU_THROUGHPUT_STREAMS": "AUTO",
                "CPU_BIND_THREAD": "YES",
                "CACHE_DIR": str(self.cache_dir),
            }
        
        return config
    
    def _get_async_pipeline_config(self) -> Dict[str, Any]:
        """
        Get dynamic async pipeline configuration based on hardware and settings
        
        Returns:
            Dictionary of async pipeline configuration options
        """
        # Base configuration from MBEDSettings
        config = {
            'num_workers': self.config.workers,
            'enable_dynamic_batching': True,
            'min_batch_size': DEFAULT_MIN_BATCH_SIZE,
            'max_batch_size': self.config.batch_size * 2
        }
        
        # Hardware-specific optimizations
        gpu_devices = [d for d in self.core.available_devices if d.startswith('GPU')]
        
        if gpu_devices:
            # GPU-optimized settings
            if len(gpu_devices) > 1:
                # Multiple GPUs: increase workers and batch sizes
                config |= {
                    'num_workers': min(self.config.workers * 2, MAX_WORKERS_MULTI_GPU),
                    'max_batch_size': self.config.batch_size * 4,
                    'enable_dynamic_batching': True,
                }
            else:
                # Single GPU: balanced settings
                config |= {
                    'max_batch_size': self.config.batch_size * 3,
                    'enable_dynamic_batching': True,
                }
        else:
            # CPU-only: conservative settings
            config |= {
                'num_workers': min(self.config.workers, MAX_WORKERS_CPU),
                'max_batch_size': self.config.batch_size,
                'enable_dynamic_batching': False,  # Less beneficial for CPU
            }
        
        # Quantization adjustments
        if self.use_quantization:
            # INT8 can handle larger batches more efficiently
            config['max_batch_size'] = int(config['max_batch_size'] * 1.5)
            
        # Performance hint adjustments
        if self.performance_hint == "LATENCY":
            # Optimize for low latency: smaller batches, fewer workers
            config |= {
                'num_workers': max(1, config['num_workers'] // 2),
                'max_batch_size': max(1, config['max_batch_size'] // 2),
                'min_batch_size': DEFAULT_MIN_BATCH_SIZE,
            }
        elif self.performance_hint == "THROUGHPUT":
            # Optimize for high throughput: larger batches, more workers
            config |= {
                'enable_dynamic_batching': True,
                'min_batch_size': max(1, self.config.batch_size // 4),
            }
        
        # Memory constraints
        max_memory = getattr(self.config, 'max_memory_gb', None)
        if max_memory:
            # Conservative batch sizing for memory-constrained systems
            memory_factor = min(1.0, max_memory / MEMORY_BASELINE_GB)
            config['max_batch_size'] = int(config['max_batch_size'] * memory_factor)
            config['num_workers'] = max(1, int(config['num_workers'] * memory_factor))
        
        # Ensure reasonable bounds
        config['num_workers'] = max(1, min(config['num_workers'], MAX_WORKERS_ABSOLUTE))
        config['max_batch_size'] = max(
            config['min_batch_size'], 
            min(config['max_batch_size'], MAX_BATCH_SIZE_ABSOLUTE)
        )
        config['min_batch_size'] = max(1, min(config['min_batch_size'], config['max_batch_size']))
        
        logger.debug(f"Dynamic async config: {config}")
        return config
    
    def _detect_embedding_dimension(self, model_name: str) -> None:
        """
        Detect embedding dimension from model configuration
        
        Args:
            model_name: Name of the model
        """
        # Known model dimensions
        model_dimensions = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "nomic-ai/nomic-embed-text-v1": 768,
            "intfloat/e5-large-v2": 1024,
        }
        
        self.embedding_dim = model_dimensions.get(model_name, 768)
        
        # Try to get from model config if available
        try:
            if hasattr(self.model, 'config') and hasattr(self.model.config, 'hidden_size'):
                self.embedding_dim = self.model.config.hidden_size
        except AttributeError as e:
            logging.warning(f"Could not retrieve 'hidden_size' from model config: {e}")
    
    def preprocess_texts(self, texts: List[str]) -> List[str]:
        """
        Preprocess texts before embedding generation
        
        Args:
            texts: List of input texts
            
        Returns:
            List of preprocessed texts
        """
        # Handle None values and empty strings
        return [
            "" if text is None
            else text.strip() if isinstance(text, str)
            else str(text).strip()
            for text in texts
        ]
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings using OpenVINO acceleration
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            Numpy array of embeddings with shape (n_texts, embedding_dim)
            
        Raises:
            RuntimeError: If model is not initialized
        """
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        # Preprocess texts
        processed = self.preprocess_texts(texts)
        
        # Handle empty input
        if not processed:
            return np.empty((0, self.embedding_dim), dtype=np.float32)
        
        # Tokenize with proper padding and truncation
        inputs = self.tokenizer(
            processed,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=DEFAULT_MAX_SEQUENCE_LENGTH
        )
        
        # Generate embeddings
        outputs = self.model(**inputs)
        
        # Mean pooling over token embeddings
        # Get attention mask for proper mean calculation
        attention_mask = inputs['attention_mask']
        embeddings = outputs.last_hidden_state
        
        # Expand attention mask for broadcasting
        mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        
        # Sum embeddings along sequence length, accounting for padding
        sum_embeddings = (embeddings * mask_expanded).sum(dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        
        # Calculate mean
        mean_embeddings = sum_embeddings / sum_mask
        
        # Convert to numpy
        embeddings_np = mean_embeddings.numpy()
        
        # Normalize embeddings (with epsilon to handle zero-norm)
        norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
        embeddings_np = embeddings_np / np.maximum(norms, 1e-12)
        
        return embeddings_np
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Generate embeddings in batches for memory efficiency
        
        Args:
            texts: List of texts to generate embeddings for
            batch_size: Batch size for processing (uses config default if None)
            
        Returns:
            Numpy array of embeddings
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.generate_embeddings(batch)
            all_embeddings.append(embeddings)
        
        if all_embeddings:
            return np.vstack(all_embeddings)
        else:
            return np.empty((0, self.embedding_dim), dtype=np.float32)
    
    def get_embedding_dimension(self) -> int:
        """
        Get embedding dimension
        
        Returns:
            Size of embedding vectors
        """
        return self.embedding_dim
    
    def is_available(self) -> bool:
        """
        Check if OpenVINO is available on this system
        
        Returns:
            True if OpenVINO can be used, False otherwise
        """
        capability = HardwareDetector.detect_openvino()
        return capability.available
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get comprehensive OpenVINO backend information
        
        Returns:
            Dictionary containing backend details and configuration
        """
        info = {
            "backend": "OpenVINO",
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "batch_size": self.batch_size,
            "device": self.device,
            "quantization": self.use_quantization,
            "performance_hint": self.performance_hint,
            "cache_dir": str(self.cache_dir),
        }
        
        # Add OpenVINO version info if available
        try:
            from openvino.runtime import get_version
            info["openvino_version"] = get_version()
        except ImportError:
            logger.debug("OpenVINO runtime version not available")
        
        # Add device details if available
        if self.core is not None:
            try:
                info["available_devices"] = self.core.available_devices
                
                # Add GPU details if using GPU
                if "GPU" in self.device:
                    # Extract base device name properly
                    gpu_device = self._get_base_gpu_device(self.device)
                    if gpu_device in self.core.available_devices:
                        info["gpu_name"] = self.core.get_property(gpu_device, "FULL_DEVICE_NAME")
                        
                        # Try to get memory info
                        try:
                            info["gpu_memory_mb"] = self.core.get_property(
                                gpu_device, "GPU_DEVICE_TOTAL_MEM_SIZE"
                            ) / (1024 * 1024)
                        except Exception as e:
                            logger.debug(f"Could not get GPU memory info: {e}")
            except Exception as e:
                logger.debug(f"Could not get device details: {e}")
        
        return info
    
    def optimize_model(self, model_path: str, output_dir: Optional[str] = None) -> str:
        """
        Optimize model for OpenVINO inference (T073)
        
        Args:
            model_path: Path to ONNX or PyTorch model
            output_dir: Directory to save optimized model
            
        Returns:
            Path to optimized model
        """
        from openvino.tools import mo
        
        if output_dir is None:
            output_dir = self.cache_dir / "optimized"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Model optimizer command
        mo_args = [
            "--input_model", str(model_path),
            "--output_dir", str(output_dir),
            "--data_type", "FP16" if self.use_quantization else "FP32",
        ]
        
        if self.use_quantization:
            # Prepare for INT8 quantization
            mo_args.extend(["--compress_to_fp16", "False"])
        
        logger.info(f"Optimizing model with OpenVINO Model Optimizer...")
        mo.main(mo_args)
        
        optimized_path = output_dir / "model.xml"
        logger.info(f"Model optimized and saved to: {optimized_path}")
        
        return str(optimized_path)
    
    def quantize_model(self, model_path: str, calibration_data: Optional[List[str]] = None) -> str:
        """
        Quantize model to INT8 for improved performance (T075)
        
        Args:
            model_path: Path to OpenVINO IR model
            calibration_data: Sample data for calibration
            
        Returns:
            Path to quantized model
        """
        from openvino.tools.pot import DataLoader, IEEngine, load_model, save_model
        from openvino.tools.pot.algorithms.quantization import DefaultQuantization
        
        logger.info("Quantizing model to INT8...")
        
        # Load model
        model = load_model(model_path)
        
        # Create data loader for calibration
        if calibration_data is None:
            calibration_data = [
                "Sample text for calibration",
                "Another sample for better quantization",
                "OpenVINO INT8 quantization example",
            ]
        
        # Store reference to backend for tokenizer access
        backend = self
        
        class CalibrationDataLoader(DataLoader):
            def __init__(self, data):
                self.data = data
                super().__init__()
            
            def __len__(self):
                return len(self.data)
            
            def __getitem__(self, idx):
                return backend.tokenizer(
                    self.data[idx],
                    padding=True,
                    truncation=True,
                    return_tensors="np",
                    max_length=DEFAULT_MAX_SEQUENCE_LENGTH
                )
        
        data_loader = CalibrationDataLoader(calibration_data)
        
        # Configure quantization
        quantization_config = {
            "algorithms": [{
                "name": "DefaultQuantization",
                "params": {
                    "target_device": "GPU" if "GPU" in self.device else "CPU",
                    "preset": "performance",
                    "stat_subset_size": min(100, len(calibration_data))
                }
            }]
        }
        
        # Run quantization
        engine = IEEngine(self.core, model_path)
        quantized_model = DefaultQuantization(quantization_config).run(
            model, engine, data_loader
        )
        
        # Save quantized model
        quantized_path = self.cache_dir / "quantized" / "model_int8.xml"
        quantized_path.parent.mkdir(parents=True, exist_ok=True)
        save_model(quantized_model, str(quantized_path))
        
        logger.info(f"Model quantized and saved to: {quantized_path}")
        return str(quantized_path)
    
    def enable_dynamic_batching(
        self, 
        min_batch: int = DEFAULT_MIN_BATCH_SIZE, 
        max_batch: int = DEFAULT_MAX_BATCH_SIZE
    ) -> None:
        """
        Enable dynamic batching for improved throughput (T076)
        
        Args:
            min_batch: Minimum batch size
            max_batch: Maximum batch size
        """
        if self.model is None:
            raise RuntimeError("Model must be initialized first")
        
        logger.info(f"Enabling dynamic batching: {min_batch} to {max_batch}")
        
        # Reshape model for dynamic batch size
        try:
            # NOTE: This accesses internal model.model attribute which is fragile
            # The optimum-intel library doesn't expose a public API for reshaping yet
            # Consider monitoring for API changes in future versions
            if hasattr(self.model, 'model'):
                # Access underlying OpenVINO model (internal implementation detail)
                ov_model = self.model.model
                # Get input name for proper reshape mapping
                input_name = ov_model.inputs[0].get_any_name()
                ov_model.reshape({input_name: [min_batch, max_batch, -1]})
                logger.info("Dynamic batching enabled")
            else:
                logger.warning("Model doesn't expose internal OpenVINO model - dynamic batching not available")
        except Exception as e:
            logger.warning(f"Could not enable dynamic batching: {e}")
            # Dynamic batching is optional - continue without it
    
    def get_device_utilization(self) -> Dict[str, float]:
        """
        Get current device utilization metrics (T081)
        
        Returns:
            Dictionary with utilization metrics
        """
        metrics = {}
        
        if self.core is None:
            return metrics
        
        try:
            if "GPU" in self.device:
                # Extract base device name properly
                gpu_device = self._get_base_gpu_device(self.device)
                if gpu_device in self.core.available_devices:
                    # Try to get GPU metrics
                    try:
                        metrics["gpu_utilization"] = self.core.get_metric(
                            gpu_device, "GPU_UTILIZATION"
                        )
                        metrics["gpu_memory_used_mb"] = self.core.get_metric(
                            gpu_device, "GPU_MEMORY_USED"
                        ) / (1024 * 1024)
                    except Exception as e:
                        logger.debug(f"GPU metrics not available: {e}")
            
            elif "CPU" in self.device:
                # CPU metrics
                try:
                    import psutil
                    metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
                    metrics["memory_percent"] = psutil.virtual_memory().percent
                except ImportError:
                    pass
        except Exception as e:
            logger.debug(f"Could not get device metrics: {e}")
        
        return metrics
    
    def create_async_processor(self, num_workers: int = 4) -> 'AsyncOpenVINOProcessor':
        """
        Create async processor for this backend (T077)
        
        Args:
            num_workers: Number of concurrent workers
            
        Returns:
            AsyncOpenVINOProcessor instance
        """
        from .openvino_async import AsyncOpenVINOProcessor
        
        if self.model is None:
            raise RuntimeError("Model must be initialized first")
        
        processor = AsyncOpenVINOProcessor(self, num_workers)
        logger.info(f"Created async processor with {num_workers} workers")
        
        return processor
    
    async def generate_embeddings_async(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Generate embeddings asynchronously (T077)
        
        Args:
            texts: List of texts to process
            batch_size: Batch size for processing
            
        Returns:
            Embeddings array
        """
        if self.async_processor is None:
            # Fallback to synchronous processing if async processor not available
            logger.warning("Async processor not available, falling back to synchronous processing")
            return self.generate_embeddings(texts)
        
        if batch_size is None:
            batch_size = self.batch_size
        
        # Create batches
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        # Use persistent async processor and return directly
        return await self.async_processor.process_batches_async(batches)
    
    def cleanup(self) -> None:
        """
        Cleanup resources including async processor
        """
        if self.async_processor:
            try:
                self.async_processor.shutdown()
                logger.debug("Async processor shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down async processor: {e}")
            finally:
                self.async_processor = None


# Register backend with factory
from .base import BackendFactory
BackendFactory.register(HardwareType.OPENVINO, OpenVINOBackend)
