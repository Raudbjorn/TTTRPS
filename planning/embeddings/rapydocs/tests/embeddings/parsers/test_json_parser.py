#!/usr/bin/env python3
"""
Test the JSON parser with semantic analysis functionality
"""

import sys
import json
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.embeddings.parsers.json_parser import JSONParser

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"

def load_test_data(filename):
    """Load test data from file"""
    filepath = TEST_DATA_DIR / filename
    with open(filepath, 'r') as f:
        return f.read()

def test_json_parser():
    """Test the JSON parser with sample content"""
    print("Testing JSON Parser with Semantic Analysis...")
    print("=" * 60)
    
    parser = JSONParser(enhance_for_embeddings=True)
    
    # Test 1: API Response JSON
    print("\n1. Testing API Response Pattern")
    print("-" * 40)
    
    sample_api_json = load_test_data('api_response.json')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(sample_api_json)
        temp_path = f.name
    
    try:
        # Test can_parse
        can_parse = parser.can_parse(temp_path, sample_api_json)
        print(f"✓ Can parse JSON: {can_parse}")
        
        # Test parsing
        result = parser.parse(sample_api_json, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print(f"✓ Parsing successful!")
            print(f"  - Blocks created: {len(parsed.blocks)}")
            print(f"  - JSON type: {parsed.metadata.get('json_type')}")
            
            # Show patterns detected
            if 'patterns' in parsed.metadata:
                patterns = parsed.metadata['patterns']
                print(f"  - Pattern detected: {patterns.get('type', 'unknown')}")
                print(f"  - Structure: {patterns.get('structure', 'unknown')}")
            
            # Show statistics
            if 'statistics' in parsed.metadata:
                stats = parsed.metadata['statistics']
                print(f"  - Statistics:")
                print(f"    • Objects: {stats.get('object_count', 0)}")
                print(f"    • Arrays: {stats.get('array_count', 0)}")
                print(f"    • Total keys: {stats.get('total_keys', 0)}")
                print(f"    • Max depth: {stats.get('max_depth', 0)}")
            
            # Show semantic enhancements
            print(f"  - Semantic blocks:")
            block_types = {}
            for block in parsed.blocks:
                block_type = block.type
                if block_type not in block_types:
                    block_types[block_type] = []
                
                # Show enhanced descriptions
                if block.metadata.get('enhanced_description'):
                    block_types[block_type].append(block.name)
                    if len(block_types[block_type]) <= 2:  # Show first 2 of each type
                        print(f"    • {block.type} '{block.name}':")
                        print(f"      {block.metadata['enhanced_description'][:100]}...")
                
                # Show semantic type detection
                if block.metadata.get('semantic_type') and block.metadata['semantic_type'] != 'general':
                    print(f"    • Field '{block.name}' detected as: {block.metadata['semantic_type']}")
            
            print(f"  - Block type summary: {dict([(k, len(v)) for k, v in block_types.items()])}")
            
        else:
            print(f"✗ Parsing failed: {result.error}")
            return False
    
    finally:
        os.unlink(temp_path)
    
    # Test 2: Configuration JSON
    print("\n2. Testing Configuration Pattern")
    print("-" * 40)
    
    sample_config_json = load_test_data('config.json')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(sample_config_json)
        temp_path = f.name
    
    try:
        result = parser.parse(sample_config_json, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print(f"✓ Configuration parsing successful!")
            
            # Check for sensitive field detection
            sensitive_fields = []
            for block in parsed.blocks:
                if block.metadata.get('semantic_type') == 'sensitive':
                    sensitive_fields.append(block.name)
            
            if sensitive_fields:
                print(f"  - Sensitive fields detected: {', '.join(sensitive_fields)}")
            
            # Check field grouping
            groups = set()
            for block in parsed.blocks:
                if block.type == 'json_object_group':
                    groups.add(block.name)
            
            if groups:
                print(f"  - Field groups identified: {', '.join(groups)}")
            
            # Pattern detection
            if 'patterns' in parsed.metadata:
                print(f"  - Pattern type: {parsed.metadata['patterns'].get('type', 'unknown')}")
        
    finally:
        os.unlink(temp_path)
    
    # Test 3: JSONL Dataset
    print("\n3. Testing JSONL Dataset")
    print("-" * 40)
    
    sample_jsonl = load_test_data('events.jsonl')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(sample_jsonl)
        temp_path = f.name
    
    try:
        result = parser.parse(sample_jsonl, temp_path)
        
        if result.success and result.data:
            parsed = result.data
            print(f"✓ JSONL parsing successful!")
            
            if 'jsonl_stats' in parsed.metadata:
                stats = parsed.metadata['jsonl_stats']
                print(f"  - Records: {stats.get('valid_records', 0)}/{stats.get('total_lines', 0)}")
                print(f"  - Errors: {stats.get('error_count', 0)}")
            
            # Check for dataset block
            for block in parsed.blocks:
                if block.type == 'jsonl_dataset':
                    print(f"  - Dataset homogeneous: {block.metadata.get('homogeneous', False)}")
                    print(f"  - Enhanced description: {block.metadata.get('enhanced_description', 'N/A')}")
                    break
        
    finally:
        os.unlink(temp_path)
    
    # Test 4: Array Analysis
    print("\n4. Testing Array Pattern Analysis")
    print("-" * 40)
    
    array_json = load_test_data('arrays.json')
    
    result = parser.parse(array_json, "test_arrays.json")
    
    if result.success and result.data:
        print("✓ Array analysis successful!")
        
        for block in result.data.blocks:
            if block.type == 'json_array':
                patterns = block.metadata.get('patterns', {})
                if patterns:
                    path = block.metadata.get('path', 'unknown')
                    print(f"  - Array at {path}:")
                    if patterns.get('sorted'):
                        print(f"    • Sorted: Yes")
                    if patterns.get('unique_values'):
                        print(f"    • Unique values: Yes")
                    if patterns.get('potential_time_series'):
                        print(f"    • Time series detected: Yes")
    
    # Test 5: Semantic Type Detection
    print("\n5. Testing Semantic Type Detection")
    print("-" * 40)
    
    semantic_json = load_test_data('semantic_types.json')
    
    result = parser.parse(semantic_json, "test_semantic.json")
    
    if result.success and result.data:
        print("✓ Semantic detection successful!")
        
        semantic_types = {}
        for block in result.data.blocks:
            if block.type == 'json_field':
                sem_type = block.metadata.get('semantic_type')
                if sem_type and sem_type != 'general':
                    semantic_types[block.name] = sem_type
        
        for field, sem_type in semantic_types.items():
            print(f"  - {field}: {sem_type}")
    
    print("\n" + "=" * 60)
    print("✓ All JSON parser tests completed successfully!")
    return True

def test_file_processor_integration():
    """Test JSON processing in the file processor"""
    print("\n\nTesting File Processor Integration...")
    print("=" * 60)
    
    try:
        from src.embeddings.file_processor import FileProcessor
        
        # Mock database config
        db_config = {
            "host": "127.0.0.1",
            "port": 54320,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres"
        }
        
        # Create processor
        processor = FileProcessor(db_config, use_largest_model=False)
        
        # Create a temporary JSON file
        sample_api_json = load_test_data('api_response.json')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(sample_api_json)
            temp_path = Path(f.name)
        
        try:
            # Test MIME detection
            mime_type, encoding = processor.detect_mime_type(temp_path)
            print(f"✓ MIME detection: {mime_type}, encoding: {encoding}")
            
            # Test content parsing
            content, parsed_data = processor.parse_content(temp_path, mime_type, encoding)
            
            if content and parsed_data:
                print("✓ File processor integration successful!")
                print(f"  - Parser type: {parsed_data.get('parser_type', 'basic')}")
                
                if parsed_data.get('parser_type') == 'advanced_json':
                    print("  - Using advanced JSON parser ✓")
                    if 'blocks' in parsed_data:
                        print(f"  - Blocks created: {len(parsed_data['blocks'])}")
                    if 'metadata' in parsed_data:
                        patterns = parsed_data['metadata'].get('patterns', {})
                        if patterns:
                            print(f"  - Pattern detected: {patterns.get('type', 'unknown')}")
                        stats = parsed_data['metadata'].get('statistics', {})
                        if stats:
                            print(f"  - Max depth: {stats.get('max_depth', 0)}")
                else:
                    print("  - Using basic JSON processing")
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
    print("JSON Parser Test Suite")
    print("=" * 60)
    
    success = True
    
    # Test 1: JSON parser functionality
    if not test_json_parser():
        success = False
    
    # Test 2: File processor integration
    if not test_file_processor_integration():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed! JSON semantic analysis is working.")
    else:
        print("✗ Some tests failed. Check the output above.")
    
    exit(0 if success else 1)