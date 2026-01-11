#!/usr/bin/env python3
"""
Unified MBED Command - CLI Template with Rich Logging
This version uses rich-click for beautiful CLI output and unified logging
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

# Rich imports for beautiful terminal output
try:
    import rich_click as click
except ImportError:
    import click  # Fallback to regular click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.logging import RichHandler
from rich import print as rprint
from rich.traceback import install
try:
    from enrich.logging import RichHandler as EnrichHandler
except ImportError:
    EnrichHandler = None  # enrich is optional

# Install rich tracebacks for better error output
install(show_locals=True)

# Configure rich-click if available
try:
    if hasattr(click, 'rich_click'):
        click.rich_click.USE_RICH_MARKUP = True
        click.rich_click.USE_MARKDOWN = True
        click.rich_click.SHOW_ARGUMENTS = True
        click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
        click.rich_click.SHOW_METAVARS_COLUMN = False
        click.rich_click.APPEND_METAVARS_HELP = True
        click.rich_click.STYLE_OPTION = "bold cyan"
        click.rich_click.STYLE_ARGUMENT = "bold green"
        click.rich_click.STYLE_COMMAND = "bold magenta"
        click.rich_click.STYLE_SWITCH = "bold yellow"
        click.rich_click.STYLE_METAVAR = "italic"
        click.rich_click.STYLE_METAVAR_APPEND = "dim italic"
        click.rich_click.STYLE_HEADER_TEXT = "bold"
        click.rich_click.STYLE_EPILOG_TEXT = "dim"
        click.rich_click.STYLE_FOOTER_TEXT = "dim"
        click.rich_click.STYLE_USAGE = "yellow"
        click.rich_click.STYLE_USAGE_COMMAND = "bold yellow"
        click.rich_click.STYLE_HELPTEXT_FIRST_LINE = "cyan"
        click.rich_click.STYLE_HELPTEXT = "dim"
        click.rich_click.STYLE_ERROR = "red"
        click.rich_click.STYLE_REQUIRED_SHORT = "red"
        click.rich_click.STYLE_REQUIRED_LONG = "dim red"
        click.rich_click.MAX_WIDTH = 100
        click.rich_click.COLOR_SYSTEM = "auto"
except AttributeError:
    pass  # Regular click, no rich configuration

# Import our unified logging (would be from src.core.logging in real implementation)
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger("mbed")

__version__ = "0.0.1-dev"

# Create console for rich output
console = Console()

class HardwareType(Enum):
    """Supported hardware acceleration types"""
    CUDA = "cuda"
    OPENVINO = "openvino"
    MPS = "mps"
    CPU = "cpu"
    AUTO = "auto"

class HardwareDetector:
    """Detects available hardware acceleration with rich output"""
    
    @staticmethod
    def detect_cuda() -> bool:
        """Check if CUDA is available"""
        try:
            result = subprocess.run(
                ['nvidia-smi'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False
            
            try:
                import torch
                return torch.cuda.is_available()
            except ImportError:
                return True
                
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def detect_openvino() -> bool:
        """Check if OpenVINO is available"""
        try:
            import openvino
            return True
        except ImportError:
            return os.environ.get('INTEL_OPENVINO_DIR') is not None
    
    @staticmethod
    def detect_mps() -> bool:
        """Check if Apple Metal Performance Shaders are available"""
        if platform.system() != 'Darwin':
            return False
        
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'hw.optional.arm64'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() != '1':
                return False
            
            try:
                import torch
                return torch.backends.mps.is_available()
            except ImportError:
                return True
                
        except Exception:
            return False
    
    @classmethod
    def detect_all(cls) -> Dict[HardwareType, bool]:
        """Detect all available hardware"""
        
        # Show detection progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Detecting hardware...", total=4)
            
            results = {}
            
            progress.update(task, description="[yellow]Checking CUDA...")
            results[HardwareType.CUDA] = cls.detect_cuda()
            progress.advance(task)
            
            progress.update(task, description="[blue]Checking OpenVINO...")
            results[HardwareType.OPENVINO] = cls.detect_openvino()
            progress.advance(task)
            
            progress.update(task, description="[magenta]Checking MPS...")
            results[HardwareType.MPS] = cls.detect_mps()
            progress.advance(task)
            
            progress.update(task, description="[white]Checking CPU...")
            results[HardwareType.CPU] = True
            progress.advance(task)
        
        return results
    
    @classmethod
    def get_available(cls) -> List[HardwareType]:
        """Get list of available hardware types"""
        detected = cls.detect_all()
        return [hw for hw, available in detected.items() if available]
    
    @classmethod
    def select_best(cls) -> HardwareType:
        """Select the best available hardware"""
        available = cls.get_available()
        priority = [
            HardwareType.CUDA,
            HardwareType.MPS,
            HardwareType.OPENVINO,
            HardwareType.CPU
        ]
        
        for hw in priority:
            if hw in available:
                return hw
        
        return HardwareType.CPU
    
    @classmethod
    def print_detection_table(cls):
        """Print hardware detection results as a rich table"""
        detected = cls.detect_all()
        
        table = Table(title="Hardware Detection Results", show_header=True, header_style="bold magenta")
        table.add_column("Backend", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Priority", justify="center", style="dim")
        
        priority_map = {
            HardwareType.CUDA: "1 (Highest)",
            HardwareType.MPS: "2",
            HardwareType.OPENVINO: "3",
            HardwareType.CPU: "4 (Lowest)"
        }
        
        for hw, available in detected.items():
            if available:
                status = "[bold green]✅ Available[/bold green]"
            else:
                status = "[dim]❌ Not Available[/dim]"
            
            table.add_row(
                hw.value.upper(),
                status,
                priority_map[hw]
            )
        
        console.print(table)
        
        best = cls.select_best()
        console.print(f"\n[bold cyan]Recommended backend:[/bold cyan] [bold yellow]{best.value}[/bold yellow]")

class DeveloperChecker:
    """Check if developer can work on specific backend with rich output"""
    
    @staticmethod
    def check_cuda_development() -> Dict[str, Any]:
        """Check CUDA development readiness"""
        report = {
            'can_develop': False,
            'hardware': False,
            'cuda_toolkit': False,
            'pytorch_cuda': False,
            'vram_gb': 0,
            'missing': []
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[yellow]Checking CUDA development environment...", total=3)
            
            # Check hardware
            progress.update(task, description="Detecting NVIDIA GPU...")
            if HardwareDetector.detect_cuda():
                report['hardware'] = True
            else:
                report['missing'].append("NVIDIA GPU not detected")
                progress.advance(task, 3)
                return report
            progress.advance(task)
            
            # Check CUDA toolkit
            progress.update(task, description="Checking CUDA toolkit...")
            try:
                result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    report['cuda_toolkit'] = True
            except FileNotFoundError:
                report['missing'].append("CUDA toolkit (nvcc) not found")
            progress.advance(task)
            
            # Check PyTorch with CUDA
            progress.update(task, description="Verifying PyTorch CUDA support...")
            try:
                import torch
                if torch.cuda.is_available():
                    report['pytorch_cuda'] = True
                    report['vram_gb'] = torch.cuda.get_device_properties(0).total_memory / 1e9
                else:
                    report['missing'].append("PyTorch CUDA support not available")
            except ImportError:
                report['missing'].append("PyTorch not installed")
            progress.advance(task)
        
        report['can_develop'] = (
            report['hardware'] and 
            report['cuda_toolkit'] and 
            report['pytorch_cuda']
        )
        
        return report
    
    @staticmethod
    def print_dev_report(backend: str, report: Dict[str, Any]):
        """Print development readiness report with rich formatting"""
        
        # Create title with appropriate color
        if report.get('can_develop', backend == 'cpu'):
            title = f"[bold green]✅ {backend} Backend: Ready for development[/bold green]"
            panel_style = "green"
        else:
            title = f"[bold red]❌ {backend} Backend: Not ready for development[/bold red]"
            panel_style = "red"
        
        # Build content
        lines = []
        
        # Add component status
        for key, value in report.items():
            if key in ['can_develop', 'missing']:
                continue
            
            if isinstance(value, bool):
                icon = "[green]✓[/green]" if value else "[red]✗[/red]"
                status = "[green]Yes[/green]" if value else "[red]No[/red]"
                lines.append(f"{icon} {key.replace('_', ' ').title()}: {status}")
            elif key == 'vram_gb' and value > 0:
                lines.append(f"💾 VRAM: [cyan]{value:.1f} GB[/cyan]")
        
        # Add missing components
        if report.get('missing'):
            lines.append("")
            lines.append("[bold red]Missing components:[/bold red]")
            for missing in report['missing']:
                lines.append(f"  • {missing}")
            
            # Add setup instructions
            lines.append("")
            lines.append("[bold yellow]Setup instructions:[/bold yellow]")
            if backend == 'cuda':
                lines.append("  1. Install CUDA Toolkit: https://developer.nvidia.com/cuda-downloads")
                lines.append("  2. Install PyTorch with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu118")
            elif backend == 'openvino':
                lines.append("  1. Install OpenVINO: https://docs.openvino.ai/latest/openvino_docs_install_guides.html")
                lines.append("  2. Run setup script: source /opt/intel/openvino/setupvars.sh")
        
        content = "\n".join(lines)
        panel = Panel(content, title=title, style=panel_style, expand=False)
        console.print(panel)

# Main CLI group with rich-click
@click.group(invoke_without_command=True, context_settings={'help_option_names': ['-h', '--help']})
@click.option('--version', '-v', is_flag=True, help='Show version and exit')
@click.option('--hardware', '--accel', 
              type=click.Choice(['cuda', 'openvino', 'mps', 'cpu', 'auto']), 
              default='auto', 
              help='Hardware acceleration backend to use')
@click.option('--debug', '-d', is_flag=True, help='Enable debug output with detailed logging')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.pass_context
def cli(ctx, version, hardware, debug, quiet):
    """
    # 🚀 Unified MBED Command
    
    **Semantic embedding pipeline for code** with hardware acceleration support.
    
    ## Features:
    - 🎯 Multi-backend support (CUDA, OpenVINO, MPS, CPU)
    - 📊 Beautiful terminal output with rich
    - 🔄 Resumable processing with state management
    - 🗄️ Multiple vector database backends
    - 🔍 Semantic search capabilities
    
    ## Quick Start:
    ```bash
    mbed generate /path/to/code  # Generate embeddings
    mbed search "auth logic"     # Search semantically
    mbed serve --mcp            # Start MCP server
    ```
    
    Use `mbed COMMAND --help` for more information on each command.
    """
    
    if version:
        console.print(f"[bold cyan]mbed[/bold cyan] version [bold yellow]{__version__}[/bold yellow]")
        console.print(f"[dim]Python {sys.version.split()[0]} on {platform.system()}[/dim]")
        sys.exit(0)
    
    # Setup logging based on flags
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    elif quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Store options in context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['quiet'] = quiet
    ctx.obj['hardware'] = HardwareType(hardware)
    
    # Hardware validation if specific backend requested
    if hardware != 'auto':
        hw_type = HardwareType(hardware)
        available = HardwareDetector.get_available()
        
        if hw_type not in available:
            console.print(f"[bold red]❌ Error:[/bold red] {hardware} acceleration not available", style="red")
            console.print(f"[dim]Available backends: {', '.join(h.value for h in available)}[/dim]")
            
            # Show helpful error messages
            error_panel = None
            if hardware == 'cuda':
                error_panel = Panel(
                    "[bold]To use CUDA acceleration, you need:[/bold]\n"
                    "• NVIDIA GPU with CUDA support\n"
                    "• CUDA toolkit installed\n"
                    "• PyTorch with CUDA support\n\n"
                    "[dim]Run 'mbed dev-check cuda' for detailed diagnostics[/dim]",
                    title="[red]CUDA Requirements[/red]",
                    style="red"
                )
            elif hardware == 'openvino':
                error_panel = Panel(
                    "[bold]To use OpenVINO acceleration, you need:[/bold]\n"
                    "• Intel GPU (Xe, Arc, or integrated)\n"
                    "• OpenVINO runtime installed\n\n"
                    "[dim]Run 'mbed dev-check openvino' for detailed diagnostics[/dim]",
                    title="[red]OpenVINO Requirements[/red]",
                    style="red"
                )
            elif hardware == 'mps':
                error_panel = Panel(
                    "[bold]To use MPS acceleration, you need:[/bold]\n"
                    "• Apple Silicon Mac (M1/M2/M3)\n"
                    "• PyTorch with MPS support\n\n"
                    "[dim]Run 'mbed dev-check mps' for detailed diagnostics[/dim]",
                    title="[red]MPS Requirements[/red]",
                    style="red"
                )
            
            if error_panel:
                console.print(error_panel)
            
            sys.exit(1)
    
    # Show help if no command
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())

@cli.command()
@click.argument('backend', type=click.Choice(['cuda', 'openvino', 'mps', 'cpu', 'all']))
def dev_check(backend):
    """
    Check development readiness for specific backend.
    
    This command verifies that all necessary components are installed
    and configured for developing with the specified hardware backend.
    """
    
    console.rule(f"[bold cyan]Development Environment Check: {backend.upper()}[/bold cyan]")
    console.print()
    
    if backend == 'all':
        backends = ['cuda', 'openvino', 'mps', 'cpu']
    else:
        backends = [backend]
    
    for b in backends:
        if b == 'cuda':
            report = DeveloperChecker.check_cuda_development()
            DeveloperChecker.print_dev_report("CUDA", report)
        elif b == 'cpu':
            panel = Panel(
                "[green]✅ Always ready for development[/green]\n"
                "No special hardware or libraries required.\n"
                "CPU backend uses standard Python packages.",
                title="[bold green]CPU Backend[/bold green]",
                style="green"
            )
            console.print(panel)
        
        if len(backends) > 1 and b != backends[-1]:
            console.print()

@cli.command()
@click.pass_context
def info(ctx):
    """
    Show comprehensive system information and available backends.
    
    Displays hardware detection results, recommended backends,
    and system configuration details.
    """
    
    # System info header
    console.rule("[bold cyan]MBED System Information[/bold cyan]")
    console.print()
    
    # Version and platform info
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="yellow")
    
    info_table.add_row("Version", __version__)
    info_table.add_row("Python", f"{sys.version.split()[0]}")
    info_table.add_row("Platform", platform.platform())
    info_table.add_row("Architecture", platform.machine())
    
    console.print(info_table)
    console.print()
    
    # Hardware detection
    console.rule("[bold magenta]Hardware Detection[/bold magenta]")
    console.print()
    HardwareDetector.print_detection_table()
    
    # Debug information if enabled
    if ctx.obj.get('debug'):
        console.print()
        console.rule("[bold yellow]Debug Information[/bold yellow]")
        
        debug_table = Table(show_header=False, box=None)
        debug_table.add_column("Variable", style="cyan")
        debug_table.add_column("Value", style="white")
        
        debug_table.add_row("CUDA_VISIBLE_DEVICES", os.environ.get('CUDA_VISIBLE_DEVICES', '[dim]not set[/dim]'))
        debug_table.add_row("INTEL_OPENVINO_DIR", os.environ.get('INTEL_OPENVINO_DIR', '[dim]not set[/dim]'))
        debug_table.add_row("Working Directory", str(Path.cwd()))
        
        console.print(debug_table)

# Placeholder commands with nice formatting
@cli.command()
def generate():
    """
    Generate embeddings for files and directories.
    
    **Status:** 🚧 Not yet implemented (Phase 2)
    """
    logger.warning("generate command not yet implemented")
    console.print(Panel(
        "[yellow]This command will:[/yellow]\n"
        "• Process files and directories\n"
        "• Generate semantic embeddings\n"
        "• Store in vector database\n"
        "• Support resume on interruption\n\n"
        "[dim]Coming in Phase 2 of development[/dim]",
        title="[yellow]⚠️  Not Implemented[/yellow]",
        style="yellow"
    ))
    raise NotImplementedError("generate command coming in Phase 2")

@cli.command()
def search():
    """
    Search using semantic similarity.
    
    **Status:** 🚧 Not yet implemented (Phase 6)
    """
    logger.warning("search command not yet implemented")
    raise NotImplementedError("search command coming in Phase 6")

@cli.command()
def serve():
    """
    Start MCP or REST API server.
    
    **Status:** 🚧 Not yet implemented (Phase 7)
    """
    logger.warning("serve command not yet implemented")
    raise NotImplementedError("serve command coming in Phase 7")

if __name__ == '__main__':
    try:
        cli()
    except Exception as e:
        if '--debug' in sys.argv or '-d' in sys.argv:
            console.print_exception(show_locals=True)
        else:
            logger.error(f"Error: {e}")
            logger.info("Run with --debug for full traceback")
        sys.exit(1)