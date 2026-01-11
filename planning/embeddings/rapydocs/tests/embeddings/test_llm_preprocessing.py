#!/usr/bin/env python3
"""
Test suite for LLM-based preprocessing functionality.

Tests the LLM preprocessor and semantic chunking modules with various
data types and configurations.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any

from src.embeddings.llm_preprocessor import (
    LLMPreprocessor,
    PreprocessorConfig,
    ProcessingMode
)
from src.embeddings.semantic_chunking import (
    SemanticChunker,
    SemanticChunkConfig,
    ChunkingStrategy
)


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_llm_preprocessor_basic():
    """Test basic LLM preprocessor functionality"""
    print_section("Testing LLM Preprocessor - Basic")

    # Sample structured data
    sample_data = {
        "user_id": "usr_123",
        "tx_id": "tx_789456",
        "amt": 150.50,
        "curr": "USD",
        "desc": "Payment for subscription",
        "meta": {
            "ip": "192.168.1.1",
            "ua": "Mozilla/5.0",
            "ts": 1234567890
        }
    }

    # Initialize with default config
    config = PreprocessorConfig(
        expand_keys=True,
        generate_summaries=False,
        add_semantic_context=True
    )
    preprocessor = LLMPreprocessor(config)

    print(f"Processing mode: {preprocessor.mode.value}")
    print(f"Original JSON:\n{json.dumps(sample_data, indent=2)}")

    # Process the data
    processed = preprocessor.preprocess_json(sample_data)
    print(f"\nProcessed Text:\n{processed}")

    # Test chunking
    chunks = preprocessor.chunk_text(processed)
    print(f"\nGenerated {len(chunks)} chunks")
    if chunks:
        print(f"First chunk preview: {chunks[0][:100]}...")

    # Add assertions
    assert preprocessor.mode in [ProcessingMode.OLLAMA, ProcessingMode.OPENVINO, ProcessingMode.FALLBACK]
    assert processed is not None
    assert len(processed) > 0
    assert len(chunks) > 0
    if preprocessor.config.expand_keys:
        # Check that keys were expanded
        assert "identifier" in processed.lower() or "description" in processed.lower()

    return True


def test_semantic_chunking():
    """Test semantic chunking strategies"""
    print_section("Testing Semantic Chunking")

    sample_text = """
    Payment Processing Documentation

    This document describes the payment processing flow for our API.

    Authentication
    All API requests must include a valid API key in the header. The key should be passed as:
    Authorization: Bearer YOUR_API_KEY

    Creating a Payment
    To create a payment, send a POST request to /api/payments with the following JSON body:
    {
        "amount": 100.00,
        "currency": "USD",
        "customer_id": "cust_123",
        "description": "Product purchase"
    }

    The API will return a payment object with a unique transaction ID.

    Webhook Notifications
    After payment processing, our system will send a webhook to your configured endpoint.
    The webhook payload includes the transaction status and any relevant metadata.

    Error Handling
    If an error occurs, the API returns an error object with code and message fields.
    Common error codes include:
    - 400: Bad Request
    - 401: Unauthorized
    - 429: Rate Limited
    """

    # Test different chunking strategies
    config = SemanticChunkConfig(
        min_chunk_size=50,
        max_chunk_size=200,
        target_chunk_size=100
    )
    chunker = SemanticChunker(config)

    strategies = [
        ChunkingStrategy.FIXED_SIZE,
        ChunkingStrategy.SENTENCE_BASED,
        ChunkingStrategy.PARAGRAPH_BASED,
        ChunkingStrategy.SEMANTIC
    ]

    results = {}
    for strategy in strategies:
        print(f"\n--- Strategy: {strategy.value} ---")
        chunks = chunker.chunk_text(sample_text, strategy)
        print(f"Generated {len(chunks)} chunks")

        # Assertions
        assert len(chunks) > 0, f"No chunks generated for strategy {strategy.value}"
        assert all(chunk.text for chunk in chunks), f"Empty chunks found in {strategy.value}"
        assert all(chunk.chunk_id for chunk in chunks), f"Missing chunk IDs in {strategy.value}"

        results[strategy] = len(chunks)

        for i, chunk in enumerate(chunks[:2], 1):  # Show first 2 chunks
            tokens = chunker.count_tokens(chunk.text)
            print(f"Chunk {i} ({tokens} tokens): {chunk.text[:80]}...")
            assert tokens > 0, f"Chunk {i} has no tokens"

    # Verify different strategies produce different results
    assert len(set(results.values())) > 1, "All strategies produced same number of chunks"

    return True


def test_complex_json_processing():
    """Test processing of complex nested JSON"""
    print_section("Testing Complex JSON Processing")

    complex_json = {
        "webhook_event": {
            "evt_id": "evt_20240315_001",
            "evt_type": "payment.completed",
            "obj": {
                "pmt_id": "pmt_abc123",
                "amt": 250.00,
                "curr": "EUR",
                "cust": {
                    "id": "cust_xyz789",
                    "email": "customer@example.com",
                    "addr": {
                        "line1": "123 Main St",
                        "city": "Berlin",
                        "country": "DE"
                    }
                },
                "items": [
                    {"sku": "PROD-001", "qty": 2, "price": 100.00},
                    {"sku": "PROD-002", "qty": 1, "price": 50.00}
                ]
            },
            "metadata": {
                "api_version": "2024-03-01",
                "idempotency_key": "idem_key_123",
                "retry_count": 0
            }
        }
    }

    config = PreprocessorConfig(
        expand_keys=True,
        generate_summaries=True,
        add_semantic_context=True,
        create_qa_pairs=False
    )

    preprocessor = LLMPreprocessor(config)

    print("Original JSON structure:")
    print(json.dumps(complex_json, indent=2)[:500] + "...")

    # Process with timing
    start_time = time.time()
    processed = preprocessor.preprocess_json(complex_json)
    processing_time = time.time() - start_time

    print(f"\nProcessing time: {processing_time:.2f} seconds")
    print(f"Processed text length: {len(processed)} characters")
    print(f"\nProcessed text preview:\n{processed[:500]}...")

    # Test chunking of processed text
    chunks = preprocessor.chunk_text(processed)
    print(f"\nGenerated {len(chunks)} chunks")

    # Assertions
    assert processed is not None, "Processing returned None"
    assert len(processed) > len(json.dumps(complex_json)), "Processed text should be expanded"
    assert len(chunks) > 0, "No chunks generated"

    # Check that nested keys were expanded if in non-fallback mode
    if preprocessor.mode != ProcessingMode.FALLBACK and preprocessor.config.expand_keys:
        # Should have expanded some keys
        assert ("event" in processed.lower() or
                "customer" in processed.lower() or
                "payment" in processed.lower()), "Keys don't appear to be expanded"

    # Verify processing time is reasonable
    assert processing_time < 30, f"Processing took too long: {processing_time}s"

    return True


def test_batch_processing():
    """Test batch processing of multiple files"""
    print_section("Testing Batch Processing")

    # Create sample files
    files = [
        ("config.json", json.dumps({"db": {"host": "localhost", "port": 5432}})),
        ("api_response.json", json.dumps({"status": "success", "data": {"id": 123}})),
        ("webhook.json", json.dumps({"event": "user.created", "user_id": "usr_456"}))
    ]

    config = PreprocessorConfig(
        expand_keys=True,
        batch_size=3,
        max_workers=2
    )
    preprocessor = LLMPreprocessor(config)

    print(f"Processing {len(files)} files in batch...")
    start_time = time.time()
    results = preprocessor.batch_process(files)
    batch_time = time.time() - start_time

    print(f"Batch processing time: {batch_time:.2f} seconds")

    successful_results = []
    for i, result in enumerate(results):
        if "error" not in result:
            print(f"\nFile {i+1}: {result['metadata']['filepath']}")
            print(f"  Chunks: {result['metadata']['num_chunks']}")
            print(f"  Mode: {result['metadata']['processing_mode']}")
            successful_results.append(result)
        else:
            print(f"\nFile {i+1}: Error - {result['error']}")

    # Assertions
    assert len(results) == len(files), "Not all files were processed"
    assert len(successful_results) > 0, "No files processed successfully"

    # Check that results have expected structure
    for result in successful_results:
        assert 'metadata' in result, "Missing metadata in result"
        assert 'chunks' in result, "Missing chunks in result"
        assert 'processed' in result, "Missing processed text in result"
        assert result['metadata']['num_chunks'] > 0, "No chunks generated"

    # Verify batch processing was reasonably fast
    assert batch_time < 60, f"Batch processing took too long: {batch_time}s"

    return True


def test_fallback_mode():
    """Test fallback mode when no LLM is available"""
    print_section("Testing Fallback Mode")

    # Force fallback mode
    config = PreprocessorConfig()
    preprocessor = LLMPreprocessor(config)
    preprocessor.mode = ProcessingMode.FALLBACK

    sample_data = {
        "cust_id": "CUST-001",
        "order_items": [
            {"prod_id": "P1", "qty": 2},
            {"prod_id": "P2", "qty": 1}
        ]
    }

    print(f"Mode: {preprocessor.mode.value}")
    processed = preprocessor.preprocess_json(sample_data)
    print(f"Fallback processed text:\n{processed}")

    # Assertions
    assert preprocessor.mode == ProcessingMode.FALLBACK, "Not in fallback mode"
    assert processed is not None, "Fallback processing returned None"
    assert len(processed) > 0, "Fallback produced empty text"

    # Check that basic structure is preserved
    assert "CUST-001" in processed, "Customer ID lost in fallback"
    assert "order_items" in processed or "Order Items" in processed, "Order items lost"

    # Verify key expansion still works in fallback
    if preprocessor.config.expand_keys:
        assert "Customer Identifier" in processed, "Key expansion not working in fallback"

    return True


def test_semantic_boundaries():
    """Test semantic boundary detection"""
    print_section("Testing Semantic Boundary Detection")

    markdown_text = """
# Main Title

This is the introduction paragraph with some important information.

## Section 1: Getting Started

First, you need to install the dependencies:

```python
pip install requests
pip install numpy
```

After installation, you can start using the API.

## Section 2: API Usage

The API provides several endpoints:

### Authentication Endpoint
POST /api/auth - Get access token

### Data Endpoint
GET /api/data - Retrieve data

## Conclusion

This concludes our documentation.
"""

    config = SemanticChunkConfig(
        preserve_code_blocks=True,
        preserve_paragraphs=True
    )
    chunker = SemanticChunker(config)

    # Detect boundaries
    boundaries = chunker._detect_semantic_boundaries(markdown_text)

    print(f"Detected {len(boundaries)} semantic boundaries:")
    for boundary in boundaries[:5]:  # Show first 5
        print(f"  Position: {boundary.position}, "
              f"Strength: {boundary.strength:.2f}, "
              f"Type: {boundary.boundary_type}")

    # Chunk using semantic strategy
    chunks = chunker.chunk_text(markdown_text, ChunkingStrategy.SEMANTIC)
    print(f"\nGenerated {len(chunks)} semantic chunks")

    # Assertions
    assert len(boundaries) > 0, "No boundaries detected"

    # Check that different boundary types were detected
    boundary_types = set(b.boundary_type for b in boundaries)
    assert len(boundary_types) > 1, "Only one type of boundary detected"

    # Verify boundaries have valid positions and strengths
    for boundary in boundaries:
        assert boundary.position >= 0, f"Invalid boundary position: {boundary.position}"
        assert 0.0 <= boundary.strength <= 1.0, f"Invalid boundary strength: {boundary.strength}"

    # Check semantic chunks
    assert len(chunks) > 0, "No semantic chunks generated"
    assert all(chunk.text for chunk in chunks), "Empty chunks found"

    # Verify code blocks were preserved if configured
    if chunker.config.preserve_code_blocks:
        code_block_found = any("```" in chunk.text or "pip install" in chunk.text for chunk in chunks)
        assert code_block_found, "Code blocks not preserved in chunks"

    return True


def run_all_tests():
    """Run all tests"""
    tests = [
        ("Basic LLM Preprocessor", test_llm_preprocessor_basic),
        ("Semantic Chunking", test_semantic_chunking),
        ("Complex JSON Processing", test_complex_json_processing),
        ("Batch Processing", test_batch_processing),
        ("Fallback Mode", test_fallback_mode),
        ("Semantic Boundaries", test_semantic_boundaries)
    ]

    print("\n" + "="*60)
    print("  LLM PREPROCESSING TEST SUITE")
    print("="*60)

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            failed += 1

    print_section("Test Summary")
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)