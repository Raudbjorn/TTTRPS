"""Unified hardware detection module for GPU and CPU capabilities"""

import platform
import subprocess
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class HardwareDetector:
    """Detects available hardware acceleration capabilities"""
    
    _cache: Optional[Dict] = None
    
    @classmethod
    def detect(cls, force_refresh: bool = False) -> Dict:
        """
        Detect available hardware capabilities
        
        Returns:
            Dict with keys:
            - has_nvidia_gpu: bool
            - has_cuda: bool
            - has_intel_gpu: bool
            - has_apple_silicon: bool
            - has_mps: bool
            - recommended_backend: str
            - system_info: dict
        """
        if cls._cache is not None and not force_refresh:
            return cls._cache
        
        result = {
            "has_nvidia_gpu": False,
            "has_cuda": False,
            "has_intel_gpu": False,
            "has_apple_silicon": False,
            "has_mps": False,
            "recommended_backend": "cpu",
            "system_info": {
                "platform": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        }
        
        system = platform.system()
        
        # Check for NVIDIA GPU and CUDA
        if system == "Linux":
            result["has_nvidia_gpu"] = cls._check_nvidia_gpu()
            result["has_cuda"] = cls._check_cuda()
            result["has_intel_gpu"] = cls._check_intel_gpu()
        
        # Check for Apple Silicon and MPS
        elif system == "Darwin":
            result["has_apple_silicon"] = cls._check_apple_silicon()
            if result["has_apple_silicon"]:
                result["has_mps"] = cls._check_mps()
        
        # Windows support (basic)
        elif system == "Windows":
            result["has_nvidia_gpu"] = cls._check_nvidia_gpu_windows()
            result["has_cuda"] = cls._check_cuda_windows()
        
        # Determine recommended backend
        result["recommended_backend"] = cls._determine_backend(result)
        
        cls._cache = result
        return result
    
    @staticmethod
    def _check_nvidia_gpu() -> bool:
        """Check for NVIDIA GPU on Linux"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def _check_cuda() -> bool:
        """Check for CUDA availability on Linux"""
        try:
            result = subprocess.run(
                ['nvcc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def _check_intel_gpu() -> bool:
        """Check for Intel GPU on Linux"""
        try:
            # Check for Intel GPU in lspci
            result = subprocess.run(
                ['lspci'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return 'Intel' in result.stdout and ('VGA' in result.stdout or 'Display' in result.stdout)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Alternative: check for Intel GPU driver
        try:
            result = subprocess.run(
                ['ls', '/dev/dri/'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'renderD' in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def _check_apple_silicon() -> bool:
        """Check for Apple Silicon on macOS"""
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'hw.optional.arm64'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() == '1'
        except (subprocess.SubprocessError, FileNotFoundError):
            return platform.machine() == 'arm64'
    
    @staticmethod
    def _check_mps() -> bool:
        """Check for Metal Performance Shaders on macOS"""
        try:
            import torch
            return torch.backends.mps.is_available()
        except ImportError:
            # If PyTorch not available, assume MPS is available on Apple Silicon
            return True
    
    @staticmethod
    def _check_nvidia_gpu_windows() -> bool:
        """Check for NVIDIA GPU on Windows"""
        try:
            result = subprocess.run(
                ['nvidia-smi.exe', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def _check_cuda_windows() -> bool:
        """Check for CUDA availability on Windows"""
        try:
            result = subprocess.run(
                ['nvcc.exe', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def _determine_backend(capabilities: Dict) -> str:
        """Determine the recommended backend based on capabilities"""
        # Priority order: CUDA > MPS > Intel GPU > CPU
        if capabilities["has_cuda"] and capabilities["has_nvidia_gpu"]:
            return "ollama_cuda"
        elif capabilities["has_mps"] and capabilities["has_apple_silicon"]:
            return "ollama_mps"
        elif capabilities["has_intel_gpu"]:
            return "ollama_intel"
        else:
            return "cpu"
    
    @classmethod
    def get_summary(cls) -> str:
        """Get a human-readable summary of hardware capabilities"""
        info = cls.detect()
        
        lines = [
            "Hardware Detection Summary:",
            f"  Platform: {info['system_info']['platform']}",
            f"  Machine: {info['system_info']['machine']}",
            f"  NVIDIA GPU: {'✓' if info['has_nvidia_gpu'] else '✗'}",
            f"  CUDA: {'✓' if info['has_cuda'] else '✗'}",
            f"  Intel GPU: {'✓' if info['has_intel_gpu'] else '✗'}",
            f"  Apple Silicon: {'✓' if info['has_apple_silicon'] else '✗'}",
            f"  MPS: {'✓' if info['has_mps'] else '✗'}",
            f"  Recommended: {info['recommended_backend']}"
        ]
        
        return "\n".join(lines)

# Convenience function for quick detection
def detect_hardware() -> Dict:
    """Quick function to detect hardware capabilities"""
    return HardwareDetector.detect()

def get_recommended_backend() -> str:
    """Get the recommended backend for the current hardware"""
    return HardwareDetector.detect()["recommended_backend"]