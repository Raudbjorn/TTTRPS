"""Factory for automatically selecting the best available embeddings backend"""

import os
import requests
from typing import Optional
from ..utils.hardware_detection import HardwareDetector, get_recommended_backend
from ..utils.logging_config import get_logger
from ..utils.common import ErrorHandler

logger = get_logger(__name__)

def detect_best_backend() -> str:
    """Detect the best available embeddings backend using unified hardware detection"""
    
    # Get hardware capabilities
    hw_info = HardwareDetector.detect()
    
    # Check for Ollama if we have GPU capabilities
    if hw_info["has_nvidia_gpu"] and hw_info["has_cuda"]:
        # Check if Ollama is available
        try:
            ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.get(f"{ollama_base_url}/api/version", timeout=1)
            if response.status_code == 200:
                logger.info("Detected NVIDIA GPU with Ollama - using GPU-accelerated Ollama embeddings")
                return "ollama_cuda"
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            logger.debug("Ollama not available")
        
        logger.info("Detected NVIDIA GPU without Ollama - using standard CUDA acceleration")
        return "cuda"
    
    # Check for Apple Silicon with MPS
    if hw_info["has_apple_silicon"] and hw_info["has_mps"]:
        try:
            import torch
            if torch.backends.mps.is_available():
                logger.info("Detected Apple Silicon with MPS - using Metal acceleration")
                return "mps"
        except ImportError:
            logger.debug("PyTorch not available for MPS")
        except Exception:
            logger.debug("Error checking MPS availability")
    
    # Check for Intel GPU
    if os.path.exists("/dev/dri/renderD128"):
        logger.info("Detected Intel GPU - using Intel GPU acceleration")
        return "intel_gpu"
    
    # Default to CPU
    logger.info("No GPU acceleration detected - using CPU")
    return "cpu"

def create_embeddings(model_name: Optional[str] = None, collection_name: str = "rapyd_docs", concurrency_limit: Optional[int] = None):
    """Create the best available embeddings instance"""
    
    backend = detect_best_backend()
    
    if backend == "ollama_cuda":
        try:
            from .ollama_cuda_embeddings import OllamaCudaEmbeddings
            logger.info("Initializing Ollama CUDA embeddings for maximum performance")
            kwargs = {
                "model_name": model_name or "nomic-embed-text",
                "collection_name": collection_name
            }
            if concurrency_limit is not None:
                kwargs["concurrency_limit"] = concurrency_limit
            return OllamaCudaEmbeddings(**kwargs)
        except ImportError:
            logger.warning("Failed to import Ollama CUDA embeddings")
            backend = "cpu"
    
    # Fallback to universal embeddings
    from .universal_embeddings import UniversalEmbeddings
    logger.info(f"Initializing universal embeddings with {backend} backend")
    return UniversalEmbeddings(
        model_name=model_name or "all-MiniLM-L6-v2",
        collection_name=collection_name
    )

def initialize_database():
    """Initialize the database with the best available backend"""
    
    backend = detect_best_backend()
    
    if backend == "ollama_cuda":
        try:
            from ollama_cuda_embeddings import initialize_ollama_database
            logger.info("Initializing database with Ollama CUDA backend")
            return initialize_ollama_database()
        except ImportError:
            logger.warning("Failed to use Ollama backend")
    
    # Fallback to universal embeddings
    from universal_embeddings import initialize_database as init_universal
    logger.info("Initializing database with universal backend")
    return init_universal()

if __name__ == "__main__":
    # Test the factory
    print("Testing embeddings factory...")
    print(f"Detected best backend: {detect_best_backend()}")
    
    # Create embeddings instance
    embeddings = create_embeddings()
    stats = embeddings.get_collection_stats()
    print(f"\nEmbeddings stats: {stats}")
    
    # Test search
    test_query = "payment processing"
    results = embeddings.search(test_query, top_k=2)
    print(f"\nSearch results for '{test_query}':")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.3f}")