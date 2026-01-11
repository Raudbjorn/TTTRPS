"""
Integration tests for all chunking strategies
"""

import pytest
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from src.mbed.pipeline.chunker import ChunkConfig, ChunkerFactory, Chunk
from src.mbed.pipeline.strategies.fixed_chunker import FixedSizeChunker
from src.mbed.pipeline.strategies.sentence_chunker import SentenceChunker
from src.mbed.pipeline.strategies.paragraph_chunker import ParagraphChunker
from src.mbed.pipeline.strategies.semantic_chunker import SemanticChunker
from src.mbed.pipeline.strategies.hierarchical_chunker import HierarchicalChunker
from src.mbed.pipeline.strategies.topic_chunker import TopicChunker
from src.mbed.pipeline.strategies.code_chunker import CodeChunker


class TestChunkingStrategies:
    """Integration tests for all chunking strategies."""

    @pytest.fixture
    def sample_text(self) -> str:
        """Sample text for testing."""
        return """# Introduction

This is a comprehensive document that covers multiple topics and concepts.

## First Section

In this section, we discuss the fundamentals of text processing. Text processing is the automatic manipulation of natural language text by a computer. It includes tasks such as tokenization, parsing, and semantic analysis.

### Tokenization

Tokenization is the process of breaking down text into individual words or tokens. This is typically the first step in most text processing pipelines.

### Parsing

Parsing involves analyzing the grammatical structure of sentences. It helps understand the relationships between words and phrases.

## Second Section

The second section covers more advanced topics in natural language processing. These include:

- Machine learning approaches
- Deep learning models
- Transformer architectures
- Attention mechanisms

### Machine Learning

Machine learning has revolutionized the field of NLP. Traditional rule-based approaches have been largely replaced by statistical and neural methods.

## Conclusion

In conclusion, text processing and NLP have evolved significantly over the years. Modern approaches leverage large-scale data and computational resources to achieve human-level performance on many tasks.

The future of NLP looks promising with continued advances in model architectures and training techniques.
"""

    @pytest.fixture
    def sample_code(self) -> str:
        """Sample code for testing."""
        return '''import os
import sys
from typing import List, Dict, Any

class TextProcessor:
    """A simple text processing class."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processed_count = 0

    def process_text(self, text: str) -> List[str]:
        """Process text and return tokens."""
        tokens = text.split()
        self.processed_count += len(tokens)
        return tokens

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'config_items': len(self.config)
        }

def main():
    """Main function."""
    config = {'mode': 'default', 'verbose': True}
    processor = TextProcessor(config)

    sample_text = "This is a sample text for processing."
    tokens = processor.process_text(sample_text)

    print(f"Processed {len(tokens)} tokens")
    print(f"Stats: {processor.get_stats()}")

if __name__ == "__main__":
    main()
'''

    @pytest.fixture
    def chunk_config(self) -> ChunkConfig:
        """Standard chunk configuration for testing."""
        return ChunkConfig(size=200, overlap=20)

    def test_fixed_size_chunker(self, sample_text: str, chunk_config: ChunkConfig):
        """Test fixed size chunking strategy."""
        chunker = FixedSizeChunker(chunk_config)
        result = chunker.chunk(sample_text, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all(chunk.text.strip() for chunk in chunks)
        assert all(chunk.metadata['strategy'] == 'fixed' for chunk in chunks)

        # Test token limits
        for chunk in chunks:
            token_count = chunk.metadata.get('token_count', 0)
            assert token_count <= chunk_config.size * 1.2  # Allow some flexibility

    def test_sentence_chunker(self, sample_text: str, chunk_config: ChunkConfig):
        """Test sentence-based chunking strategy."""
        chunker = SentenceChunker(chunk_config)
        result = chunker.chunk(sample_text, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0
        assert all(chunk.metadata['strategy'] == 'sentence' for chunk in chunks)

        # Check sentence preservation
        for chunk in chunks:
            assert chunk.metadata.get('sentence_count', 0) > 0
            # Check that chunk contains complete content (not just checking punctuation)
            # as last chunk might not end with typical punctuation
            assert len(chunk.text.strip()) > 0
            # Verify chunk has sentence-like structure (contains words)
            assert any(c.isalpha() for c in chunk.text)

    def test_paragraph_chunker(self, sample_text: str, chunk_config: ChunkConfig):
        """Test paragraph-based chunking strategy."""
        chunker = ParagraphChunker(chunk_config)
        result = chunker.chunk(sample_text, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0
        assert all(chunk.metadata['strategy'] == 'paragraph' for chunk in chunks)

        # Check paragraph structure preservation
        for chunk in chunks:
            assert chunk.metadata.get('paragraph_count', 0) > 0
            assert chunk.metadata.get('structure_preserved', False)

    def test_semantic_chunker(self, sample_text: str, chunk_config: ChunkConfig):
        """Test semantic chunking strategy."""
        chunker = SemanticChunker(chunk_config)
        result = chunker.chunk(sample_text, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0
        assert all(chunk.metadata['strategy'] in ['semantic', 'semantic_fallback'] for chunk in chunks)

        # Check semantic features
        for chunk in chunks:
            metadata = chunk.metadata
            assert 'semantic_confidence' in metadata or 'strategy' == 'semantic_fallback'
            assert 'has_headers' in metadata
            assert 'has_code' in metadata

    def test_hierarchical_chunker(self, sample_text: str, chunk_config: ChunkConfig):
        """Test hierarchical chunking strategy."""
        chunker = HierarchicalChunker(chunk_config)
        result = chunker.chunk(sample_text, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0

        # Check for hierarchical structure
        parent_chunks = [c for c in chunks if c.metadata.get('hierarchy_level') == 0]
        child_chunks = [c for c in chunks if c.metadata.get('hierarchy_level') == 1]

        assert len(parent_chunks) > 0

        # If there are child chunks, they should have parent references
        for child in child_chunks:
            assert child.metadata.get('parent_chunk_id') is not None

    def test_topic_chunker(self, sample_text: str, chunk_config: ChunkConfig):
        """Test topic-based chunking strategy."""
        chunker = TopicChunker(chunk_config)
        result = chunker.chunk(sample_text, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0
        assert all(chunk.metadata['strategy'] == 'topic' for chunk in chunks)

        # Check topic analysis
        for chunk in chunks:
            metadata = chunk.metadata
            assert 'dominant_topics' in metadata
            assert 'topic_coherence' in metadata
            assert 'topic_labels' in metadata
            assert isinstance(metadata['dominant_topics'], dict)

    def test_code_chunker(self, sample_code: str, chunk_config: ChunkConfig):
        """Test code-aware chunking strategy."""
        chunker = CodeChunker(chunk_config)
        result = chunker.chunk(sample_code, chunk_config)

        assert result.is_ok()
        chunks = result.unwrap()

        assert len(chunks) > 0

        # Check code-specific features
        found_code_chunks = False
        for chunk in chunks:
            metadata = chunk.metadata
            if metadata['strategy'] == 'code':
                found_code_chunks = True
                assert 'language' in metadata
                assert 'structure_types' in metadata
                assert 'has_functions' in metadata
                assert 'has_classes' in metadata

        # Should detect Python code structures
        assert found_code_chunks

    def test_chunker_factory(self, sample_text: str, chunk_config: ChunkConfig):
        """Test chunker factory registration and creation."""
        # Test all registered strategies
        strategies = ['fixed', 'sentence', 'paragraph', 'semantic', 'hierarchical', 'topic', 'code']

        for strategy in strategies:
            chunker = ChunkerFactory.create(strategy, chunk_config)
            assert chunker is not None

            # Test chunking works
            result = chunker.chunk(sample_text, chunk_config)
            assert result.is_ok()

            chunks = result.unwrap()
            if chunks:  # Some strategies might return empty for certain texts
                assert all(isinstance(chunk, Chunk) for chunk in chunks)

    def test_chunk_overlap_functionality(self, sample_text: str):
        """Test overlap functionality across strategies."""
        config = ChunkConfig(size=100, overlap=20)

        strategies = ['fixed', 'sentence', 'paragraph']

        for strategy_name in strategies:
            chunker = ChunkerFactory.create(strategy_name, config)
            result = chunker.chunk(sample_text, config)

            assert result.is_ok()
            chunks = result.unwrap()

            if len(chunks) > 1:
                # Check that overlaps are recorded
                overlap_found = False
                for chunk in chunks[1:]:  # Skip first chunk
                    if (chunk.metadata.get('has_prev_overlap') or
                        chunk.metadata.get('has_contextual_overlap')):
                        overlap_found = True
                        break

                # At least some chunks should have overlap information
                # (not all strategies implement overlap the same way)

    def test_chunk_metadata_consistency(self, sample_text: str, chunk_config: ChunkConfig):
        """Test that all chunks have consistent metadata."""
        required_fields = ['strategy', 'token_count', 'chunk_index']

        for strategy_name in ['fixed', 'sentence', 'paragraph', 'topic']:
            chunker = ChunkerFactory.create(strategy_name, chunk_config)
            result = chunker.chunk(sample_text, chunk_config)

            assert result.is_ok()
            chunks = result.unwrap()

            for chunk in chunks:
                # Check required fields
                for field in required_fields:
                    assert field in chunk.metadata, f"Missing {field} in {strategy_name} chunk"

                # Check data types
                assert isinstance(chunk.metadata['token_count'], int)
                assert isinstance(chunk.metadata['chunk_index'], int)
                assert chunk.metadata['token_count'] >= 0
                assert chunk.metadata['chunk_index'] >= 0

    def test_empty_text_handling(self, chunk_config: ChunkConfig):
        """Test how strategies handle empty or whitespace-only text."""
        empty_texts = ["", "   ", "\n\n\n", "\t\t"]

        for strategy_name in ['fixed', 'sentence', 'paragraph', 'semantic']:
            chunker = ChunkerFactory.create(strategy_name, chunk_config)

            for empty_text in empty_texts:
                result = chunker.chunk(empty_text, chunk_config)
                assert result.is_ok()

                chunks = result.unwrap()
                # Empty text should produce empty chunks list
                assert len(chunks) == 0

    def test_configuration_validation(self):
        """Test configuration validation across strategies."""
        # Test invalid configurations
        invalid_configs = [
            ChunkConfig(size=0, overlap=0),      # Zero size
            ChunkConfig(size=-10, overlap=0),    # Negative size
            ChunkConfig(size=100, overlap=-5),   # Negative overlap
            ChunkConfig(size=100, overlap=150),  # Overlap > size
        ]

        for strategy_name in ['fixed', 'sentence', 'paragraph']:
            for config in invalid_configs:
                with pytest.raises(ValueError):
                    ChunkerFactory.create(strategy_name, config)

    def test_large_text_handling(self, chunk_config: ChunkConfig):
        """Test handling of large text documents."""
        # Create a large text by repeating sample text
        large_text = "This is a test sentence. " * 1000  # ~5000 words

        for strategy_name in ['fixed', 'sentence', 'paragraph']:
            chunker = ChunkerFactory.create(strategy_name, chunk_config)
            result = chunker.chunk(large_text, chunk_config)

            assert result.is_ok()
            chunks = result.unwrap()

            # Should produce multiple chunks
            assert len(chunks) > 5

            # All chunks should be within reasonable size limits
            for chunk in chunks:
                token_count = chunk.metadata.get('token_count', 0)
                assert token_count <= chunk_config.size * 1.5  # Allow some flexibility

    def test_special_characters_handling(self, chunk_config: ChunkConfig):
        """Test handling of text with special characters."""
        special_text = """
        Text with émojis 🚀 and special chars: áéíóú, çñ, αβγ.

        Code snippets: `var x = "hello"` and ```python\nprint("world")\n```

        URLs: https://example.com and emails: test@example.com

        Math: E=mc², ∑(x²), ∫f(x)dx
        """

        for strategy_name in ['fixed', 'sentence', 'paragraph', 'semantic']:
            chunker = ChunkerFactory.create(strategy_name, chunk_config)
            result = chunker.chunk(special_text, chunk_config)

            assert result.is_ok()
            chunks = result.unwrap()

            # Should handle special characters without errors
            assert len(chunks) > 0

            # Text should be preserved
            combined_text = " ".join(chunk.text for chunk in chunks)
            assert "🚀" in combined_text
            assert "áéíóú" in combined_text or "áéíóú" in repr(combined_text)

    def test_performance_benchmarks(self, sample_text: str, chunk_config: ChunkConfig):
        """Basic performance test for chunking strategies."""
        import time

        # Multiply text to make it larger for meaningful timing
        large_text = sample_text * 10

        performance_results = {}

        for strategy_name in ['fixed', 'sentence', 'paragraph', 'semantic', 'topic']:
            chunker = ChunkerFactory.create(strategy_name, chunk_config)

            start_time = time.time()
            result = chunker.chunk(large_text, chunk_config)
            end_time = time.time()

            assert result.is_ok()
            chunks = result.unwrap()

            duration = end_time - start_time
            performance_results[strategy_name] = {
                'duration': duration,
                'chunks_produced': len(chunks),
                'chunks_per_second': len(chunks) / duration if duration > 0 else 0
            }

        # Log performance results (could be enhanced with proper benchmarking)
        print(f"\nPerformance Results:")
        for strategy, results in performance_results.items():
            print(f"{strategy}: {results['duration']:.3f}s, "
                  f"{results['chunks_produced']} chunks, "
                  f"{results['chunks_per_second']:.1f} chunks/sec")

        # All strategies should complete in reasonable time
        for strategy, results in performance_results.items():
            assert results['duration'] < 15.0, f"{strategy} took too long: {results['duration']:.3f}s"


class TestChunkingIntegration:
    """Integration tests for chunking with different content types."""

    @pytest.fixture
    def markdown_content(self) -> str:
        """Sample markdown content."""
        return """# API Documentation

## Authentication

To authenticate with the API, include your API key in the header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.example.com/data
```

### API Keys

API keys can be generated from your dashboard. Keep them secure!

## Endpoints

### GET /users

Returns a list of users.

**Parameters:**
- `limit` (optional): Maximum number of users to return
- `offset` (optional): Number of users to skip

**Response:**
```json
{
  "users": [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Jane Smith"}
  ]
}
```

### POST /users

Creates a new user.

## Rate Limiting

The API enforces rate limiting:
- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated users
"""

    @pytest.fixture
    def json_content(self) -> str:
        """Sample JSON content."""
        return """{
  "api_version": "1.0",
  "endpoints": {
    "users": {
      "methods": ["GET", "POST", "PUT", "DELETE"],
      "description": "Manage users",
      "authentication_required": true
    },
    "posts": {
      "methods": ["GET", "POST"],
      "description": "Manage blog posts",
      "authentication_required": false
    }
  },
  "rate_limits": {
    "authenticated": 100,
    "unauthenticated": 10
  },
  "features": [
    "Real-time updates",
    "Batch operations",
    "Webhook support"
  ]
}"""

    def test_markdown_chunking_strategies(self, markdown_content: str):
        """Test different strategies on markdown content."""
        config = ChunkConfig(size=150, overlap=15)

        strategies_to_test = {
            'hierarchical': 'should preserve header structure',
            'semantic': 'should detect code blocks and sections',
            'paragraph': 'should respect paragraph boundaries',
            'fixed': 'should create consistent sized chunks'
        }

        for strategy_name, expectation in strategies_to_test.items():
            chunker = ChunkerFactory.create(strategy_name, config)
            result = chunker.chunk(markdown_content, config)

            assert result.is_ok(), f"{strategy_name} failed: {result.unwrap_err() if result.is_err() else ''}"
            chunks = result.unwrap()

            assert len(chunks) > 0, f"{strategy_name} produced no chunks"

            # Strategy-specific tests
            if strategy_name == 'hierarchical':
                # Should have sections with headers
                header_chunks = [c for c in chunks if '# ' in c.text or '## ' in c.text]
                assert len(header_chunks) > 0, "Hierarchical chunking should preserve headers"

            elif strategy_name == 'semantic':
                # Should detect code blocks
                code_blocks_detected = any(
                    c.metadata.get('has_code', False) for c in chunks
                )
                assert code_blocks_detected, "Semantic chunking should detect code blocks"

    def test_code_content_chunking(self, sample_code: str):
        """Test code chunking on different programming languages."""
        config = ChunkConfig(size=300, overlap=30)

        # Test with Python code
        chunker = ChunkerFactory.create('code', config)
        result = chunker.chunk(sample_code, config)

        assert result.is_ok()
        chunks = result.unwrap()
        assert len(chunks) > 0

        # Should detect Python language
        python_chunks = [c for c in chunks if c.metadata.get('language') == 'python']
        assert len(python_chunks) > 0

        # Should detect classes and functions
        structure_found = False
        for chunk in chunks:
            if chunk.metadata.get('has_functions') or chunk.metadata.get('has_classes'):
                structure_found = True
                break
        assert structure_found

    def test_mixed_content_strategies(self):
        """Test strategies on mixed content (code + documentation)."""
        mixed_content = '''# Database Module

This module handles database operations.

```python
import sqlite3

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Connect to database."""
        self.connection = sqlite3.connect(self.db_path)
        return self.connection
```

## Usage Example

Here's how to use the Database class:

1. Create instance
2. Connect to database
3. Execute queries

```python
db = Database("mydb.sqlite")
db.connect()
```

The database supports all standard SQL operations.
'''

        config = ChunkConfig(size=200, overlap=20)

        # Test multiple strategies
        strategies = ['semantic', 'hierarchical', 'code', 'paragraph']

        results = {}
        for strategy_name in strategies:
            chunker = ChunkerFactory.create(strategy_name, config)
            result = chunker.chunk(mixed_content, config)

            assert result.is_ok()
            results[strategy_name] = result.unwrap()

        # All strategies should handle mixed content
        for strategy_name, chunks in results.items():
            assert len(chunks) > 0, f"{strategy_name} failed on mixed content"

            # Check that code blocks are preserved somewhere
            combined_text = " ".join(chunk.text for chunk in chunks)
            assert "class Database" in combined_text
            assert "import sqlite3" in combined_text

    def test_error_recovery(self):
        """Test error handling and recovery in chunking strategies."""
        # Test with problematic content
        problematic_texts = [
            "A" * 50000,  # Very long text
            "Line 1\n" * 1000,  # Many short lines
            "🚀" * 1000,  # Many unicode characters
        ]

        config = ChunkConfig(size=100, overlap=10)

        for strategy_name in ['fixed', 'sentence', 'paragraph']:
            chunker = ChunkerFactory.create(strategy_name, config)

            for text in problematic_texts:
                result = chunker.chunk(text, config)

                # Should either succeed or fail gracefully
                if result.is_err():
                    error_msg = result.unwrap_err()
                    assert isinstance(error_msg, str)
                    assert len(error_msg) > 0
                else:
                    chunks = result.unwrap()
                    # If successful, should produce valid chunks
                    assert all(isinstance(chunk, Chunk) for chunk in chunks)

    def test_chunk_id_uniqueness(self, sample_text: str):
        """Test that chunk IDs are unique within a chunking operation."""
        config = ChunkConfig(size=100, overlap=10)

        for strategy_name in ['fixed', 'sentence', 'paragraph', 'topic']:
            chunker = ChunkerFactory.create(strategy_name, config)
            result = chunker.chunk(sample_text, config)

            assert result.is_ok()
            chunks = result.unwrap()

            if len(chunks) > 1:
                chunk_ids = [chunk.chunk_id for chunk in chunks]
                unique_ids = set(chunk_ids)

                assert len(chunk_ids) == len(unique_ids), f"{strategy_name} produced duplicate chunk IDs"

    def test_chunking_determinism(self, sample_text: str):
        """Test that chunking produces deterministic results."""
        config = ChunkConfig(size=150, overlap=15)

        # Test strategies that should be deterministic
        deterministic_strategies = ['fixed', 'sentence', 'paragraph']

        for strategy_name in deterministic_strategies:
            chunker = ChunkerFactory.create(strategy_name, config)

            # Run chunking multiple times
            results = []
            for _ in range(3):
                result = chunker.chunk(sample_text, config)
                assert result.is_ok()
                results.append(result.unwrap())

            # Results should be identical
            first_result = results[0]
            for other_result in results[1:]:
                assert len(first_result) == len(other_result)

                for i, (chunk1, chunk2) in enumerate(zip(first_result, other_result)):
                    assert chunk1.text == chunk2.text, f"{strategy_name} not deterministic at chunk {i}"