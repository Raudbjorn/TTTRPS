"""
Base database interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


class VectorDatabase(ABC):
    """Abstract base class for vector databases"""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the database connection"""
        pass

    @abstractmethod
    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents with embeddings to the database"""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar documents

        Returns:
            List of tuples (document_text, distance, metadata)
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        pass

    @abstractmethod
    def get_count(self) -> int:
        """Get the total number of documents"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from the database"""
        pass


class DatabaseFactory:
    """Factory for creating database backends"""

    _databases: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, database_class: type) -> None:
        """Register a database backend"""
        cls._databases[name] = database_class

    @classmethod
    def create(cls, db_type: str, config: Any) -> VectorDatabase:
        """Create a database backend"""
        if db_type not in cls._databases:
            raise ValueError(f"Unknown database type: {db_type}. Available: {list(cls._databases.keys())}")

        return cls._databases[db_type](config)

    @classmethod
    def list_available(cls) -> List[str]:
        """List available database backends"""
        return list(cls._databases.keys())