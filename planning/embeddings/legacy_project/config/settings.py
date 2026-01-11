"""Embedding generation settings and configuration."""

from pathlib import Path
from typing import Optional

from pydantic import Field
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Embedding generation settings loaded from environment variables."""

    # Application
    app_name: str = Field(default="Embedding Generator", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # Vector Database
    chroma_db_path: Path = Field(default=Path("./data/chromadb"), env="CHROMA_DB_PATH")
    chroma_collection_prefix: str = Field(default="embeddings_", env="CHROMA_COLLECTION_PREFIX")

    # Document Processing
    max_chunk_size: int = Field(default=1000, env="MAX_CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    enable_adaptive_learning: bool = Field(default=True, env="ENABLE_ADAPTIVE_LEARNING")

    # Search
    default_search_results: int = Field(default=5, env="DEFAULT_SEARCH_RESULTS")
    enable_hybrid_search: bool = Field(default=True, env="ENABLE_HYBRID_SEARCH")
    semantic_weight: float = Field(default=0.7, env="SEMANTIC_WEIGHT")
    keyword_weight: float = Field(default=0.3, env="KEYWORD_WEIGHT")

    # Embeddings
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    use_ollama_embeddings: bool = Field(default=False, env="USE_OLLAMA_EMBEDDINGS")
    ollama_embedding_model: str = Field(default="nomic-embed-text", env="OLLAMA_EMBEDDING_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")

    # Cache
    cache_dir: Path = Field(default=Path("./data/cache"), env="CACHE_DIR")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    search_cache_size: int = Field(default=1000, env="SEARCH_CACHE_SIZE")
    cache_max_memory_mb: int = Field(default=100, env="CACHE_MAX_MEMORY_MB")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialize settings."""
        super().__init__(**kwargs)
        
        # Validate weights sum to 1.0
        if abs(self.semantic_weight + self.keyword_weight - 1.0) > 0.01:
            raise ValueError(
                f"Semantic weight ({self.semantic_weight}) + Keyword weight ({self.keyword_weight}) must equal 1.0"
            )
    
    def create_directories(self):
        """Create necessary directories. Should be called at application startup."""
        self.chroma_db_path.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()