"""Universal embeddings that work on any platform (Intel, Apple Silicon, etc.)
This is a minimal fallback implementation for compatibility."""

import json
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
import platform
import os

from ..utils.logging_config import get_logger
from ..utils.common import ErrorHandler, CollectionUtils, DatabaseLoader

logger = get_logger(__name__)

class UniversalEmbeddings:
    """Basic embeddings that work on any platform - CPU fallback"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", collection_name: str = "rapyd_docs"):
        self.model_name = model_name
        self.collection_name = collection_name
        self.device = "cpu"  # Simple CPU fallback
        
        logger.info(f"Initializing basic embeddings on CPU...")
        
        # Initialize ChromaDB with sentence transformer
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=f"sentence-transformers/{model_name}"
        )
        
        # Get existing collection or create new one
        self.collection = self._get_or_create_collection(collection_name)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        with ErrorHandler.log_duration("Search"):
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
                "Search error"
            )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection.name,
            "model": self.model_name,
            "device": self.device,
            "platform": f"{platform.system()} {platform.machine()}"
        }
    
    def _get_or_create_collection(self, collection_name: str):
        """Get existing collection or create new one with error handling."""
        def get_collection():
            existing_collections = self.chroma_client.list_collections()
            
            # Look for collections with data
            best_collection = None
            for col in existing_collections:
                if col.count() > 0:
                    if best_collection is None or col.count() > best_collection.count():
                        best_collection = col
            
            if best_collection:
                logger.info(f"Using existing collection '{best_collection.name}' with {best_collection.count()} documents")
                return best_collection
            else:
                logger.info("Creating new collection")
                return self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
        
        def fallback_collection():
            return self.chroma_client.create_collection(
                name=f"{collection_name}_fallback",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        
        return ErrorHandler.handle_with_fallback(
            get_collection,
            fallback_collection(),
            "Error accessing collections"
        )

def initialize_database():
    """Initialize the database from scraped_content.json if empty"""
    embeddings = UniversalEmbeddings()
    
    if embeddings.collection.count() == 0:
        logger.info("Empty database detected, loading from scraped_content.json...")
        
        data = DatabaseLoader.load_scraped_content()
        if data:
            documents, metadatas, ids = DatabaseLoader.prepare_documents_for_embedding(data)
            
            def add_batch(batch_data):
                batch_docs, batch_meta, batch_ids = batch_data
                embeddings.collection.add(
                    documents=batch_docs,
                    metadatas=batch_meta,
                    ids=batch_ids
                )
            
            # Create batches of (docs, meta, ids) tuples
            batch_size = 100
            batches = []
            for i in range(0, len(documents), batch_size):
                batches.append((
                    documents[i:i+batch_size],
                    metadatas[i:i+batch_size],
                    ids[i:i+batch_size]
                ))
            
            CollectionUtils.batch_process(batches, 1, add_batch)
            logger.info(f"Initialized database with {len(documents)} documents")
    
    return embeddings

if __name__ == "__main__":
    # Test the embeddings
    embeddings = initialize_database()
    stats = embeddings.get_collection_stats()
    print(f"\nDatabase stats: {stats}")
    
    # Test search
    test_query = "payment webhook signature verification"
    print(f"\nSearching for: '{test_query}'")
    results = embeddings.search(test_query, top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   URL: {result['metadata'].get('url', 'N/A')}")
        print(f"   Preview: {result['content'][:200]}...")