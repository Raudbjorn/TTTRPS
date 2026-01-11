#!/usr/bin/env python3
"""
Test script for processing Odoo repos with advanced embedding features
"""

import sys
import os
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple
import json
import time
import tempfile
import subprocess

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def _setup_chromadb_client(db_path: str, collection_name: str):
    """Helper function to setup ChromaDB client and collection"""
    if not CHROMADB_AVAILABLE:
        logger.error("The 'chromadb' package is not installed. Please install it using 'pip install chromadb' before running this script.")
        sys.exit(1)
    
    client = chromadb.PersistentClient(path=db_path)
    
    try:
        collection = client.get_collection(collection_name)
        logger.info(f"Using existing collection: {collection_name}")
    except ValueError:
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Created new collection: {collection_name}")
    
    return client, collection

def _process_files_common(directory_path: str, max_files: int, use_llm: bool = False):
    """Common file processing logic with optional LLM preprocessing"""
    dir_path = Path(directory_path)
    extensions = ['.py', '.js', '.xml', '.csv', '.json', '.yml', '.yaml', '.md', '.rst', '.txt']
    
    documents = []
    metadatas = []
    ids = []
    
    # Setup LLM preprocessing if requested
    preprocessor = None
    chunker = None
    
    if use_llm:
        try:
            from src.embeddings.llm_preprocessor import LLMPreprocessor, PreprocessorConfig
            from src.embeddings.semantic_chunking import SemanticChunker, ChunkingConfig, ChunkingStrategy
            
            config = PreprocessorConfig(
                model_name="llama3.2:latest",
                enable_key_expansion=True,
                enable_summary=True,
                cache_enabled=True
            )
            preprocessor = LLMPreprocessor(config)
            
            chunk_config = ChunkingConfig(
                strategy=ChunkingStrategy.SEMANTIC,
                max_chunk_size=500,
                min_chunk_size=100,
                overlap_size=50
            )
            chunker = SemanticChunker(chunk_config)
            
        except ImportError as e:
            logger.warning(f"LLM preprocessing not available: {e}")
            use_llm = False
    
    files_processed = 0
    for file_path in dir_path.rglob('*'):
        if files_processed >= max_files:
            break
        
        # Skip .git directories
        if '.git' in str(file_path.parts):
            continue
        
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                if not content.strip():
                    continue
                
                # Process content based on LLM availability
                if use_llm and preprocessor and chunker:
                    # Use LLM preprocessing for JSON files
                    if file_path.suffix.lower() == '.json':
                        try:
                            json_data = json.loads(content)
                            processed_content = preprocessor.preprocess_json(json_data)
                        except json.JSONDecodeError:
                            processed_content = content
                    else:
                        processed_content = content
                    
                    chunks = chunker.chunk_text(processed_content, ChunkingStrategy.SEMANTIC)
                    chunk_texts = [chunk.text for chunk in chunks]
                else:
                    # Simple chunking fallback
                    chunk_size = 1000
                    overlap = 100
                    chunk_texts = []
                    
                    for i in range(0, len(content), chunk_size - overlap):
                        chunk = content[i:i + chunk_size]
                        if chunk.strip():
                            chunk_texts.append(chunk)
                
                # Create document entries
                file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
                
                for i, chunk_text in enumerate(chunk_texts[:5]):  # Limit chunks per file
                    documents.append(chunk_text)
                    metadatas.append({
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'chunk_index': i,
                        'total_chunks': len(chunk_texts),
                        'file_hash': file_hash,
                        'preprocessing_used': use_llm and preprocessor is not None
                    })
                    ids.append(f"{file_hash}_chunk_{i}")
                
                files_processed += 1
                
                if files_processed % 10 == 0:
                    processing_type = "with LLM" if use_llm else "basic"
                    logger.info(f"Processed {files_processed} files ({processing_type})...")
                
            except Exception as e:
                logger.debug(f"Error processing {file_path}: {e}")
    
    return documents, metadatas, ids, files_processed

def process_files_with_chromadb(directory_path: str, max_files: int = 100):
    """Process files from directory and store in ChromaDB"""
    logger.info(f"Processing directory: {directory_path}")
    
    client, collection = _setup_chromadb_client("./odoo_chroma_db", "odoo_embeddings")
    documents, metadatas, ids, files_processed = _process_files_common(directory_path, max_files, use_llm=False)
    
    # Store in ChromaDB
    if documents:
        logger.info(f"Storing {len(documents)} chunks from {files_processed} files...")
        
        # Add in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        logger.info(f"Successfully stored {len(documents)} chunks")
        
        # Test query
        logger.info("\nTesting search...")
        results = collection.query(
            query_texts=["payment processing"],
            n_results=3
        )
        
        if results['documents'][0]:
            logger.info("Search results:")
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                logger.info(f"  {i+1}. {meta.get('file_name', 'Unknown')} "
                          f"(chunk {meta.get('chunk_index', 0)})")
                logger.info(f"     Preview: {doc[:100]}...")
    
    logger.info(f"\nTotal documents in collection: {collection.count()}")

def process_with_llm_preprocessing(directory_path: str, max_files: int = 50):
    """Process files with LLM preprocessing for better embeddings"""
    logger.info("Processing with LLM preprocessing...")
    
    # Check if LLM preprocessing is available first
    try:
        from src.embeddings.llm_preprocessor import LLMPreprocessor
        from src.embeddings.semantic_chunking import SemanticChunker
        logger.info("LLM preprocessing available")
    except ImportError as e:
        logger.warning(f"LLM preprocessing not available: {e}")
        # Fall back to basic processing
        process_files_with_chromadb(directory_path, max_files)
        return
    except Exception as e:
        logger.error(f"Error setting up LLM preprocessing: {e}")
        # Fall back to basic processing
        process_files_with_chromadb(directory_path, max_files)
        return
    
    logger.info(f"Processing directory with LLM: {directory_path}")
    
    client, collection = _setup_chromadb_client("./odoo_chroma_db_llm", "odoo_embeddings_llm")
    documents, metadatas, ids, files_processed = _process_files_common(directory_path, max_files, use_llm=True)
    
    # Store in ChromaDB
    if documents:
        logger.info(f"Storing {len(documents)} chunks from {files_processed} files with LLM preprocessing...")
        
        # Add in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        logger.info(f"Successfully stored {len(documents)} chunks with LLM preprocessing")
        
        # Test query
        logger.info("\nTesting search with LLM preprocessing...")
        results = collection.query(
            query_texts=["payment processing"],
            n_results=3
        )
        
        if results['documents'][0]:
            logger.info("Search results:")
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                logger.info(f"  {i+1}. {meta.get('file_name', 'Unknown')} "
                          f"(chunk {meta.get('chunk_index', 0)}, "
                          f"LLM: {meta.get('preprocessing_used', False)})")
                logger.info(f"     Preview: {doc[:100]}...")
    
    logger.info(f"\nTotal documents in LLM collection: {collection.count()}")

def main():
    """Main entry point"""
    
    # Check if odoo repos exist
    temp_dir = Path(tempfile.gettempdir())
    odoo_path = temp_dir / "odoo"
    docs_path = temp_dir / "documentation"
    
    if not odoo_path.exists():
        logger.error(f"Odoo repository not found at {odoo_path}")
        logger.info(f"Please clone: git clone --depth=1 https://github.com/odoo/odoo.git {odoo_path}")
        return
    
    if not docs_path.exists():
        logger.error(f"Documentation repository not found at {docs_path}")
        logger.info(f"Please clone: git clone --depth=1 https://github.com/odoo/documentation.git {docs_path}")
        return
    
    # Process repositories
    logger.info("=" * 60)
    logger.info("Processing Odoo Repositories")
    logger.info("=" * 60)
    
    # Process documentation first (smaller)
    logger.info("\n1. Processing Documentation Repository")
    process_files_with_chromadb(docs_path, max_files=200)
    
    # Process odoo main repo
    logger.info("\n2. Processing Odoo Main Repository")
    process_files_with_chromadb(odoo_path, max_files=500)
    
    logger.info("\n" + "=" * 60)
    logger.info("Processing Complete!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()