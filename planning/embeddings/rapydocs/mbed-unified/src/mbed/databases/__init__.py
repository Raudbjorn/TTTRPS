"""
Database backends for storing embeddings
"""

from .base import VectorDatabase, DatabaseFactory
from .chromadb import ChromaDBBackend
from .postgres import PostgreSQLBackend
from .faiss_backend import FAISSBackend
from .qdrant import QdrantBackend

__all__ = [
    "VectorDatabase",
    "DatabaseFactory",
    "ChromaDBBackend",
    "PostgreSQLBackend",
    "FAISSBackend",
    "QdrantBackend"
]

# All backends are automatically registered via their respective modules