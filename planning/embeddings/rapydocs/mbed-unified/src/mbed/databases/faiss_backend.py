"""
FAISS backend for high-performance vector similarity search
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from uuid import uuid4
import threading

from mbed.databases.base import VectorDatabase, DatabaseFactory
from mbed.core.config import MBEDSettings

logger = logging.getLogger(__name__)


class FAISSBackend(VectorDatabase):
    """FAISS vector database backend with GPU support"""

    def __init__(self, config: MBEDSettings):
        self.config = config
        self.index = None
        self.documents = []
        self.metadata = []
        self.id_to_idx = {}
        self.idx_to_id = {}
        self.vector_dimension = 768  # Default for nomic-embed-text
        self._initialized = False
        self._lock = threading.Lock()

        # FAISS configuration
        self.index_type = getattr(config, 'faiss_index_type', 'Flat')
        self.use_gpu = config.use_gpu and self._gpu_available()
        self.gpu_device = getattr(config, 'faiss_gpu_device', 0)
        self.metric = getattr(config, 'faiss_metric', 'cosine')

        # Index parameters
        self.nlist = getattr(config, 'faiss_nlist', 100)  # For IVF indexes
        self.nprobe = getattr(config, 'faiss_nprobe', 10)  # For IVF search
        self.m = getattr(config, 'faiss_m', 32)  # For HNSW
        self.ef_construction = getattr(config, 'faiss_ef_construction', 200)  # For HNSW
        self.ef_search = getattr(config, 'faiss_ef_search', 50)  # For HNSW search

        # Storage path
        self.persist_dir = Path(config.db_path) / "faiss"
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Files for persistence
        self.index_file = self.persist_dir / f"index_{self.index_type.lower()}.faiss"
        self.metadata_file = self.persist_dir / "metadata.json"
        self.config_file = self.persist_dir / "config.json"

    def _gpu_available(self) -> bool:
        """Check if FAISS GPU is available"""
        try:
            import faiss
            return faiss.get_num_gpus() > 0
        except (ImportError, AttributeError):
            return False

    def initialize(self) -> None:
        """Initialize FAISS index"""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            try:
                import faiss
                self.faiss = faiss
            except ImportError:
                raise ImportError(
                    "FAISS not installed. Install with: "
                    "pip install faiss-cpu or pip install faiss-gpu"
                )

            # Try to load existing index
            if self._load_existing_index():
                logger.info(f"Loaded existing FAISS index with {len(self.documents)} documents")
            else:
                # Create new index
                self._create_index()
                logger.info(f"Created new FAISS {self.index_type} index")

            self._initialized = True

    def _create_index(self):
        """Create FAISS index based on configuration"""
        # Choose metric
        if self.metric == "cosine":
            metric = self.faiss.METRIC_INNER_PRODUCT
            normalize_vectors = True
        elif self.metric == "euclidean":
            metric = self.faiss.METRIC_L2
            normalize_vectors = False
        else:
            raise ValueError(f"Unsupported metric: {self.metric}")

        # Create base index
        if self.index_type == "Flat":
            if metric == self.faiss.METRIC_INNER_PRODUCT:
                self.index = self.faiss.IndexFlatIP(self.vector_dimension)
            else:
                self.index = self.faiss.IndexFlatL2(self.vector_dimension)

        elif self.index_type == "IVF":
            quantizer = (self.faiss.IndexFlatIP(self.vector_dimension)
                        if metric == self.faiss.METRIC_INNER_PRODUCT
                        else self.faiss.IndexFlatL2(self.vector_dimension))
            self.index = self.faiss.IndexIVFFlat(quantizer, self.vector_dimension, self.nlist, metric)
            self.index.nprobe = self.nprobe

        elif self.index_type == "HNSW":
            self.index = self.faiss.IndexHNSWFlat(self.vector_dimension, self.m, metric)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search

        elif self.index_type == "LSH":
            nbits = self.vector_dimension * 2  # Typical choice
            self.index = self.faiss.IndexLSH(self.vector_dimension, nbits)

        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

        # Move to GPU if available and requested
        if self.use_gpu and self.faiss.get_num_gpus() > 0:
            try:
                gpu_resource = self.faiss.StandardGpuResources()
                self.index = self.faiss.index_cpu_to_gpu(gpu_resource, self.gpu_device, self.index)
                logger.info(f"Moved FAISS index to GPU {self.gpu_device}")
            except Exception as e:
                logger.warning(f"Failed to use GPU: {e}. Falling back to CPU.")
                self.use_gpu = False

        # Store configuration
        config_data = {
            'index_type': self.index_type,
            'vector_dimension': self.vector_dimension,
            'metric': self.metric,
            'use_gpu': self.use_gpu,
            'nlist': self.nlist,
            'nprobe': self.nprobe,
            'm': self.m,
            'ef_construction': self.ef_construction,
            'ef_search': self.ef_search
        }

        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

    def _load_existing_index(self) -> bool:
        """Load existing FAISS index from disk"""
        if not (self.index_file.exists() and self.metadata_file.exists() and self.config_file.exists()):
            return False

        try:
            # Load configuration
            with open(self.config_file, 'r') as f:
                saved_config = json.load(f)

            # Verify configuration compatibility
            if (saved_config['index_type'] != self.index_type or
                saved_config['vector_dimension'] != self.vector_dimension or
                saved_config['metric'] != self.metric):
                logger.warning("Index configuration mismatch. Creating new index.")
                return False

            # Load index
            if self.use_gpu and self.faiss.get_num_gpus() > 0:
                try:
                    # Load to CPU first, then move to GPU
                    cpu_index = self.faiss.read_index(str(self.index_file))
                    gpu_resource = self.faiss.StandardGpuResources()
                    self.index = self.faiss.index_cpu_to_gpu(gpu_resource, self.gpu_device, cpu_index)
                except Exception as e:
                    logger.warning(f"Failed to load index to GPU: {e}. Using CPU.")
                    self.index = self.faiss.read_index(str(self.index_file))
                    self.use_gpu = False
            else:
                self.index = self.faiss.read_index(str(self.index_file))

            # Load metadata
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                self.documents = data['documents']
                self.metadata = data['metadata']
                self.id_to_idx = data['id_to_idx']
                self.idx_to_id = {int(k): v for k, v in data['idx_to_id'].items()}  # JSON converts int keys to strings

            return True

        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}")
            return False

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """L2 normalize embeddings for cosine similarity"""
        if self.metric == "cosine":
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Avoid division by zero
            norms = np.where(norms == 0, 1, norms)
            return embeddings / norms
        return embeddings

    def _save_index(self):
        """Save index and metadata to disk"""
        try:
            # Ensure directory exists
            self.persist_dir.mkdir(parents=True, exist_ok=True)

            # Save index (move to CPU if on GPU)
            index_to_save = self.index
            if self.use_gpu:
                try:
                    index_to_save = self.faiss.index_gpu_to_cpu(self.index)
                except Exception as e:
                    logger.warning(f"Failed to convert GPU index to CPU for saving: {e}")
                    logger.warning("Saving GPU index as-is (may not be portable)")

            self.faiss.write_index(index_to_save, str(self.index_file))

            # Save metadata
            metadata_data = {
                'documents': self.documents,
                'metadata': self.metadata,
                'id_to_idx': self.id_to_idx,
                'idx_to_id': self.idx_to_id
            }

            with open(self.metadata_file, 'w') as f:
                json.dump(metadata_data, f, indent=2)

            logger.debug(f"Saved FAISS index with {len(self.documents)} documents")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents with embeddings to FAISS index"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid4()) for _ in range(len(texts))]

        # Prepare metadata
        if metadata is None:
            metadata = [{} for _ in range(len(texts))]

        # Add source field to metadata
        for meta in metadata:
            if "source" not in meta:
                meta["source"] = "unknown"

        # Validate dimensions
        if embeddings.shape[1] != self.vector_dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} "
                f"doesn't match index dimension {self.vector_dimension}"
            )

        # Convert to float32 and normalize if needed
        embeddings = embeddings.astype(np.float32)
        embeddings = self._normalize_embeddings(embeddings)

        with self._lock:
            # For IVF indexes, train if not already trained
            if hasattr(self.index, 'is_trained') and not self.index.is_trained:
                if len(embeddings) >= self.nlist:
                    logger.info("Training IVF index...")
                    self.index.train(embeddings)
                else:
                    logger.warning(
                        f"Need at least {self.nlist} vectors to train IVF index, "
                        f"got {len(embeddings)}. Delaying training."
                    )
                    # Store for later training
                    base_idx = len(self.documents)
                    for i, (doc, emb, meta, doc_id) in enumerate(zip(texts, embeddings, metadata, ids)):
                        idx = base_idx + i
                        self.documents.append(doc)
                        self.metadata.append(meta)
                        self.id_to_idx[doc_id] = idx
                        self.idx_to_id[idx] = doc_id
                    return

            # Add vectors to index
            base_idx = len(self.documents)
            self.index.add(embeddings)

            # Update metadata
            for i, (doc, meta, doc_id) in enumerate(zip(texts, metadata, ids)):
                idx = base_idx + i
                self.documents.append(doc)
                self.metadata.append(meta)
                self.id_to_idx[doc_id] = idx
                self.idx_to_id[idx] = doc_id

        # Always save after adding documents to prevent data loss
        # This ensures data persistence even if the process crashes
        self._save_index()

        logger.debug(f"Added {len(texts)} documents to FAISS index")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar documents in FAISS index"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        if len(self.documents) == 0:
            return []

        # Prepare query embedding
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        query_embedding = self._normalize_embeddings(query_embedding)

        # Pre-filter documents by metadata if filter is provided
        candidate_indices_set = None
        candidate_count = 0
        if filter:
            candidate_indices_set = set()
            for idx, meta in enumerate(self.metadata):
                if not meta.get('_deleted', False):  # Skip deleted documents
                    match = True
                    for key, value in filter.items():
                        if key not in meta or meta[key] != value:
                            match = False
                            break
                    if match:
                        candidate_indices_set.add(idx)

            candidate_count = len(candidate_indices_set)
            # If no matching documents, return empty results
            if candidate_count == 0:
                return []

        # Perform search
        with self._lock:
            # Set search parameters for HNSW
            if self.index_type == "HNSW":
                self.index.hnsw.efSearch = max(self.ef_search, k)

            # If we have a small set of candidate indices, search more broadly
            # and filter afterwards, otherwise search normally
            search_k = k if candidate_indices_set is None or candidate_count > k * 3 else min(len(self.documents), k * 10)
            distances, indices = self.index.search(query_embedding, search_k)

        # Format results
        results = []
        valid_indices = indices[0][indices[0] != -1]  # Filter out invalid indices
        valid_distances = distances[0][:len(valid_indices)]

        for idx, score in zip(valid_indices, valid_distances):
            if idx < len(self.documents) and not self.metadata[idx].get('_deleted', False):
                # If we have candidate indices, check if this index is in our pre-filtered set
                if candidate_indices_set is not None and idx not in candidate_indices_set:
                    continue

                doc = self.documents[idx]
                meta = self.metadata[idx]
                # Convert similarity score to distance for consistency
                # FAISS with METRIC_INNER_PRODUCT returns similarity (higher is better)
                # Convert to distance (lower is better) for consistency with other backends
                if self.metric == "cosine":
                    distance = 1.0 - float(score)  # Convert similarity to distance
                else:
                    distance = float(score)  # L2 distance is already a distance
                results.append((doc, distance, meta))

                # Stop when we have enough results
                if len(results) >= k:
                    break

        return results

    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        logger.warning("FAISS doesn't support direct deletion. Consider rebuilding index.")

        # For now, we can only mark as deleted in metadata
        with self._lock:
            deleted_count = 0
            for doc_id in ids:
                if doc_id in self.id_to_idx:
                    idx = self.id_to_idx[doc_id]
                    if idx < len(self.metadata):
                        self.metadata[idx]['_deleted'] = True
                        deleted_count += 1

            logger.info(f"Marked {deleted_count} documents as deleted")

    def get_count(self) -> int:
        """Get the total number of documents"""
        if not self._initialized:
            return 0

        # Count non-deleted documents
        count = 0
        for meta in self.metadata:
            if not meta.get('_deleted', False):
                count += 1

        return count

    def clear(self) -> None:
        """Clear all documents from the index"""
        if not self._initialized:
            return

        with self._lock:
            # Recreate index
            self._create_index()

            # Clear metadata
            self.documents = []
            self.metadata = []
            self.id_to_idx = {}
            self.idx_to_id = {}

        # Remove saved files
        for file_path in [self.index_file, self.metadata_file]:
            if file_path.exists():
                file_path.unlink()

        logger.info("Cleared FAISS index")

    def optimize_index(self, vectors_count: int):
        """Optimize index parameters based on dataset size"""
        if self.index_type == "IVF" and hasattr(self, 'nlist'):
            # Rule of thumb: nlist = sqrt(N), but at least 64 and at most 10000
            optimal_nlist = max(64, min(10000, int(np.sqrt(vectors_count))))

            if optimal_nlist != self.nlist:
                logger.info(f"Optimizing IVF index: changing nlist from {self.nlist} to {optimal_nlist}")
                self.nlist = optimal_nlist

                # Would require rebuilding the index
                logger.warning("Index optimization requires rebuilding. Consider recreating the index.")

    def update_vector_dimension(self, dimension: int):
        """Update vector dimension (requires index recreation)"""
        if dimension == self.vector_dimension:
            return

        logger.warning(f"Changing vector dimension from {self.vector_dimension} to {dimension}")
        logger.warning("This will clear the existing index!")

        self.vector_dimension = dimension
        self.clear()

    def __del__(self):
        """Cleanup and save index on deletion"""
        if hasattr(self, '_initialized') and self._initialized:
            try:
                self._save_index()
            except Exception as e:
                logger.error(f"Failed to save FAISS index on object deletion: {e}")


# Register with factory
DatabaseFactory.register("faiss", FAISSBackend)