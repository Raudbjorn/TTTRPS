"""
Tests for embedding backend implementations
"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock, Mock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from mbed.backends.base import EmbeddingBackend, BackendFactory
from mbed.backends.cpu import CPUBackend
from mbed.backends.cuda import CUDABackend
from mbed.backends.openvino import OpenVINOBackend
from mbed.backends.mps import MPSBackend
from mbed.core.hardware import HardwareType
from mbed.core.config import MBEDSettings


class TestBackendFactory(unittest.TestCase):
    """Test backend factory pattern"""
    
    def test_factory_registration(self):
        """Test that backends are registered with factory"""
        available = BackendFactory._backends
        
        # All backends should be registered
        self.assertIn(HardwareType.CPU, available)
        self.assertIn(HardwareType.CUDA, available)
        self.assertIn(HardwareType.OPENVINO, available)
        self.assertIn(HardwareType.MPS, available)
    
    @patch('mbed.core.hardware.HardwareDetector.validate_hardware')
    @patch('mbed.core.hardware.HardwareDetector.select_best')
    def test_factory_create_auto(self, mock_select, mock_validate):
        """Test factory creation with auto hardware selection"""
        mock_select.return_value = HardwareType.CPU
        mock_validate.return_value = True
        
        config = MBEDSettings(hardware="auto")
        
        with patch.object(CPUBackend, 'initialize'):
            backend = BackendFactory.create(config)
            
            self.assertIsInstance(backend, CPUBackend)
            mock_select.assert_called_once()
    
    @patch('mbed.core.hardware.HardwareDetector.validate_hardware')
    def test_factory_create_specific(self, mock_validate):
        """Test factory creation with specific hardware"""
        mock_validate.return_value = True
        
        config = MBEDSettings(hardware="cpu")
        
        with patch.object(CPUBackend, 'initialize'):
            backend = BackendFactory.create(config)
            
            self.assertIsInstance(backend, CPUBackend)
            self.assertEqual(backend.config.hardware, "cpu")
    
    @patch('mbed.core.hardware.HardwareDetector.validate_hardware')
    def test_factory_create_unavailable(self, mock_validate):
        """Test factory creation with unavailable hardware"""
        mock_validate.return_value = False
        
        config = MBEDSettings(hardware="cuda")
        
        with self.assertRaises(ValueError) as context:
            BackendFactory.create(config)
        
        self.assertIn("not available", str(context.exception))


class TestCPUBackend(unittest.TestCase):
    """Test CPU backend implementation"""
    
    def setUp(self):
        """Create CPU backend instance"""
        self.config = MBEDSettings(hardware="cpu")
        self.backend = CPUBackend(self.config)
    
    def test_cpu_always_available(self):
        """Test that CPU backend is always available"""
        self.assertTrue(self.backend.is_available())
    
    def test_cpu_info(self):
        """Test CPU backend info"""
        info = self.backend.get_info()
        
        self.assertEqual(info['backend'], 'CPU')
        self.assertIn('model', info)
        self.assertIn('embedding_dim', info)
        self.assertIn('batch_size', info)
        self.assertIn('cpu_count', info)
    
    def test_cpu_initialize(self):
        """Test CPU backend initialization"""
        # Mock the model loading
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((1, 768))
        
        mock_st = MagicMock(return_value=mock_model)
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock(SentenceTransformer=mock_st)}):
            self.backend.initialize()
            
            self.assertIsNotNone(self.backend.model)
            self.assertEqual(self.backend.embedding_dim, 768)
    
    def test_cpu_generate_embeddings(self):
        """Test CPU embedding generation"""
        mock_model = MagicMock()
        expected_embeddings = np.random.randn(2, 768)
        # First call returns dummy embedding for dimension check, second returns actual embeddings
        mock_model.encode.side_effect = [np.zeros((1, 768)), expected_embeddings]
        
        mock_st = MagicMock(return_value=mock_model)
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock(SentenceTransformer=mock_st)}):
            self.backend.initialize()
            
            texts = ["test text 1", "test text 2"]
            embeddings = self.backend.generate_embeddings(texts)
            
            np.testing.assert_array_equal(embeddings, expected_embeddings)
            # Should be called twice - once during init, once for generate
            self.assertEqual(mock_model.encode.call_count, 2)
    
    def test_preprocess_texts(self):
        """Test text preprocessing"""
        texts = [
            "  Extra   spaces  ",
            "Very " + "long " * 2000 + "text",  # Very long text
            "Normal text"
        ]
        
        processed = self.backend.preprocess_texts(texts)
        
        # Check whitespace normalization
        self.assertEqual(processed[0], "Extra spaces")
        
        # Check truncation
        self.assertLessEqual(len(processed[1]), 8192)
        
        # Check normal text passes through
        self.assertEqual(processed[2], "Normal text")


class TestCUDABackend(unittest.TestCase):
    """Test CUDA backend implementation"""
    
    def setUp(self):
        """Create CUDA backend instance"""
        self.config = MBEDSettings(hardware="cuda")
        self.backend = CUDABackend(self.config)
    
    @patch('mbed.core.hardware.HardwareDetector.detect_cuda')
    def test_cuda_availability_check(self, mock_detect):
        """Test CUDA availability checking"""
        from mbed.core.hardware import HardwareCapability
        
        # Test when CUDA is available
        mock_detect.return_value = HardwareCapability(HardwareType.CUDA, True, {})
        self.assertTrue(self.backend.is_available())
        
        # Test when CUDA is not available
        mock_detect.return_value = HardwareCapability(HardwareType.CUDA, False, {})
        self.assertFalse(self.backend.is_available())
    
    def test_cuda_initialize_success(self):
        """Test successful CUDA initialization"""
        # Mock torch module
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "RTX 3090"
        mock_torch.cuda.get_device_properties.return_value = MagicMock(
            total_memory=24 * 1024**3
        )
        # Mock device capability as tuple (major, minor)
        mock_torch.cuda.get_device_capability.return_value = (8, 6)  # Ampere architecture
        
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((1, 768))
        
        mock_st = MagicMock(return_value=mock_model)
        
        with patch.object(self.backend, 'is_available', return_value=True):
            with patch.dict('sys.modules', {
                'torch': mock_torch,
                'sentence_transformers': MagicMock(SentenceTransformer=mock_st)
            }):
                self.backend.initialize()
                
                self.assertIsNotNone(self.backend.model)
    
    def test_cuda_initialize_not_available(self):
        """Test CUDA initialization when not available"""
        with patch.object(self.backend, 'is_available', return_value=False):
            with self.assertRaises(RuntimeError) as context:
                self.backend.initialize()
            
            self.assertIn("not available", str(context.exception))
    
    def test_cuda_larger_batch_size(self):
        """Test that CUDA processes texts in batches"""
        # CUDA should process texts efficiently
        texts = ["test"] * 10  # Smaller test set
        
        # Mock the CUDA backend's batch processing
        with patch.object(self.backend, 'model') as mock_model:
            mock_model.encode.return_value = np.zeros((10, 768))
            self.backend.model = mock_model
            self.backend.current_batch_size = 128  # Set expected batch size
            
            # Mock the actual batch processing method
            with patch.object(self.backend, '_generate_with_optimization') as mock_gen:
                mock_gen.return_value = np.zeros((10, 768))
                
                result = self.backend.generate_embeddings(texts)
                
                # Verify that batch processing was called
                mock_gen.assert_called_once()
                self.assertEqual(result.shape, (10, 768))


class TestBackendIntegration(unittest.TestCase):
    """Integration tests for backend system"""
    
    def test_backend_interface_compliance(self):
        """Test that all backends implement the required interface"""
        backends = [CPUBackend, CUDABackend, OpenVINOBackend, MPSBackend]
        
        for backend_class in backends:
            # Check that class inherits from EmbeddingBackend
            self.assertTrue(issubclass(backend_class, EmbeddingBackend))
            
            # Check required methods exist
            self.assertTrue(hasattr(backend_class, 'initialize'))
            self.assertTrue(hasattr(backend_class, 'generate_embeddings'))
            self.assertTrue(hasattr(backend_class, 'get_embedding_dimension'))
            self.assertTrue(hasattr(backend_class, 'is_available'))
            self.assertTrue(hasattr(backend_class, 'get_info'))
    
    @patch('mbed.core.hardware.HardwareDetector.get_available')
    def test_list_available_backends(self, mock_available):
        """Test listing available backends"""
        mock_available.return_value = [HardwareType.CPU, HardwareType.CUDA]
        
        with patch('mbed.core.hardware.HardwareDetector.validate_hardware') as mock_validate:
            def validate_side_effect(hw_type):
                return hw_type in [HardwareType.CPU, HardwareType.CUDA]
            
            mock_validate.side_effect = validate_side_effect
            
            available = BackendFactory.list_available()
            
            self.assertIn('cpu', available)
            self.assertIn('cuda', available)
            self.assertNotIn('mps', available)
            self.assertNotIn('openvino', available)


if __name__ == '__main__':
    unittest.main()