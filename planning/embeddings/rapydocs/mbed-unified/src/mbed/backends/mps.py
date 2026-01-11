"""
MPS backend implementation for Apple Silicon
"""

import numpy as np
from typing import List, Dict, Any
import logging
import platform

from .base import EmbeddingBackend
from ..core.hardware import HardwareType, HardwareDetector
from ..core.config import MBEDSettings

logger = logging.getLogger(__name__)


class MPSBackend(EmbeddingBackend):
    """MPS-accelerated embedding backend for Apple Silicon"""
    
    def __init__(self, config: MBEDSettings):
        super().__init__(config)
        self.model = None
        self.embedding_dim = 768
        self.device = "mps"
        
    def initialize(self) -> None:
        """Initialize MPS backend"""
        if not self.is_available():
            raise RuntimeError("MPS is not available on this system")
        
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Verify MPS is really available
            if not torch.backends.mps.is_available():
                raise RuntimeError("PyTorch MPS support not available")
            
            # Map model names
            model_map = {
                "nomic-embed-text": "nomic-ai/nomic-embed-text-v1",
                "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
                "mxbai-embed-large": "mixedbread-ai/mxbai-embed-large-v1",
            }
            
            model_name = model_map.get(self.model_name, self.model_name)
            logger.info(f"Loading MPS model: {model_name}")
            
            # Load model on MPS
            self.model = SentenceTransformer(
                model_name,
                device="mps",
                cache_folder=str(self.config.model_cache_dir)
            )
            
            # Get embedding dimension
            dummy_embedding = self.model.encode(["test"], show_progress_bar=False)
            self.embedding_dim = dummy_embedding.shape[1]
            
            # Log Apple Silicon info
            if platform.processor() == 'arm':
                logger.info(f"Using Apple Silicon with MPS acceleration")
            
        except ImportError as e:
            raise RuntimeError(f"Required libraries not available: {e}")
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using MPS acceleration"""
        if self.model is None:
            raise RuntimeError("Model not initialized")
        
        # Preprocess texts
        processed = self.preprocess_texts(texts)
        
        # Generate embeddings with MPS
        embeddings = self.model.encode(
            processed,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            device="mps"
        )
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    def is_available(self) -> bool:
        """Check if MPS is available"""
        capability = HardwareDetector.detect_mps()
        return capability.available
    
    def get_info(self) -> Dict[str, Any]:
        """Get MPS backend information"""
        info = {
            "backend": "MPS",
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "batch_size": self.batch_size,
        }
        
        # Add Apple Silicon info
        capability = HardwareDetector.detect_mps()
        if capability.available and 'chip' in capability.details:
            info["chip"] = capability.details['chip']
        
        # Add PyTorch MPS info if available
        try:
            import torch
            if torch.backends.mps.is_available():
                info["pytorch_mps"] = True
                info["pytorch_version"] = torch.__version__
        except:
            pass
        
        return info


# Register backend
from .base import BackendFactory
BackendFactory.register(HardwareType.MPS, MPSBackend)