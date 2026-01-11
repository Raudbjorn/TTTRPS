"""
PostgreSQL with pgvector backend for high-performance vector operations
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from uuid import uuid4
from urllib.parse import urlparse
import threading
import time

from mbed.databases.base import VectorDatabase, DatabaseFactory
from mbed.core.config import MBEDSettings

logger = logging.getLogger(__name__)


class PostgreSQLBackend(VectorDatabase):
    """PostgreSQL with pgvector backend"""

    def __init__(self, config: MBEDSettings):
        self.config = config
        self.connection_pool = None
        self.table_name = "embeddings"
        self.vector_dimension = 768  # Default for nomic-embed-text
        self._initialized = False
        self._lock = threading.Lock()

        # Parse connection string if provided
        if config.db_connection:
            self._parse_connection_string(config.db_connection)
        else:
            # Use defaults (password must be provided via environment or config)
            import os
            self.connection_params = {
                'host': 'localhost',
                'port': 5432,
                'database': 'embeddings',
                'user': 'postgres',
                'password': os.environ.get('POSTGRES_PASSWORD')
            }

    def _parse_connection_string(self, connection_string: str):
        """Parse PostgreSQL connection string"""
        parsed = urlparse(connection_string)

        import os
        self.connection_params = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path else 'embeddings',
            'user': parsed.username or 'postgres',
            'password': parsed.password or os.environ.get('POSTGRES_PASSWORD')
        }

    def initialize(self) -> None:
        """Initialize PostgreSQL connection and setup"""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            try:
                import psycopg2
                from psycopg2 import pool, sql
                from psycopg2.extras import RealDictCursor
            except ImportError:
                raise ImportError(
                    "PostgreSQL dependencies not installed. "
                    "Install with: pip install psycopg2-binary"
                )

            # Create connection pool
            try:
                self.connection_pool = pool.ThreadedConnectionPool(
                    self.config.postgres_pool_min,
                    self.config.postgres_pool_max,
                    **self.connection_params
                )
                logger.info(f"Created PostgreSQL connection pool to {self.connection_params['host']}")
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL connection pool: {e}")
                raise

            # Setup database schema
            self._setup_database()
            self._initialized = True

    def _get_connection(self):
        """Get connection from pool"""
        if not self.connection_pool:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.connection_pool.getconn()

    def _return_connection(self, conn):
        """Return connection to pool"""
        if self.connection_pool:
            self.connection_pool.putconn(conn)

    def _setup_database(self):
        """Setup database schema with pgvector extension"""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Create pgvector extension
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    conn.commit()
                    logger.info("pgvector extension enabled")
                except Exception as e:
                    logger.warning(f"Could not create pgvector extension: {e}")
                    conn.rollback()
                    raise RuntimeError(
                        "pgvector extension not available. "
                        "Please install pgvector: https://github.com/pgvector/pgvector"
                    )

                # Create embeddings table
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id UUID PRIMARY KEY,
                        document TEXT NOT NULL,
                        embedding vector({self.vector_dimension}),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Create indexes for better performance
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding_cosine
                    ON {self.table_name} USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)

                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_metadata_gin
                    ON {self.table_name} USING GIN (metadata);
                """)

                conn.commit()
                logger.info(f"Database schema initialized with table: {self.table_name}")

        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._return_connection(conn)

    def _optimize_index(self, total_vectors: int):
        """Optimize IVFFlat index based on dataset size"""
        # Rule of thumb: lists = rows / 1000, but at least 64 and at most 10000
        optimal_lists = max(64, min(10000, total_vectors // 1000))

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Drop existing index
                cur.execute(f"DROP INDEX IF EXISTS idx_{self.table_name}_embedding_cosine;")

                # Create optimized index
                cur.execute(f"""
                    CREATE INDEX idx_{self.table_name}_embedding_cosine
                    ON {self.table_name} USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {optimal_lists});
                """)

                conn.commit()
                logger.info(f"Optimized index with {optimal_lists} lists for {total_vectors} vectors")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.warning(f"Failed to optimize index: {e}")
        finally:
            if conn:
                self._return_connection(conn)

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents with embeddings to PostgreSQL"""
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

        conn = None
        try:
            conn = self._get_connection()

            # Insert documents in batches
            batch_size = self.config.batch_size
            for i in range(0, len(texts), batch_size):
                end_idx = min(i + batch_size, len(texts))
                batch_texts = texts[i:end_idx]
                batch_embeddings = embeddings[i:end_idx]
                batch_metadata = metadata[i:end_idx]
                batch_ids = ids[i:end_idx]

                # Prepare data for batch insert
                data_batch = []
                for j in range(len(batch_texts)):
                    embedding_list = batch_embeddings[j].tolist()
                    data_batch.append((
                        batch_ids[j],
                        batch_texts[j],
                        embedding_list,
                        json.dumps(batch_metadata[j])
                    ))

                with conn.cursor() as cur:
                    # Use execute_batch for efficient batch insert
                    from psycopg2.extras import execute_batch
                    execute_batch(
                        cur,
                        f"""
                        INSERT INTO {self.table_name} (id, document, embedding, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            document = EXCLUDED.document,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            created_at = CURRENT_TIMESTAMP
                        """,
                        data_batch
                    )

                conn.commit()
                logger.debug(f"Added batch {i//batch_size + 1}: {end_idx - i} documents")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to add documents: {e}")
            raise e
        finally:
            if conn:
                self._return_connection(conn)

        # Optimize index if we've added a significant number of documents
        if len(texts) > 1000:
            current_count = self.get_count()
            if current_count > 1000:
                self._optimize_index(current_count)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar documents using cosine similarity"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Build query with optional filter
                base_query = f"""
                    SELECT document, (1 - (embedding <=> %s)) AS similarity, metadata
                    FROM {self.table_name}
                """

                params = [query_embedding.tolist()]

                if filter:
                    # Add metadata filter
                    filter_conditions = []
                    for key, value in filter.items():
                        if isinstance(value, str):
                            filter_conditions.append(f"metadata ->> %s = %s")
                            params.extend([key, value])
                        elif isinstance(value, (int, float)):
                            filter_conditions.append(f"(metadata ->> %s)::numeric = %s")
                            params.extend([key, value])
                        elif isinstance(value, bool):
                            filter_conditions.append(f"(metadata ->> %s)::boolean = %s")
                            params.extend([key, value])

                    if filter_conditions:
                        base_query += " WHERE " + " AND ".join(filter_conditions)

                # Add ordering and limit
                query = base_query + " ORDER BY embedding <=> %s LIMIT %s"
                params.extend([query_embedding.tolist(), k])

                cur.execute(query, params)
                results = cur.fetchall()

                # Format results
                formatted_results = []
                for doc, similarity, meta in results:
                    # Convert similarity to distance (ChromaDB compatibility)
                    distance = 1.0 - similarity
                    metadata_dict = meta if isinstance(meta, dict) else {}
                    formatted_results.append((doc, distance, metadata_dict))

                return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise e
        finally:
            if conn:
                self._return_connection(conn)

    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Use ANY to delete multiple IDs efficiently
                cur.execute(
                    f"DELETE FROM {self.table_name} WHERE id = ANY(%s)",
                    (ids,)
                )
                deleted_count = cur.rowcount
                conn.commit()
                logger.info(f"Deleted {deleted_count} documents")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to delete documents: {e}")
            raise e
        finally:
            if conn:
                self._return_connection(conn)

    def get_count(self) -> int:
        """Get the total number of documents"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                count = cur.fetchone()[0]
                return count

        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            raise e
        finally:
            if conn:
                self._return_connection(conn)

    def clear(self) -> None:
        """Clear all documents from the table"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.table_name}")
                conn.commit()
                logger.info(f"Cleared all documents from table: {self.table_name}")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to clear table: {e}")
            raise e
        finally:
            if conn:
                self._return_connection(conn)

    def update_vector_dimension(self, dimension: int) -> None:
        """Update vector dimension (requires table recreation)"""
        if dimension == self.vector_dimension:
            return

        logger.warning(f"Changing vector dimension from {self.vector_dimension} to {dimension}")
        logger.warning("This will drop and recreate the embeddings table!")

        self.vector_dimension = dimension

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Drop existing table
                cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._return_connection(conn)

        # Recreate with new dimension
        self._setup_database()

    def __del__(self):
        """Cleanup connection pool"""
        if hasattr(self, 'connection_pool') and self.connection_pool:
            self.connection_pool.closeall()


# Register with factory
DatabaseFactory.register("postgres", PostgreSQLBackend)
DatabaseFactory.register("postgresql", PostgreSQLBackend)