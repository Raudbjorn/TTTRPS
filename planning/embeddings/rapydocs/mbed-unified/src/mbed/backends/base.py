"""
Base backend interface and factory pattern
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path

from ..core.hardware import HardwareType, HardwareDetector
from ..core.config import MBEDSettings


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends"""
    
    def __init__(self, config: MBEDSettings):
        """
        Initialize backend with configuration
        
        Args:
            config: MBED configuration settings
        """
        self.config = config
        self.model_name = config.model
        self.batch_size = config.batch_size
        self.device = None
        
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the backend and load models"""
        pass
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Numpy array of embeddings (n_texts, embedding_dim)
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this backend"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available on the current system"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get backend information and capabilities"""
        pass
    
    def preprocess_texts(self, texts: List[str]) -> List[str]:
        """
        Preprocess texts before embedding (can be overridden)
        
        Args:
            texts: Raw input texts
            
        Returns:
            Preprocessed texts
        """
        # Default: basic cleaning
        processed = []
        for text in texts:
            # Remove excessive whitespace
            cleaned = " ".join(text.split())
            # Truncate if too long (model-specific limits)
            max_length = 8192  # Default max
            if len(cleaned) > max_length:
                cleaned = cleaned[:max_length]
            processed.append(cleaned)
        return processed
    
    def batch_generate(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings in batches for memory efficiency
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of embeddings
        """
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.generate_embeddings(batch)
            embeddings.append(batch_embeddings)
        
        return np.vstack(embeddings) if embeddings else np.array([])


class BackendFactory:
    """Factory for creating embedding backends"""
    
    _backends: Dict[HardwareType, type] = {}
    
    @classmethod
    def register(cls, hardware_type: HardwareType, backend_class: type) -> None:
        """
        Register a backend implementation
        
        Args:
            hardware_type: Hardware type this backend supports
            backend_class: Backend class to instantiate
        """
        cls._backends[hardware_type] = backend_class
    
    @classmethod
    def create(cls, config: MBEDSettings) -> EmbeddingBackend:
        """
        Create appropriate backend based on configuration
        
        Args:
            config: MBED configuration
            
        Returns:
            Initialized embedding backend
            
        Raises:
            ValueError: If requested backend is not available
        """
        # Determine hardware type
        if config.hardware == "auto":
            hardware_type = HardwareDetector.select_best()
        else:
            hardware_type = HardwareType(config.hardware)
        
        # Validate availability
        if not HardwareDetector.validate_hardware(hardware_type):
            raise ValueError(f"Hardware backend {hardware_type.value} is not available")
        
        # Get backend class
        backend_class = cls._backends.get(hardware_type)
        if not backend_class:
            raise ValueError(f"No backend implementation for {hardware_type.value}")
        
        # Create and initialize backend
        backend = backend_class(config)
        backend.initialize()
        
        return backend
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List available backend types"""
        available = []
        for hw_type in cls._backends:
            if HardwareDetector.validate_hardware(hw_type):
                available.append(hw_type.value)
        return available