"""Ollama embeddings with CUDA GPU acceleration for high-performance semantic search"""

import json
import time
import subprocess
import atexit
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import platform
import os
import requests
import numpy as np

try:
    import chromadb
    from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    # Create dummy types for type hints
    EmbeddingFunction = object
    Documents = List[str]
    Embeddings = List[List[float]]

from ..utils.logging_config import get_logger
from ..utils.common import ErrorHandler, CollectionUtils, DatabaseLoader

logger = get_logger(__name__)

# Model configuration constants
MODEL_DIMENSIONS = {
    "mxbai-embed-large": 1024,
    "nomic-embed-text": 768,
    "mxbai-embed-large:latest": 1024,
    "nomic-embed-text:latest": 768,
}

# Configuration constants
DEFAULT_MODEL_NAME = "nomic-embed-text"
DEFAULT_MODEL_DIMENSION = 768
DEFAULT_CONCURRENCY_LIMIT = 3
DEFAULT_EMBEDDING_TIMEOUT = 30  # Increased timeout from 10s to 30s for larger models
OLLAMA_SERVICE_START_DELAY = 2
SCORE_THRESHOLD = 0.3
MAX_EMBEDDING_FAILURES = 10
SMALL_BATCH_SIZE = 3

class OllamaEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function for Ollama with GPU acceleration"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, base_url: str = "http://localhost:11434", concurrency_limit: int = DEFAULT_CONCURRENCY_LIMIT):
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is required for OllamaEmbeddingFunction. Install with: pip install chromadb")
        self.model_name = model_name
        self.base_url = self._validate_ollama_url(base_url)
        self.concurrency_limit = concurrency_limit
        self._failure_count = 0
        self._ensure_model_available()
    
    def _validate_ollama_url(self, url: str) -> str:
        """Validate and sanitize Ollama base URL to prevent SSRF attacks"""
        parsed = urlparse(url)
        
        # Only allow http/https schemes
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed")
        
        # Only allow localhost connections for security
        allowed_hosts = ['localhost', '127.0.0.1', '::1']
        if parsed.hostname not in allowed_hosts:
            raise ValueError(f"Only localhost connections allowed. Got: {parsed.hostname}")
        
        # Validate port if specified
        if parsed.port and (parsed.port < 1 or parsed.port > 65535):
            raise ValueError(f"Invalid port number: {parsed.port}")
        
        return url
        
    def _ensure_model_available(self):
        """Ensure the embedding model is available in Ollama"""
        try:
            # Check if model exists
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.model_name not in model_names and f"{self.model_name}:latest" not in model_names:
                    logger.warning(f"Model {self.model_name} not found in Ollama!")
                    logger.info("Available models:")
                    for name in model_names:
                        logger.info(f"  - {name}")
                    
                    # Don't automatically pull models - let user do this manually
                    logger.info(f"Please run: ollama pull {self.model_name}")
                    raise ValueError(f"Model {self.model_name} not available in Ollama")
                else:
                    logger.info(f"Model {self.model_name} is available in Ollama")
        except Exception as e:
            logger.warning(f"Could not check model availability: {e}")
    
    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for the input documents using Ollama with parallel processing"""
        import concurrent.futures
        
        def get_single_embedding(text: str) -> list:
            """Get embedding for a single text"""
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": text
                    },
                    timeout=DEFAULT_EMBEDDING_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.json()['embedding']
                else:
                    logger.error(f"Failed to get embedding: {response.text}")
                    # Track failures and warn about fallback
                    self._failure_count += 1
                    logger.warning(f"Embedding generation failed (failure #{self._failure_count}), using zero vector fallback")
                    
                    if self._failure_count > MAX_EMBEDDING_FAILURES:
                        raise RuntimeError(f"Too many embedding failures ({self._failure_count}). Check Ollama service status.")
                    
                    dim = MODEL_DIMENSIONS.get(self.model_name, DEFAULT_MODEL_DIMENSION)
                    return [0.0] * dim
                    
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                self._failure_count += 1
                logger.warning(f"Embedding generation error (failure #{self._failure_count}), using zero vector fallback")
                
                if self._failure_count > MAX_EMBEDDING_FAILURES:
                    raise RuntimeError(f"Too many embedding failures ({self._failure_count}). Error: {e}")
                
                dim = MODEL_DIMENSIONS.get(self.model_name, DEFAULT_MODEL_DIMENSION)
                return [0.0] * dim
        
        # For small batches, use sequential processing to avoid overhead
        if len(input) <= SMALL_BATCH_SIZE:
            embeddings = []
            for text in input:
                embeddings.append(get_single_embedding(text))
            return embeddings
        
        # For larger batches, use parallel processing with limited concurrency
        max_workers = min(self.concurrency_limit, len(input))  # Conservative limit to avoid overwhelming Ollama
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all requests and maintain order
                futures = [executor.submit(get_single_embedding, text) for text in input]
                
                embeddings = []
                for i, future in enumerate(futures):
                    try:
                        embedding = future.result(timeout=15)
                        embeddings.append(embedding)
                    except concurrent.futures.TimeoutError:
                        logger.error(f"Embedding request {i+1} timed out")
                        dim = MODEL_DIMENSIONS.get(self.model_name, DEFAULT_MODEL_DIMENSION)
                        embeddings.append([0.0] * dim)
                    except Exception as e:
                        logger.error(f"Error in parallel embedding {i+1}: {e}")
                        dim = MODEL_DIMENSIONS.get(self.model_name, DEFAULT_MODEL_DIMENSION)
                        embeddings.append([0.0] * dim)
                
                logger.debug(f"Processed {len(input)} embeddings in parallel")
                return embeddings
                
        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            # Fallback to sequential processing
            logger.info("Falling back to sequential embedding generation")
            embeddings = []
            for text in input:
                embeddings.append(get_single_embedding(text))
            return embeddings

class OllamaCudaEmbeddings:
    """High-performance embeddings using Ollama with CUDA GPU acceleration"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, collection_name: str = "rapyd_docs", concurrency_limit: int = DEFAULT_CONCURRENCY_LIMIT):
        self.model_name = model_name
        self.collection_name = collection_name
        self.concurrency_limit = concurrency_limit
        self.ollama_process = None  # Track subprocess for proper cleanup
        self.device = self._detect_device()
        
        logger.info(f"Initializing Ollama embeddings with {self.device}...")
        
        # Check Ollama service
        if not self._check_ollama_service():
            logger.warning("Ollama service not running, attempting to start...")
            self._start_ollama_service()
        
        # Initialize ChromaDB with Ollama embedding function
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Use custom Ollama embedding function
        self.embedding_function = OllamaEmbeddingFunction(model_name=model_name, concurrency_limit=concurrency_limit)
        
        # Get or create collection
        try:
            # Try to get existing collection
            existing_collections = self.chroma_client.list_collections()
            
            # Look for Ollama-specific collection first
            ollama_collection_name = f"{collection_name}_ollama"
            collection_found = False
            
            for col in existing_collections:
                if col.name == ollama_collection_name:
                    # Check if this collection is compatible with our embedding dimensions
                    try:
                        # Get the collection with our Ollama embedding function
                        self.collection = self.chroma_client.get_collection(
                            name=ollama_collection_name,
                            embedding_function=self.embedding_function
                        )
                        
                        # Test compatibility by trying to add a dummy embedding
                        test_embedding = self.embedding_function(["test"])[0]
                        test_dim = len(test_embedding)
                        logger.info(f"Ollama embedding dimension: {test_dim}")
                        
                        logger.info(f"Using existing Ollama collection '{ollama_collection_name}' with {col.count()} documents")
                        collection_found = True
                        break
                        
                    except Exception as e:
                        logger.warning(f"Existing collection '{ollama_collection_name}' is incompatible: {e}")
                        
                        # Ask for confirmation before deleting collection
                        if os.environ.get('OLLAMA_AUTO_DELETE_COLLECTIONS', '').lower() == 'true':
                            logger.info(f"Auto-deleting incompatible collection (OLLAMA_AUTO_DELETE_COLLECTIONS=true)")
                            try:
                                self.chroma_client.delete_collection(ollama_collection_name)
                            except Exception as del_err:
                                logger.debug(f"Failed to delete collection: {del_err}")
                        else:
                            logger.error(f"Cannot use incompatible collection '{ollama_collection_name}'")
                            logger.info("To auto-delete incompatible collections, set OLLAMA_AUTO_DELETE_COLLECTIONS=true")
                            raise ValueError(f"Incompatible collection exists. Please delete manually or set OLLAMA_AUTO_DELETE_COLLECTIONS=true")
                        break
            
            if not collection_found:
                # Create new Ollama-specific collection
                self.collection = self.chroma_client.create_collection(
                    name=ollama_collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new Ollama collection '{ollama_collection_name}'")
                
                # Try to migrate data from existing collection
                self._migrate_from_existing_collection(existing_collections)
                
        except Exception as e:
            logger.error(f"Error setting up collection: {e}")
            # Create fallback collection
            self.collection = self.chroma_client.create_collection(
                name=f"{collection_name}_ollama_fallback",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
    
    def _detect_device(self) -> str:
        """Detect available GPU device"""
        # Check for NVIDIA GPU with CUDA
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                # Check CUDA availability in output
                if 'CUDA Version' in result.stdout:
                    cuda_version = result.stdout.split('CUDA Version:')[1].split()[0]
                    logger.info(f"NVIDIA GPU detected with CUDA {cuda_version}")
                    return f"nvidia_gpu_cuda_{cuda_version}"
        except FileNotFoundError:
            logger.debug("nvidia-smi not found")
        except (subprocess.SubprocessError, IndexError, ValueError) as e:
            logger.debug(f"Error detecting NVIDIA GPU: {e}")
        
        # Check for AMD GPU
        if os.path.exists("/dev/kfd"):
            return "amd_gpu"
        
        # Check for Intel GPU
        if os.path.exists("/dev/dri/renderD128"):
            return "intel_gpu"
        
        return "cpu"
    
    def _check_ollama_service(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get("http://localhost:11434/api/version")
            if response.status_code == 200:
                version = response.json()
                logger.info(f"Ollama service running, version: {version}")
                return True
        except requests.exceptions.RequestException as e:
            logger.debug(f"Ollama service check failed: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error checking Ollama service: {e}")
        return False
    
    def _start_ollama_service(self):
        """Attempt to start Ollama service"""
        try:
            # Check if we already have a process running
            if self.ollama_process and self.ollama_process.poll() is None:
                logger.info("Ollama process already running")
                return
            
            logger.info("Starting Ollama service...")
            self.ollama_process = subprocess.Popen(
                ['ollama', 'serve'], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Create new process group for clean shutdown
            )
            time.sleep(OLLAMA_SERVICE_START_DELAY)  # Give it time to start
            
            if self._check_ollama_service():
                logger.info("Ollama service started successfully")
            else:
                logger.warning("Failed to start Ollama service")
                if self.ollama_process:
                    self.ollama_process.terminate()
                    self.ollama_process = None
        except FileNotFoundError:
            logger.error("Ollama executable not found. Please install Ollama.")
        except Exception as e:
            logger.error(f"Error starting Ollama service: {e}")
            if self.ollama_process:
                try:
                    self.ollama_process.terminate()
                except Exception:
                    pass
                self.ollama_process = None
    
    def _migrate_from_existing_collection(self, existing_collections):
        """Migrate data from existing collection to Ollama collection"""
        try:
            # Look for existing collection with data
            for col in existing_collections:
                if col.count() > 0 and 'ollama' not in col.name:
                    logger.info(f"Migrating {col.count()} documents from '{col.name}'...")
                    
                    # Get all data from existing collection
                    data = col.get(include=['documents', 'metadatas', 'ids'])
                    
                    if data['documents']:
                        # Add to new collection in batches
                        batch_size = 50
                        for i in range(0, len(data['documents']), batch_size):
                            batch_docs = data['documents'][i:i+batch_size]
                            batch_meta = data['metadatas'][i:i+batch_size] if data['metadatas'] else [{}] * len(batch_docs)
                            batch_ids = data['ids'][i:i+batch_size]
                            
                            self.collection.add(
                                documents=batch_docs,
                                metadatas=batch_meta,
                                ids=batch_ids
                            )
                            logger.info(f"Migrated batch {i//batch_size + 1}/{(len(data['documents'])-1)//batch_size + 1}")
                        
                        logger.info(f"Migration completed: {len(data['documents'])} documents")
                        break
        except Exception as e:
            logger.error(f"Error during migration: {e}")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using GPU-accelerated embeddings"""
        with ErrorHandler.log_duration(f"Ollama search on {self.device}"):
            def search_operation():
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    include=['documents', 'metadatas', 'distances']
                )
                return CollectionUtils.format_search_results(results)
            
            return ErrorHandler.handle_with_fallback(
                search_operation,
                [],
                "Ollama search error"
            )
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None, ids: List[str] = None):
        """Add documents to the collection with GPU-accelerated embedding generation"""
        try:
            if not ids:
                ids = [f"doc_{i}" for i in range(len(documents))]
            if not metadatas:
                metadatas = [{}] * len(documents)
            
            # Add in batches for better performance
            batch_size = 50
            total_batches = (len(documents) - 1) // batch_size + 1
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_meta = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                start = time.time()
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_meta,
                    ids=batch_ids
                )
                batch_time = time.time() - start
                
                current_batch = i // batch_size + 1
                logger.info(f"Added batch {current_batch}/{total_batches} in {batch_time:.2f}s (GPU: {self.device})")
                
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        gpu_info = {}
        if 'nvidia' in self.device:
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', 
                                       '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    parts = result.stdout.strip().split(', ')
                    gpu_info = {
                        'gpu_name': parts[0],
                        'memory_used_mb': parts[1],
                        'memory_total_mb': parts[2],
                        'utilization': f"{parts[3]}%"
                    }
            except (FileNotFoundError, subprocess.SubprocessError, IndexError, ValueError) as e:
                logger.debug(f"Error getting GPU info: {e}")
            except Exception as e:
                logger.debug(f"Unexpected error getting GPU info: {e}")
        
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection.name,
            "model": self.model_name,
            "device": self.device,
            "platform": f"{platform.system()} {platform.machine()}",
            "gpu_info": gpu_info,
            "ollama_enabled": True
        }
    
    def cleanup(self):
        """Clean up resources, especially subprocess"""
        if self.ollama_process:
            try:
                logger.info("Cleaning up Ollama process...")
                self.ollama_process.terminate()
                # Wait for graceful termination, then force kill if necessary
                try:
                    self.ollama_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Ollama process did not terminate gracefully, forcing kill...")
                    self.ollama_process.kill()
                    self.ollama_process.wait()
                logger.info("Ollama process cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            finally:
                self.ollama_process = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup on object deletion"""
        try:
            self.cleanup()
        except Exception:
            # Suppress all exceptions in destructor
            pass

def initialize_ollama_database():
    """Initialize the Ollama database from scraped_content.json if empty"""
    embeddings = OllamaCudaEmbeddings()
    
    if embeddings.collection.count() == 0:
        logger.info("Empty Ollama database detected, loading from scraped_content.json...")
        
        data = DatabaseLoader.load_scraped_content()
        if data:
            documents, metadatas, ids = DatabaseLoader.prepare_documents_for_embedding(data)
            embeddings.add_documents(documents, metadatas, ids)
            logger.info(f"Initialized Ollama database with {len(documents)} documents using GPU acceleration")
    
    return embeddings

if __name__ == "__main__":
    # Test the Ollama GPU-accelerated embeddings
    logger.info("Testing Ollama CUDA embeddings...")
    
    embeddings = initialize_ollama_database()
    stats = embeddings.get_collection_stats()
    print(f"\nDatabase stats: {json.dumps(stats, indent=2)}")
    
    # Test search with GPU acceleration
    test_queries = [
        "payment webhook signature verification",
        "API authentication methods",
        "currency conversion rates"
    ]
    
    for test_query in test_queries:
        print(f"\nSearching for: '{test_query}'")
        start = time.time()
        results = embeddings.search(test_query, top_k=3)
        total_time = time.time() - start
        
        print(f"Total search time: {total_time:.3f}s")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.3f}")
            print(f"   URL: {result['metadata'].get('url', 'N/A')}")
            print(f"   Preview: {result['content'][:200]}...")