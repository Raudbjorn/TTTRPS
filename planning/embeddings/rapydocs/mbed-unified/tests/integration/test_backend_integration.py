"""
Integration tests for backend system
"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mbed.backends.base import BackendFactory
from mbed.core.config import MBEDSettings
from mbed.core.hardware import HardwareDetector, HardwareType


class TestBackendIntegration(unittest.TestCase):
    """Integration tests for the entire backend system"""
    
    def test_end_to_end_cpu_backend(self):
        """Test complete flow with CPU backend"""
        # Create config
        config = MBEDSettings(
            hardware="cpu",
            model="nomic-embed-text",
            batch_size=32,
            workers=2
        )
        
        # Mock the model to avoid downloading
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock()}) as mock_modules:
            mock_st = mock_modules['sentence_transformers']
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.randn(3, 768)
            mock_st.SentenceTransformer.return_value = mock_model
            
            # Create backend through factory
            backend = BackendFactory.create(config)
            
            # Verify backend type
            self.assertEqual(backend.__class__.__name__, 'CPUBackend')
            
            # Test embedding generation
            texts = ["Hello world", "Test text", "Another sample"]
            embeddings = backend.generate_embeddings(texts)
            
            # Verify embeddings shape
            self.assertEqual(embeddings.shape[0], 3)  # Number of texts
            self.assertEqual(embeddings.shape[1], 768)  # Embedding dimension
    
    def test_hardware_auto_selection(self):
        """Test automatic hardware selection"""
        config = MBEDSettings(hardware="auto")
        
        # Mock hardware detection to return CPU only
        with patch.object(HardwareDetector, 'select_best', return_value=HardwareType.CPU):
            with patch.dict('sys.modules', {'sentence_transformers': MagicMock()}) as mock_modules:
                mock_st = mock_modules['sentence_transformers']
                mock_model = MagicMock()
                mock_model.encode.return_value = np.zeros((1, 768))
                mock_st.SentenceTransformer.return_value = mock_model
                
                # Create backend with auto selection
                backend = BackendFactory.create(config)
                
                # Should select CPU backend
                self.assertEqual(backend.__class__.__name__, 'CPUBackend')
    
    def test_batch_processing(self):
        """Test batch processing of embeddings"""
        config = MBEDSettings(
            hardware="cpu",
            batch_size=2  # Small batch size for testing
        )
        
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock()}) as mock_modules:
            mock_st = mock_modules['sentence_transformers']
            mock_model = MagicMock()
            
            # Mock encode to return different sizes based on input
            def encode_side_effect(texts, **kwargs):
                return np.random.randn(len(texts), 768)
            
            mock_model.encode.side_effect = encode_side_effect
            mock_st.SentenceTransformer.return_value = mock_model
            
            backend = BackendFactory.create(config)
            
            # Process multiple batches
            texts = ["Text " + str(i) for i in range(10)]
            embeddings = backend.batch_generate(texts)
            
            # Verify all texts were processed
            self.assertEqual(embeddings.shape[0], 10)
            
            # Verify encode was called multiple times (batching)
            self.assertGreater(mock_model.encode.call_count, 1)
    
    def test_backend_info_reporting(self):
        """Test backend information reporting"""
        config = MBEDSettings(hardware="cpu")
        
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock()}) as mock_modules:
            mock_st = mock_modules['sentence_transformers']
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros((1, 768))
            mock_st.SentenceTransformer.return_value = mock_model
            
            backend = BackendFactory.create(config)
            info = backend.get_info()
            
            # Verify info structure
            self.assertIn('backend', info)
            self.assertIn('model', info)
            self.assertIn('embedding_dim', info)
            self.assertIn('batch_size', info)
            
            # Verify values
            self.assertEqual(info['backend'], 'CPU')
            self.assertEqual(info['model'], 'nomic-embed-text')
            self.assertEqual(info['batch_size'], 32)
    
    def test_text_preprocessing(self):
        """Test text preprocessing in backend"""
        config = MBEDSettings(hardware="cpu")
        
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock()}) as mock_modules:
            mock_st = mock_modules['sentence_transformers']
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros((2, 768))
            mock_st.SentenceTransformer.return_value = mock_model
            
            backend = BackendFactory.create(config)
            
            # Test with texts that need preprocessing
            texts = [
                "  Text with   extra    spaces  ",
                "Very " + "long " * 5000 + "text"  # Exceeds max length
            ]
            
            embeddings = backend.generate_embeddings(texts)
            
            # Verify preprocessing was applied
            call_args = mock_model.encode.call_args[0][0]
            
            # Check whitespace was normalized
            self.assertNotIn("   ", call_args[0])
            
            # Check text was truncated
            self.assertLessEqual(len(call_args[1]), 8192)
    
    @patch('mbed.core.hardware.HardwareDetector.validate_hardware')
    def test_unavailable_hardware_fallback(self, mock_validate):
        """Test fallback when requested hardware is unavailable"""
        # CUDA not available
        mock_validate.return_value = False
        
        config = MBEDSettings(hardware="cuda")
        
        # Should raise error for unavailable hardware
        with self.assertRaises(ValueError) as context:
            BackendFactory.create(config)
        
        self.assertIn("not available", str(context.exception))
    
    def test_multiple_backend_instances(self):
        """Test creating multiple backend instances"""
        configs = [
            MBEDSettings(hardware="cpu", batch_size=32),
            MBEDSettings(hardware="cpu", batch_size=64),
        ]
        
        backends = []
        
        with patch.dict('sys.modules', {'sentence_transformers': MagicMock()}) as mock_modules:
            mock_st = mock_modules['sentence_transformers']
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros((1, 768))
            mock_st.SentenceTransformer.return_value = mock_model
            
            for config in configs:
                backend = BackendFactory.create(config)
                backends.append(backend)
            
            # Verify different instances
            self.assertIsNot(backends[0], backends[1])
            
            # Verify different configurations
            self.assertEqual(backends[0].batch_size, 32)
            self.assertEqual(backends[1].batch_size, 64)


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration with backend system"""
    
    @patch('mbed.core.hardware.HardwareDetector.detect_all')
    def test_cli_hardware_detection(self, mock_detect):
        """Test that CLI properly detects hardware"""
        from mbed.core.hardware import HardwareCapability
        
        # Mock hardware detection
        mock_detect.return_value = {
            HardwareType.CUDA: HardwareCapability(HardwareType.CUDA, False, {}),
            HardwareType.MPS: HardwareCapability(HardwareType.MPS, False, {}),
            HardwareType.OPENVINO: HardwareCapability(HardwareType.OPENVINO, False, {}),
            HardwareType.CPU: HardwareCapability(HardwareType.CPU, True, {'cpu_count': 8}),
        }
        
        # Get available hardware
        available = HardwareDetector.get_available()
        
        # Should only have CPU available
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0], HardwareType.CPU)
    
    def test_config_integration(self):
        """Test configuration system integration"""
        import os
        
        # Set environment variables
        os.environ['MBED_HARDWARE'] = 'cpu'
        os.environ['MBED_BATCH_SIZE'] = '64'
        
        # Reload settings
        from mbed.core.config import reload_settings
        settings = reload_settings()
        
        # Verify environment overrides
        self.assertEqual(settings.hardware, 'cpu')
        self.assertEqual(settings.batch_size, 64)
        
        # Clean up
        del os.environ['MBED_HARDWARE']
        del os.environ['MBED_BATCH_SIZE']


if __name__ == '__main__':
    unittest.main()