"""
Backend implementations for hardware acceleration

This module provides hardware-specific implementations for:
- CUDA (NVIDIA GPUs)
- OpenVINO (Intel GPUs)
- MPS (Apple Silicon)
- CPU (Fallback)
- Ollama (Local LLM embeddings)
"""

from .base import EmbeddingBackend, BackendFactory

# Import backends to register them automatically
from .cpu import CPUBackend
from .cuda import CUDABackend
from .openvino import OpenVINOBackend
from .mps import MPSBackend
from .ollama import OllamaBackend

__all__ = [
    "EmbeddingBackend",
    "BackendFactory",
    "CPUBackend",
    "CUDABackend",
    "OpenVINOBackend",
    "MPSBackend",
    "OllamaBackend",
]