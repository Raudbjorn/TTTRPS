#!/usr/bin/env python3
"""
Test the enhanced markdown parser functionality
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.embeddings.parsers.markdown_parser import MarkdownParser

try:
    from src.embeddings.file_processor import FileProcessor
    FILE_PROCESSOR_AVAILABLE = True
except ImportError:
    FILE_PROCESSOR_AVAILABLE = False

# Sample markdown content with various features
SAMPLE_MARKDOWN = """---
title: "API Documentation"
author: "RapyDocs Team"
layout: "docs"
---

# Rapyd Payment API Documentation

This document covers the **Rapyd Payment API** with examples and usage patterns.

## Table of Contents

1. [Authentication](#authentication)
2. [Making Payments](#making-payments)
3. [Code Examples](#code-examples)

## Authentication

To authenticate with the Rapyd API, you need:

- API Key
- Secret Key

> **Important**: Keep your secret key secure at all times.

## Making Payments

Here's how to create a payment:

```python
import requests

def create_payment(amount, currency):
    # Create payment request
    payload = {
        "amount": amount,
        "currency": currency,
        "payment_method": "card"
    }
    return requests.post("/v1/payments", json=payload)

# Example usage
payment = create_payment(100, "USD")
```

### Payment Types

| Type | Description | Fee |
|------|-------------|-----|
| Card | Credit/Debit cards | 2.9% |
| ACH  | Bank transfer | $0.50 |
| Wire | Wire transfer | $15 |

### Task List

- [x] Implement basic payment flow
- [x] Add error handling
- [ ] Add webhook support
- [ ] Implement refunds

## Inline Code

Use `POST /v1/payments` to create payments and `GET /v1/payments/{id}` to retrieve them.

## Links and References

Check out the [official documentation](https://docs.rapyd.net) and [GitHub repository][repo].

[repo]: https://github.com/rapyd/docs

## Images

![Rapyd Logo](https://rapyd.net/logo.png)

## Footnotes

This API supports webhooks[^1] and real-time notifications[^2].

[^1]: Webhooks are HTTP callbacks sent when events occur
[^2]: Real-time notifications use WebSocket connections

---

*Last updated: 2024*
"""

def test_markdown_parser():
    """Test the markdown parser with sample content"""
    print("Testing Enhanced Markdown Parser...")
    
    parser = MarkdownParser()
    
    # Test with temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(SAMPLE_MARKDOWN)
        temp_path = f.name
    
    try:
        # Test can_parse
        can_parse = parser.can_parse(temp_path, SAMPLE_MARKDOWN)
        print(f"✓ Can parse markdown: {can_parse}")
        
        # Test parsing
        result = parser.parse(SAMPLE_MARKDOWN, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print(f"✓ Parsing successful!")
            print(f"  - Language: {parsed.language}")
            print(f"  - Blocks found: {len(parsed.blocks)}")
            print(f"  - Has frontmatter: {parsed.metadata.get('has_frontmatter')}")
            print(f"  - Word count: {parsed.metadata.get('word_count')}")
            print(f"  - Reading time: {parsed.metadata.get('reading_time_minutes')} minutes")
            print(f"  - Features: {', '.join(parsed.metadata.get('markdown_features', []))}")
            print(f"  - Is documentation: {parsed.metadata.get('is_documentation', False)}")
            
            # Show block types
            block_types = {}
            for block in parsed.blocks:
                block_type = block.type
                if block_type not in block_types:
                    block_types[block_type] = 0
                block_types[block_type] += 1
            
            print("  - Block types:", dict(block_types))
            
            # Show some specific blocks
            for block in parsed.blocks[:5]:  # Show first 5 blocks
                if block.type == "header":
                    print(f"    Header L{block.metadata['level']}: {block.name}")
                elif block.type == "code_block":
                    print(f"    Code block: {block.language} ({block.metadata['lines_of_code']} lines)")
                elif block.type == "table":
                    print(f"    Table: {block.metadata['row_count']} rows, {block.metadata['column_count']} columns")
                elif block.type == "frontmatter":
                    print(f"    Frontmatter: {len(block.metadata['data'])} fields")
            
            # Show links and images
            if 'links' in parsed.metadata:
                print(f"  - Links found: {len(parsed.metadata['links'])}")
            if 'images' in parsed.metadata:
                print(f"  - Images found: {len(parsed.metadata['images'])}")
            if 'tasks' in parsed.metadata:
                print(f"  - Tasks: {parsed.metadata['completed_tasks']}/{parsed.metadata['task_count']} completed")
                
        else:
            print(f"✗ Parsing failed: {result.error}")
            return False
    
    finally:
        # Clean up
        os.unlink(temp_path)
    
    return True

def test_file_processor_integration():
    """Test markdown processing in the file processor"""
    print("\nTesting File Processor Integration...")
    
    if not FILE_PROCESSOR_AVAILABLE:
        print("  File processor not available - skipping integration test")
        return
    
    try:
        
        # Mock database config
        db_config = {
            "host": "127.0.0.1",
            "port": 54320,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres"
        }
        
        # Create processor without embedding generation for this test
        processor = FileProcessor(db_config, use_largest_model=False)
        
        # Create a temporary markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(SAMPLE_MARKDOWN)
            temp_path = Path(f.name)
        
        try:
            # Test MIME detection
            mime_type, encoding = processor.detect_mime_type(temp_path)
            print(f"✓ MIME detection: {mime_type}, encoding: {encoding}")
            
            # Test content parsing
            content, parsed_data = processor.parse_content(temp_path, mime_type, encoding)
            
            if content and parsed_data:
                print("✓ File processor integration successful!")
                print(f"  - Content length: {len(content)} characters")
                print(f"  - Parser type: {parsed_data.get('parser_type', 'basic')}")
                
                if parsed_data.get('parser_type') == 'advanced_markdown':
                    print("  - Using advanced markdown parser ✓")
                    if 'blocks' in parsed_data:
                        print(f"  - Blocks parsed: {len(parsed_data['blocks'])}")
                    if 'metadata' in parsed_data:
                        features = parsed_data['metadata'].get('markdown_features', [])
                        print(f"  - Features detected: {len(features)}")
                else:
                    print("  - Using basic markdown processing")
            else:
                print("✗ File processor integration failed")
                return False
        
        finally:
            temp_path.unlink()
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Enhanced Markdown Parser Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test 1: Basic parser functionality
    if not test_markdown_parser():
        success = False
    
    # Test 2: File processor integration
    if not test_file_processor_integration():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! Enhanced markdown processing is working.")
    else:
        print("✗ Some tests failed. Check the output above.")
    
    exit(0 if success else 1)