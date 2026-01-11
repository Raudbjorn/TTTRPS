"""
Enhanced logging with rich for beautiful terminal output

Features:
- Colored output based on log level
- Component-specific loggers
- Hardware status display
- Progress tracking
- File and console handlers
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.text import Text

# Global console instance
console = Console()

# Component-specific loggers
COMPONENT_LOGGERS = {
    "hardware": "mbed.hardware",
    "embedding": "mbed.embedding",
    "database": "mbed.database",
    "preprocessing": "mbed.preprocessing",
    "chunking": "mbed.chunking",
    "cli": "mbed.cli",
    "config": "mbed.config",
}

def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    rich_tracebacks: bool = True,
    show_path: bool = False,
) -> None:
    """
    Setup unified logging with rich
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
        rich_tracebacks: Enable rich exception formatting
        show_path: Show file path in logs
    """
    # Configure rich handler for console
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=rich_tracebacks,
        show_path=show_path,
        markup=True,
        log_time_format="[%X]",
    )
    rich_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Base configuration
    handlers = [rich_handler]
    
    # Add file handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True
    )
    
    # Set component logger levels
    for component, logger_name in COMPONENT_LOGGERS.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with component context"""
    return logging.getLogger(name)

def hardware_status(hardware_type: str, status: str, details: Dict[str, Any] = None) -> None:
    """
    Display hardware status with rich formatting
    
    Args:
        hardware_type: Type of hardware (cuda, mps, openvino, cpu)
        status: Status message
        details: Optional hardware details
    """
    table = Table(title=f"{hardware_type.upper()} Hardware Status", show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="yellow")
    
    table.add_row("Status", status)
    
    if details:
        for key, value in details.items():
            table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print(table)

def log_configuration(config: Dict[str, Any]) -> None:
    """Display configuration with rich panel"""
    lines = []
    for key, value in config.items():
        lines.append(f"[cyan]{key}:[/cyan] [yellow]{value}[/yellow]")
    
    panel = Panel(
        "\n".join(lines),
        title="[bold]MBED Configuration[/bold]",
        border_style="blue"
    )
    console.print(panel)

def log_error(error: Exception, context: str = None) -> None:
    """
    Log error with rich formatting
    
    Args:
        error: Exception to log
        context: Optional context about where error occurred
    """
    error_text = Text(str(error), style="bold red")
    
    if context:
        console.print(f"[red]Error in {context}:[/red]")
    
    console.print(error_text)
    
    if hasattr(error, "__traceback__"):
        console.print_exception()

def create_progress(description: str = "Processing") -> Progress:
    """
    Create a rich progress bar
    
    Args:
        description: Progress bar description
    
    Returns:
        Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )

def log_success(message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log success message with optional details
    
    Args:
        message: Success message
        details: Optional additional details
    """
    console.print(f"[bold green]✅ {message}[/bold green]")
    
    if details:
        for key, value in details.items():
            console.print(f"  [dim]{key}: {value}[/dim]")

def log_warning(message: str) -> None:
    """Log warning message"""
    console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")

def log_info(message: str) -> None:
    """Log info message"""
    console.print(f"[cyan]ℹ️ {message}[/cyan]")

def log_code(code: str, language: str = "python", title: Optional[str] = None) -> None:
    """
    Display code with syntax highlighting
    
    Args:
        code: Code to display
        language: Programming language for highlighting
        title: Optional title for code block
    """
    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=False
    )
    
    if title:
        panel = Panel(syntax, title=title, border_style="blue")
        console.print(panel)
    else:
        console.print(syntax)

def log_stats(stats: Dict[str, Any], title: str = "Statistics") -> None:
    """
    Display statistics in a table
    
    Args:
        stats: Statistics dictionary
        title: Table title
    """
    table = Table(title=title, show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow", justify="right")
    
    for key, value in stats.items():
        # Format numbers nicely
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                formatted = f"{value:,.2f}"
            else:
                formatted = f"{value:,}"
        else:
            formatted = str(value)
        
        table.add_row(key.replace("_", " ").title(), formatted)
    
    console.print(table)

class ComponentLogger:
    """Logger wrapper for specific components with rich output"""
    
    def __init__(self, component: str):
        """
        Initialize component logger
        
        Args:
            component: Component name (hardware, embedding, etc.)
        """
        self.component = component
        self.logger = get_logger(COMPONENT_LOGGERS.get(component, f"mbed.{component}"))
        self.console = console
    
    def info(self, message: str, extra: Optional[Dict] = None) -> None:
        """Log info with component context"""
        self.logger.info(f"[{self.component}] {message}", extra=extra)
    
    def debug(self, message: str, extra: Optional[Dict] = None) -> None:
        """Log debug with component context"""
        self.logger.debug(f"[{self.component}] {message}", extra=extra)
    
    def warning(self, message: str, extra: Optional[Dict] = None) -> None:
        """Log warning with component context"""
        self.logger.warning(f"[{self.component}] {message}", extra=extra)
    
    def error(self, message: str, error: Optional[Exception] = None) -> None:
        """Log error with component context"""
        self.logger.error(f"[{self.component}] {message}")
        if error:
            log_error(error, context=self.component)
    
    def success(self, message: str, details: Optional[Dict] = None) -> None:
        """Log success with component context"""
        log_success(f"[{self.component}] {message}", details)
    
    def progress(self, description: str) -> Progress:
        """Create progress bar for component"""
        return create_progress(f"[{self.component}] {description}")

# Convenience functions for component loggers
def get_hardware_logger() -> ComponentLogger:
    """Get hardware component logger"""
    return ComponentLogger("hardware")

def get_embedding_logger() -> ComponentLogger:
    """Get embedding component logger"""
    return ComponentLogger("embedding")

def get_database_logger() -> ComponentLogger:
    """Get database component logger"""
    return ComponentLogger("database")

def get_cli_logger() -> ComponentLogger:
    """Get CLI component logger"""
    return ComponentLogger("cli")