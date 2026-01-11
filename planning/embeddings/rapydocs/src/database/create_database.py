#!/usr/bin/env python3
"""
Create ChromaDB database from scraped_content.json
Automatically detects platform and creates appropriate embeddings
"""

import json
import logging
import platform
import sys
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_platform():
    """Detect the current platform and best embedding approach"""
    system = platform.system()
    machine = platform.machine()
    
    # First check if OpenVINO with Intel GPU is available
    try:
        import openvino as ov
        core = ov.Core()
        devices = core.available_devices
        for device in devices:
            if device.startswith('GPU'):
                gpu_name = core.get_property(device, 'FULL_DEVICE_NAME')
                logger.info(f"🚀 Detected Intel GPU with OpenVINO: {gpu_name}")
                return "openvino"
    except ImportError:
        logger.debug("OpenVINO not available")
    except Exception as e:
        logger.debug(f"OpenVINO error: {e}")
    
    if system == "Darwin" and machine == "arm64":
        # Apple Silicon Mac
        logger.info("🍎 Detected Apple Silicon Mac (ARM64)")
        return "apple_silicon"
    else:
        logger.info("💻 Detected CPU platform")
        return "cpu"

def create_embedding_function(platform_type):
    """Create appropriate embedding function for the platform"""
    
    if platform_type == "openvino":
        # Use OpenVINO embeddings for Intel GPU acceleration
        logger.info("Using OpenVINO embeddings (Intel GPU accelerated)")
        # Note: This requires custom OpenVINO embedding function
        # For now, fall back to sentence-transformers on CPU since ChromaDB's
        # built-in OpenVINO support is limited
        logger.warning("ChromaDB OpenVINO integration complex, using CPU fallback")
        device = "cpu"
    elif platform_type == "apple_silicon":
        device = "mps"
    else:
        device = "cpu"
    
    logger.info(f"Using sentence-transformers embeddings on {device}")
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device=device
    )

def create_database():
    """Create ChromaDB from scraped content"""
    
    # Check if scraped content exists
    if not Path("scraped_content.json").exists():
        logger.error("scraped_content.json not found!")
        logger.info("Please run the crawler first or download the scraped content")
        return False
    
    # Detect platform
    platform_type = detect_platform()
    
    # Load scraped content
    logger.info("Loading scraped content...")
    with open("scraped_content.json", "r") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} documents")
    
    # Initialize ChromaDB
    logger.info("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # Create appropriate embedding function
    embedding_function = create_embedding_function(platform_type)
    
    # Collection name based on platform
    collection_name = f"rapyd_docs_{platform_type}"
    
    # Delete existing collection if it exists
    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass
    
    # Create new collection
    logger.info(f"Creating collection: {collection_name}")
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Process documents in batches
    batch_size = 50
    documents = []
    metadatas = []
    ids = []
    
    logger.info("Adding documents to ChromaDB...")
    for idx, item in enumerate(data):
        # Prepare document
        documents.append(item['content'])
        metadatas.append({
            'title': item['title'],
            'url': item['url'],
            'source': 'rapyd-docs'
        })
        ids.append(f"doc_{idx}")
        
        # Add batch to collection
        if len(documents) >= batch_size or idx == len(data) - 1:
            logger.info(f"Adding batch {idx//batch_size + 1}/{(len(data) + batch_size - 1)//batch_size}")
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            # Clear batch
            documents = []
            metadatas = []
            ids = []
    
    # Verify
    count = collection.count()
    logger.info(f"✅ Database created successfully with {count} documents")
    logger.info(f"📁 Collection name: {collection_name}")
    logger.info(f"📂 Database saved to ./chroma_db/")
    
    # Update MCP server to use this collection
    logger.info("\n⚠️  Important: The MCP server will automatically detect and use this collection")
    
    return True

if __name__ == "__main__":
    success = create_database()
    if success:
        print("\n✅ ChromaDB is ready to use!")
        print("You can now run the MCP server or web interface")
        print("\nNote: Embeddings are platform-specific.")
        print("This database was created for your current platform.")
    else:
        print("\n❌ Failed to create database")
        print("Make sure scraped_content.json exists")