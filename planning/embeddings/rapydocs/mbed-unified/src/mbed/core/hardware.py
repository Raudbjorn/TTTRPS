"""
Hardware detection and capability reporting
"""

import os
import platform
import subprocess
import sys
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class HardwareType(Enum):
    """Supported hardware acceleration types"""
    CUDA = "cuda"
    OPENVINO = "openvino"
    MPS = "mps"
    CPU = "cpu"
    OLLAMA = "ollama"
    AUTO = "auto"

class HardwareCapability:
    """Hardware capability information"""
    
    def __init__(self, 
                 hardware_type: HardwareType,
                 available: bool,
                 details: Optional[Dict[str, Any]] = None):
        self.hardware_type = hardware_type
        self.available = available
        self.details = details or {}
    
    def __repr__(self):
        return f"HardwareCapability({self.hardware_type.value}, available={self.available})"

class HardwareDetector:
    """Detects available hardware acceleration"""
    
    @classmethod
    def detect_cuda(cls) -> HardwareCapability:
        """Check if CUDA is available"""
        details = {}
        available = False
        
        try:
            # Check nvidia-smi
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse GPU info
                gpu_info = result.stdout.strip()
                if gpu_info:
                    parts = gpu_info.split(', ')
                    if len(parts) >= 2:
                        details['gpu_name'] = parts[0]
                        details['vram_mb'] = parts[1].replace(' MiB', '')
                
                # Check PyTorch CUDA support
                try:
                    import torch
                    if torch.cuda.is_available():
                        available = True
                        details['cuda_version'] = torch.version.cuda
                        details['device_count'] = torch.cuda.device_count()
                        details['current_device'] = torch.cuda.current_device()
                        
                        # Get VRAM in GB
                        if torch.cuda.device_count() > 0:
                            props = torch.cuda.get_device_properties(0)
                            details['vram_gb'] = props.total_memory / (1024**3)
                except ImportError:
                    # PyTorch not installed, but CUDA might still be available
                    available = True
                    details['pytorch_available'] = False
        
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"CUDA detection failed: {e}")
        
        return HardwareCapability(HardwareType.CUDA, available, details)
    
    @classmethod
    def detect_openvino(cls) -> HardwareCapability:
        """Check if OpenVINO is available"""
        details = {}
        available = False
        
        try:
            # Check for OpenVINO Python package
            import openvino as ov
            available = True
            details['version'] = ov.__version__
            
            # Check for Intel GPU
            try:
                core = ov.Core()
                devices = core.available_devices
                details['available_devices'] = devices
                
                # Check specifically for GPU
                if 'GPU' in devices:
                    details['intel_gpu'] = True
                    try:
                        gpu_props = core.get_property('GPU', 'FULL_DEVICE_NAME')
                        details['gpu_name'] = gpu_props
                    except:
                        pass
            except Exception as e:
                logger.debug(f"OpenVINO device detection error: {e}")
                
        except ImportError:
            # Check environment variable
            if os.environ.get('INTEL_OPENVINO_DIR'):
                details['env_configured'] = True
                # OpenVINO might be available but not in Python path
        
        return HardwareCapability(HardwareType.OPENVINO, available, details)
    
    @classmethod
    def detect_mps(cls) -> HardwareCapability:
        """Check if Apple Metal Performance Shaders are available"""
        details = {}
        available = False
        
        if platform.system() != 'Darwin':
            return HardwareCapability(HardwareType.MPS, False, {'reason': 'Not macOS'})
        
        try:
            # Check if we're on Apple Silicon
            result = subprocess.run(
                ['sysctl', '-n', 'hw.optional.arm64'],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip() == '1':
                details['apple_silicon'] = True
                
                # Get chip info
                chip_result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True,
                    text=True
                )
                if chip_result.returncode == 0:
                    details['chip'] = chip_result.stdout.strip()
                
                # Check PyTorch MPS support
                try:
                    import torch
                    if torch.backends.mps.is_available():
                        available = True
                        details['pytorch_mps'] = True
                        
                        # Check if MPS is built
                        if torch.backends.mps.is_built():
                            details['mps_built'] = True
                except ImportError:
                    # PyTorch not installed, but MPS might still be available
                    available = True
                    details['pytorch_available'] = False
            else:
                details['apple_silicon'] = False
                details['reason'] = 'Not Apple Silicon'
                
        except Exception as e:
            logger.debug(f"MPS detection error: {e}")
            details['error'] = str(e)
        
        return HardwareCapability(HardwareType.MPS, available, details)
    
    @classmethod
    def detect_cpu(cls) -> HardwareCapability:
        """CPU is always available"""
        import multiprocessing
        
        details = {
            'processor': platform.processor() or 'Unknown',
            'cpu_count': multiprocessing.cpu_count(),
            'python_version': sys.version.split()[0],
            'platform': platform.platform(),
            'architecture': platform.machine(),
        }
        
        # Check for specific CPU features
        try:
            import numpy as np
            details['numpy_version'] = np.__version__
            
            # Check BLAS backend
            try:
                blas_info = np.__config__.show()
                details['blas_available'] = True
            except:
                pass
                
        except ImportError:
            pass
        
        return HardwareCapability(HardwareType.CPU, True, details)
    
    @classmethod
    def detect_all(cls) -> Dict[HardwareType, HardwareCapability]:
        """Detect all available hardware"""
        return {
            HardwareType.CUDA: cls.detect_cuda(),
            HardwareType.OPENVINO: cls.detect_openvino(),
            HardwareType.MPS: cls.detect_mps(),
            HardwareType.CPU: cls.detect_cpu(),
        }
    
    @classmethod
    def get_available(cls) -> List[HardwareType]:
        """Get list of available hardware types"""
        detected = cls.detect_all()
        return [hw for hw, cap in detected.items() if cap.available]
    
    @classmethod
    def select_best(cls) -> HardwareType:
        """Select the best available hardware"""
        available = cls.get_available()
        
        # Priority order
        priority = [
            HardwareType.CUDA,
            HardwareType.MPS,
            HardwareType.OPENVINO,
            HardwareType.CPU
        ]
        
        for hw in priority:
            if hw in available:
                logger.info(f"Selected hardware backend: {hw.value}")
                return hw
        
        return HardwareType.CPU
    
    @classmethod
    def validate_hardware(cls, requested: HardwareType) -> bool:
        """Check if requested hardware is available"""
        if requested == HardwareType.AUTO:
            return True
        
        if requested == HardwareType.CPU:
            return True  # CPU is always available
        
        capability = cls.detect_all().get(requested)
        return capability and capability.available
    
    @classmethod
    def get_capability_report(cls, hardware: HardwareType) -> Dict[str, Any]:
        """Get detailed capability report for specific hardware"""
        if hardware == HardwareType.AUTO:
            hardware = cls.select_best()
        
        capability = cls.detect_all().get(hardware)
        if not capability:
            return {'error': f'Unknown hardware type: {hardware}'}
        
        return {
            'hardware': hardware.value,
            'available': capability.available,
            'details': capability.details
        }

class DeveloperChecker:
    """Check development readiness for specific backends"""
    
    @staticmethod
    def check_cuda_development() -> Dict[str, Any]:
        """Check CUDA development readiness"""
        report = {
            'can_develop': False,
            'hardware': False,
            'cuda_toolkit': False,
            'pytorch_cuda': False,
            'missing': []
        }
        
        # Check hardware
        cuda_cap = HardwareDetector.detect_cuda()
        if cuda_cap.available:
            report['hardware'] = True
            if 'vram_gb' in cuda_cap.details:
                report['vram_gb'] = cuda_cap.details['vram_gb']
        else:
            report['missing'].append("NVIDIA GPU not detected")
            report['ready_message'] = "❌ Not ready for CUDA development"
            return report
        
        # Check CUDA toolkit
        try:
            result = subprocess.run(
                ['nvcc', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                report['cuda_toolkit'] = True
                # Parse version
                for line in result.stdout.split('\n'):
                    if 'release' in line.lower():
                        report['cuda_toolkit_version'] = line.strip()
                        break
        except FileNotFoundError:
            report['missing'].append("CUDA toolkit (nvcc) not found")
        
        # Check PyTorch with CUDA
        try:
            import torch
            if torch.cuda.is_available():
                report['pytorch_cuda'] = True
                report['pytorch_version'] = torch.__version__
                report['cuda_version'] = torch.version.cuda
            else:
                report['missing'].append("PyTorch CUDA support not available")
        except ImportError:
            report['missing'].append("PyTorch not installed")
        
        report['can_develop'] = (
            report['hardware'] and 
            report['cuda_toolkit'] and 
            report['pytorch_cuda']
        )
        
        if report['can_develop']:
            report['ready_message'] = "✅ Ready for CUDA development"
        else:
            report['ready_message'] = "❌ Not ready for CUDA development"
        
        return report
    
    @staticmethod
    def check_openvino_development() -> Dict[str, Any]:
        """Check OpenVINO development readiness"""
        report = {
            'can_develop': False,
            'intel_gpu': False,
            'openvino_runtime': False,
            'model_optimizer': False,
            'missing': []
        }
        
        # Check OpenVINO capability
        ov_cap = HardwareDetector.detect_openvino()
        if ov_cap.available:
            report['openvino_runtime'] = True
            if 'version' in ov_cap.details:
                report['openvino_version'] = ov_cap.details['version']
            if ov_cap.details.get('intel_gpu'):
                report['intel_gpu'] = True
        else:
            report['missing'].append("OpenVINO runtime not installed")
        
        # Check for Intel GPU (on Linux)
        if platform.system() == 'Linux' and not report['intel_gpu']:
            try:
                result = subprocess.run(
                    ['lspci'],
                    capture_output=True,
                    text=True
                )
                if 'Intel' in result.stdout and ('Graphics' in result.stdout or 'VGA' in result.stdout):
                    report['intel_gpu'] = True
            except:
                pass
        
        # Check model optimizer
        try:
            import openvino.tools.mo
            report['model_optimizer'] = True
        except ImportError:
            report['missing'].append("OpenVINO Model Optimizer not found")
        
        report['can_develop'] = (
            report['openvino_runtime'] and 
            report['model_optimizer']
        )
        
        if report['can_develop']:
            report['ready_message'] = "✅ Ready for OpenVINO development"
        else:
            report['ready_message'] = "❌ Not ready for OpenVINO development"
        
        return report
    
    @staticmethod
    def check_mps_development() -> Dict[str, Any]:
        """Check MPS development readiness"""
        report = {
            'can_develop': False,
            'apple_silicon': False,
            'pytorch_mps': False,
            'xcode_tools': False,
            'missing': []
        }
        
        # Check MPS capability
        mps_cap = HardwareDetector.detect_mps()
        if mps_cap.available:
            report['apple_silicon'] = True
            if 'chip' in mps_cap.details:
                report['chip'] = mps_cap.details['chip']
            if mps_cap.details.get('pytorch_mps'):
                report['pytorch_mps'] = True
        else:
            report['missing'].append("Apple Silicon Mac required")
            report['ready_message'] = "❌ Not ready for MPS development"
            return report
        
        # Check Xcode command line tools
        try:
            result = subprocess.run(
                ['xcode-select', '-p'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                report['xcode_tools'] = True
                report['xcode_path'] = result.stdout.strip()
        except:
            report['missing'].append("Xcode command line tools not installed")
        
        report['can_develop'] = (
            report['apple_silicon'] and 
            report['pytorch_mps'] and 
            report['xcode_tools']
        )
        
        if report['can_develop']:
            report['ready_message'] = "✅ Ready for MPS development"
        else:
            report['ready_message'] = "❌ Not ready for MPS development"
        
        return report
    
    @staticmethod
    def check_cpu_development() -> Dict[str, Any]:
        """Check CPU development readiness"""
        report = {
            'can_develop': True,
            'hardware': True,
            'python': True,
            'numpy': True,
            'missing': []
        }
        
        # Get CPU details
        cpu_cap = HardwareDetector.detect_cpu()
        if 'cpu_count' in cpu_cap.details:
            report['cpu_count'] = cpu_cap.details['cpu_count']
        if 'numpy_version' in cpu_cap.details:
            report['numpy_version'] = cpu_cap.details['numpy_version']
        
        # Check Python version
        report['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # CPU development is always ready
        report['ready_message'] = "✅ Ready for CPU development"
        
        return report