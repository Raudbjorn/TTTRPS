# Tests Directory

This directory contains all tests for the Rapydocs project, organized by functionality.

## Structure

```
tests/
├── embeddings/
│   ├── parsers/           # Parser-specific tests
│   │   ├── test_json_parser.py
│   │   ├── test_html_parser.py
│   │   └── test_markdown_parser.py
│   ├── test_file_processor.py
│   └── test_llm_preprocessing.py
├── mcp/                   # MCP server tests
│   ├── test_mcp_integration.py
│   ├── test_mcp_postgres.py
│   └── test_mcp_server.py
├── integration/           # Integration tests
│   ├── test_embeddings_complete.py
│   ├── test_ollama_embeddings.py
│   ├── test_odoo_embedding.py
│   └── test_suite.py
├── database/              # Database-related tests
│   └── test_postgres_setup.py
├── utils/                 # Utility tests
├── data/                  # Test data files
│   ├── test_data_minimal.json
│   ├── api_response.json
│   ├── arrays.json
│   ├── events.jsonl
│   └── semantic_types.json
├── quick_test.py          # Quick system test
└── README.md              # This file
```

## Running Tests

### Run All Tests
```bash
python run_tests.py
```

### Run Specific Categories
```bash
# Parser tests only
python run_tests.py --category parsers

# Embedding tests only  
python run_tests.py --category embeddings

# MCP tests only
python run_tests.py --category mcp

# Integration tests only
python run_tests.py --category integration

# Database tests only
python run_tests.py --category database
```

### Run with Options
```bash
# Verbose output
python run_tests.py --verbose

# Stop on first failure
python run_tests.py --fail-fast

# Quick tests (skip slow integration tests)
python run_tests.py --quick

# Generate detailed report
python run_tests.py --report my_report.json
```

### Run Individual Tests
```bash
# Run a specific test file
python tests/embeddings/parsers/test_json_parser.py

# Run the quick system test
python tests/quick_test.py
```

## Test Categories

### Parser Tests (`tests/embeddings/parsers/`)
Test individual file parsers:
- **test_json_parser.py**: JSON parsing and semantic analysis
- **test_html_parser.py**: HTML parsing and content extraction
- **test_markdown_parser.py**: Markdown parsing with metadata

### Embedding Tests (`tests/embeddings/`)
Test core embedding functionality:
- **test_file_processor.py**: File processing pipeline
- **test_llm_preprocessing.py**: LLM-based preprocessing

### MCP Tests (`tests/mcp/`)
Test Model Context Protocol server:
- **test_mcp_integration.py**: MCP protocol integration
- **test_mcp_postgres.py**: MCP with PostgreSQL backend
- **test_mcp_server.py**: MCP server functionality

### Integration Tests (`tests/integration/`)
Test complete workflows:
- **test_embeddings_complete.py**: End-to-end embedding pipeline
- **test_ollama_embeddings.py**: Ollama model integration
- **test_odoo_embedding.py**: Odoo-specific processing
- **test_suite.py**: Comprehensive test suite

### Database Tests (`tests/database/`)
Test database operations:
- **test_postgres_setup.py**: PostgreSQL setup and configuration

### Quick Test (`tests/quick_test.py`)
Fast system verification test that checks:
- Basic file processing
- Database connectivity
- Model availability

## Test Data

Test data files are stored in `tests/data/`:
- **test_data_minimal.json**: Minimal test dataset
- **api_response.json**: Sample API response data
- **arrays.json**: Array structure test data
- **events.jsonl**: Event log test data
- **semantic_types.json**: Semantic type examples

## Prerequisites

Tests may require:
- PostgreSQL with pgvector extension
- Ollama with models (nomic-embed-text, llama3.2)
- Python packages: psycopg2-binary, requests, numpy

## Environment Variables

Some tests use these environment variables:
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_HOST`: PostgreSQL host (default: 127.0.0.1)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)

## CI/CD Integration

### GitHub Actions
Tests run automatically on:
- Push to main branch
- Pull request creation
- Multiple OS: Ubuntu, macOS, Windows
- Multiple Python versions: 3.10, 3.11, 3.12

### Local Development
```bash
# Run before committing
python run_tests.py --quick

# Full test suite
python run_tests.py --verbose
```

## Adding New Tests

1. **Choose the right category** based on what you're testing
2. **Follow naming convention**: `test_*.py`
3. **Add proper imports** and path handling
4. **Include docstrings** explaining what the test covers
5. **Handle dependencies gracefully** (check if services are available)

Example test structure:
```python
#!/usr/bin/env python3
"""
Test description here
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.module_to_test import ClassToTest

def test_basic_functionality():
    """Test basic functionality"""
    # Test implementation
    pass

if __name__ == "__main__":
    # Run tests when called directly
    test_basic_functionality()
    print("✅ All tests passed")
```

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure `sys.path.insert(0, ...)` points to project root
- Check that `src/` directory structure is correct

**Database Connection Errors**  
- Verify PostgreSQL is running
- Check environment variables are set
- Ensure pgvector extension is installed

**Model Not Found Errors**
- Start Ollama: `ollama serve`
- Pull required models: `ollama pull nomic-embed-text`

**Timeout Errors**
- Some integration tests may take time to complete
- Increase timeout in test runner if needed
- Use `--quick` flag to skip slow tests

### Debug Mode
Run individual tests with Python's `-v` flag for detailed output:
```bash
python -v tests/embeddings/test_file_processor.py
```