"""
ChromaDB vector database backend
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from uuid import uuid4
from pathlib import Path

from mbed.databases.base import VectorDatabase, DatabaseFactory
from mbed.core.config import MBEDSettings

logger = logging.getLogger(__name__)


class ChromaDBBackend(VectorDatabase):
    """ChromaDB vector database backend"""

    def __init__(self, config: MBEDSettings):
        self.config = config
        self.client = None
        self.collection = None
        self.collection_name = "mbed_documents"

    def initialize(self) -> None:
        """Initialize ChromaDB connection"""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )

        # Create client
        db_path = self.config.db_path / "chromadb"
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents with embeddings to ChromaDB"""
        if self.collection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid4()) for _ in range(len(texts))]

        # Prepare metadata
        if metadata is None:
            metadata = [{} for _ in range(len(texts))]

        # Add source field to metadata
        for i, meta in enumerate(metadata):
            if "source" not in meta:
                meta["source"] = "unknown"

        # Convert embeddings to list format for ChromaDB
        embeddings_list = embeddings.tolist()

        # Add to collection in batches
        batch_size = self.config.batch_size
        for i in range(0, len(texts), batch_size):
            end_idx = min(i + batch_size, len(texts))

            self.collection.add(
                ids=ids[i:end_idx],
                documents=texts[i:end_idx],
                embeddings=embeddings_list[i:end_idx],
                metadatas=metadata[i:end_idx]
            )

            logger.debug(f"Added batch {i//batch_size + 1}: {end_idx - i} documents")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar documents in ChromaDB"""
        if self.collection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        # Prepare query
        query_params = {
            "query_embeddings": [query_embedding.tolist()],
            "n_results": k
        }

        # Add filter if provided
        if filter:
            query_params["where"] = filter

        # Perform search
        results = self.collection.query(**query_params)

        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            distances = results["distances"][0]
            metadatas = results["metadatas"][0]

            for doc, dist, meta in zip(docs, distances, metadatas):
                formatted_results.append((doc, dist, meta))

        return formatted_results

    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        if self.collection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} documents")

    def get_count(self) -> int:
        """Get the total number of documents"""
        if self.collection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.collection.count()

    def clear(self) -> None:
        """Clear all documents from the collection"""
        if self.collection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        # Delete and recreate collection
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Cleared collection: {self.collection_name}")

    def update_collection_name(self, name: str) -> None:
        """Update the collection name to use"""
        self.collection_name = name
        if self.client:
            try:
                self.collection = self.client.get_collection(name)
                logger.info(f"Switched to collection: {name}")
            except:
                self.collection = self.client.create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {name}")


# Register with factory
DatabaseFactory.register("chromadb", ChromaDBBackend)