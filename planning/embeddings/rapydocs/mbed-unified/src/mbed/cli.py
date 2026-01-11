#!/usr/bin/env python3
"""
Unified MBED CLI with hardware detection and UV support
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.hardware import HardwareDetector, HardwareType, DeveloperChecker
from .utils.uv import UVManager, setup_environment

# Setup console for rich output
console = Console()

# Create typer app
app = typer.Typer(
    name="mbed",
    help="🚀 Unified MBED - Semantic embedding pipeline with hardware acceleration",
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)

# Version info
__version__ = "1.0.0-dev"

@app.command()
def info(
    hardware: bool = typer.Option(False, "--hardware", "-h", help="Show detailed hardware info"),
    config: bool = typer.Option(False, "--config", "-c", help="Show configuration"),
):
    """
    Show system information and available backends
    """
    console.rule("[bold cyan]MBED System Information[/bold cyan]")
    console.print()
    
    # Basic info
    import platform
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="yellow")
    
    info_table.add_row("Version", __version__)
    info_table.add_row("Python", sys.version.split()[0])
    info_table.add_row("Platform", platform.platform())
    info_table.add_row("Architecture", platform.machine())
    
    console.print(info_table)
    console.print()
    
    # Hardware detection
    console.rule("[bold magenta]Hardware Detection[/bold magenta]")
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Detecting hardware...", total=None)
        capabilities = HardwareDetector.detect_all()
    
    # Display results
    hw_table = Table(title="Available Hardware Backends", show_header=True)
    hw_table.add_column("Backend", style="cyan", no_wrap=True)
    hw_table.add_column("Status", justify="center")
    hw_table.add_column("Details", style="dim")
    
    for hw_type, capability in capabilities.items():
        if capability.available:
            status = "[bold green]✅ Available[/bold green]"
            # Build details string
            details = []
            if hw_type == HardwareType.CUDA and 'vram_gb' in capability.details:
                details.append(f"VRAM: {capability.details['vram_gb']:.1f}GB")
            elif hw_type == HardwareType.MPS and 'chip' in capability.details:
                details.append(capability.details['chip'])
            elif hw_type == HardwareType.OPENVINO and 'version' in capability.details:
                details.append(f"v{capability.details['version']}")
            elif hw_type == HardwareType.CPU and 'cpu_count' in capability.details:
                details.append(f"{capability.details['cpu_count']} cores")
            detail_str = ", ".join(details) if details else ""
        else:
            status = "[dim]❌ Not Available[/dim]"
            detail_str = ""
        
        hw_table.add_row(hw_type.value.upper(), status, detail_str)
    
    console.print(hw_table)
    
    # Show recommended backend
    best = HardwareDetector.select_best()
    console.print(f"\n[bold cyan]Recommended backend:[/bold cyan] [bold yellow]{best.value}[/bold yellow]")
    
    # Show UV info
    console.print()
    console.rule("[bold yellow]Package Manager[/bold yellow]")
    
    uv_manager = UVManager()
    uv_info = uv_manager.get_info()
    
    uv_table = Table(show_header=False, box=None)
    uv_table.add_column("Property", style="cyan")
    uv_table.add_column("Value", style="yellow")
    
    if 'uv_version' in uv_info:
        uv_table.add_row("UV Version", uv_info['uv_version'])
    uv_table.add_row("UV Binary", uv_info['uv_binary'] or "Not found")
    uv_table.add_row("Virtual Env", str(uv_info['venv_path']))
    uv_table.add_row("Packages Installed", str(uv_info.get('package_count', 0)))
    
    console.print(uv_table)

@app.command(name="dev-check")
def dev_check(
    backend: str = typer.Argument("all", help="Backend to check (cuda/openvino/mps/cpu/all)"),
):
    """
    Check development readiness for specific backend
    """
    console.rule(f"[bold cyan]Development Environment Check: {backend.upper()}[/bold cyan]")
    console.print()
    
    backends = ["cuda", "openvino", "mps", "cpu"] if backend == "all" else [backend]
    
    for b in backends:
        if b == "cuda":
            report = DeveloperChecker.check_cuda_development()
        elif b == "openvino":
            report = DeveloperChecker.check_openvino_development()
        elif b == "mps":
            report = DeveloperChecker.check_mps_development()
        elif b == "cpu":
            report = DeveloperChecker.check_cpu_development()
        else:
            console.print(f"[red]Unknown backend: {b}[/red]")
            continue
        
        # Display report as panel
        if report.get('can_develop'):
            panel_style = "green"
            title = f"[bold green]{report['ready_message']}[/bold green]"
        else:
            panel_style = "red"
            title = f"[bold red]{report['ready_message']}[/bold red]"
        
        # Build content
        lines = []
        for key, value in report.items():
            if key in ['can_develop', 'ready_message', 'missing']:
                continue
            
            if isinstance(value, bool):
                icon = "[green]✓[/green]" if value else "[red]✗[/red]"
                lines.append(f"{icon} {key.replace('_', ' ').title()}: {value}")
            elif key in ['vram_gb', 'chip', 'cuda_version']:
                lines.append(f"• {key.replace('_', ' ').title()}: [cyan]{value}[/cyan]")
        
        # Add missing components
        if report.get('missing'):
            lines.append("")
            lines.append("[bold red]Missing components:[/bold red]")
            for item in report['missing']:
                lines.append(f"  - {item}")
        
        content = "\n".join(lines) if lines else "Ready for development"
        
        panel = Panel(content, title=title, style=panel_style, expand=False)
        console.print(panel)
        
        if len(backends) > 1 and b != backends[-1]:
            console.print()

@app.command()
def setup(
    hardware: Optional[str] = typer.Option(None, "--hardware", help="Hardware backend to set up"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinstall"),
):
    """
    Set up the development environment with UV
    """
    console.rule("[bold cyan]MBED Environment Setup[/bold cyan]")
    console.print()
    
    # Detect hardware if not specified
    if not hardware:
        hardware = HardwareDetector.select_best().value
        console.print(f"[cyan]Auto-detected hardware:[/cyan] [bold yellow]{hardware}[/bold yellow]")
    
    # Validate hardware
    if hardware != "auto" and hardware != "cpu":
        hw_type = HardwareType(hardware)
        if not HardwareDetector.validate_hardware(hw_type):
            console.print(f"[red]Error: {hardware} is not available on this system[/red]")
            raise typer.Exit(1)
    
    console.print(f"\n[bold]Setting up environment for {hardware} backend...[/bold]\n")
    
    # Setup with UV
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Installing dependencies with UV...", total=None)
        
        if setup_environment(hardware):
            progress.update(task, description="[green]✅ Environment setup complete!")
        else:
            progress.update(task, description="[red]❌ Setup failed")
            raise typer.Exit(1)
    
    console.print("\n[bold green]✅ Environment ready![/bold green]")
    console.print(f"\nYou can now use: [bold cyan]mbed generate[/bold cyan] to process files")

@app.command()
def generate(
    path: Path = typer.Argument(..., help="Path to file or directory to process"),
    hardware: Optional[str] = typer.Option(None, "--hardware", "--accel", help="Hardware backend"),
    model: str = typer.Option("nomic-embed-text", "--model", "-m", help="Embedding model"),
    database: str = typer.Option("chromadb", "--database", "--db", help="Vector database"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for results"),
):
    """
    Generate embeddings for files using the unified pipeline
    """
    from .core.config import MBEDSettings
    from .core.orchestrator import EmbeddingOrchestrator
    import asyncio
    import glob
    
    # Setup logging level
    log_level = "DEBUG" if verbose else "INFO"
    logging.basicConfig(level=getattr(logging, log_level), format='%(levelname)s: %(message)s')
    
    # Validate hardware if specified
    if hardware:
        hw_type = HardwareType(hardware)
        if not HardwareDetector.validate_hardware(hw_type):
            error_panel = Panel(
                f"[bold]Hardware '{hardware}' is not available[/bold]\n\n"
                f"Available backends:\n"
                f"• {', '.join(h.value for h in HardwareDetector.get_available())}\n\n"
                f"Use [cyan]mbed info --hardware[/cyan] for details",
                title="[red]Hardware Error[/red]",
                style="red"
            )
            console.print(error_panel)
            raise typer.Exit(1)
    else:
        hardware = HardwareDetector.select_best().value
    
    # Validate input path
    if not path.exists():
        console.print(f"[red]Error: Path '{path}' does not exist[/red]")
        raise typer.Exit(1)
    
    # Collect files to process
    files_to_process = []
    if path.is_file():
        files_to_process = [path]
    elif path.is_dir():
        # Find all supported files in directory
        supported_extensions = ['.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.json', '.html', '.htm']
        for ext in supported_extensions:
            files_to_process.extend(path.glob(f'**/*{ext}'))
    
    if not files_to_process:
        console.print("[yellow]No supported files found to process[/yellow]")
        console.print("Supported file types: .txt, .md, .py, .js, .ts, .jsx, .tsx, .rs, .json, .html, .htm")
        raise typer.Exit(0)
    
    console.print(f"[cyan]Found {len(files_to_process)} files to process[/cyan]")
    
    # Create configuration
    config = MBEDSettings(
        hardware=hardware,
        model=model,
        database=database,
        db_path=output_dir / "database" if output_dir else Path(".mbed/database"),
        log_level=log_level
    )
    
    console.print()
    console.rule("[bold cyan]Processing Configuration[/bold cyan]")
    
    # Display processing info
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="yellow")
    
    info_table.add_row("Files to process", str(len(files_to_process)))
    info_table.add_row("Hardware backend", hardware)
    info_table.add_row("Embedding model", model)
    info_table.add_row("Vector database", database)
    info_table.add_row("Output directory", str(config.db_path))
    
    console.print(info_table)
    console.print()
    
    # Initialize and run orchestrator
    async def process_files_async():
        """Async wrapper for file processing"""
        with EmbeddingOrchestrator(config) as orchestrator:
            console.rule("[bold magenta]Processing Pipeline[/bold magenta]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Processing files...", total=None)
                
                result = await orchestrator.process_files(files_to_process)
                
                if result.is_err():
                    progress.update(task, description="[red]❌ Processing failed")
                    console.print(f"[red]Error: {result.unwrap_err()}[/red]")
                    return False
                else:
                    progress.update(task, description="[green]✅ Processing complete")
                    processing_result = result.unwrap()
                    
                    # Display results
                    console.print()
                    console.rule("[bold green]Processing Results[/bold green]")
                    
                    results_table = Table(show_header=False, box=None)
                    results_table.add_column("Metric", style="cyan")
                    results_table.add_column("Value", style="green")
                    
                    results_table.add_row("Files processed", str(processing_result.files_processed))
                    results_table.add_row("Chunks created", str(processing_result.chunks_created))
                    results_table.add_row("Embeddings generated", str(processing_result.embeddings_generated))
                    results_table.add_row("Processing time", f"{processing_result.duration_seconds:.2f}s")
                    
                    console.print(results_table)
                    
                    if processing_result.errors:
                        console.print(f"\n[yellow]Errors encountered ({len(processing_result.errors)}):[/yellow]")
                        for error in processing_result.errors[:5]:  # Show first 5 errors
                            console.print(f"  • {error}")
                        if len(processing_result.errors) > 5:
                            console.print(f"  ... and {len(processing_result.errors) - 5} more")
                    
                    console.print(f"\n[bold green]✅ Processing complete![/bold green]")
                    console.print(f"Results saved to: [cyan]{config.db_path}[/cyan]")
                    
                    return True
    
    # Run the async processing
    try:
        success = asyncio.run(process_files_async())
        if not success:
            raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Processing interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)

@app.command()
def config(
    show: bool = typer.Option(True, "--show", help="Show current configuration"),
    validate: bool = typer.Option(False, "--validate", help="Validate configuration"),
):
    """
    Show or validate configuration settings
    """
    from .core.config import get_settings, print_config
    
    settings = get_settings()
    
    if validate:
        # Validate hardware backend
        if settings.hardware != "auto":
            from .core.hardware import HardwareDetector, HardwareType
            try:
                hw_type = HardwareType(settings.hardware)
                if HardwareDetector.validate_hardware(hw_type):
                    console.print(f"[green]✅ Hardware backend '{settings.hardware}' is available[/green]")
                else:
                    console.print(f"[red]❌ Hardware backend '{settings.hardware}' is not available[/red]")
            except ValueError:
                console.print(f"[red]❌ Invalid hardware backend: {settings.hardware}[/red]")
        
        # Check paths
        if settings.db_path.exists():
            console.print(f"[green]✅ Database path exists: {settings.db_path}[/green]")
        else:
            console.print(f"[yellow]⚠️ Database path does not exist: {settings.db_path}[/yellow]")
        
        console.print("\n[bold]Configuration is valid[/bold]")
    
    if show:
        print_config(settings)

@app.command()
def version():
    """
    Show version information
    """
    console.print(f"[bold cyan]mbed[/bold cyan] version [bold yellow]{__version__}[/bold yellow]")
    console.print(f"[dim]Unified semantic embedding pipeline[/dim]")

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()