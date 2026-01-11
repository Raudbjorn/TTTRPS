#!/usr/bin/env python3
"""
Example usage of the unified MBED system
"""

import sys
from pathlib import Path
import logging
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mbed.core.config import MBEDSettings, get_settings
from mbed.core.hardware import HardwareDetector
from mbed.backends.base import BackendFactory
from mbed.databases.base import DatabaseFactory

# Import backends and databases to register them
import mbed.backends.cpu
import mbed.backends.cuda
import mbed.backends.openvino
import mbed.backends.mps
import mbed.backends.ollama
import mbed.databases.chromadb

console = Console()
logging.basicConfig(level=logging.INFO)


def main():
    """Main example function"""
    console.print("\n[bold cyan]MBED Unified System Example[/bold cyan]\n")

    # 1. Hardware Detection
    console.print("[yellow]1. Detecting Available Hardware...[/yellow]")
    available_hardware = HardwareDetector.get_available()

    table = Table(title="Available Hardware", show_header=True)
    table.add_column("Hardware", style="cyan")
    table.add_column("Available", style="green")
    table.add_column("Details", style="dim")

    for hw_type, capability in HardwareDetector.detect_all().items():
        table.add_row(
            hw_type.value,
            "✅" if capability.available else "❌",
            str(capability.details.get("reason", "Available"))
        )

    console.print(table)

    # 2. Configuration
    console.print("\n[yellow]2. Loading Configuration...[/yellow]")
    config = get_settings()

    # Select best available backend
    best_hardware = HardwareDetector.select_best()
    console.print(f"Selected backend: [green]{best_hardware.value}[/green]")

    # Update config with selected hardware
    config.hardware = best_hardware.value

    # 3. Initialize Embedding Backend
    console.print("\n[yellow]3. Initializing Embedding Backend...[/yellow]")

    # Try Ollama first if available
    try:
        from mbed.backends.ollama import OllamaBackend
        ollama = OllamaBackend(config)
        if ollama.is_available():
            console.print("[green]Using Ollama backend[/green]")
            backend = ollama
            backend.initialize()
        else:
            raise RuntimeError("Ollama not available")
    except Exception as e:
        console.print(f"[yellow]Ollama not available: {e}[/yellow]")
        console.print(f"[green]Using {best_hardware.value} backend[/green]")
        backend = BackendFactory.create(config)

    # Show backend info
    info = backend.get_info()
    console.print(f"Backend: {info['backend']}")
    console.print(f"Model: {info.get('model', 'default')}")
    console.print(f"Embedding dimension: {info.get('embedding_dim', 'unknown')}")

    # 4. Generate Embeddings
    console.print("\n[yellow]4. Generating Sample Embeddings...[/yellow]")

    sample_texts = [
        "The unified MBED system supports multiple hardware backends.",
        "ChromaDB provides efficient vector storage and retrieval.",
        "Ollama enables local LLM inference for embeddings.",
        "The system automatically detects and uses the best available hardware."
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating embeddings...", total=None)

        try:
            embeddings = backend.generate_embeddings(sample_texts)
            progress.update(task, completed=True)

            console.print(f"[green]✅ Generated {embeddings.shape[0]} embeddings[/green]")
            console.print(f"Embedding shape: {embeddings.shape}")
        except Exception as e:
            console.print(f"[red]❌ Failed to generate embeddings: {e}[/red]")
            console.print("[yellow]Using random embeddings for demo[/yellow]")
            embeddings = np.random.randn(len(sample_texts), 768)

    # 5. Initialize Database
    console.print("\n[yellow]5. Initializing Vector Database...[/yellow]")

    try:
        db = DatabaseFactory.create("chromadb", config)
        db.initialize()
        console.print("[green]✅ ChromaDB initialized[/green]")

        # 6. Store Embeddings
        console.print("\n[yellow]6. Storing Documents...[/yellow]")

        metadata = [
            {"source": "documentation", "topic": "system"},
            {"source": "documentation", "topic": "database"},
            {"source": "documentation", "topic": "models"},
            {"source": "documentation", "topic": "hardware"}
        ]

        db.add_documents(
            texts=sample_texts,
            embeddings=embeddings,
            metadata=metadata
        )

        doc_count = db.get_count()
        console.print(f"[green]✅ Stored {len(sample_texts)} documents[/green]")
        console.print(f"Total documents in database: {doc_count}")

        # 7. Search Example
        console.print("\n[yellow]7. Performing Similarity Search...[/yellow]")

        query = "What hardware options are available?"
        console.print(f"Query: [cyan]{query}[/cyan]")

        # Generate query embedding
        query_embedding = backend.generate_embeddings([query])[0]

        # Search
        results = db.search(query_embedding, k=3)

        console.print("\n[bold]Search Results:[/bold]")
        for i, (text, distance, meta) in enumerate(results, 1):
            console.print(f"\n{i}. [green]Distance: {distance:.4f}[/green]")
            console.print(f"   Source: {meta.get('source', 'unknown')}")
            console.print(f"   Text: {text[:100]}...")

    except ImportError as e:
        console.print(f"[red]❌ ChromaDB not installed: {e}[/red]")
        console.print("[yellow]Install with: pip install chromadb[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Database error: {e}[/red]")

    # Summary
    console.print("\n[bold green]✨ Example Complete![/bold green]")
    console.print("\nThis example demonstrated:")
    console.print("• Hardware detection and selection")
    console.print("• Backend initialization with fallback")
    console.print("• Embedding generation")
    console.print("• Vector database operations")
    console.print("• Similarity search")


if __name__ == "__main__":
    main()