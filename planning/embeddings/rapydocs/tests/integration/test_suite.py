#!/usr/bin/env python3
"""
Unified test suite for Rapyd Documentation Embeddings System

This test suite covers:
- Ollama embeddings with CUDA acceleration
- PostgreSQL with pgvector
- ChromaDB vector database
- MCP server integration
- Hardware detection
"""

import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_all_tests():
    """Run all tests in the test suite"""
    
    # Create test loader
    loader = unittest.TestLoader()
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test modules
    test_modules = [
        'test_ollama_embeddings',      # Ollama embeddings tests
        'test_embeddings_complete',     # Complete embeddings workflow
        'test_mcp_server',             # MCP server tests
        'test_mcp_integration',        # MCP integration tests
        'test_mcp_postgres',           # MCP with PostgreSQL
        'test_postgres_setup',         # PostgreSQL setup tests
    ]
    
    print("=" * 60)
    print("Rapyd Documentation Test Suite")
    print("=" * 60)
    
    # Load tests from modules
    for module_name in test_modules:
        try:
            module = __import__(module_name)
            suite.addTests(loader.loadTestsFromModule(module))
            print(f"✓ Loaded tests from {module_name}")
        except ImportError as e:
            print(f"✗ Could not load {module_name}: {e}")
        except Exception as e:
            print(f"✗ Error loading {module_name}: {e}")
    
    print("-" * 60)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

def run_specific_test(test_name):
    """Run a specific test module"""
    
    print(f"Running test: {test_name}")
    print("-" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    try:
        module = __import__(test_name)
        suite.addTests(loader.loadTestsFromModule(module))
    except ImportError as e:
        print(f"Error: Could not load {test_name}: {e}")
        return 1
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        # Run specific test
        exit_code = run_specific_test(sys.argv[1])
    else:
        # Run all tests
        exit_code = run_all_tests()
    
    sys.exit(exit_code)