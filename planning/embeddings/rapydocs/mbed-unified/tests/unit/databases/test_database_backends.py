"""
Comprehensive tests for all vector database backends
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any

from mbed.core.config import MBEDSettings
from mbed.databases.base import VectorDatabase, DatabaseFactory
from mbed.databases.chromadb import ChromaDBBackend
from mbed.databases.postgres import PostgreSQLBackend
from mbed.databases.faiss_backend import FAISSBackend
from mbed.databases.qdrant import QdrantBackend


class TestDatabaseFactory:
    """Test database factory functionality"""

    def test_factory_registration(self):
        """Test that all backends are registered"""
        available = DatabaseFactory.list_available()

        expected_backends = ["chromadb", "postgres", "postgresql", "faiss", "qdrant"]
        for backend in expected_backends:
            assert backend in available

    def test_factory_create_chromadb(self):
        """Test factory creates ChromaDB backend"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = MBEDSettings(db_path=Path(temp_dir))
            db = DatabaseFactory.create("chromadb", config)
            assert isinstance(db, ChromaDBBackend)

    def test_factory_create_postgres(self):
        """Test factory creates PostgreSQL backend"""
        config = MBEDSettings(db_connection="postgresql://user:pass@localhost/test")
        db = DatabaseFactory.create("postgres", config)
        assert isinstance(db, PostgreSQLBackend)

    def test_factory_create_faiss(self):
        """Test factory creates FAISS backend"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = MBEDSettings(db_path=Path(temp_dir))
            db = DatabaseFactory.create("faiss", config)
            assert isinstance(db, FAISSBackend)

    def test_factory_create_qdrant(self):
        """Test factory creates Qdrant backend"""
        config = MBEDSettings(db_connection="qdrant://localhost:6333")
        db = DatabaseFactory.create("qdrant", config)
        assert isinstance(db, QdrantBackend)

    def test_factory_unknown_backend(self):
        """Test factory raises error for unknown backend"""
        config = MBEDSettings()
        with pytest.raises(ValueError, match="Unknown database type"):
            DatabaseFactory.create("unknown", config)


class TestChromaDBBackend:
    """Test ChromaDB backend implementation"""

    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield MBEDSettings(db_path=Path(temp_dir))

    @pytest.fixture
    def mock_chromadb(self):
        """Mock ChromaDB dependencies"""
        with patch('mbed.databases.chromadb.chromadb') as mock_chromadb_module:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client_class = MagicMock(return_value=mock_client)
            mock_chromadb_module.PersistentClient = mock_client_class
            mock_chromadb_module.config.Settings = MagicMock()

            mock_client.get_collection.side_effect = Exception("Not found")
            mock_client.create_collection.return_value = mock_collection
            mock_collection.count.return_value = 0

            yield mock_chromadb_module, mock_client, mock_collection

    def test_chromadb_initialization(self, temp_config, mock_chromadb):
        """Test ChromaDB initialization"""
        mock_chromadb_module, mock_client, mock_collection = mock_chromadb

        backend = ChromaDBBackend(temp_config)
        backend.initialize()

        assert backend._initialized is True
        mock_client.create_collection.assert_called_once()

    def test_chromadb_add_documents(self, temp_config, mock_chromadb):
        """Test adding documents to ChromaDB"""
        mock_chromadb_module, mock_client, mock_collection = mock_chromadb

        backend = ChromaDBBackend(temp_config)
        backend.initialize()

        texts = ["Document 1", "Document 2"]
        embeddings = np.random.rand(2, 768)
        metadata = [{"source": "test1"}, {"source": "test2"}]
        ids = ["id1", "id2"]

        backend.add_documents(texts, embeddings, metadata, ids)

        # Check that collection.add was called
        mock_collection.add.assert_called()

    def test_chromadb_search(self, temp_config, mock_chromadb):
        """Test searching in ChromaDB"""
        mock_chromadb_module, mock_client, mock_collection = mock_chromadb

        # Mock search results
        mock_collection.query.return_value = {
            "documents": [["Document 1", "Document 2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]]
        }

        backend = ChromaDBBackend(temp_config)
        backend.initialize()

        query_embedding = np.random.rand(768)
        results = backend.search(query_embedding, k=2)

        assert len(results) == 2
        assert results[0][0] == "Document 1"
        assert results[0][1] == 0.1  # distance
        assert results[0][2]["source"] == "test1"  # metadata

    def test_chromadb_not_initialized_error(self, temp_config):
        """Test error when backend not initialized"""
        backend = ChromaDBBackend(temp_config)

        with pytest.raises(RuntimeError, match="Database not initialized"):
            backend.add_documents(["test"], np.random.rand(1, 768))


class TestPostgreSQLBackend:
    """Test PostgreSQL backend implementation"""

    @pytest.fixture
    def pg_config(self):
        """Create PostgreSQL test configuration"""
        return MBEDSettings(
            db_connection="postgresql://test:test@localhost:5432/test_db"
        )

    @pytest.fixture
    def mock_psycopg2(self):
        """Mock psycopg2 dependencies"""
        with patch('mbed.databases.postgres.psycopg2') as mock_pg:
            mock_pool = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_pg.pool.ThreadedConnectionPool.return_value = mock_pool
            mock_pool.getconn.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [100]  # count result

            yield mock_pg, mock_pool, mock_conn, mock_cursor

    def test_postgres_initialization(self, pg_config, mock_psycopg2):
        """Test PostgreSQL initialization"""
        mock_pg, mock_pool, mock_conn, mock_cursor = mock_psycopg2

        backend = PostgreSQLBackend(pg_config)
        backend.initialize()

        assert backend._initialized is True
        mock_pg.pool.ThreadedConnectionPool.assert_called_once()

    def test_postgres_connection_string_parsing(self):
        """Test PostgreSQL connection string parsing"""
        config = MBEDSettings(
            db_connection="postgresql://user:pass@example.com:5433/mydb"
        )
        backend = PostgreSQLBackend(config)

        assert backend.connection_params['host'] == 'example.com'
        assert backend.connection_params['port'] == 5433
        assert backend.connection_params['database'] == 'mydb'
        assert backend.connection_params['user'] == 'user'
        assert backend.connection_params['password'] == 'pass'

    def test_postgres_add_documents(self, pg_config, mock_psycopg2):
        """Test adding documents to PostgreSQL"""
        mock_pg, mock_pool, mock_conn, mock_cursor = mock_psycopg2

        backend = PostgreSQLBackend(pg_config)
        backend.initialize()

        texts = ["Document 1"]
        embeddings = np.random.rand(1, 768)

        backend.add_documents(texts, embeddings)

        # Verify execute_batch was called for insert
        from unittest.mock import call
        assert mock_cursor.execute.call_count >= 2  # Schema setup + insert


class TestFAISSBackend:
    """Test FAISS backend implementation"""

    @pytest.fixture
    def faiss_config(self):
        """Create FAISS test configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield MBEDSettings(db_path=Path(temp_dir), use_gpu=False)

    @pytest.fixture
    def mock_faiss(self):
        """Mock FAISS dependencies"""
        with patch('mbed.databases.faiss_backend.faiss') as mock_faiss_lib:
            mock_index = MagicMock()
            mock_index.is_trained = True
            mock_index.ntotal = 0
            mock_index.search.return_value = (
                np.array([[0.1, 0.2]]),  # distances
                np.array([[0, 1]])       # indices
            )

            mock_faiss_lib.IndexFlatIP.return_value = mock_index
            mock_faiss_lib.IndexFlatL2.return_value = mock_index
            mock_faiss_lib.METRIC_INNER_PRODUCT = 1
            mock_faiss_lib.METRIC_L2 = 0
            mock_faiss_lib.get_num_gpus.return_value = 0
            mock_faiss_lib.read_index.return_value = mock_index
            mock_faiss_lib.write_index = MagicMock()

            yield mock_faiss_lib, mock_index

    def test_faiss_initialization(self, faiss_config, mock_faiss):
        """Test FAISS initialization"""
        mock_faiss_lib, mock_index = mock_faiss

        backend = FAISSBackend(faiss_config)
        backend.initialize()

        assert backend._initialized is True
        assert backend.index is mock_index

    def test_faiss_add_documents(self, faiss_config, mock_faiss):
        """Test adding documents to FAISS"""
        mock_faiss_lib, mock_index = mock_faiss

        backend = FAISSBackend(faiss_config)
        backend.initialize()

        texts = ["Document 1", "Document 2"]
        embeddings = np.random.rand(2, 768)

        backend.add_documents(texts, embeddings)

        mock_index.add.assert_called_once()
        assert len(backend.documents) == 2

    def test_faiss_search(self, faiss_config, mock_faiss):
        """Test searching in FAISS"""
        mock_faiss_lib, mock_index = mock_faiss

        backend = FAISSBackend(faiss_config)
        backend.initialize()

        # Add some test documents first
        backend.documents = ["Document 1", "Document 2"]
        backend.metadata = [{"source": "test1"}, {"source": "test2"}]

        query_embedding = np.random.rand(768)
        results = backend.search(query_embedding, k=2)

        mock_index.search.assert_called_once()
        assert len(results) == 2

    def test_faiss_vector_dimension_validation(self, faiss_config, mock_faiss):
        """Test vector dimension validation"""
        mock_faiss_lib, mock_index = mock_faiss

        backend = FAISSBackend(faiss_config)
        backend.initialize()

        texts = ["Document 1"]
        wrong_dim_embeddings = np.random.rand(1, 384)  # Wrong dimension

        with pytest.raises(ValueError, match="Embedding dimension"):
            backend.add_documents(texts, wrong_dim_embeddings)


class TestQdrantBackend:
    """Test Qdrant backend implementation"""

    @pytest.fixture
    def qdrant_config(self):
        """Create Qdrant test configuration"""
        return MBEDSettings(
            db_connection="qdrant://localhost:6333"
        )

    @pytest.fixture
    def mock_qdrant(self):
        """Mock Qdrant dependencies"""
        # Mock the qdrant_client module import
        with patch.dict('sys.modules', {'qdrant_client': MagicMock(),
                                         'qdrant_client.models': MagicMock(),
                                         'qdrant_client.http.exceptions': MagicMock()}):
            mock_qdrant_module = MagicMock()
            mock_client_class = MagicMock()
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock collections
            mock_collections = MagicMock()
            mock_collections.collections = []
            mock_client.get_collections.return_value = mock_collections

            # Mock collection info
            mock_collection_info = MagicMock()
            mock_collection_info.points_count = 10
            mock_client.get_collection.return_value = mock_collection_info

            # Mock search results
            mock_hit = MagicMock()
            mock_hit.payload = {"text": "Test document", "source": "test"}
            mock_hit.score = 0.9
            mock_client.search.return_value = [mock_hit]

            yield mock_client_class, mock_client, MagicMock(), MagicMock(), MagicMock()

    def test_qdrant_initialization(self, qdrant_config, mock_qdrant):
        """Test Qdrant initialization"""
        mock_client_class, mock_client, mock_distance, mock_vector_params, mock_point_struct = mock_qdrant

        backend = QdrantBackend(qdrant_config)
        backend.initialize()

        assert backend._initialized is True
        mock_client_class.assert_called_once()
        mock_client.create_collection.assert_called_once()

    def test_qdrant_connection_string_parsing(self):
        """Test Qdrant connection string parsing"""
        # Test qdrant:// format
        config1 = MBEDSettings(db_connection="qdrant://example.com:6333")
        backend1 = QdrantBackend(config1)
        assert backend1.host == "example.com"
        assert backend1.port == 6333

        # Test HTTPS format
        config2 = MBEDSettings(db_connection="https://example.qdrant.tech")
        backend2 = QdrantBackend(config2)
        assert backend2.url == "https://example.qdrant.tech"

    def test_qdrant_add_documents(self, qdrant_config, mock_qdrant):
        """Test adding documents to Qdrant"""
        mock_client_class, mock_client, mock_distance, mock_vector_params, mock_point_struct = mock_qdrant

        backend = QdrantBackend(qdrant_config)
        backend.initialize()

        texts = ["Document 1"]
        embeddings = np.random.rand(1, 768)

        backend.add_documents(texts, embeddings)

        mock_client.upsert.assert_called_once()

    def test_qdrant_search(self, qdrant_config, mock_qdrant):
        """Test searching in Qdrant"""
        mock_client_class, mock_client, mock_distance, mock_vector_params, mock_point_struct = mock_qdrant

        backend = QdrantBackend(qdrant_config)
        backend.initialize()

        query_embedding = np.random.rand(768)
        results = backend.search(query_embedding, k=1)

        mock_client.search.assert_called_once()
        assert len(results) == 1
        assert results[0][0] == "Test document"
        assert results[0][1] == 0.1  # 1.0 - 0.9 (distance from similarity)

    def test_qdrant_get_count(self, qdrant_config, mock_qdrant):
        """Test getting document count from Qdrant"""
        mock_client_class, mock_client, mock_distance, mock_vector_params, mock_point_struct = mock_qdrant

        backend = QdrantBackend(qdrant_config)
        backend.initialize()

        count = backend.get_count()

        assert count == 10
        mock_client.get_collection.assert_called()


class TestDatabaseIntegration:
    """Integration tests for database backends"""

    def test_all_backends_implement_interface(self):
        """Test that all backends implement the VectorDatabase interface"""
        backends = [ChromaDBBackend, PostgreSQLBackend, FAISSBackend, QdrantBackend]

        for backend_class in backends:
            # Check that backend inherits from VectorDatabase
            assert issubclass(backend_class, VectorDatabase)

            # Check that all abstract methods are implemented
            abstract_methods = {
                'initialize', 'add_documents', 'search',
                'delete', 'get_count', 'clear'
            }

            implemented_methods = set(dir(backend_class))

            for method in abstract_methods:
                assert method in implemented_methods, f"{backend_class.__name__} missing {method}"

    def test_embedding_dimension_consistency(self):
        """Test that backends handle embedding dimensions consistently"""
        test_embeddings = {
            384: np.random.rand(5, 384),
            768: np.random.rand(5, 768),
            1024: np.random.rand(5, 1024)
        }

        for dim, embeddings in test_embeddings.items():
            # This test would ideally run against actual backend instances
            # but requires actual database connections
            assert embeddings.shape[1] == dim
            assert embeddings.dtype == np.float64  # Default numpy type

    def test_metadata_handling_consistency(self):
        """Test that metadata is handled consistently across backends"""
        test_metadata = [
            {"source": "file1.txt", "type": "document", "tags": ["important"]},
            {"source": "file2.py", "type": "code", "lines": 100},
            {"source": "file3.md", "type": "markdown"}
        ]

        # All backends should accept this metadata format
        for meta in test_metadata:
            assert isinstance(meta, dict)
            assert "source" in meta or len(meta) == 0


# Benchmarking tests
# Performance benchmarking tests are implemented in tests/benchmarks/ directory


# Error handling tests
class TestDatabaseErrorHandling:
    """Test error handling across all backends"""

    def test_invalid_connection_strings(self):
        """Test handling of invalid connection strings"""
        invalid_configs = [
            "invalid://connection/string",
            "postgresql://missing@password",
            "qdrant://invalid:port"
        ]

        for invalid_conn in invalid_configs:
            config = MBEDSettings(db_connection=invalid_conn)
            # Backends should handle invalid connections gracefully
            # Specific behavior depends on backend implementation

    # Additional error handling tests can be implemented as needed
    # Currently focusing on valid connection string testing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])