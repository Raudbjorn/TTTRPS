"""
Tests for hardware detection and validation
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import platform
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from mbed.core.hardware import (
    HardwareDetector, 
    HardwareType,
    HardwareCapability,
    DeveloperChecker
)


class TestHardwareDetection(unittest.TestCase):
    """Test hardware detection functionality"""
    
    def test_hardware_type_enum(self):
        """Test HardwareType enum values"""
        self.assertEqual(HardwareType.CUDA.value, "cuda")
        self.assertEqual(HardwareType.OPENVINO.value, "openvino")
        self.assertEqual(HardwareType.MPS.value, "mps")
        self.assertEqual(HardwareType.CPU.value, "cpu")
        self.assertEqual(HardwareType.AUTO.value, "auto")
    
    def test_cpu_always_available(self):
        """Test that CPU backend is always detected as available"""
        cpu_cap = HardwareDetector.detect_cpu()
        self.assertTrue(cpu_cap.available)
        self.assertEqual(cpu_cap.hardware_type, HardwareType.CPU)
        self.assertIn('cpu_count', cpu_cap.details)
    
    @patch('mbed.core.hardware.subprocess.run')
    def test_cuda_detection_with_nvidia_smi(self, mock_run):
        """Test CUDA detection when nvidia-smi is available"""
        # Mock successful nvidia-smi output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NVIDIA GeForce RTX 3090, 24576 MiB"
        )
        
        # Mock torch module
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 3090"
        mock_torch.cuda.get_device_capability.return_value = (8, 6)
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            cuda_cap = HardwareDetector.detect_cuda()
            
            # Should detect CUDA when nvidia-smi succeeds
            self.assertTrue(cuda_cap.available)
            self.assertEqual(cuda_cap.hardware_type, HardwareType.CUDA)
    
    @patch('mbed.core.hardware.subprocess.run')
    def test_cuda_detection_without_gpu(self, mock_run):
        """Test CUDA detection when no GPU is present"""
        # Mock nvidia-smi not found
        mock_run.side_effect = FileNotFoundError()
        
        cuda_cap = HardwareDetector.detect_cuda()
        
        # Should not detect CUDA when nvidia-smi fails
        self.assertFalse(cuda_cap.available)
        self.assertEqual(cuda_cap.hardware_type, HardwareType.CUDA)
    
    @patch('platform.system')
    @patch('mbed.core.hardware.subprocess.run')
    def test_mps_detection_on_mac(self, mock_run, mock_system):
        """Test MPS detection on Apple Silicon Mac"""
        mock_system.return_value = 'Darwin'
        
        # Mock sysctl output for Apple Silicon
        def run_side_effect(cmd, *args, **kwargs):
            if 'sysctl' in cmd:
                return MagicMock(stdout='1')
            return MagicMock(stdout='Apple M1\n8')
        
        mock_run.side_effect = run_side_effect
        
        # Mock torch module
        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            mps_cap = HardwareDetector.detect_mps()
            
            # Should detect MPS on Apple Silicon
            self.assertTrue(mps_cap.available)
            self.assertEqual(mps_cap.hardware_type, HardwareType.MPS)
    
    @patch('platform.system')
    def test_mps_detection_on_linux(self, mock_system):
        """Test MPS detection on non-Mac systems"""
        mock_system.return_value = 'Linux'
        
        mps_cap = HardwareDetector.detect_mps()
        
        # Should not detect MPS on Linux
        self.assertFalse(mps_cap.available)
        self.assertEqual(mps_cap.hardware_type, HardwareType.MPS)
    
    def test_select_best_with_cpu_only(self):
        """Test best hardware selection when only CPU is available"""
        with patch.object(HardwareDetector, 'detect_all', return_value={
            HardwareType.CUDA: HardwareCapability(HardwareType.CUDA, False, {}),
            HardwareType.MPS: HardwareCapability(HardwareType.MPS, False, {}),
            HardwareType.OPENVINO: HardwareCapability(HardwareType.OPENVINO, False, {}),
            HardwareType.CPU: HardwareCapability(HardwareType.CPU, True, {'cpu_count': 8}),
        }):
            best = HardwareDetector.select_best()
            self.assertEqual(best, HardwareType.CPU)
    
    def test_select_best_priority(self):
        """Test hardware selection priority (CUDA > MPS > OpenVINO > CPU)"""
        # Test with all available - should pick CUDA
        with patch.object(HardwareDetector, 'detect_all', return_value={
            HardwareType.CUDA: HardwareCapability(HardwareType.CUDA, True, {}),
            HardwareType.MPS: HardwareCapability(HardwareType.MPS, True, {}),
            HardwareType.OPENVINO: HardwareCapability(HardwareType.OPENVINO, True, {}),
            HardwareType.CPU: HardwareCapability(HardwareType.CPU, True, {}),
        }):
            best = HardwareDetector.select_best()
            self.assertEqual(best, HardwareType.CUDA)
        
        # Test with MPS and CPU - should pick MPS
        with patch.object(HardwareDetector, 'detect_all', return_value={
            HardwareType.CUDA: HardwareCapability(HardwareType.CUDA, False, {}),
            HardwareType.MPS: HardwareCapability(HardwareType.MPS, True, {}),
            HardwareType.OPENVINO: HardwareCapability(HardwareType.OPENVINO, False, {}),
            HardwareType.CPU: HardwareCapability(HardwareType.CPU, True, {}),
        }):
            best = HardwareDetector.select_best()
            self.assertEqual(best, HardwareType.MPS)
    
    def test_validate_hardware(self):
        """Test hardware validation"""
        # CPU should always validate as true
        self.assertTrue(HardwareDetector.validate_hardware(HardwareType.CPU))
        
        # AUTO should always validate as true
        self.assertTrue(HardwareDetector.validate_hardware(HardwareType.AUTO))
        
        # Test validation with unavailable hardware
        with patch.object(HardwareDetector, 'detect_all', return_value={
            HardwareType.CUDA: HardwareCapability(HardwareType.CUDA, False, {}),
        }):
            self.assertFalse(HardwareDetector.validate_hardware(HardwareType.CUDA))


class TestDeveloperChecker(unittest.TestCase):
    """Test developer readiness checking"""
    
    def test_cpu_development_always_ready(self):
        """Test that CPU development is always ready"""
        report = DeveloperChecker.check_cpu_development()
        self.assertTrue(report['can_develop'])
        self.assertIn('ready_message', report)
        self.assertIn('Ready for CPU development', report['ready_message'])
    
    @patch('subprocess.run')
    def test_cuda_development_missing_toolkit(self, mock_run):
        """Test CUDA development check when toolkit is missing"""
        # Check if CUDA/torch can be imported - skip if environment doesn't support it
        try:
            import torch
            # If torch import fails due to CUDA libraries, we'll catch it below
        except (ImportError, OSError, ValueError) as e:
            if "libcublas" in str(e) or "libcudart" in str(e) or "CUDA" in str(e):
                self.skipTest(f"Skipping CUDA test - CUDA not available in environment: {e}")
            raise

        # Mock nvidia-smi success but nvcc failure
        def side_effect(*args, **kwargs):
            if 'nvidia-smi' in args[0]:
                return MagicMock(returncode=0, stdout="GPU present")
            elif 'nvcc' in args[0]:
                raise FileNotFoundError()

        mock_run.side_effect = side_effect

        with patch.object(HardwareDetector, 'detect_cuda',
                         return_value=HardwareCapability(HardwareType.CUDA, True, {})):
            report = DeveloperChecker.check_cuda_development()

            self.assertFalse(report['can_develop'])
            self.assertIn('missing', report)
            self.assertTrue(any('nvcc' in item for item in report['missing']))
    
    @patch('platform.system')
    def test_mps_development_on_non_mac(self, mock_system):
        """Test MPS development check on non-Mac systems"""
        mock_system.return_value = 'Linux'
        
        report = DeveloperChecker.check_mps_development()
        
        self.assertFalse(report['can_develop'])
        self.assertIn('ready_message', report)
        self.assertIn('Not ready', report['ready_message'])


if __name__ == '__main__':
    unittest.main()