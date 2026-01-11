"""
Ollama backend for embeddings
"""

import json
import logging
import numpy as np
from typing import List, Optional, Dict, Any
import requests
from time import sleep

from mbed.backends.base import EmbeddingBackend, BackendFactory
from mbed.core.hardware import HardwareType
from mbed.core.config import MBEDSettings

logger = logging.getLogger(__name__)


class OllamaBackend(EmbeddingBackend):
    """Ollama-based embedding backend"""

    def __init__(self, config: MBEDSettings):
        super().__init__(config)
        self.base_url = "http://localhost:11434"
        self.model = None
        self.embedding_dim = None

    def initialize(self) -> None:
        """Initialize Ollama backend"""
        if not self.is_available():
            raise RuntimeError("Ollama is not available. Please ensure Ollama is running.")

        # Map model names to Ollama models
        model_map = {
            "nomic-embed-text": "nomic-embed-text",
            "mxbai-embed-large": "mxbai-embed-large",
            "all-minilm": "all-minilm",
        }

        self.model = model_map.get(self.model_name, "nomic-embed-text")
        logger.info(f"Using Ollama model: {self.model}")

        # Pull model if needed
        self._ensure_model()

        # Get embedding dimension
        test_embedding = self._generate_embedding("test")
        self.embedding_dim = len(test_embedding)
        logger.info(f"Embedding dimension: {self.embedding_dim}")

    def _ensure_model(self) -> None:
        """Ensure model is available in Ollama"""
        try:
            # Check if model exists
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]

                if self.model not in model_names and f"{self.model}:latest" not in model_names:
                    logger.info(f"Pulling model {self.model}...")
                    pull_response = requests.post(
                        f"{self.base_url}/api/pull",
                        json={"name": self.model},
                        stream=True
                    )

                    # Stream pull progress
                    for line in pull_response.iter_lines():
                        if line:
                            data = json.loads(line)
                            if "status" in data:
                                logger.debug(f"Pull status: {data['status']}")
        except Exception as e:
            logger.warning(f"Could not ensure model availability: {e}")

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )

            if response.status_code == 200:
                return response.json()["embedding"]
            else:
                raise RuntimeError(f"Ollama API error: {response.status_code}")

        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Ollama. Is it running?")

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        if self.model is None:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        # Process texts
        processed_texts = self.preprocess_texts(texts)

        embeddings = []
        for text in processed_texts:
            # Add retry logic for resilience
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    embedding = self._generate_embedding(text)
                    embeddings.append(embedding)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to generate embedding after {max_retries} attempts: {e}")
                        # Propagate the failure instead of using a zero vector
                        raise RuntimeError(f"Failed to generate embedding for a document after {max_retries} attempts") from e
                    else:
                        sleep(0.5 * (attempt + 1))  # Exponential backoff

        return np.array(embeddings)

    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension"""
        if self.embedding_dim is None:
            raise RuntimeError("Backend not initialized")
        return self.embedding_dim

    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get backend information"""
        info = {
            'backend': 'Ollama',
            'base_url': self.base_url,
            'model': self.model or 'not initialized',
            'embedding_dim': self.embedding_dim or 'unknown',
        }

        # Try to get available models
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                info['available_models'] = [m["name"] for m in models]
        except:
            info['available_models'] = []

        return info

    def preprocess_texts(self, texts: List[str]) -> List[str]:
        """Preprocess texts before embedding"""
        processed = []
        for text in texts:
            # Clean up whitespace
            text = ' '.join(text.split())

            # Truncate if too long (Ollama has context limits)
            max_length = 8192
            if len(text) > max_length:
                text = text[:max_length]
                logger.debug(f"Truncated text to {max_length} characters")

            processed.append(text)

        return processed


# Register with factory
BackendFactory.register(HardwareType.OLLAMA, OllamaBackend)