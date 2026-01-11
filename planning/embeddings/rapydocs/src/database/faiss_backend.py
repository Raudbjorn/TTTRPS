#!/usr/bin/env python3
"""
FAISS backend for high-performance vector similarity search.
Supports both CPU and GPU acceleration with multiple index types.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

logger = logging.getLogger(__name__)


class FAISSConfig:
    """Configuration for FAISS backend"""
    
    def __init__(self,
                 index_type: str = "Flat",
                 metric: str = "cosine",
                 dimension: int = 384,
                 use_gpu: bool = False,
                 gpu_device: int = 0,
                 normalize_embeddings: bool = True,
                 nlist: int = 100,  # For IVF indexes
                 nprobe: int = 10,  # For IVF search
                 m: int = 32,  # For HNSW
                 ef_construction: int = 200,  # For HNSW
                 ef_search: int = 50):  # For HNSW search
        
        self.index_type = index_type
        self.metric = metric
        self.dimension = dimension
        self.use_gpu = use_gpu
        self.gpu_device = gpu_device
        self.normalize_embeddings = normalize_embeddings
        self.nlist = nlist
        self.nprobe = nprobe
        self.m = m
        self.ef_construction = ef_construction
        self.ef_search = ef_search


class FAISSBackend:
    """FAISS vector database backend"""
    
    def __init__(self, config: Optional[FAISSConfig] = None, persist_dir: str = "./faiss_index"):
        """Initialize FAISS backend"""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not installed. Install with: pip install faiss-cpu or faiss-gpu")
        
        self.config = config or FAISSConfig()
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.index = None
        self.documents = []
        self.metadata = []
        self.id_to_idx = {}
        
        # Initialize index
        self._create_index()
    
    def _create_index(self):
        """Create FAISS index based on configuration"""
        dimension = self.config.dimension
        
        # Choose metric
        if self.config.metric == "cosine":
            metric = faiss.METRIC_INNER_PRODUCT
            self.config.normalize_embeddings = True
        elif self.config.metric == "euclidean":
            metric = faiss.METRIC_L2
        else:
            raise ValueError(f"Unsupported metric: {self.config.metric}")
        
        # Create base index
        if self.config.index_type == "Flat":
            self.index = faiss.IndexFlatIP(dimension) if metric == faiss.METRIC_INNER_PRODUCT else faiss.IndexFlatL2(dimension)
            logger.info(f"Created Flat index with {self.config.metric} metric")
            
        elif self.config.index_type == "IVF":
            quantizer = faiss.IndexFlatIP(dimension) if metric == faiss.METRIC_INNER_PRODUCT else faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, self.config.nlist, metric)
            logger.info(f"Created IVF index with {self.config.nlist} clusters")
            
        elif self.config.index_type == "HNSW":
            self.index = faiss.IndexHNSWFlat(dimension, self.config.m, metric)
            self.index.hnsw.efConstruction = self.config.ef_construction
            self.index.hnsw.efSearch = self.config.ef_search
            logger.info(f"Created HNSW index with M={self.config.m}")
            
        elif self.config.index_type == "LSH":
            nbits = dimension * 2  # Typical choice
            self.index = faiss.IndexLSH(dimension, nbits)
            logger.info(f"Created LSH index with {nbits} bits")
            
        else:
            raise ValueError(f"Unsupported index type: {self.config.index_type}")
        
        # Move to GPU if requested and available
        if self.config.use_gpu and faiss.get_num_gpus() > 0:
            try:
                gpu_resource = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(gpu_resource, self.config.gpu_device, self.index)
                logger.info(f"Moved index to GPU {self.config.gpu_device}")
            except Exception as e:
                logger.warning(f"Failed to use GPU: {e}. Falling back to CPU.")
    
    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """L2 normalize embeddings for cosine similarity"""
        if self.config.normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Avoid division by zero
            norms = np.where(norms == 0, 1, norms)
            return embeddings / norms
        return embeddings
    
    def add_documents(self,
                     documents: List[str],
                     embeddings: Union[List[List[float]], np.ndarray],
                     metadata: Optional[List[Dict[str, Any]]] = None,
                     ids: Optional[List[str]] = None) -> bool:
        """Add documents with embeddings to the index"""
        
        # Convert to numpy array
        if isinstance(embeddings, list):
            embeddings = np.array(embeddings, dtype=np.float32)
        else:
            embeddings = embeddings.astype(np.float32)
        
        # Validate dimensions
        if embeddings.shape[1] != self.config.dimension:
            raise ValueError(f"Embedding dimension {embeddings.shape[1]} doesn't match index dimension {self.config.dimension}")
        
        # Normalize if needed
        embeddings = self._normalize_embeddings(embeddings)
        
        # Generate IDs if not provided
        if ids is None:
            base_idx = len(self.documents)
            ids = [f"doc_{base_idx + i}" for i in range(len(documents))]
        
        # Train index if needed (for IVF)
        if hasattr(self.index, 'is_trained') and not self.index.is_trained:
            logger.info(f"Training index with {len(embeddings)} vectors...")
            self.index.train(embeddings)
        
        # Add to index
        start_idx = len(self.documents)
        self.index.add(embeddings)
        
        # Store documents and metadata
        for i, (doc, doc_id) in enumerate(zip(documents, ids)):
            idx = start_idx + i
            self.documents.append(doc)
            self.metadata.append(metadata[i] if metadata else {})
            self.id_to_idx[doc_id] = idx
        
        logger.info(f"Added {len(documents)} documents to index. Total: {len(self.documents)}")
        return True
    
    def search(self,
              query_embedding: Union[List[float], np.ndarray],
              k: int = 5,
              filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        
        if len(self.documents) == 0:
            return []
        
        # Convert to numpy array
        if isinstance(query_embedding, list):
            query_embedding = np.array([query_embedding], dtype=np.float32)
        else:
            query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Normalize if needed
        query_embedding = self._normalize_embeddings(query_embedding)
        
        # Set search parameters for IVF
        if hasattr(self.index, 'nprobe'):
            self.index.nprobe = self.config.nprobe
        
        # Search
        k = min(k, len(self.documents))
        distances, indices = self.index.search(query_embedding, k)
        
        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            
            # Apply metadata filter if provided
            if filter_metadata:
                doc_metadata = self.metadata[idx]
                if not all(doc_metadata.get(k) == v for k, v in filter_metadata.items()):
                    continue
            
            # Convert distance to similarity score
            if self.config.metric == "cosine":
                score = float(dist)  # Already similarity for normalized vectors
            else:
                # For L2 distance, convert to similarity
                score = 1.0 / (1.0 + float(dist))
            
            results.append({
                "content": self.documents[idx],
                "metadata": self.metadata[idx],
                "score": score,
                "distance": float(dist),
                "index": int(idx)
            })
        
        return results
    
    def batch_search(self,
                    query_embeddings: Union[List[List[float]], np.ndarray],
                    k: int = 5) -> List[List[Dict[str, Any]]]:
        """Batch search for multiple queries"""
        
        if isinstance(query_embeddings, list):
            query_embeddings = np.array(query_embeddings, dtype=np.float32)
        else:
            query_embeddings = query_embeddings.astype(np.float32)
        
        # Normalize if needed
        query_embeddings = self._normalize_embeddings(query_embeddings)
        
        # Search
        k = min(k, len(self.documents))
        distances, indices = self.index.search(query_embeddings, k)
        
        # Build results for each query
        all_results = []
        for query_dists, query_indices in zip(distances, indices):
            results = []
            for dist, idx in zip(query_dists, query_indices):
                if idx < 0 or idx >= len(self.documents):
                    continue
                
                if self.config.metric == "cosine":
                    score = float(dist)
                else:
                    score = 1.0 / (1.0 + float(dist))
                
                results.append({
                    "content": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "score": score,
                    "distance": float(dist),
                    "index": int(idx)
                })
            all_results.append(results)
        
        return all_results
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        if doc_id not in self.id_to_idx:
            return None
        
        idx = self.id_to_idx[doc_id]
        return {
            "id": doc_id,
            "content": self.documents[idx],
            "metadata": self.metadata[idx]
        }
    
    def delete_by_id(self, doc_id: str) -> bool:
        """Delete document by ID (note: FAISS doesn't support efficient deletion)"""
        logger.warning("FAISS doesn't support efficient deletion. Consider rebuilding the index.")
        return False
    
    def save(self, name: str = "default"):
        """Save index and metadata to disk"""
        index_path = self.persist_dir / f"{name}_index.faiss"
        meta_path = self.persist_dir / f"{name}_metadata.json"

        # Save FAISS index
        if self.config.use_gpu:
            # Transfer to CPU before saving
            cpu_index = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(cpu_index, str(index_path))
        else:
            faiss.write_index(self.index, str(index_path))

        # Save metadata as JSON for security and portability
        metadata_dict = {
            'documents': self.documents,
            'metadata': self.metadata,
            'id_to_idx': self.id_to_idx,
            'config': self.config.__dict__
        }

        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved index to {index_path} and metadata to {meta_path}")
    
    def load(self, name: str = "default"):
        """Load index and metadata from disk"""
        index_path = self.persist_dir / f"{name}_index.faiss"
        meta_path_json = self.persist_dir / f"{name}_metadata.json"
        meta_path_pkl = self.persist_dir / f"{name}_metadata.pkl"  # Legacy fallback

        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

        # Try JSON first, then fallback to pickle for backward compatibility
        if meta_path_json.exists():
            with open(meta_path_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif meta_path_pkl.exists():
            logger.warning("Loading legacy pickle metadata. Consider saving to upgrade to JSON format.")
            import pickle
            with open(meta_path_pkl, 'rb') as f:
                data = pickle.load(f)
        else:
            raise FileNotFoundError(f"Metadata file not found for '{name}'")

        # Load FAISS index
        self.index = faiss.read_index(str(index_path))

        # Move to GPU if configured
        if self.config.use_gpu and faiss.get_num_gpus() > 0:
            try:
                gpu_resource = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(gpu_resource, self.config.gpu_device, self.index)
            except Exception as e:
                logger.warning(f"Failed to use GPU: {e}")

        # Load metadata
        self.documents = data['documents']
        self.metadata = data['metadata']
        self.id_to_idx = data['id_to_idx']

        # Update config from saved data
        for key, value in data.get('config', {}).items():
            setattr(self.config, key, value)

        logger.info(f"Loaded index with {len(self.documents)} documents")
    
    def clear(self):
        """Clear the index and all data"""
        self._create_index()
        self.documents = []
        self.metadata = []
        self.id_to_idx = {}
        logger.info("Cleared index")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        stats = {
            "total_documents": len(self.documents),
            "index_type": self.config.index_type,
            "dimension": self.config.dimension,
            "metric": self.config.metric,
            "use_gpu": self.config.use_gpu
        }
        
        if hasattr(self.index, 'ntotal'):
            stats["vectors_in_index"] = self.index.ntotal
        
        if self.config.index_type == "IVF":
            stats["nlist"] = self.config.nlist
            stats["is_trained"] = self.index.is_trained if hasattr(self.index, 'is_trained') else True
        
        return stats


class HybridFAISSBackend(FAISSBackend):
    """Extended FAISS backend with BM25 support for hybrid search"""
    
    def __init__(self, config: Optional[FAISSConfig] = None, persist_dir: str = "./faiss_index"):
        """Initialize hybrid backend"""
        super().__init__(config, persist_dir)
        
        # BM25 components
        self.bm25_index = None
        self.tokenized_docs = []
        
        # Try to import rank_bm25
        try:
            from rank_bm25 import BM25Okapi
            self.BM25Okapi = BM25Okapi
            self.bm25_available = True
        except ImportError:
            logger.warning("rank_bm25 not installed. BM25 search will not be available.")
            self.bm25_available = False
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        import re
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def add_documents(self,
                     documents: List[str],
                     embeddings: Union[List[List[float]], np.ndarray],
                     metadata: Optional[List[Dict[str, Any]]] = None,
                     ids: Optional[List[str]] = None) -> bool:
        """Add documents with both dense and sparse indexing"""
        
        # Add to dense index
        result = super().add_documents(documents, embeddings, metadata, ids)
        
        # Add to BM25 index if available
        if self.bm25_available:
            # Tokenize new documents
            new_tokenized = [self._tokenize(doc) for doc in documents]
            self.tokenized_docs.extend(new_tokenized)

            # Only rebuild BM25 index if we don't have one, or if it's a significant update
            if (self.bm25_index is None or
                len(new_tokenized) > len(self.tokenized_docs) * 0.1):  # Rebuild if >10% new docs
                self.bm25_index = self.BM25Okapi(self.tokenized_docs)
                logger.info(f"Rebuilt BM25 index with {len(self.tokenized_docs)} documents")
            else:
                logger.info(f"BM25 index updated incrementally ({len(new_tokenized)} new docs)")
        
        return result
    
    def hybrid_search(self,
                     query_text: str,
                     query_embedding: Union[List[float], np.ndarray],
                     k: int = 5,
                     alpha: float = 0.5) -> List[Dict[str, Any]]:
        """Perform hybrid search combining dense and sparse retrieval"""
        
        # Dense search
        dense_results = self.search(query_embedding, k * 2)  # Get more candidates
        
        if not self.bm25_available or not self.bm25_index:
            return dense_results[:k]
        
        # BM25 search
        query_tokens = self._tokenize(query_text)
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top-k from BM25
        top_bm25_indices = np.argsort(bm25_scores)[-k*2:][::-1]
        
        # Combine scores
        combined_scores = {}
        
        # Add dense scores
        for result in dense_results:
            idx = result['index']
            combined_scores[idx] = alpha * result['score']
        
        # Add BM25 scores (normalized)
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        for idx in top_bm25_indices:
            if idx < len(self.documents):
                normalized_bm25 = bm25_scores[idx] / max_bm25
                if idx in combined_scores:
                    combined_scores[idx] += (1 - alpha) * normalized_bm25
                else:
                    combined_scores[idx] = (1 - alpha) * normalized_bm25
        
        # Sort by combined score
        sorted_indices = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        
        # Build results
        results = []
        for idx in sorted_indices[:k]:
            results.append({
                "content": self.documents[idx],
                "metadata": self.metadata[idx],
                "score": combined_scores[idx],
                "index": int(idx)
            })
        
        return results


def create_faiss_backend(backend_type: str = "basic",
                        dimension: int = 384,
                        index_type: str = "Flat",
                        use_gpu: bool = False,
                        persist_dir: str = "./faiss_index") -> Union[FAISSBackend, HybridFAISSBackend]:
    """Factory function to create FAISS backend"""
    
    config = FAISSConfig(
        dimension=dimension,
        index_type=index_type,
        use_gpu=use_gpu
    )
    
    if backend_type == "hybrid":
        return HybridFAISSBackend(config, persist_dir)
    else:
        return FAISSBackend(config, persist_dir)