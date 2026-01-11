"""
Qdrant backend for cloud-native vector operations
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from uuid import uuid4
from urllib.parse import urlparse

from mbed.databases.base import VectorDatabase, DatabaseFactory
from mbed.core.config import MBEDSettings

logger = logging.getLogger(__name__)


class QdrantBackend(VectorDatabase):
    """Qdrant vector database backend"""

    def __init__(self, config: MBEDSettings):
        self.config = config
        self.client = None
        self.collection_name = "mbed_documents"
        self.vector_dimension = 768  # Default for nomic-embed-text
        self._initialized = False

        # Parse connection configuration
        if config.db_connection:
            self._parse_connection_string(config.db_connection)
        else:
            # Default to local Qdrant
            self.host = "localhost"
            self.port = 6333
            self.api_key = None
            self.url = None
            self.prefer_grpc = False

    def _parse_connection_string(self, connection_string: str):
        """Parse Qdrant connection string"""
        if connection_string.startswith("qdrant://"):
            parsed = urlparse(connection_string)
            self.host = parsed.hostname or "localhost"
            self.port = parsed.port or 6333
            self.api_key = parsed.password  # API key can be in password field
            self.url = None
            self.prefer_grpc = False
        elif connection_string.startswith("https://") or connection_string.startswith("http://"):
            # Cloud/remote URL
            self.url = connection_string
            self.host = None
            self.port = None
            self.api_key = None  # Should be set separately
            self.prefer_grpc = False
        else:
            raise ValueError(f"Invalid Qdrant connection string: {connection_string}")

    def initialize(self) -> None:
        """Initialize Qdrant connection"""
        if self._initialized:
            return

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            from qdrant_client.http.exceptions import UnexpectedResponse
            self.qdrant_client = QdrantClient
            self.Distance = Distance
            self.VectorParams = VectorParams
            self.PointStruct = PointStruct
            self.UnexpectedResponse = UnexpectedResponse
        except ImportError:
            raise ImportError(
                "Qdrant client not installed. Install with: pip install qdrant-client"
            )

        # Create client
        try:
            if self.url:
                self.client = self.qdrant_client(
                    url=self.url,
                    api_key=self.api_key,
                    prefer_grpc=self.prefer_grpc
                )
            else:
                self.client = self.qdrant_client(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key,
                    prefer_grpc=self.prefer_grpc
                )

            logger.info(f"Connected to Qdrant at {self.url or f'{self.host}:{self.port}'}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

        # Setup collection
        self._setup_collection()
        self._initialized = True

    def _setup_collection(self):
        """Setup Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)

            if not collection_exists:
                # Create collection with cosine distance
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=self.VectorParams(
                        size=self.vector_dimension,
                        distance=self.Distance.COSINE
                    ),
                    # Enable optimizations
                    optimizers_config={
                        "default_segment_number": 2,
                        "max_optimization_threads": 1,
                    },
                    # Enable indexing
                    hnsw_config={
                        "m": 16,
                        "ef_construct": 200,
                        "full_scan_threshold": 10000,
                    }
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to setup Qdrant collection: {e}")
            raise

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents with embeddings to Qdrant"""
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

        # Prepare points for Qdrant
        points = []
        for i, (doc_id, text, embedding, meta) in enumerate(zip(ids, texts, embeddings, metadata)):
            # Add document text to metadata
            full_meta = dict(meta)
            full_meta["text"] = text

            point = self.PointStruct(
                id=doc_id,
                vector=embedding.tolist(),
                payload=full_meta
            )
            points.append(point)

        # Upload points in batches
        batch_size = self.config.batch_size
        try:
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]

                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points,
                    wait=True
                )

                logger.debug(f"Added batch {i//batch_size + 1}: {len(batch_points)} documents")

            logger.info(f"Successfully added {len(texts)} documents to Qdrant")

        except Exception as e:
            logger.error(f"Failed to add documents to Qdrant: {e}")
            raise

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar documents in Qdrant"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            # Prepare search query
            search_params = {
                "collection_name": self.collection_name,
                "query_vector": query_embedding.tolist(),
                "limit": k,
                "with_payload": True,
                "with_vectors": False  # Don't return vectors to save bandwidth
            }

            # Add filter if provided
            if filter:
                # Convert filter to Qdrant filter format
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                conditions = []
                for key, value in filter.items():
                    if key != "text":  # Skip text field from filtering
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value))
                        )

                if conditions:
                    search_params["query_filter"] = Filter(must=conditions)

            # Perform search
            search_results = self.client.search(**search_params)

            # Format results
            formatted_results = []
            for hit in search_results:
                # Extract text from payload
                text = hit.payload.get("text", "")

                # Extract metadata (excluding text)
                metadata = {k: v for k, v in hit.payload.items() if k != "text"}

                # Qdrant returns similarity score, convert to distance for consistency
                distance = 1.0 - hit.score

                formatted_results.append((text, distance, metadata))

            return formatted_results

        except Exception as e:
            logger.error(f"Search failed in Qdrant: {e}")
            raise

    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            # Delete points by IDs
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids,
                wait=True
            )
            logger.info(f"Deleted {len(ids)} documents from Qdrant")

        except Exception as e:
            logger.error(f"Failed to delete documents from Qdrant: {e}")
            raise

    def get_count(self) -> int:
        """Get the total number of documents"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count

        except Exception as e:
            logger.error(f"Failed to get count from Qdrant: {e}")
            raise

    def clear(self) -> None:
        """Clear all documents from the collection"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            # Delete the collection and recreate it
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted Qdrant collection: {self.collection_name}")

            # Recreate collection
            self._setup_collection()
            logger.info(f"Recreated Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to clear Qdrant collection: {e}")
            raise

    def update_collection_name(self, name: str) -> None:
        """Update the collection name to use"""
        self.collection_name = name
        if self.client:
            self._setup_collection()

    def update_vector_dimension(self, dimension: int) -> None:
        """Update vector dimension (requires collection recreation)"""
        if dimension == self.vector_dimension:
            return

        logger.warning(f"Changing vector dimension from {self.vector_dimension} to {dimension}")
        logger.warning("This will recreate the collection and lose all data!")

        self.vector_dimension = dimension

        if self._initialized:
            # Clear and recreate collection with new dimension
            self.clear()

    def create_index(self, field_name: str, field_type: str = "keyword") -> None:
        """Create index on payload field for faster filtering"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            from qdrant_client.models import PayloadSchemaType

            schema_type_map = {
                "keyword": PayloadSchemaType.KEYWORD,
                "integer": PayloadSchemaType.INTEGER,
                "float": PayloadSchemaType.FLOAT,
                "bool": PayloadSchemaType.BOOL,
            }

            if field_type not in schema_type_map:
                raise ValueError(f"Unsupported field type: {field_type}")

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=schema_type_map[field_type]
            )

            logger.info(f"Created index on field '{field_name}' of type '{field_type}'")

        except Exception as e:
            logger.error(f"Failed to create index on field '{field_name}': {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """Get detailed collection information"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": collection_info.config.name,
                "status": collection_info.status,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance,
                }
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    def optimize_collection(self) -> None:
        """Trigger collection optimization"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            # Trigger optimization for better search performance
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizer_config={
                    "default_segment_number": 2,
                    "max_optimization_threads": 1,
                    "memmap_threshold": 20000,
                    "indexing_threshold": 20000,
                }
            )
            logger.info(f"Triggered optimization for collection: {self.collection_name}")

        except Exception as e:
            logger.warning(f"Failed to optimize collection: {e}")


# Register with factory
DatabaseFactory.register("qdrant", QdrantBackend)