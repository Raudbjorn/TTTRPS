"""
Configuration management with pydantic-settings

Precedence order (highest to lowest):
1. CLI arguments
2. Environment variables (MBED_* prefix)
3. .env file
4. pyproject.toml [tool.mbed] section
5. Default values
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

try:
    from pydantic import validator
except ImportError:
    # Pydantic v2 uses field_validator
    validator = field_validator

PYDANTIC_V2 = True  # Assuming v2 since pydantic-settings is used

class HardwareBackend(str, Enum):
    """Available hardware backends"""
    AUTO = "auto"
    CUDA = "cuda"
    OPENVINO = "openvino"
    MPS = "mps"
    CPU = "cpu"

class VectorDatabase(str, Enum):
    """Available vector databases"""
    CHROMADB = "chromadb"
    POSTGRES = "postgres"
    FAISS = "faiss"
    QDRANT = "qdrant"

class ChunkingStrategy(str, Enum):
    """Available chunking strategies"""
    FIXED = "fixed"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"
    TOPIC = "topic"

class EmbeddingModel(str, Enum):
    """Available embedding models"""
    NOMIC = "nomic-embed-text"
    MXBAI = "mxbai-embed-large"
    MINILM = "all-MiniLM-L6-v2"
    BGE_M3 = "bge-m3"

if BaseSettings is not object:
    class MBEDSettings(BaseSettings):
        """MBED configuration with validation"""
        
        # Hardware settings
        hardware: HardwareBackend = Field(
            default=HardwareBackend.AUTO,
            description="Hardware acceleration backend"
        )
        
        # Model settings
        model: EmbeddingModel = Field(
            default=EmbeddingModel.NOMIC,
            description="Embedding model to use"
        )
        model_cache_dir: Path = Field(
            default=Path.home() / ".cache" / "mbed" / "models",
            description="Directory for cached models"
        )
        
        # Database settings
        database: VectorDatabase = Field(
            default=VectorDatabase.CHROMADB,
            description="Vector database backend"
        )
        db_path: Path = Field(
            default=Path("./mbed_data"),
            description="Path to database storage"
        )
        db_connection: Optional[str] = Field(
            default=None,
            description="Database connection string (for PostgreSQL)"
        )
        postgres_pool_min: int = Field(
            default=1,
            ge=1,
            le=50,
            description="Minimum PostgreSQL connection pool size"
        )
        postgres_pool_max: int = Field(
            default=20,
            ge=1,
            le=100,
            description="Maximum PostgreSQL connection pool size"
        )
        
        # Processing settings
        chunk_strategy: ChunkingStrategy = Field(
            default=ChunkingStrategy.FIXED,
            description="Text chunking strategy"
        )
        chunk_size: int = Field(
            default=512,
            ge=100,
            le=4096,
            description="Size of text chunks"
        )
        chunk_overlap: int = Field(
            default=50,
            ge=0,
            le=500,
            description="Overlap between chunks"
        )
        
        # Performance settings
        batch_size: int = Field(
            default=128,
            ge=1,
            le=1024,
            description="Batch size for processing"
        )
        workers: int = Field(
            default=4,
            description="Number of worker threads (use -1 for auto-detection)"
        )
        use_gpu: bool = Field(
            default=True,
            description="Use GPU if available"
        )
        
        # Logging settings
        verbose: bool = Field(
            default=False,
            description="Enable verbose output"
        )
        debug: bool = Field(
            default=False,
            description="Enable debug mode"
        )
        log_level: str = Field(
            default="INFO",
            description="Logging level"
        )
        log_file: Optional[Path] = Field(
            default=None,
            description="Log file path"
        )
        
        # LLM preprocessing settings
        enable_preprocessing: bool = Field(
            default=False,
            description="Enable LLM preprocessing"
        )
        llm_model: str = Field(
            default="llama3.2:latest",
            description="LLM model for preprocessing"
        )
        llm_backend: str = Field(
            default="ollama",
            description="LLM backend (ollama/openvino)"
        )

        # CUDA-specific settings
        mixed_precision: bool = Field(
            default=False,
            description="Enable mixed precision (FP16) for CUDA"
        )
        multi_gpu: bool = Field(
            default=False,
            description="Enable multi-GPU support with DataParallel"
        )
        use_faiss_gpu: bool = Field(
            default=False,
            description="Use FAISS-GPU for vector operations"
        )
        cuda_device: int = Field(
            default=0,
            ge=0,
            description="CUDA device index to use"
        )
        cuda_vram_reserved_gb: float = Field(
            default=2.0,
            ge=0.5,
            le=8.0,
            description="VRAM to reserve for system (GB)"
        )
        cuda_use_pinned_memory: bool = Field(
            default=True,
            description="Use pinned memory for faster CPU-GPU transfers"
        )
        normalize_embeddings: bool = Field(
            default=True,
            description="Normalize embeddings to unit vectors"
        )

        if PYDANTIC_V2:
            model_config = SettingsConfigDict(
                env_prefix="MBED_",
                env_file=".env",
                env_file_encoding="utf-8",
                case_sensitive=False,
                extra="ignore",
                validate_assignment=True,
                use_enum_values=True
            )
        else:
            class Config:
                env_prefix = "MBED_"
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False
                extra = "ignore"
                validate_assignment = True
                use_enum_values = True
        
        if PYDANTIC_V2:
            @field_validator("model_cache_dir", "db_path", "log_file", mode="before")
            @classmethod
            def resolve_path(cls, v):
                """Resolve paths to absolute"""
                if v is None:
                    return v
                path = Path(v).expanduser().resolve()
                # Create directory if it's a cache or data directory
                if str(v).endswith(("cache", "data", "state")):
                    path.mkdir(parents=True, exist_ok=True)
                return path

            @field_validator("chunk_overlap", mode="before")
            @classmethod
            def validate_chunk_overlap(cls, v, info):
                """Ensure chunk_overlap is not larger than chunk_size"""
                if not isinstance(v, int):
                    raise ValueError("chunk_overlap must be an integer")
                if v < 0:
                    raise ValueError("chunk_overlap must be non-negative")
                # Get chunk_size from context if available
                if hasattr(info, 'data') and 'chunk_size' in info.data:
                    chunk_size = info.data['chunk_size']
                    if v >= chunk_size:
                        raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})")
                elif v > 4096:  # Maximum reasonable overlap
                    raise ValueError("chunk_overlap must be at most 4096")
                return v

            @field_validator("log_level", mode="before")
            @classmethod
            def validate_log_level(cls, v):
                """Validate log level"""
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if isinstance(v, str):
                    v = v.upper()
                if v not in valid_levels:
                    raise ValueError(f"log_level must be one of {valid_levels}")
                return v

            @field_validator("llm_backend", mode="before")
            @classmethod
            def validate_llm_backend(cls, v):
                """Validate LLM backend"""
                valid_backends = ["ollama", "openvino"]
                if v not in valid_backends:
                    raise ValueError(f"llm_backend must be one of {valid_backends}")
                return v

            @field_validator("db_connection", mode="before")
            @classmethod
            def validate_db_connection(cls, v):
                """Validate database connection string format"""
                if v is None:
                    return v
                if isinstance(v, str) and v.startswith(("postgresql://", "postgres://")):
                    return v
                if isinstance(v, str) and not v.startswith(("postgresql://", "postgres://")):
                    raise ValueError("db_connection must be a valid PostgreSQL connection string starting with postgresql:// or postgres://")
                return v

            @field_validator("workers", mode="before")
            @classmethod
            def validate_workers(cls, v):
                """Auto-detect optimal worker count and validate range"""
                if v == -1:
                    import multiprocessing
                    return min(multiprocessing.cpu_count(), 8)
                
                # Validate range manually since we removed Field constraints
                if not isinstance(v, int):
                    raise ValueError("workers must be an integer")
                if v < 1:
                    raise ValueError("workers must be at least 1 (or -1 for auto-detection)")
                if v > 32:
                    raise ValueError("workers must be at most 32")
                
                return v
        else:
            @validator("model_cache_dir", "db_path", "log_file", pre=True)
            @classmethod
            def resolve_path(cls, v):
                """Resolve paths to absolute"""
                if v is None:
                    return v
                path = Path(v).expanduser().resolve()
                # Create directory if it's a cache or data directory
                if str(v).endswith(("cache", "data", "state")):
                    path.mkdir(parents=True, exist_ok=True)
                return path

            @validator("chunk_overlap", pre=True)
            @classmethod
            def validate_chunk_overlap(cls, v, values):
                """Ensure chunk_overlap is not larger than chunk_size"""
                if not isinstance(v, int):
                    raise ValueError("chunk_overlap must be an integer")
                if v < 0:
                    raise ValueError("chunk_overlap must be non-negative")
                # Get chunk_size from values if available
                chunk_size = values.get('chunk_size', 4096)
                if v >= chunk_size:
                    raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})")
                return v

            @validator("log_level", pre=True)
            @classmethod
            def validate_log_level(cls, v):
                """Validate log level"""
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if isinstance(v, str):
                    v = v.upper()
                if v not in valid_levels:
                    raise ValueError(f"log_level must be one of {valid_levels}")
                return v

            @validator("llm_backend", pre=True)
            @classmethod
            def validate_llm_backend(cls, v):
                """Validate LLM backend"""
                valid_backends = ["ollama", "openvino"]
                if v not in valid_backends:
                    raise ValueError(f"llm_backend must be one of {valid_backends}")
                return v

            @validator("db_connection", pre=True)
            @classmethod
            def validate_db_connection(cls, v):
                """Validate database connection string format"""
                if v is None:
                    return v
                if isinstance(v, str) and v.startswith(("postgresql://", "postgres://")):
                    return v
                if isinstance(v, str) and not v.startswith(("postgresql://", "postgres://")):
                    raise ValueError("db_connection must be a valid PostgreSQL connection string starting with postgresql:// or postgres://")
                return v

            @validator("workers", pre=True)
            @classmethod
            def validate_workers(cls, v, values):
                """Auto-detect optimal worker count and validate range"""
                if v == -1:
                    import multiprocessing
                    return min(multiprocessing.cpu_count(), 8)
                
                # Validate range manually since we removed Field constraints
                if not isinstance(v, int):
                    raise ValueError("workers must be an integer")
                if v < 1:
                    raise ValueError("workers must be at least 1 (or -1 for auto-detection)")
                if v > 32:
                    raise ValueError("workers must be at most 32")
                
                return v
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary"""
            return {
                k: str(v) if isinstance(v, Path) else v
                for k, v in self.model_dump().items()
                if v is not None
            }
else:
    # Fallback dataclass for demo
    @dataclass
    class MBEDSettings:
        """Configuration settings for MBED"""
        hardware: str = "auto"
        model: str = "nomic-embed-text"
        model_cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "mbed" / "models")
        database: str = "chromadb"
        db_path: Path = field(default_factory=lambda: Path("./mbed_data"))
        db_connection: Optional[str] = None
        postgres_pool_min: int = 1
        postgres_pool_max: int = 20
        chunk_strategy: str = "fixed"
        chunk_size: int = 512
        chunk_overlap: int = 50
        batch_size: int = 128
        workers: int = 4
        use_gpu: bool = True
        verbose: bool = False
        debug: bool = False
        log_level: str = "INFO"
        log_file: Optional[Path] = None
        enable_preprocessing: bool = False
        llm_model: str = "llama3.2:latest"
        llm_backend: str = "ollama"
        mixed_precision: bool = False
        multi_gpu: bool = False
        use_faiss_gpu: bool = False
        cuda_device: int = 0
        cuda_vram_reserved_gb: float = 2.0
        cuda_use_pinned_memory: bool = True
        normalize_embeddings: bool = True

        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary"""
            return {
                k: str(v) if isinstance(v, Path) else v
                for k, v in self.__dict__.items()
                if v is not None
            }

# Global settings instance
_settings: Optional[MBEDSettings] = None

def get_settings() -> MBEDSettings:
    """Get current settings (singleton)"""
    global _settings
    if _settings is None:
        # Note: pyproject.toml loading would require custom settings source implementation
        # Currently using environment variables and defaults only for simplicity
        # This provides the essential functionality with proper precedence: CLI > env > defaults
        _settings = MBEDSettings()
    return _settings

def reload_settings() -> MBEDSettings:
    """Force reload settings from environment"""
    global _settings
    # MBEDSettings will automatically read from environment variables
    # due to pydantic-settings, so we don't pass pyproject config here
    # to avoid overriding environment variables
    _settings = MBEDSettings()
    return _settings

def resolve_settings(overrides: Dict[str, Any]) -> MBEDSettings:
    """Resolve settings with CLI overrides"""
    settings = get_settings()
    
    # Apply CLI overrides (highest precedence)
    for key, value in overrides.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    
    return settings

def load_from_pyproject() -> Dict[str, Any]:
    """Load settings from pyproject.toml if exists"""
    try:
        import tomli
    except ImportError:
        try:
            import tomllib as tomli
        except ImportError:
            return {}
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return {}
    
    try:
        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
            return data.get("tool", {}).get("mbed", {})
    except Exception:
        return {}

def print_config(settings: MBEDSettings) -> None:
    """Print current configuration"""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    table = Table(title="MBED Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")
    table.add_column("Source", style="dim")
    
    config_dict = settings.to_dict()
    
    for key, value in config_dict.items():
        # Determine source
        env_key = f"MBED_{key.upper()}"
        if env_key in os.environ:
            source = "environment"
        elif Path(".env").exists() and env_key in open(".env").read():
            source = ".env file"
        else:
            source = "default"
        
        table.add_row(key, str(value), source)
    
    console.print(table)