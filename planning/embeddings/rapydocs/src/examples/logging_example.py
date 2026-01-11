#!/usr/bin/env python3
"""
Example of using the unified logging system in mbed components
"""

import time
import random
from pathlib import Path
from typing import List

# In real implementation, this would be:
# from src.core.logging import logger, create_progress, hardware_status, print_panel, rule
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler
import logging

# Setup
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger("mbed")

def simulate_embedding_generation():
    """Simulate the embedding generation process with rich output"""
    
    console.rule("[bold cyan]MBED Embedding Generation[/bold cyan]")
    console.print()
    
    # Phase 1: Hardware Detection
    console.print("[bold]Phase 1: Hardware Detection[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Detecting hardware...", total=None)
        time.sleep(1)
        progress.update(task, description="[yellow]Checking CUDA...")
        time.sleep(0.5)
        progress.update(task, description="[blue]Checking OpenVINO...")
        time.sleep(0.5)
        progress.update(task, description="[magenta]Checking MPS...")
        time.sleep(0.5)
    
    # Show hardware results
    hw_table = Table(title="Hardware Detection", show_header=True)
    hw_table.add_column("Backend", style="cyan")
    hw_table.add_column("Status", justify="center")
    hw_table.add_column("Selected", justify="center")
    
    hw_table.add_row("CUDA", "[red]❌ Not Available[/red]", "")
    hw_table.add_row("OpenVINO", "[red]❌ Not Available[/red]", "")
    hw_table.add_row("MPS", "[red]❌ Not Available[/red]", "")
    hw_table.add_row("CPU", "[green]✅ Available[/green]", "[yellow]✓[/yellow]")
    
    console.print(hw_table)
    logger.info("[green]✅ Using CPU backend[/green]")
    console.print()
    
    # Phase 2: File Discovery
    console.print("[bold]Phase 2: File Discovery[/bold]")
    files = [
        "src/main.py",
        "src/utils/helpers.py", 
        "src/models/encoder.py",
        "src/models/decoder.py",
        "tests/test_main.py"
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Discovering files...", total=len(files))
        
        for file in files:
            time.sleep(0.3)
            progress.update(task, advance=1, description=f"Found: {file}")
    
    logger.info(f"[green]✅ Discovered {len(files)} files[/green]")
    console.print()
    
    # Phase 3: Chunking
    console.print("[bold]Phase 3: Chunking Files[/bold]")
    
    chunk_table = Table(show_header=True)
    chunk_table.add_column("File", style="cyan")
    chunk_table.add_column("Size", justify="right")
    chunk_table.add_column("Chunks", justify="center")
    chunk_table.add_column("Strategy")
    
    total_chunks = 0
    for file in files:
        size = random.randint(100, 5000)
        chunks = size // 500 + 1
        total_chunks += chunks
        chunk_table.add_row(
            file,
            f"{size} tokens",
            str(chunks),
            "semantic" if "model" in file else "fixed"
        )
    
    console.print(chunk_table)
    logger.info(f"[green]✅ Created {total_chunks} chunks[/green]")
    console.print()
    
    # Phase 4: Embedding Generation
    console.print("[bold]Phase 4: Generating Embeddings[/bold]")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        "[cyan]{task.completed}/{task.total}[/cyan]",
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing chunks...", total=total_chunks)
        
        for i in range(total_chunks):
            time.sleep(0.1)  # Simulate processing
            progress.update(task, advance=1)
            
            # Simulate occasional warnings
            if i == 5:
                logger.warning("[yellow]⚠️  Large chunk detected, splitting...[/yellow]")
            if i == 10:
                logger.info("[blue]ℹ️  Switching to batch processing mode[/blue]")
    
    logger.info(f"[green]✅ Generated embeddings for {total_chunks} chunks[/green]")
    console.print()
    
    # Phase 5: Storage
    console.print("[bold]Phase 5: Storing in Vector Database[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Connecting to ChromaDB...", total=None)
        time.sleep(1)
        progress.update(task, description="[cyan]Creating collection...")
        time.sleep(0.5)
        progress.update(task, description="[cyan]Storing embeddings...")
        time.sleep(1)
        progress.update(task, description="[cyan]Building index...")
        time.sleep(0.5)
    
    logger.info("[green]✅ Successfully stored in ChromaDB[/green]")
    console.print()
    
    # Final Summary
    console.rule("[bold green]Processing Complete[/bold green]")
    
    summary = f"""[bold cyan]Summary:[/bold cyan]
• Files processed: {len(files)}
• Total chunks: {total_chunks}
• Embeddings generated: {total_chunks}
• Database: ChromaDB
• Backend used: CPU
• Processing time: 8.5 seconds
• Vectors dimension: 768
"""
    
    panel = Panel(summary, title="[bold green]✅ Success[/bold green]", style="green")
    console.print(panel)

def simulate_error_handling():
    """Show how errors are displayed with rich"""
    
    console.rule("[bold red]Error Handling Example[/bold red]")
    console.print()
    
    # Simulate a hardware error
    error_panel = Panel(
        "[bold red]Hardware acceleration requested but not available![/bold red]\n\n"
        "[yellow]You requested CUDA acceleration, but:[/yellow]\n"
        "• No NVIDIA GPU detected\n"
        "• CUDA toolkit not installed\n"
        "• PyTorch CUDA support missing\n\n"
        "[bold]Suggestions:[/bold]\n"
        "1. Use CPU backend instead: [cyan]mbed --accel cpu[/cyan]\n"
        "2. Install CUDA: https://developer.nvidia.com/cuda-downloads\n"
        "3. Check hardware: [cyan]mbed dev-check cuda[/cyan]",
        title="[red]❌ CUDA Not Available[/red]",
        style="red",
        expand=False
    )
    console.print(error_panel)
    console.print()
    
    # Simulate a warning
    warning_panel = Panel(
        "[yellow]Large file detected that may take significant time to process.[/yellow]\n\n"
        "File: [cyan]src/generated/api_client.py[/cyan]\n"
        "Size: [bold]125,000 tokens[/bold]\n\n"
        "[dim]Consider using --chunk-size flag to process in smaller pieces[/dim]",
        title="[yellow]⚠️  Performance Warning[/yellow]",
        style="yellow",
        expand=False
    )
    console.print(warning_panel)

def main():
    """Run the examples"""
    
    # Example 1: Normal processing
    simulate_embedding_generation()
    
    console.print("\n" * 2)
    
    # Example 2: Error handling
    simulate_error_handling()

if __name__ == "__main__":
    main()