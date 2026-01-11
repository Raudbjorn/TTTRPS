#!/usr/bin/env python3
"""Test script for Ollama CUDA embeddings with dependency checking"""

import sys
import subprocess
import json
import time

def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    
    # Check required modules
    required_modules = {
        'chromadb': 'ChromaDB for vector storage',
        'requests': 'Requests for HTTP communication',
        'numpy': 'NumPy for numerical operations'
    }
    
    for module, description in required_modules.items():
        try:
            __import__(module)
            print(f"✓ {module}: {description}")
        except ImportError:
            print(f"✗ {module}: {description} - NOT FOUND")
            missing.append(module)
    
    return missing

def check_ollama():
    """Check if Ollama is available and running"""
    try:
        # Check if ollama command exists
        result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
        if result.returncode != 0:
            print("✗ Ollama: Not installed")
            return False
        
        print("✓ Ollama: Installed")
        
        # Check if Ollama service is running
        import requests
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=1)
            if response.status_code == 200:
                version = response.json()
                print(f"✓ Ollama service: Running (version {version.get('version', 'unknown')})")
                return True
            else:
                print("✗ Ollama service: Not responding correctly")
                return False
        except requests.exceptions.RequestException:
            print("✗ Ollama service: Not running")
            print("  Tip: Start Ollama with 'ollama serve'")
            return False
            
    except Exception as e:
        print(f"✗ Error checking Ollama: {e}")
        return False

# GPU info cache
_gpu_info_cache = None

def get_gpu_info():
    """Get GPU info using nvidia-smi, with caching."""
    global _gpu_info_cache
    if _gpu_info_cache is not None:
        return _gpu_info_cache
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                                '--format=csv,noheader'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            info = result.stdout.strip()
            _gpu_info_cache = info
            return info
        else:
            _gpu_info_cache = None
            return None
    except FileNotFoundError:
        _gpu_info_cache = None
        return None

def check_gpu():
    """Check GPU availability"""
    info = get_gpu_info()
    if info is not None:
        print(f"✓ NVIDIA GPU: {info}")
        return True
    else:
        # Determine if nvidia-smi is missing or just failed
        try:
            subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            print("✗ NVIDIA GPU: Not available")
        except FileNotFoundError:
            print("✗ NVIDIA GPU: nvidia-smi not found")
        return False

def test_embeddings_basic():
    """Test basic embedding functionality without ChromaDB"""
    print("\n--- Testing Basic Ollama Embeddings ---")
    
    try:
        import requests
        
        # Test embedding generation
        test_text = "This is a test document for GPU-accelerated embeddings"
        
        print(f"Testing embedding generation for: '{test_text[:50]}...'")
        
        start = time.time()
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": test_text
            }
        )
        
        if response.status_code == 200:
            embedding = response.json()['embedding']
            elapsed = time.time() - start
            print(f"✓ Embedding generated successfully")
            print(f"  - Dimension: {len(embedding)}")
            print(f"  - Time: {elapsed:.3f}s")
            print(f"  - First 5 values: {embedding[:5]}")
            return True
        else:
            print(f"✗ Failed to generate embedding: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing embeddings: {e}")
        return False

def test_ollama_models():
    """List available Ollama models"""
    print("\n--- Available Ollama Models ---")
    
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            
            # Check if nomic-embed-text is available
            if 'nomic-embed-text' in result.stdout:
                print("✓ nomic-embed-text model is available")
            else:
                print("✗ nomic-embed-text model not found")
                print("  Tip: Pull it with 'ollama pull nomic-embed-text'")
        else:
            print("✗ Failed to list models")
            
    except Exception as e:
        print(f"✗ Error listing models: {e}")

def main():
    print("=== Ollama CUDA Embeddings Test Suite ===\n")
    
    print("--- Checking Dependencies ---")
    missing = check_dependencies()
    
    print("\n--- Checking GPU ---")
    has_gpu = check_gpu()
    
    print("\n--- Checking Ollama ---")
    has_ollama = check_ollama()
    
    if has_ollama:
        test_ollama_models()
        
        if 'requests' not in missing:
            test_embeddings_basic()
    
    print("\n--- Summary ---")
    if missing:
        print(f"⚠ Missing Python modules: {', '.join(missing)}")
        print("  Install with: pip install " + " ".join(missing))
    else:
        print("✓ All Python dependencies available")
    
    if has_gpu:
        print("✓ GPU acceleration available")
    else:
        print("⚠ No GPU acceleration available")
    
    if has_ollama:
        print("✓ Ollama is ready")
    else:
        print("⚠ Ollama needs to be started")
    
    # Test full implementation if ChromaDB is available
    if 'chromadb' not in missing and has_ollama:
        print("\n--- Testing Full Implementation ---")
        try:
            from src.embeddings.ollama_cuda_embeddings import OllamaCudaEmbeddings
            
            print("Creating Ollama embeddings instance...")
            embeddings = OllamaCudaEmbeddings()
            
            stats = embeddings.get_collection_stats()
            print(f"✓ Embeddings initialized")
            print(f"  Collection: {stats['collection_name']}")
            print(f"  Documents: {stats['total_documents']}")
            print(f"  Device: {stats['device']}")
            
            if stats.get('gpu_info'):
                gpu_info = stats['gpu_info']
                print(f"  GPU: {gpu_info.get('gpu_name', 'Unknown')}")
                print(f"  GPU Memory: {gpu_info.get('memory_used_mb', '?')}/{gpu_info.get('memory_total_mb', '?')} MB")
            
            # Test search
            print("\nTesting search functionality...")
            results = embeddings.search("payment processing", top_k=2)
            print(f"✓ Search completed, found {len(results)} results")
            
        except Exception as e:
            print(f"✗ Error testing full implementation: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()