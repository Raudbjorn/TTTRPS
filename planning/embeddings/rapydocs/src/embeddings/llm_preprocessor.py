"""
LLM-based data pre-processor for enhanced embeddings generation.

This module provides intelligent pre-processing of structured data (JSON, XML, etc.)
using Large Language Models to transform raw data into semantically rich, human-readable
text that produces superior embeddings for RAG applications.

Key Features:
- Ollama integration for local LLM inference
- OpenVINO acceleration support for Intel hardware
- Semantic enrichment of structured data
- Intelligent key expansion and description
- Natural language summarization
- Question-answer pair generation
"""

import json
import re
import pickle
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

try:
    from optimum.intel.openvino import OVModelForCausalLM, OVModelForFeatureExtraction
    from transformers import AutoTokenizer, pipeline
    OPENVINO_AVAILABLE = True
except ImportError:
    OPENVINO_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing mode for LLM operations"""
    OLLAMA = "ollama"
    OPENVINO = "openvino"
    FALLBACK = "fallback"


@dataclass
class PreprocessorConfig:
    """Configuration for LLM preprocessor"""
    # Model settings
    ollama_model: str = "llama3"
    ollama_embedding_model: str = "mxbai-embed-large"
    openvino_model: str = "meta-llama/Llama-2-7b-chat-hf"
    openvino_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Processing settings
    chunk_size: int = 512
    chunk_overlap: int = 100
    max_context_length: int = 2048
    max_new_tokens: int = 512  # Separate from max_context_length for efficiency
    temperature: float = 0.3
    top_p: float = 0.9

    # Performance settings
    batch_size: int = 4
    max_workers: int = 4
    timeout_seconds: int = 60
    cache_enabled: bool = True
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "llm_preprocessor")

    # Enhancement settings
    expand_keys: bool = True
    generate_summaries: bool = True
    create_qa_pairs: bool = False
    add_semantic_context: bool = True

    # Hardware settings
    device: str = "CPU"  # CPU, GPU for OpenVINO
    ollama_host: str = "http://localhost:11434"


class LLMPreprocessor:
    """Intelligent pre-processor using LLMs for data enrichment"""

    def __init__(self, config: Optional[PreprocessorConfig] = None):
        """Initialize the LLM preprocessor"""
        self.config = config or PreprocessorConfig()
        self.mode = self._detect_processing_mode()
        self.models_loaded = False
        self._cache = {}
        self._load_cache()

        # Initialize based on available backends
        if self.mode == ProcessingMode.OPENVINO:
            self._init_openvino()
        elif self.mode == ProcessingMode.OLLAMA:
            self._init_ollama()

        # Setup cache directory
        if self.config.cache_enabled:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LLM Preprocessor initialized with mode: {self.mode.value}")

    def _detect_processing_mode(self) -> ProcessingMode:
        """Detect available processing backends"""
        if OPENVINO_AVAILABLE and self.config.device in ["CPU", "GPU"]:
            return ProcessingMode.OPENVINO
        elif OLLAMA_AVAILABLE:
            return ProcessingMode.OLLAMA
        else:
            logger.warning("No LLM backend available, using fallback mode")
            return ProcessingMode.FALLBACK

    def _init_ollama(self):
        """Initialize Ollama backend"""
        if not OLLAMA_AVAILABLE:
            return

        try:
            # Test connection to Ollama
            response = ollama.list()
            available_models = [m['name'] for m in response.get('models', [])]

            if self.config.ollama_model not in available_models:
                logger.warning(f"Model {self.config.ollama_model} not found in Ollama")
                logger.info(f"Available models: {available_models}")

            self.models_loaded = True
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            self.mode = ProcessingMode.FALLBACK

    def _init_openvino(self):
        """Initialize OpenVINO backend"""
        if not OPENVINO_AVAILABLE:
            return

        try:
            model_dir = self.config.cache_dir / "openvino_models" / "llm"
            embedding_model_dir = self.config.cache_dir / "openvino_models" / "embeddings"

            # Load or convert LLM
            if model_dir.exists():
                self.ov_model = OVModelForCausalLM.from_pretrained(
                    model_dir,
                    device=self.config.device
                )
                self.ov_tokenizer = AutoTokenizer.from_pretrained(model_dir)
            else:
                logger.info(f"Converting {self.config.openvino_model} to OpenVINO format...")
                self.ov_model = OVModelForCausalLM.from_pretrained(
                    self.config.openvino_model,
                    export=True,
                    device=self.config.device
                )
                self.ov_tokenizer = AutoTokenizer.from_pretrained(self.config.openvino_model)

                # Save for future use
                model_dir.mkdir(parents=True, exist_ok=True)
                self.ov_model.save_pretrained(model_dir)
                self.ov_tokenizer.save_pretrained(model_dir)

            # Load embedding model
            if embedding_model_dir.exists():
                self.ov_embedding_model = OVModelForFeatureExtraction.from_pretrained(
                    embedding_model_dir,
                    device=self.config.device
                )
                self.ov_embedding_tokenizer = AutoTokenizer.from_pretrained(embedding_model_dir)
            else:
                logger.info(f"Converting {self.config.openvino_embedding_model} to OpenVINO format...")
                self.ov_embedding_model = OVModelForFeatureExtraction.from_pretrained(
                    self.config.openvino_embedding_model,
                    export=True,
                    device=self.config.device
                )
                self.ov_embedding_tokenizer = AutoTokenizer.from_pretrained(
                    self.config.openvino_embedding_model
                )

                embedding_model_dir.mkdir(parents=True, exist_ok=True)
                self.ov_embedding_model.save_pretrained(embedding_model_dir)
                self.ov_embedding_tokenizer.save_pretrained(embedding_model_dir)

            self.models_loaded = True
            logger.info("OpenVINO models loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenVINO: {e}")
            self.mode = ProcessingMode.OLLAMA if OLLAMA_AVAILABLE else ProcessingMode.FALLBACK


    def _load_cache(self):
        """Load cache from disk if available"""
        if not self.config.cache_enabled:
            return

        cache_file = self.config.cache_dir / "preprocessor_cache.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    self._cache = pickle.load(f)
                logger.info(f"Loaded {len(self._cache)} cached entries")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}

    def _save_cache(self):
        """Save cache to disk"""
        if not self.config.cache_enabled or not self._cache:
            return

        cache_file = self.config.cache_dir / "preprocessor_cache.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def preprocess_json(self, json_data: Union[str, Dict, List]) -> str:
        """
        Transform JSON data into semantically rich text for embeddings.

        Args:
            json_data: JSON string, dictionary, or list

        Returns:
            Enhanced text representation of the JSON data
        """
        # Parse JSON if string
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                return json_data
        else:
            data = json_data

        # Generate cache key
        cache_key = self._generate_cache_key(data)

        # Check file-based cache first
        if self.config.cache_enabled:
            cache_file = self.config.cache_dir / f"{cache_key}.txt"
            if cache_file.exists():
                try:
                    return cache_file.read_text()
                except Exception as e:
                    logger.warning(f"Failed to read cache file: {e}")

        # Check memory cache as fallback
        if self.config.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        # Process based on mode
        if self.mode == ProcessingMode.OLLAMA:
            result = self._preprocess_with_ollama(data)
        elif self.mode == ProcessingMode.OPENVINO:
            result = self._preprocess_with_openvino(data)
        else:
            result = self._preprocess_fallback(data)

        # Cache result to both memory and file
        if self.config.cache_enabled:
            self._cache[cache_key] = result
            # Save to file cache
            cache_file = self.config.cache_dir / f"{cache_key}.txt"
            try:
                cache_file.write_text(result)
            except Exception as e:
                logger.warning(f"Failed to write cache file: {e}")
            # Also update pickle cache for backwards compatibility
            self._save_cache()

        return result

    def _generate_cache_key(self, data: Any) -> str:
        """Generate cache key for data"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _preprocess_with_ollama(self, data: Dict) -> str:
        """Preprocess data using Ollama"""
        if not OLLAMA_AVAILABLE or not self.models_loaded:
            return self._preprocess_fallback(data)

        prompt = self._create_preprocessing_prompt(data)

        try:
            response = ollama.generate(
                model=self.config.ollama_model,
                prompt=prompt,
                options={
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "num_predict": self.config.max_new_tokens  # Use separate config for efficiency
                }
            )

            return response['response']

        except Exception as e:
            logger.error(f"Ollama preprocessing failed: {e}")
            return self._preprocess_fallback(data)

    def _preprocess_with_openvino(self, data: Dict) -> str:
        """Preprocess data using OpenVINO-accelerated model"""
        if not OPENVINO_AVAILABLE or not self.models_loaded:
            return self._preprocess_fallback(data)

        prompt = self._create_preprocessing_prompt(data)

        try:
            # Tokenize input
            # Ensure device is properly set
            device = getattr(self.ov_model, 'device', 'cpu')
            inputs = self.ov_tokenizer(prompt, return_tensors="pt")
            # Only move to device if it's not CPU (OpenVINO handles this internally)
            if device != 'cpu' and hasattr(inputs, 'to'):
                inputs = inputs.to(device)

            # Generate response with optimized token count
            outputs = self.ov_model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,  # Use separate config for efficiency
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                do_sample=True
            )

            # Decode response
            response = self.ov_tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

            # Extract generated text (remove prompt)
            if prompt in response:
                response = response.replace(prompt, "").strip()

            return response

        except Exception as e:
            logger.error(f"OpenVINO preprocessing failed: {e}")
            return self._preprocess_fallback(data)

    def _create_preprocessing_prompt(self, data: Dict) -> str:
        """Create prompt for LLM preprocessing"""
        json_str = json.dumps(data, indent=2)

        prompt_parts = [
            "Transform the following JSON data into a clear, descriptive text suitable for semantic search.",
            "Guidelines:"
        ]

        guidelines = []
        if self.config.expand_keys:
            guidelines.append("- Expand abbreviated keys into descriptive names")
        if self.config.generate_summaries:
            guidelines.append("- Provide a brief summary of the overall data")
        if self.config.add_semantic_context:
            guidelines.append("- Add semantic context to explain relationships")
        if self.config.create_qa_pairs:
            guidelines.append("- Include relevant questions this data answers")

        prompt_parts.extend(guidelines)
        prompt_parts.append(f"\nJSON Data:\n```json\n{json_str}\n```\n\nDescriptive text:")

        return "\n".join(prompt_parts)

    def _preprocess_fallback(self, data: Any) -> str:
        """Fallback preprocessing without LLM"""
        if isinstance(data, dict):
            return self._dict_to_text(data)
        elif isinstance(data, list):
            return self._list_to_text(data)
        else:
            return str(data)

    def _dict_to_text(self, data: Dict, indent: int = 0) -> str:
        """Convert dictionary to readable text"""
        lines = []
        indent_str = "  " * indent

        for key, value in data.items():
            # Expand common abbreviations
            expanded_key = self._expand_key(key) if self.config.expand_keys else key

            if isinstance(value, dict):
                lines.append(f"{indent_str}{expanded_key}:")
                lines.append(self._dict_to_text(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}{expanded_key}:")
                lines.append(self._list_to_text(value, indent + 1))
            else:
                lines.append(f"{indent_str}{expanded_key}: {value}")

        return "\n".join(lines)

    def _list_to_text(self, data: List, indent: int = 0) -> str:
        """Convert list to readable text"""
        lines = []
        indent_str = "  " * indent

        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"{indent_str}Item {i}:")
                lines.append(self._dict_to_text(item, indent + 1))
            elif isinstance(item, list):
                lines.append(f"{indent_str}Item {i}:")
                lines.append(self._list_to_text(item, indent + 1))
            else:
                lines.append(f"{indent_str}- {item}")

        return "\n".join(lines)

    def _expand_key(self, key: str) -> str:
        """Expand common abbreviations in keys"""
        expansions = {
            "id": "identifier",
            "cust": "customer",
            "prod": "product",
            "qty": "quantity",
            "addr": "address",
            "desc": "description",
            "config": "configuration",
            "auth": "authentication",
            "admin": "administrator",
            "dept": "department",
            "mgr": "manager",
            "org": "organization",
            "req": "request",
            "res": "response",
            "err": "error",
            "msg": "message",
            "ctx": "context",
            "ref": "reference",
            "tx": "transaction",
            "db": "database",
            "api": "application programming interface",
            "url": "uniform resource locator",
            "uri": "uniform resource identifier",
            "http": "hypertext transfer protocol",
            "json": "javascript object notation",
            "xml": "extensible markup language"
        }

        # Check exact match
        lower_key = key.lower()
        if lower_key in expansions:
            return expansions[lower_key]

        # Check if key ends with common abbreviations
        for abbr, expansion in expansions.items():
            if lower_key.endswith(f"_{abbr}") or lower_key.endswith(abbr):
                expanded = key[:-len(abbr)] + expansion
                return expanded.replace("_", " ").title()

        # Convert snake_case or camelCase to readable
        if "_" in key:
            return key.replace("_", " ").title()

        # Handle camelCase
        spaced = re.sub(r'([A-Z])', r' \1', key).strip()
        return spaced.title() if spaced != key else key

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk preprocessed text with overlap for embeddings.

        Args:
            text: Preprocessed text to chunk

        Returns:
            List of text chunks with overlap
        """
        words = text.split()
        chunks = []

        start = 0
        while start < len(words):
            end = start + self.config.chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            # Move start with overlap
            start += self.config.chunk_size - self.config.chunk_overlap
            if start >= len(words):
                break

        return chunks

    def generate_embeddings(self, chunks: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for text chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of embedding vectors
        """
        if self.mode == ProcessingMode.OLLAMA:
            return self._generate_embeddings_ollama(chunks)
        elif self.mode == ProcessingMode.OPENVINO:
            return self._generate_embeddings_openvino(chunks)
        else:
            # Return dummy embeddings for fallback
            return [np.random.randn(384) for _ in chunks]

    def _generate_embeddings_ollama(self, chunks: List[str]) -> List[np.ndarray]:
        """Generate embeddings using Ollama"""
        if not OLLAMA_AVAILABLE:
            return []

        embeddings = []

        for chunk in chunks:
            try:
                response = ollama.embeddings(
                    model=self.config.ollama_embedding_model,
                    prompt=chunk
                )
                embeddings.append(np.array(response['embedding']))
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                embeddings.append(np.zeros(1024))  # Default size

        return embeddings

    def _generate_embeddings_openvino(self, chunks: List[str]) -> List[np.ndarray]:
        """Generate embeddings using OpenVINO"""
        if not OPENVINO_AVAILABLE or not self.models_loaded:
            return []

        # Create pipeline
        pipe = pipeline(
            "feature-extraction",
            model=self.ov_embedding_model,
            tokenizer=self.ov_embedding_tokenizer
        )

        # Generate embeddings
        embeddings_output = pipe(chunks)

        # Mean pooling
        embeddings = []
        for chunk_embedding in embeddings_output:
            # Average token embeddings
            mean_embedding = np.mean(chunk_embedding[0], axis=0)
            embeddings.append(mean_embedding)

        return embeddings

    def process_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """
        Process a file with LLM preprocessing and embedding generation.

        Args:
            filepath: Path to the file
            content: File content

        Returns:
            Dictionary with processed text and embeddings
        """
        # Determine if content needs preprocessing
        if self._is_structured_data(filepath, content):
            # Preprocess with LLM
            processed_text = self.preprocess_json(content)
        else:
            processed_text = content

        # Chunk the text
        chunks = self.chunk_text(processed_text)

        # Generate embeddings
        embeddings = self.generate_embeddings(chunks)

        return {
            "original": content,
            "processed": processed_text,
            "chunks": chunks,
            "embeddings": embeddings,
            "metadata": {
                "filepath": filepath,
                "processing_mode": self.mode.value,
                "num_chunks": len(chunks),
                "timestamp": time.time()
            }
        }

    def _is_structured_data(self, filepath: str, content: str) -> bool:
        """Check if content is structured data requiring preprocessing"""
        path = Path(filepath)

        # Check file extension
        structured_extensions = {'.json', '.jsonl', '.xml', '.yaml', '.yml', '.toml'}
        if path.suffix.lower() in structured_extensions:
            return True

        # Try parsing as JSON
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        return False

    def batch_process(self, files: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Process multiple files in batch with parallel processing.

        Args:
            files: List of (filepath, content) tuples

        Returns:
            List of processed results
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self.process_file, filepath, content): (filepath, content)
                for filepath, content in files
            }

            for future in as_completed(futures):
                filepath, content = futures[future]
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {filepath}: {e}")
                    results.append({
                        "error": str(e),
                        "filepath": filepath
                    })

        return results


def main():
    """Example usage of LLM preprocessor"""
    # Sample JSON data
    sample_json = {
        "doc_id": "inv_789123",
        "cust_details": {
            "cust_id": "CUST-001",
            "name": "John Doe",
            "contact": {
                "email": "john.doe@example.com",
                "phone": "123-456-7890"
            }
        },
        "order_items": [
            {
                "prod_id": "PROD-A1",
                "prod_name": "Laptop",
                "qty": 1,
                "price_per_unit": 1200
            },
            {
                "prod_id": "PROD-B2",
                "prod_name": "Mouse",
                "qty": 1,
                "price_per_unit": 25
            }
        ],
        "ship_info": {
            "addr": "123 Main St, Anytown, USA",
            "ship_date": "2025-09-15"
        },
        "is_paid": True
    }

    # Initialize preprocessor
    config = PreprocessorConfig(
        expand_keys=True,
        generate_summaries=True,
        add_semantic_context=True
    )
    preprocessor = LLMPreprocessor(config)

    # Process JSON
    processed_text = preprocessor.preprocess_json(sample_json)
    print("Processed Text:")
    print(processed_text)
    print("\n" + "="*50 + "\n")

    # Chunk text
    chunks = preprocessor.chunk_text(processed_text)
    print(f"Generated {len(chunks)} chunks")
    print(f"First chunk:\n{chunks[0]}")
    print("\n" + "="*50 + "\n")

    # Generate embeddings
    embeddings = preprocessor.generate_embeddings(chunks[:2])  # Just first 2 for demo
    if embeddings:
        print(f"Generated {len(embeddings)} embeddings")
        print(f"Embedding dimension: {len(embeddings[0])}")
        print(f"First 5 dimensions: {embeddings[0][:5]}")


if __name__ == "__main__":
    main()