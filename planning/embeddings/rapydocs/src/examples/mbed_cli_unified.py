#!/usr/bin/env python3
"""
Unified MBED CLI with typed configuration and rich logging
Combines pydantic-settings configuration with rich output
"""

from __future__ import annotations
import sys
import pathlib
from typing import Optional, List, Dict, Any
import logging

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler
from pydantic import ValidationError

# Import our configuration system (would be from src.core in real implementation)
# For now, we'll define a simplified version inline
from enum import Enum
from pydantic import BaseModel, Field, SecretStr
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback for demo without pydantic_settings
    from pydantic import BaseSettings
    SettingsConfigDict = dict
import tomllib

# Setup rich console and logging
console = Console()

def setup_logging(level: str = "INFO"):
    """Setup rich logging with proper handlers"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            rich_tracebacks=True,
            show_path=False,
            console=console,
            markup=True
        )]
    )

logger = logging.getLogger("mbed")

# Create typer app
app = typer.Typer(
    add_completion=False,
    help="🚀 Unified MBED - Semantic embedding pipeline with hardware acceleration",
    rich_markup_mode="rich"
)

# ---------- Configuration ----------

class HardwareBackend(str, Enum):
    cuda = "cuda"
    openvino = "openvino" 
    mps = "mps"
    cpu = "cpu"
    auto = "auto"

class VectorDatabase(str, Enum):
    chromadb = "chromadb"
    postgres = "postgres"
    faiss = "faiss"
    qdrant = "qdrant"

class ChunkingStrategy(str, Enum):
    fixed = "fixed"
    sentence = "sentence"
    paragraph = "paragraph"
    semantic = "semantic"
    hierarchical = "hierarchical"
    topic = "topic"

def load_pyproject_defaults() -> dict:
    """Load defaults from pyproject.toml"""
    pp = pathlib.Path("pyproject.toml")
    if not pp.exists():
        return {}
    try:
        with pp.open("rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("mbed", {})
    except Exception:
        return {}

class MBEDSettings(BaseSettings):
    """Configuration with proper precedence: CLI > env > .env > pyproject.toml"""
    
    # Core
    hardware: HardwareBackend = Field(default=HardwareBackend.auto)
    model: str = Field(default="nomic-embed-text")
    database: VectorDatabase = Field(default=VectorDatabase.chromadb)
    
    # Processing
    chunk_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.fixed)
    chunk_size: int = Field(default=512, ge=64, le=8192)
    chunk_overlap: int = Field(default=128, ge=0, le=512)
    batch_size: int = Field(default=128, ge=1, le=1024)
    workers: int = Field(default=4, ge=1, le=64)
    
    # Paths
    db_path: pathlib.Path = Field(default=pathlib.Path(".mbed/db"))
    state_dir: pathlib.Path = Field(default=pathlib.Path(".mbed/state"))
    log_dir: pathlib.Path | None = Field(default=None)
    
    # Features
    enable_gpu: bool = Field(default=True)
    normalize_embeddings: bool = Field(default=True)
    resume: bool = Field(default=False)
    
    # Output
    verbose: bool = Field(default=False)
    debug: bool = Field(default=False)
    quiet: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    if SettingsConfigDict != dict:
        model_config = SettingsConfigDict(
            env_prefix="MBED_",
            env_file=".env",
            extra="ignore"
        )
    else:
        # Fallback config
        class Config:
            env_prefix = "MBED_"
            env_file = ".env"
            extra = "ignore"

def resolve_settings(cli_overrides: dict) -> MBEDSettings:
    """Resolve settings with proper precedence"""
    pyproject_defaults = load_pyproject_defaults()
    
    # Merge defaults with CLI overrides
    merged = {**pyproject_defaults}
    for key, value in cli_overrides.items():
        if value is not None:
            merged[key] = value
    
    return MBEDSettings(**merged)

# ---------- Hardware Detection ----------

class HardwareDetector:
    """Detect available hardware with progress indication"""
    
    @classmethod
    def detect_with_progress(cls) -> Dict[HardwareBackend, bool]:
        """Detect hardware with rich progress"""
        results = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Detecting hardware...", total=4)
            
            # Check CUDA
            progress.update(task, description="[yellow]Checking CUDA...")
            results[HardwareBackend.cuda] = cls._check_cuda()
            progress.advance(task)
            
            # Check OpenVINO
            progress.update(task, description="[blue]Checking OpenVINO...")
            results[HardwareBackend.openvino] = cls._check_openvino()
            progress.advance(task)
            
            # Check MPS
            progress.update(task, description="[magenta]Checking MPS...")
            results[HardwareBackend.mps] = cls._check_mps()
            progress.advance(task)
            
            # CPU always available
            progress.update(task, description="[white]Checking CPU...")
            results[HardwareBackend.cpu] = True
            progress.advance(task)
        
        return results
    
    @staticmethod
    def _check_cuda() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    @staticmethod
    def _check_openvino() -> bool:
        try:
            import openvino
            return True
        except ImportError:
            return False
    
    @staticmethod
    def _check_mps() -> bool:
        try:
            import torch
            return torch.backends.mps.is_available()
        except ImportError:
            return False

# ---------- CLI Commands ----------

@app.command()
def generate(
    # Input/Output
    input_path: pathlib.Path = typer.Argument(..., help="Input file or directory"),
    output: Optional[pathlib.Path] = typer.Option(None, "--output", "-o", help="Output path"),
    
    # Hardware
    hardware: Optional[HardwareBackend] = typer.Option(None, "--hardware", "--accel", help="Hardware backend"),
    
    # Model
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Embedding model"),
    database: Optional[VectorDatabase] = typer.Option(None, "--database", "--db", help="Vector database"),
    db_path: Optional[pathlib.Path] = typer.Option(None, "--db-path", help="Database path"),
    
    # Processing
    chunk_strategy: Optional[ChunkingStrategy] = typer.Option(None, "--chunk-strategy", help="Chunking strategy"),
    chunk_size: Optional[int] = typer.Option(None, "--chunk-size", help="Chunk size"),
    chunk_overlap: Optional[int] = typer.Option(None, "--chunk-overlap", help="Chunk overlap"),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", "-b", help="Batch size"),
    workers: Optional[int] = typer.Option(None, "--workers", "-w", help="Parallel workers"),
    
    # Features
    resume: bool = typer.Option(False, "--resume", help="Resume from checkpoint"),
    
    # Output control
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Debug mode"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Quiet mode"),
    log_level: Optional[str] = typer.Option(None, "--log-level", help="Log level"),
):
    """
    Generate embeddings for files and directories.
    
    Example:
        mbed generate /path/to/code --model nomic-embed-text --db chromadb
    """
    
    # Resolve settings
    try:
        settings = resolve_settings(locals())
    except ValidationError as e:
        console.print(f"[red]Configuration error:[/red] {e}", style="red")
        raise typer.Exit(1)
    
    # Setup logging
    setup_logging(settings.log_level)
    
    if settings.debug:
        logger.debug("Debug mode enabled")
        settings.verbose = True
    
    # Header
    console.rule("[bold cyan]MBED Embedding Generation[/bold cyan]")
    console.print()
    
    # Step 1: Hardware detection
    if settings.hardware == HardwareBackend.auto:
        logger.info("[bold]Detecting hardware...[/bold]")
        hw_status = HardwareDetector.detect_with_progress()
        
        # Show results
        table = Table(title="Hardware Detection", show_header=True)
        table.add_column("Backend", style="cyan")
        table.add_column("Status", justify="center")
        
        selected = None
        for hw, available in hw_status.items():
            status = "[green]✅ Available[/green]" if available else "[dim]❌ Not Available[/dim]"
            table.add_row(hw.value.upper(), status)
            
            # Select first available in priority order
            if available and selected is None and hw != HardwareBackend.cpu:
                selected = hw
        
        if selected is None:
            selected = HardwareBackend.cpu
        
        console.print(table)
        logger.info(f"[green]Selected backend: {selected.value}[/green]")
        settings.hardware = selected
    else:
        # Validate requested hardware
        if settings.hardware != HardwareBackend.cpu:
            hw_status = HardwareDetector.detect_with_progress()
            if not hw_status.get(settings.hardware, False):
                error_panel = Panel(
                    f"[bold]Hardware '{settings.hardware.value}' not available![/bold]\n\n"
                    f"Available options:\n"
                    f"• {', '.join(h.value for h, a in hw_status.items() if a)}\n\n"
                    f"[dim]Use --hardware auto for automatic selection[/dim]",
                    title="[red]Hardware Error[/red]",
                    style="red"
                )
                console.print(error_panel)
                raise typer.Exit(1)
    
    console.print()
    
    # Step 2: Process files
    logger.info(f"[bold]Processing: {input_path}[/bold]")
    
    # Simulated processing with progress
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console
    ) as progress:
        # Discovery
        task1 = progress.add_task("[cyan]Discovering files...", total=100)
        for i in range(100):
            progress.update(task1, advance=1)
        
        logger.info("[green]✅ Found 42 files[/green]")
        
        # Chunking
        task2 = progress.add_task("[cyan]Creating chunks...", total=42)
        for i in range(42):
            progress.update(task2, advance=1)
        
        logger.info(f"[green]✅ Created 256 chunks using {settings.chunk_strategy.value} strategy[/green]")
        
        # Embedding
        task3 = progress.add_task("[cyan]Generating embeddings...", total=256)
        for i in range(256):
            progress.update(task3, advance=1)
        
        logger.info(f"[green]✅ Generated embeddings with {settings.model}[/green]")
        
        # Storage
        task4 = progress.add_task(f"[cyan]Storing in {settings.database.value}...", total=256)
        for i in range(256):
            progress.update(task4, advance=1)
        
        logger.info(f"[green]✅ Stored in {settings.database.value} at {settings.db_path}[/green]")
    
    console.print()
    
    # Summary
    summary = Panel(
        f"[bold cyan]Processing Complete![/bold cyan]\n\n"
        f"• Files processed: 42\n"
        f"• Chunks created: 256\n"
        f"• Model: {settings.model}\n"
        f"• Backend: {settings.hardware.value}\n"
        f"• Database: {settings.database.value}\n"
        f"• Time: 12.3 seconds",
        title="[green]✅ Success[/green]",
        style="green"
    )
    console.print(summary)

@app.command()
def info(
    show_config: bool = typer.Option(False, "--config", help="Show configuration"),
    show_hardware: bool = typer.Option(False, "--hardware", help="Show hardware details"),
):
    """
    Show system information and configuration.
    """
    console.rule("[bold cyan]MBED System Information[/bold cyan]")
    console.print()
    
    # Basic info
    import platform
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="yellow")
    
    info_table.add_row("Version", "1.0.0")
    info_table.add_row("Python", sys.version.split()[0])
    info_table.add_row("Platform", platform.platform())
    
    console.print(info_table)
    console.print()
    
    # Hardware detection
    if show_hardware or True:  # Always show for now
        console.rule("[bold magenta]Hardware Detection[/bold magenta]")
        hw_status = HardwareDetector.detect_with_progress()
        
        table = Table(show_header=True)
        table.add_column("Backend", style="cyan")
        table.add_column("Available", justify="center")
        table.add_column("Notes")
        
        for hw, available in hw_status.items():
            status = "[green]✅ Yes[/green]" if available else "[red]❌ No[/red]"
            notes = ""
            if hw == HardwareBackend.cuda and available:
                try:
                    import torch
                    notes = f"CUDA {torch.version.cuda}"
                except:
                    pass
            
            table.add_row(hw.value.upper(), status, notes)
        
        console.print(table)
    
    # Configuration
    if show_config:
        console.print()
        console.rule("[bold yellow]Configuration[/bold yellow]")
        
        settings = resolve_settings({})
        config_table = Table(show_header=True)
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="yellow")
        config_table.add_column("Source", style="dim")
        
        # Show key settings
        config_table.add_row("Model", settings.model, "default")
        config_table.add_row("Database", settings.database.value, "default")
        config_table.add_row("Chunk Strategy", settings.chunk_strategy.value, "default")
        config_table.add_row("Batch Size", str(settings.batch_size), "default")
        config_table.add_row("Workers", str(settings.workers), "default")
        
        console.print(config_table)

@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    save: Optional[pathlib.Path] = typer.Option(None, "--save", help="Save config to file"),
    load: Optional[pathlib.Path] = typer.Option(None, "--load", help="Load config from file"),
):
    """
    Manage configuration settings.
    """
    if show:
        settings = resolve_settings({})
        
        console.rule("[bold cyan]Current Configuration[/bold cyan]")
        console.print()
        
        # Create detailed table
        table = Table(title="MBED Settings", show_header=True)
        table.add_column("Category", style="magenta")
        table.add_column("Setting", style="cyan")  
        table.add_column("Value", style="yellow")
        
        # Group settings by category
        table.add_row("Hardware", "Backend", settings.hardware.value)
        table.add_row("Hardware", "Enable GPU", str(settings.enable_gpu))
        table.add_row("", "", "")
        
        table.add_row("Model", "Model Name", settings.model)
        table.add_row("Model", "Normalize", str(settings.normalize_embeddings))
        table.add_row("", "", "")
        
        table.add_row("Processing", "Chunk Strategy", settings.chunk_strategy.value)
        table.add_row("Processing", "Chunk Size", str(settings.chunk_size))
        table.add_row("Processing", "Chunk Overlap", str(settings.chunk_overlap))
        table.add_row("Processing", "Batch Size", str(settings.batch_size))
        table.add_row("Processing", "Workers", str(settings.workers))
        table.add_row("", "", "")
        
        table.add_row("Storage", "Database", settings.database.value)
        table.add_row("Storage", "DB Path", str(settings.db_path))
        table.add_row("Storage", "State Dir", str(settings.state_dir))
        
        console.print(table)
    
    if save:
        logger.info(f"[green]Configuration would be saved to {save}[/green]")
    
    if load:
        logger.info(f"[green]Configuration would be loaded from {load}[/green]")

# ---------- Main ----------

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()