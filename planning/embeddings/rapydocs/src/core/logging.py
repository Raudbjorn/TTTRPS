"""
Unified Logging Module for MBED
Uses rich for beautiful terminal output and structured logging
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn
)
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.traceback import install as install_rich_traceback
from rich.theme import Theme
from enrich.logging import RichHandler as EnrichHandler

# Install rich traceback handler for beautiful exception output
install_rich_traceback(show_locals=True, suppress=[])

# Custom theme for MBED
MBED_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "debug": "dim white",
    "hardware.cuda": "bold yellow",
    "hardware.openvino": "bold blue",
    "hardware.mps": "bold magenta",
    "hardware.cpu": "bold white",
    "progress.description": "bold cyan",
    "progress.percentage": "bold magenta",
})

class LogLevel(Enum):
    """Log levels with rich colors"""
    DEBUG = ("DEBUG", "dim white")
    INFO = ("INFO", "cyan")
    WARNING = ("WARNING", "yellow")
    ERROR = ("ERROR", "bold red")
    SUCCESS = ("SUCCESS", "bold green")
    
    def __init__(self, name: str, style: str):
        self.level_name = name
        self.style = style

class MBEDLogger:
    """Unified logger for MBED with rich output"""
    
    _instance = None
    _console = None
    _file_handler = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.console = Console(theme=MBED_THEME)
            self.setup_logging()
            self.initialized = True
    
    def setup_logging(self, 
                     log_file: Optional[Path] = None,
                     level: str = "INFO",
                     use_enrich: bool = True):
        """Setup unified logging with rich handler"""
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, level),
            format="%(message)s",
            datefmt="[%X]",
            handlers=[]
        )
        
        # Add rich console handler
        if use_enrich:
            # EnrichHandler provides additional context
            console_handler = EnrichHandler(
                console=self.console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                log_time_format="[%X]"
            )
        else:
            console_handler = RichHandler(
                console=self.console,
                rich_tracebacks=True,
                log_time_format="[%X]"
            )
        
        logging.getLogger().addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            logging.getLogger().addHandler(file_handler)
            self._file_handler = file_handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a named logger"""
        return logging.getLogger(name)
    
    # Convenience methods for direct logging
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.console.log(f"[debug]{message}[/debug]", **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.console.log(f"[info]{message}[/info]", **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.console.log(f"[warning]⚠️  {message}[/warning]", **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.console.log(f"[error]❌ {message}[/error]", **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message"""
        self.console.log(f"[success]✅ {message}[/success]", **kwargs)
    
    def hardware_status(self, hardware_type: str, status: str, details: Dict[str, Any] = None):
        """Log hardware-specific status with formatted output"""
        
        # Create a nice table for hardware status
        table = Table(title=f"{hardware_type.upper()} Hardware Status", show_header=True)
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        # Main status
        status_icon = "✅" if status == "ready" else "❌"
        table.add_row("Overall", f"{status_icon} {status.title()}", "")
        
        # Add details if provided
        if details:
            for key, value in details.items():
                if isinstance(value, bool):
                    icon = "✓" if value else "✗"
                    status_str = f"{icon} {'Available' if value else 'Not Available'}"
                else:
                    status_str = str(value)
                
                table.add_row(key.replace('_', ' ').title(), status_str, "")
        
        self.console.print(table)
    
    def print_panel(self, content: str, title: str = None, style: str = "cyan"):
        """Print content in a nice panel"""
        panel = Panel(content, title=title, style=style)
        self.console.print(panel)
    
    def print_code(self, code: str, language: str = "python", line_numbers: bool = True):
        """Print syntax-highlighted code"""
        syntax = Syntax(code, language, line_numbers=line_numbers, theme="monokai")
        self.console.print(syntax)
    
    def create_progress(self, *columns, **kwargs) -> Progress:
        """Create a rich progress bar with custom columns"""
        if not columns:
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]
        return Progress(*columns, console=self.console, **kwargs)
    
    def rule(self, title: str = "", style: str = "cyan"):
        """Print a horizontal rule"""
        self.console.rule(title, style=style)
    
    def print_exception(self):
        """Print the current exception with rich formatting"""
        self.console.print_exception()

# Global logger instance
logger = MBEDLogger()

# Convenience functions for module-level logging
def get_logger(name: str = __name__) -> logging.Logger:
    """Get a logger instance for a module"""
    return logger.get_logger(name)

def setup_logging(log_file: Optional[Path] = None, 
                 level: str = "INFO",
                 use_enrich: bool = True):
    """Setup logging configuration"""
    logger.setup_logging(log_file, level, use_enrich)

def debug(message: str, **kwargs):
    """Log debug message"""
    logger.debug(message, **kwargs)

def info(message: str, **kwargs):
    """Log info message"""
    logger.info(message, **kwargs)

def warning(message: str, **kwargs):
    """Log warning message"""
    logger.warning(message, **kwargs)

def error(message: str, **kwargs):
    """Log error message"""
    logger.error(message, **kwargs)

def success(message: str, **kwargs):
    """Log success message"""
    logger.success(message, **kwargs)

def hardware_status(hardware_type: str, status: str, details: Dict[str, Any] = None):
    """Log hardware status"""
    logger.hardware_status(hardware_type, status, details)

def print_panel(content: str, title: str = None, style: str = "cyan"):
    """Print a panel"""
    logger.print_panel(content, title, style)

def print_code(code: str, language: str = "python", line_numbers: bool = True):
    """Print syntax-highlighted code"""
    logger.print_code(code, language, line_numbers)

def create_progress(*columns, **kwargs) -> Progress:
    """Create a progress bar"""
    return logger.create_progress(*columns, **kwargs)

def rule(title: str = "", style: str = "cyan"):
    """Print a rule"""
    logger.rule(title, style)

# Example usage for different components
class ComponentLogger:
    """Base class for component-specific loggers"""
    
    def __init__(self, component_name: str):
        self.logger = get_logger(component_name)
        self.component = component_name
    
    def log_start(self, task: str):
        """Log task start"""
        self.logger.info(f"[{self.component}] Starting: {task}")
    
    def log_complete(self, task: str):
        """Log task completion"""
        self.logger.info(f"[{self.component}] ✅ Completed: {task}")
    
    def log_error(self, task: str, error: Exception):
        """Log task error"""
        self.logger.error(f"[{self.component}] ❌ Failed: {task}")
        self.logger.exception(error)
    
    def log_progress(self, current: int, total: int, description: str = ""):
        """Log progress update"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.logger.info(f"[{self.component}] Progress: {description} ({current}/{total} - {percentage:.1f}%)")