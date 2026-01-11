"""Rapyd Documentation Embeddings System"""

__version__ = "1.0.0"

# Import with graceful fallback for optional dependencies
__all__ = []

try:
    from .embeddings.ollama_cuda_embeddings import OllamaCudaEmbeddings
    __all__.append("OllamaCudaEmbeddings")
except ImportError:
    pass

try:
    from .embeddings.embeddings_factory import detect_best_backend, create_embeddings
    __all__.extend(["detect_best_backend", "create_embeddings"])
except ImportError:
    pass

try:
    from .database.postgres_embeddings import PostgreSQLEmbeddingsBackend
    __all__.append("PostgreSQLEmbeddingsBackend")
except ImportError:
    pass

# These should always be available
from .utils.hardware_detection import HardwareDetector, detect_hardware
from .utils.ollama_service_manager import OllamaServiceManager, ollama_service

__all__.extend([
    "HardwareDetector",
    "detect_hardware",
    "OllamaServiceManager",
    "ollama_service",
])