#!/usr/bin/env python3
"""
Test script for the file processing system with Ollama embeddings and PostgreSQL storage
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import json

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.embeddings.file_processor import FileProcessor, FileInfo, ProcessedFile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileProcessorTester:
    """Test harness for the file processing system"""
    
    def __init__(self):
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),  # Use IPv4 instead of localhost (which might resolve to ::1)
            "port": int(os.getenv("POSTGRES_PORT", 5432)),  # Use env var for port, default to 5432
            "database": os.getenv("POSTGRES_DB", "postgres"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres")
        }
        
        self.test_results = {
            "passed": [],
            "failed": [],
            "skipped": []
        }
        
        self.processor = None
        
    def test_postgres_connection(self):
        """Test PostgreSQL connection on port 5454"""
        test_name = "PostgreSQL Connection"
        try:
            logger.info(f"Testing PostgreSQL connection on port {self.db_config['port']}...")
            conn = psycopg2.connect(**self.db_config)
            
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"✓ Connected to PostgreSQL: {version}")
                
                # Check if vector extension is available
                cur.execute("""
                    SELECT * FROM pg_extension WHERE extname = 'vector'
                """)
                vector_ext = cur.fetchone()
                if not vector_ext:
                    logger.warning("Vector extension not installed, attempting to install...")
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        conn.commit()
                        logger.info("✓ Vector extension installed successfully")
                    except Exception as e:
                        logger.error(f"Failed to install vector extension: {e}")
                        logger.info("To install manually, run as superuser: CREATE EXTENSION vector;")
                else:
                    logger.info("✓ Vector extension is installed")
                    
            conn.close()
            self.test_results["passed"].append(test_name)
            return True
            
        except psycopg2.OperationalError as e:
            logger.error(f"✗ Cannot connect to PostgreSQL on port {self.db_config['port']}: {e}")
            logger.info(f"Please ensure PostgreSQL is running on port {self.db_config['port']}")
            logger.info(f"You can start it with: docker run -d -p {self.db_config['port']}:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16")
            self.test_results["failed"].append((test_name, str(e)))
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            self.test_results["failed"].append((test_name, str(e)))
            return False
    
    def test_ollama_service(self):
        """Test Ollama service availability"""
        test_name = "Ollama Service"
        try:
            import requests
            
            logger.info("Testing Ollama service...")
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            
            if response.status_code == 200:
                version = response.json()
                logger.info(f"✓ Ollama service is running: {version}")
                
                # Check if mxbai-embed-large model is available
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    
                    if 'mxbai-embed-large' in model_names or 'mxbai-embed-large:latest' in model_names:
                        logger.info("✓ mxbai-embed-large model is available")
                    else:
                        logger.warning("✗ mxbai-embed-large model not found")
                        logger.info("Available models:")
                        for name in model_names:
                            logger.info(f"  - {name}")
                        logger.info("\nTo install the model, run: ollama pull mxbai-embed-large")
                        self.test_results["failed"].append((test_name, "Model not available"))
                        return False
                
                self.test_results["passed"].append(test_name)
                return True
            else:
                logger.error(f"✗ Ollama service returned status {response.status_code}")
                self.test_results["failed"].append((test_name, f"Status {response.status_code}"))
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error("✗ Cannot connect to Ollama service at http://localhost:11434")
            logger.info("Please ensure Ollama is running. Start it with: ollama serve")
            self.test_results["failed"].append((test_name, "Connection refused"))
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            self.test_results["failed"].append((test_name, str(e)))
            return False
    
    def test_file_processor_init(self):
        """Test FileProcessor initialization"""
        test_name = "FileProcessor Initialization"
        try:
            logger.info("Initializing FileProcessor...")
            self.processor = FileProcessor(self.db_config, use_largest_model=True)
            logger.info("✓ FileProcessor initialized successfully")
            self.test_results["passed"].append(test_name)
            return True
        except Exception as e:
            logger.error(f"✗ Failed to initialize FileProcessor: {e}")
            self.test_results["failed"].append((test_name, str(e)))
            return False
    
    def test_sample_files(self):
        """Create and process sample test files"""
        test_name = "Sample File Processing"
        
        if not self.processor:
            logger.error("✗ FileProcessor not initialized")
            self.test_results["skipped"].append((test_name, "No processor"))
            return False
        
        try:
            # Create temporary directory for test files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                logger.info(f"Creating test files in {temp_path}")
                
                # Create sample Python file
                python_file = temp_path / "test_module.py"
                python_file.write_text('''
"""Test Python module for embedding generation"""

def calculate_payment(amount: float, tax_rate: float = 0.1) -> float:
    """Calculate total payment including tax"""
    tax_amount = amount * tax_rate
    total = amount + tax_amount
    return total

class PaymentProcessor:
    """Process payments using Rapyd API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.rapyd.net"
    
    def create_payment(self, amount: float, currency: str = "USD"):
        """Create a new payment"""
        return {
            "amount": amount,
            "currency": currency,
            "status": "pending"
        }
''')
                
                # Create sample JavaScript file
                js_file = temp_path / "payment.js"
                js_file.write_text('''
// Payment processing module

function processPayment(amount, currency = 'USD') {
    // Validate amount
    if (amount <= 0) {
        throw new Error('Amount must be positive');
    }
    
    // Create payment object
    const payment = {
        amount: amount,
        currency: currency,
        timestamp: new Date().toISOString(),
        status: 'pending'
    };
    
    return payment;
}

class PaymentGateway {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.baseUrl = 'https://api.rapyd.net';
    }
    
    async createCheckout(items) {
        // Implementation here
        return { success: true };
    }
}

module.exports = { processPayment, PaymentGateway };
''')
                
                # Create sample JSON config file
                json_file = temp_path / "config.json"
                json_file.write_text(json.dumps({
                    "api": {
                        "base_url": "https://api.rapyd.net",
                        "version": "v1",
                        "timeout": 30
                    },
                    "payment": {
                        "supported_currencies": ["USD", "EUR", "GBP"],
                        "max_amount": 10000,
                        "min_amount": 1
                    }
                }, indent=2))
                
                # Create sample Markdown documentation
                md_file = temp_path / "README.md"
                md_file.write_text('''# Payment Processing System

## Overview
This system integrates with Rapyd API for payment processing.

## Features
- Multi-currency support
- Webhook handling
- Secure payment tokenization

## Installation
```bash
pip install rapyd-sdk
```

## Usage
```python
from rapyd import Client

client = Client(api_key="your_key")
payment = client.create_payment(amount=100, currency="USD")
```
''')
                
                # Process each file
                files_to_process = [python_file, js_file, json_file, md_file]
                processed_count = 0
                
                for file_path in files_to_process:
                    logger.info(f"\nProcessing {file_path.name}...")
                    try:
                        processed = self.processor.process_file(file_path)
                        
                        # Validate processing result
                        assert processed.file_info is not None, "No file info"
                        assert processed.file_info.mime_type is not None, "No MIME type detected"
                        
                        logger.info(f"  - MIME type: {processed.file_info.mime_type}")
                        logger.info(f"  - Size: {processed.file_info.size} bytes")
                        logger.info(f"  - Hash: {processed.file_info.hash[:16]}...")
                        
                        if processed.content:
                            logger.info(f"  - Content extracted: {len(processed.content)} chars")
                        
                        if processed.parsed_data:
                            logger.info(f"  - Parsed data: {type(processed.parsed_data)}")
                        
                        if processed.chunks:
                            logger.info(f"  - Chunks created: {len(processed.chunks)}")
                            logger.info(f"  - Embeddings generated: {processed.embeddings is not None}")
                        
                        # Save to database
                        self.processor.save_to_database(processed)
                        logger.info(f"  ✓ Saved to database")
                        
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"  ✗ Failed to process {file_path.name}: {e}")
                
                logger.info(f"\n✓ Processed {processed_count}/{len(files_to_process)} test files successfully")
                
                if processed_count == len(files_to_process):
                    self.test_results["passed"].append(test_name)
                    return True
                else:
                    self.test_results["failed"].append((test_name, f"Only {processed_count}/{len(files_to_process)} processed"))
                    return False
                    
        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            self.test_results["failed"].append((test_name, str(e)))
            return False
    
    def test_archive_extraction(self):
        """Test processing of compressed archives"""
        test_name = "Archive Extraction"
        
        if not self.processor:
            logger.error("✗ FileProcessor not initialized")
            self.test_results["skipped"].append((test_name, "No processor"))
            return False
        
        try:
            # Process a small archive from more_data directory
            more_data_dir = Path(__file__).parent / "more_data"
            
            # Find smallest archive for quick testing
            archives = list(more_data_dir.glob("*.zip"))
            if not archives:
                logger.warning("No archives found in more_data directory")
                self.test_results["skipped"].append((test_name, "No archives"))
                return False
            
            # Sort by size and pick smallest
            smallest_archive = min(archives, key=lambda p: p.stat().st_size)
            logger.info(f"\nTesting archive extraction with: {smallest_archive.name}")
            logger.info(f"Archive size: {smallest_archive.stat().st_size / 1024:.1f} KB")
            
            # Extract and process
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                extracted_files = self.processor.extract_archive(smallest_archive, temp_path)
                logger.info(f"✓ Extracted {len(extracted_files)} files")
                
                # Process first few files
                files_to_process = extracted_files[:5]  # Limit for testing
                processed_count = 0
                
                for file_path in files_to_process:
                    try:
                        logger.info(f"  Processing: {file_path.name}")
                        processed = self.processor.process_file(file_path)
                        self.processor.save_to_database(processed)
                        processed_count += 1
                    except Exception as e:
                        logger.warning(f"  Failed to process {file_path.name}: {e}")
                
                logger.info(f"✓ Processed {processed_count}/{len(files_to_process)} files from archive")
                
                if processed_count > 0:
                    self.test_results["passed"].append(test_name)
                    return True
                else:
                    self.test_results["failed"].append((test_name, "No files processed"))
                    return False
                    
        except Exception as e:
            logger.error(f"✗ Archive test failed: {e}")
            self.test_results["failed"].append((test_name, str(e)))
            return False
    
    def test_database_queries(self):
        """Test database queries and vector similarity search"""
        test_name = "Database Queries"
        
        try:
            logger.info("\nTesting database queries...")
            
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Count processed files
                    cur.execute("SELECT COUNT(*) as count FROM processed_files")
                    file_count = cur.fetchone()['count']
                    logger.info(f"✓ Total files in database: {file_count}")
                    
                    # Count embeddings
                    cur.execute("SELECT COUNT(*) as count FROM file_embeddings")
                    embedding_count = cur.fetchone()['count']
                    logger.info(f"✓ Total embeddings in database: {embedding_count}")
                    
                    # Sample query for recent files
                    cur.execute("""
                        SELECT file_name, mime_type, size, created_at 
                        FROM processed_files 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    """)
                    recent_files = cur.fetchall()
                    
                    if recent_files:
                        logger.info("✓ Recent files:")
                        for f in recent_files:
                            logger.info(f"  - {f['file_name']} ({f['mime_type']}, {f['size']} bytes)")
                    
                    # Test vector similarity search if embeddings exist
                    if embedding_count > 0:
                        cur.execute("""
                            SELECT embedding 
                            FROM file_embeddings 
                            LIMIT 1
                        """)
                        sample_embedding = cur.fetchone()['embedding']
                        
                        # Perform similarity search
                        cur.execute("""
                            SELECT 
                                fe.chunk_text,
                                fe.embedding <=> %s::vector as distance,
                                pf.file_name
                            FROM file_embeddings fe
                            JOIN processed_files pf ON fe.file_id = pf.id
                            ORDER BY fe.embedding <=> %s::vector
                            LIMIT 3
                        """, (sample_embedding, sample_embedding))
                        
                        similar_chunks = cur.fetchall()
                        logger.info("✓ Vector similarity search working:")
                        for chunk in similar_chunks:
                            preview = chunk['chunk_text'][:100] if chunk['chunk_text'] else "N/A"
                            logger.info(f"  - {chunk['file_name']}: {preview}...")
                    
                    self.test_results["passed"].append(test_name)
                    return True
                    
        except Exception as e:
            logger.error(f"✗ Database query test failed: {e}")
            self.test_results["failed"].append((test_name, str(e)))
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("=" * 60)
        logger.info("Starting File Processing System Tests")
        logger.info("=" * 60)
        
        # Run tests in order
        tests = [
            ("PostgreSQL Connection", self.test_postgres_connection),
            ("Ollama Service", self.test_ollama_service),
            ("FileProcessor Init", self.test_file_processor_init),
            ("Sample Files", self.test_sample_files),
            ("Archive Extraction", self.test_archive_extraction),
            ("Database Queries", self.test_database_queries)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n{'=' * 40}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'=' * 40}")
            
            try:
                test_func()
            except Exception as e:
                logger.error(f"Unexpected error in {test_name}: {e}")
                self.test_results["failed"].append((test_name, str(e)))
            
            time.sleep(1)  # Brief pause between tests
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"\n✓ PASSED: {len(self.test_results['passed'])} tests")
        for test in self.test_results['passed']:
            logger.info(f"  - {test}")
        
        if self.test_results['failed']:
            logger.info(f"\n✗ FAILED: {len(self.test_results['failed'])} tests")
            for test, error in self.test_results['failed']:
                logger.info(f"  - {test}: {error}")
        
        if self.test_results['skipped']:
            logger.info(f"\n⊘ SKIPPED: {len(self.test_results['skipped'])} tests")
            for test, reason in self.test_results['skipped']:
                logger.info(f"  - {test}: {reason}")
        
        # Overall result
        logger.info("\n" + "=" * 60)
        if not self.test_results['failed']:
            logger.info("✓ ALL TESTS PASSED!")
        else:
            logger.info("✗ SOME TESTS FAILED - Please review the errors above")
        logger.info("=" * 60)
        
        return len(self.test_results['failed']) == 0


def main():
    """Main entry point"""
    tester = FileProcessorTester()
    success = tester.run_all_tests()
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()