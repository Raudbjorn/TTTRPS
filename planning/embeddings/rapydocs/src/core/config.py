"""
Unified Configuration System for MBED
Using pydantic-settings for typed, 12-factor config with proper precedence:
CLI flags > env vars > .env > pyproject.toml defaults
"""

from __future__ import annotations
import sys
import pathlib
import tomllib
from enum import Enum
from typing import Optional, Any, Dict, List
import logging

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

# ---------- Enums ----------

class HardwareBackend(str, Enum):
    """Available hardware acceleration backends"""
    cuda = "cuda"
    openvino = "openvino"
    mps = "mps"
    cpu = "cpu"
    auto = "auto"

class VectorDatabase(str, Enum):
    """Supported vector database backends"""
    chromadb = "chromadb"
    postgres = "postgres"
    faiss = "faiss"
    qdrant = "qdrant"

class ChunkingStrategy(str, Enum):
    """Text chunking strategies"""
    fixed = "fixed"
    sentence = "sentence"
    paragraph = "paragraph"
    semantic = "semantic"
    hierarchical = "hierarchical"
    topic = "topic"

class EmbeddingModel(str, Enum):
    """Supported embedding models"""
    nomic_embed_text = "nomic-embed-text"
    mxbai_embed_large = "mxbai-embed-large"
    all_minilm_l6_v2 = "all-MiniLM-L6-v2"
    bge_m3 = "bge-m3"
    e5_large = "e5-large"

class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# ---------- PyProject Defaults ----------

class PyProjectDefaults(BaseModel):
    """Optional defaults from [tool.mbed] in pyproject.toml"""
    # Core settings
    hardware: HardwareBackend | None = None
    model: str | None = None
    database: VectorDatabase | None = None
    
    # Processing settings
    chunk_strategy: ChunkingStrategy | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    batch_size: int | None = None
    workers: int | None = None
    
    # Paths
    db_path: str | None = None
    state_dir: str | None = None
    log_dir: str | None = None
    
    # Features
    enable_gpu: bool | None = None
    enable_preprocessing: bool | None = None
    enable_qa: bool | None = None
    enable_summary: bool | None = None
    normalize_embeddings: bool | None = None
    
    # Output
    output_format: str | None = None
    verbose: bool | None = None
    debug: bool | None = None
    quiet: bool | None = None

def load_pyproject_defaults() -> dict:
    """Load defaults from pyproject.toml if it exists"""
    pp = pathlib.Path("pyproject.toml")
    if not pp.exists():
        return {}
    
    try:
        with pp.open("rb") as f:
            data = tomllib.load(f)
        tool = data.get("tool", {}).get("mbed", {})
        defaults = PyProjectDefaults(**tool)
        return defaults.model_dump(exclude_none=True)
    except Exception as e:
        logger.debug(f"Could not load pyproject.toml defaults: {e}")
        return {}

# ---------- Main Settings ----------

class MBEDSettings(BaseSettings):
    """Main configuration for MBED with proper precedence"""
    
    # Core settings
    hardware: HardwareBackend = Field(
        default=HardwareBackend.auto,
        description="Hardware acceleration backend"
    )
    model: str = Field(
        default="nomic-embed-text",
        description="Embedding model to use"
    )
    database: VectorDatabase = Field(
        default=VectorDatabase.chromadb,
        description="Vector database backend"
    )
    
    # Processing settings
    chunk_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.fixed,
        description="Text chunking strategy"
    )
    chunk_size: int = Field(
        default=512,
        ge=64,
        le=8192,
        description="Chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=128,
        ge=0,
        le=512,
        description="Overlap between chunks"
    )
    batch_size: int = Field(
        default=128,
        ge=1,
        le=1024,
        description="Processing batch size"
    )
    workers: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Number of parallel workers"
    )
    
    # Paths
    db_path: pathlib.Path = Field(
        default=pathlib.Path(".mbed/db"),
        description="Vector database storage path"
    )
    state_dir: pathlib.Path = Field(
        default=pathlib.Path(".mbed/state"),
        description="State and checkpoint directory"
    )
    log_dir: pathlib.Path | None = Field(
        default=None,
        description="Log file directory (None = no file logging)"
    )
    cache_dir: pathlib.Path = Field(
        default=pathlib.Path(".mbed/cache"),
        description="Model cache directory"
    )
    
    # Database connections
    postgres_connection: SecretStr | None = Field(
        default=None,
        description="PostgreSQL connection string"
    )
    qdrant_url: str | None = Field(
        default=None,
        description="Qdrant server URL"
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None,
        description="Qdrant API key"
    )
    
    # Model providers
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key (for OpenAI embeddings)"
    )
    huggingface_token: SecretStr | None = Field(
        default=None,
        description="HuggingFace token for private models"
    )
    
    # Features
    enable_gpu: bool = Field(
        default=True,
        description="Enable GPU acceleration if available"
    )
    enable_preprocessing: bool = Field(
        default=False,
        description="Enable LLM preprocessing"
    )
    preprocessing_model: str = Field(
        default="llama3.2:latest",
        description="Model for preprocessing"
    )
    enable_qa: bool = Field(
        default=False,
        description="Generate Q&A pairs"
    )
    enable_summary: bool = Field(
        default=False,
        description="Generate summaries"
    )
    normalize_embeddings: bool = Field(
        default=True,
        description="L2-normalize embeddings"
    )
    
    # Resume/state
    resume: bool = Field(
        default=False,
        description="Resume from last checkpoint"
    )
    clear_state: bool = Field(
        default=False,
        description="Clear saved state"
    )
    no_state: bool = Field(
        default=False,
        description="Disable state tracking"
    )
    
    # Output settings
    output_format: str = Field(
        default="jsonl",
        description="Output format (jsonl|parquet|npy)"
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level"
    )
    verbose: bool = Field(
        default=False,
        description="Verbose output"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode with detailed output"
    )
    quiet: bool = Field(
        default=False,
        description="Suppress non-essential output"
    )
    color: bool = Field(
        default=True,
        description="Use colored output"
    )
    
    # Performance tuning
    max_memory_gb: float | None = Field(
        default=None,
        description="Maximum memory usage in GB"
    )
    gpu_memory_fraction: float = Field(
        default=0.9,
        ge=0.1,
        le=1.0,
        description="Fraction of GPU memory to use"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="MBED_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap is less than chunk size"""
        chunk_size = info.data.get('chunk_size', 512)
        if v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})")
        return v
    
    @model_validator(mode='after')
    def validate_paths(self) -> 'MBEDSettings':
        """Create directories if they don't exist"""
        for path_attr in ['db_path', 'state_dir', 'cache_dir']:
            path = getattr(self, path_attr)
            if path and not path.exists():
                path.mkdir(parents=True, exist_ok=True)
        
        if self.log_dir and not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        return self
    
    @model_validator(mode='after')
    def adjust_for_hardware(self) -> 'MBEDSettings':
        """Adjust settings based on hardware backend"""
        if self.hardware == HardwareBackend.cpu:
            # CPU optimizations
            if self.batch_size > 32:
                self.batch_size = 32
            if self.workers > 4:
                self.workers = 4
        elif self.hardware == HardwareBackend.cuda:
            # CUDA optimizations
            if self.batch_size < 256:
                self.batch_size = 256
        elif self.hardware == HardwareBackend.openvino:
            # OpenVINO optimizations
            if self.batch_size > 128:
                self.batch_size = 128
        
        return self
    
    def get_model_dimensions(self) -> int:
        """Get embedding dimensions for the selected model"""
        dimensions = {
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            "all-MiniLM-L6-v2": 384,
            "bge-m3": 1024,
            "e5-large": 1024,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return dimensions.get(self.model, 768)
    
    def get_optimal_batch_size(self) -> int:
        """Get optimal batch size for current hardware"""
        if self.hardware == HardwareBackend.cuda:
            return min(512, self.batch_size)
        elif self.hardware == HardwareBackend.openvino:
            return min(128, self.batch_size)
        elif self.hardware == HardwareBackend.mps:
            return min(256, self.batch_size)
        else:  # CPU
            return min(32, self.batch_size)
    
    def to_dict(self) -> dict:
        """Export settings as dictionary"""
        return self.model_dump(exclude_none=True, exclude={'postgres_connection', 'openai_api_key', 'huggingface_token', 'qdrant_api_key'})
    
    def print_config(self, show_secrets: bool = False):
        """Pretty print configuration using rich"""
        from rich.table import Table
        
        table = Table(title="MBED Configuration", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_column("Source", style="dim")
        
        # Determine source of each setting
        pyproject_defaults = load_pyproject_defaults()
        
        for field_name, field_value in self.model_dump().items():
            if field_value is None:
                continue
            
            # Hide secrets unless requested
            if isinstance(field_value, SecretStr) and not show_secrets:
                display_value = "***hidden***"
            elif isinstance(field_value, pathlib.Path):
                display_value = str(field_value)
            else:
                display_value = str(field_value)
            
            # Determine source
            if field_name in pyproject_defaults:
                source = "pyproject.toml"
            elif f"MBED_{field_name.upper()}" in os.environ:
                source = "environment"
            else:
                source = "default"
            
            table.add_row(field_name.replace('_', ' ').title(), display_value, source)
        
        console.print(table)

# ---------- Settings Resolution ----------

def resolve_settings(cli_overrides: dict | None = None) -> MBEDSettings:
    """
    Resolve settings with proper precedence:
    CLI overrides > env vars > .env file > pyproject.toml > defaults
    """
    # Load pyproject defaults
    pyproject_defaults = load_pyproject_defaults()
    
    # Create base settings with pyproject defaults
    settings = MBEDSettings(**pyproject_defaults)
    
    # Apply CLI overrides if provided
    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)
    
    # Validate final configuration
    if settings.debug:
        settings.log_level = LogLevel.DEBUG
    elif settings.quiet:
        settings.log_level = LogLevel.WARNING
    elif settings.verbose:
        settings.log_level = LogLevel.INFO
    
    return settings

# ---------- Global Settings Instance ----------

_settings: MBEDSettings | None = None

def get_settings() -> MBEDSettings:
    """Get or create the global settings instance"""
    global _settings
    if _settings is None:
        _settings = resolve_settings()
    return _settings

def set_settings(settings: MBEDSettings):
    """Set the global settings instance"""
    global _settings
    _settings = settings

# ---------- Config File Management ----------

import os
import yaml

def save_config(settings: MBEDSettings, path: pathlib.Path | None = None):
    """Save current configuration to YAML file"""
    path = path or pathlib.Path(".mbed/config.yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    config_dict = settings.to_dict()
    with path.open("w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=True)
    
    logger.info(f"Configuration saved to {path}")

def load_config(path: pathlib.Path) -> MBEDSettings:
    """Load configuration from YAML file"""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with path.open() as f:
        config_dict = yaml.safe_load(f)
    
    return MBEDSettings(**config_dict)