"""
CPU backend implementation for embedding generation
Optimized for multi-core CPU processing with thread pool executor
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
from pathlib import Path

from .base import EmbeddingBackend
from ..core.hardware import HardwareType
from ..core.config import MBEDSettings

logger = logging.getLogger(__name__)


class CPUBackend(EmbeddingBackend):
    """CPU-based embedding backend using sentence-transformers or ONNX"""

    # Constants
    _MAX_TEXT_LENGTH_CPU = 8000  # Conservative limit for CPU processing
    _DEFAULT_EMBEDDING_DIM = 768  # Default for nomic-embed-text
    _MAX_THREAD_WORKERS = 4  # Limit threads to avoid overload
    _MIN_BATCH_SIZE = 8
    _MAX_BATCH_SIZE = 32
    _ONNX_BATCH_SIZE = 16  # Smaller batch size for ONNX

    def __init__(self, config: MBEDSettings):
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.embedding_dim = self._DEFAULT_EMBEDDING_DIM
        self.implementation = "none"
        self.executor: Optional[ThreadPoolExecutor] = None

        # CPU-optimized batch size (smaller than GPU)
        cpu_count = multiprocessing.cpu_count()
        self.optimal_batch_size = min(self._MAX_BATCH_SIZE, max(self._MIN_BATCH_SIZE, cpu_count * 2))
        self.max_workers = min(self._MAX_THREAD_WORKERS, cpu_count)
        logger.info(f"CPU backend using {cpu_count} cores, batch size: {self.optimal_batch_size}")
        
    def initialize(self) -> None:
        """Initialize CPU backend with sentence-transformers or ONNX"""
        # Create thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers,
                                         thread_name_prefix="cpu_backend")
        logger.info(f"Initialized thread pool with {self.max_workers} workers")

        # Try sentence-transformers first
        if self._try_sentence_transformers():
            return

        # Fallback to ONNX
        logger.warning("sentence-transformers not available, trying ONNX fallback")
        if self._try_onnx():
            return

        # Final fallback - raise error
        raise RuntimeError(
            "No CPU backend available. Install: pip install sentence-transformers"
        )

    def _try_sentence_transformers(self) -> bool:
        """Try to initialize with sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            return self._load_sentence_transformer_model(SentenceTransformer)
        except ImportError as e:
            logger.debug(f"sentence-transformers not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformers: {e}")
            return False

    def _load_sentence_transformer_model(self, SentenceTransformer) -> bool:
        """Load the sentence transformer model - extracted method"""
        # Map model names to sentence-transformers models
        model_map = {
            "nomic-embed-text": "nomic-ai/nomic-embed-text-v1",
            "mxbai-embed-large": "mixedbread-ai/mxbai-embed-large-v1",
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "bge-m3": "BAAI/bge-m3",
        }

        model_name = model_map.get(self.model_name, self.model_name)
        logger.info(f"Loading CPU model: {model_name}")

        self.model = SentenceTransformer(
            model_name,
            device="cpu",
            cache_folder=str(self.config.model_cache_dir)
        )

        # Get actual embedding dimension
        dummy_embedding = self.model.encode(["test"], show_progress_bar=False)
        self.embedding_dim = dummy_embedding.shape[1]
        self.implementation = "sentence-transformers"

        logger.info(f"✅ CPU backend loaded with sentence-transformers (dim: {self.embedding_dim})")
        return True

    def _try_onnx(self) -> bool:
        """Try to initialize with ONNX Runtime"""
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
            return self._load_onnx_model(ort, AutoTokenizer)
        except ImportError as e:
            logger.debug(f"ONNX Runtime not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load ONNX model: {e}")
            return False

    def _load_onnx_model(self, ort, AutoTokenizer) -> bool:
        """Load the ONNX model - extracted method"""
        # Download/convert model to ONNX if needed
        model_path = self._get_or_create_onnx_model()
        if not model_path:
            return False

        # Create ONNX inference session
        providers = ['CPUExecutionProvider']
        self.model = ort.InferenceSession(str(model_path), providers=providers)

        # Load tokenizer
        model_map = {
            "nomic-embed-text": "nomic-ai/nomic-embed-text-v1",
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
        }
        tokenizer_name = model_map.get(self.model_name, self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

        # Test inference to get embedding dimension
        test_tokens = self.tokenizer("test", return_tensors="np", padding=True, truncation=True)
        outputs = self.model.run(None, dict(test_tokens))
        self.embedding_dim = outputs[0].shape[-1]
        self.implementation = "onnx"

        logger.info(f"✅ CPU backend loaded with ONNX Runtime (dim: {self.embedding_dim})")
        return True

    def _get_or_create_onnx_model(self) -> Optional[Path]:
        """Get or create ONNX model file

        NOTE: This is a skeleton implementation. Full ONNX model conversion
        would require the 'optimum' library to convert HuggingFace models to ONNX format.
        This is left as a future enhancement to avoid adding heavy dependencies.

        To implement:
        1. Check if ONNX model exists in cache
        2. If not, use optimum.onnxruntime to convert HF model
        3. Cache the converted model for future use

        Returns:
            Path to ONNX model file, or None if not available
        """
        # Skeleton implementation - actual conversion not implemented
        # to avoid heavy dependency on 'optimum' library
        logger.warning("ONNX model auto-conversion not implemented (skeleton only)")
        return None
    
    def preprocess_texts(self, texts: List[str]) -> List[str]:
        """Preprocess texts for embedding generation"""
        if not texts:
            return []

        processed = []
        for text in texts:
            if not isinstance(text, str):
                text = str(text)

            # Basic preprocessing
            # Normalize whitespace (multiple spaces to single space)
            text = " ".join(text.split())
            text = text.strip() or "[EMPTY]"  # Placeholder for empty strings

            # Truncate very long texts to avoid memory issues
            if len(text) > self._MAX_TEXT_LENGTH_CPU:
                text = f"{text[:self._MAX_TEXT_LENGTH_CPU]}..."
                logger.debug("Truncated long text for CPU processing")

            processed.append(text)

        return processed
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using CPU with optimized processing"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        if not texts:
            return np.empty((0, self.embedding_dim))

        # Preprocess texts
        processed = self.preprocess_texts(texts)
        logger.debug(f"Processing {len(processed)} texts with {self.implementation}")

        if self.implementation == "sentence-transformers":
            return self._generate_with_sentence_transformers(processed)
        elif self.implementation == "onnx":
            return self._generate_with_onnx(processed)
        else:
            raise RuntimeError(f"Unknown implementation: {self.implementation}")

    def _generate_with_sentence_transformers(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using sentence-transformers with thread pooling"""
        if len(texts) <= self.optimal_batch_size:
            # Small batch, process directly
            return self.model.encode(
                texts,
                batch_size=self.optimal_batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )

        # Large batch, use thread pool for parallel processing
        logger.debug(f"Using thread pool for {len(texts)} texts")

        # Split into chunks for parallel processing
        chunks = [texts[i:i + self.optimal_batch_size]
                 for i in range(0, len(texts), self.optimal_batch_size)]

        # Use the instance's executor and track indices for ordering
        futures = {
            self.executor.submit(self._encode_batch, chunk, idx): idx
            for idx, chunk in enumerate(chunks)
        }

        # Collect results in correct order
        results = [None] * len(chunks)
        for future in as_completed(futures):
            idx = futures[future]
            try:
                batch_embeddings = future.result()
                results[idx] = batch_embeddings
            except Exception as e:
                logger.error(f"Batch processing failed for chunk {idx}: {e}")
                raise

        # Concatenate all batches in correct order
        if not any(r is None for r in results):
            embeddings = np.vstack(results)
            logger.debug(f"Generated {embeddings.shape[0]} embeddings with dim {embeddings.shape[1]}")
            return embeddings
        else:
            return np.empty((0, self.embedding_dim))

    def _encode_batch(self, texts: List[str], batch_idx: int) -> np.ndarray:
        """Encode a single batch of texts"""
        logger.debug(f"Processing batch {batch_idx} with {len(texts)} texts")
        embeddings = self.model.encode(
            texts,
            batch_size=len(texts),  # Process entire chunk at once
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )

        # Note: Removed gc.collect() for better performance
        # Python's automatic GC handles memory efficiently
        return embeddings

    def _generate_with_onnx(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using ONNX Runtime"""
        if not self.tokenizer:
            raise RuntimeError("ONNX tokenizer not initialized")

        embeddings_list = []

        # Process in smaller batches for ONNX
        onnx_batch_size = min(self._ONNX_BATCH_SIZE, self.optimal_batch_size)

        for i in range(0, len(texts), onnx_batch_size):
            batch_texts = texts[i:i + onnx_batch_size]

            # Tokenize
            tokens = self.tokenizer(
                batch_texts,
                return_tensors="np",
                padding=True,
                truncation=True,
                max_length=512
            )

            # Run inference
            outputs = self.model.run(None, dict(tokens))
            batch_embeddings = outputs[0]

            # Mean pooling and normalization
            if len(batch_embeddings.shape) == 3:  # [batch, seq_len, hidden]
                # Mean pooling over sequence dimension
                batch_embeddings = np.mean(batch_embeddings, axis=1)

            # L2 normalize for cosine similarity
            norms = np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            batch_embeddings = batch_embeddings / norms

            embeddings_list.append(batch_embeddings)

        if not embeddings_list:
            return np.empty((0, self.embedding_dim))

        embeddings = np.vstack(embeddings_list)
        logger.debug(f"ONNX generated {embeddings.shape[0]} embeddings with dim {embeddings.shape[1]}")
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    def is_available(self) -> bool:
        """CPU is always available"""
        return True
    
    def cleanup(self) -> None:
        """Clean up CPU backend resources"""
        if self.executor:
            logger.debug("Shutting down thread pool executor")
            self.executor.shutdown(wait=True)
            self.executor = None

        # Clear model from memory
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        # Force garbage collection
        gc.collect()
        logger.info("CPU backend cleanup complete")

    def get_info(self) -> Dict[str, Any]:
        """Get CPU backend information"""
        import multiprocessing

        info = {
            "backend": "CPU",
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "batch_size": self.optimal_batch_size,
            "cpu_count": multiprocessing.cpu_count(),
            "implementation": self.implementation,
            "thread_pool_workers": self.max_workers if self.executor else 0
        }

        # Add memory info if available
        try:
            import psutil
            memory = psutil.virtual_memory()
            info |= {
                "memory_total_gb": round(memory.total / (1024**3), 1),
                "memory_available_gb": round(memory.available / (1024**3), 1),
                "memory_percent": memory.percent
            }
        except ImportError:
            pass

        return info


    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()


# Register backend
from .base import BackendFactory
BackendFactory.register(HardwareType.CPU, CPUBackend)