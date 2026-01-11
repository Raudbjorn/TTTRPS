#!/usr/bin/env python3
"""
Unified MBED Command - CLI Template
This is the initial skeleton for the mbed command with hardware detection
and graceful failure for missing hardware.
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import click

__version__ = "0.0.1-dev"

class HardwareType(Enum):
    """Supported hardware acceleration types"""
    CUDA = "cuda"
    OPENVINO = "openvino"
    MPS = "mps"
    CPU = "cpu"
    AUTO = "auto"

class HardwareDetector:
    """Detects available hardware acceleration"""
    
    @staticmethod
    def detect_cuda() -> bool:
        """Check if CUDA is available"""
        try:
            # Check nvidia-smi
            result = subprocess.run(
                ['nvidia-smi'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False
            
            # Try to import torch and check CUDA
            try:
                import torch
                return torch.cuda.is_available()
            except ImportError:
                # nvidia-smi exists but PyTorch not installed yet
                return True
                
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def detect_openvino() -> bool:
        """Check if OpenVINO is available"""
        try:
            # Check for OpenVINO runtime
            import openvino
            return True
        except ImportError:
            # Check environment variable
            return os.environ.get('INTEL_OPENVINO_DIR') is not None
    
    @staticmethod
    def detect_mps() -> bool:
        """Check if Apple Metal Performance Shaders are available"""
        if platform.system() != 'Darwin':
            return False
        
        try:
            # Check if we're on Apple Silicon
            import subprocess
            result = subprocess.run(
                ['sysctl', '-n', 'hw.optional.arm64'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() != '1':
                return False
            
            # Try to import torch and check MPS
            try:
                import torch
                return torch.backends.mps.is_available()
            except ImportError:
                # Apple Silicon detected but PyTorch not installed yet
                return True
                
        except Exception:
            return False
    
    @classmethod
    def detect_all(cls) -> Dict[HardwareType, bool]:
        """Detect all available hardware"""
        return {
            HardwareType.CUDA: cls.detect_cuda(),
            HardwareType.OPENVINO: cls.detect_openvino(),
            HardwareType.MPS: cls.detect_mps(),
            HardwareType.CPU: True  # Always available
        }
    
    @classmethod
    def get_available(cls) -> List[HardwareType]:
        """Get list of available hardware types"""
        detected = cls.detect_all()
        return [hw for hw, available in detected.items() if available]
    
    @classmethod
    def select_best(cls) -> HardwareType:
        """Select the best available hardware"""
        available = cls.get_available()
        
        # Priority order
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

class DeveloperChecker:
    """Check if developer can work on specific backend"""
    
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
        
        # Check hardware
        if HardwareDetector.detect_cuda():
            report['hardware'] = True
        else:
            report['missing'].append("NVIDIA GPU not detected")
            return report
        
        # Check CUDA toolkit
        try:
            result = subprocess.run(
                ['nvcc', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                report['cuda_toolkit'] = True
        except FileNotFoundError:
            report['missing'].append("CUDA toolkit (nvcc) not found")
        
        # Check PyTorch with CUDA
        try:
            import torch
            if torch.cuda.is_available():
                report['pytorch_cuda'] = True
                # Get VRAM
                report['vram_gb'] = torch.cuda.get_device_properties(0).total_memory / 1e9
            else:
                report['missing'].append("PyTorch CUDA support not available")
        except ImportError:
            report['missing'].append("PyTorch not installed")
        
        report['can_develop'] = (
            report['hardware'] and 
            report['cuda_toolkit'] and 
            report['pytorch_cuda']
        )
        
        return report
    
    @staticmethod
    def check_openvino_development() -> Dict[str, Any]:
        """Check OpenVINO development readiness"""
        report = {
            'can_develop': False,
            'intel_gpu': False,
            'openvino_runtime': False,
            'model_optimizer': False,
            'missing': []
        }
        
        # Check for Intel GPU (simplified check)
        try:
            result = subprocess.run(
                ['lspci'],
                capture_output=True,
                text=True
            )
            if 'Intel' in result.stdout and ('Graphics' in result.stdout or 'VGA' in result.stdout):
                report['intel_gpu'] = True
        except:
            report['missing'].append("Cannot detect Intel GPU")
        
        # Check OpenVINO
        if HardwareDetector.detect_openvino():
            report['openvino_runtime'] = True
            
            # Check model optimizer
            try:
                import openvino.tools.mo
                report['model_optimizer'] = True
            except ImportError:
                report['missing'].append("OpenVINO Model Optimizer not found")
        else:
            report['missing'].append("OpenVINO runtime not installed")
        
        report['can_develop'] = (
            report['intel_gpu'] and 
            report['openvino_runtime'] and 
            report['model_optimizer']
        )
        
        return report
    
    @staticmethod
    def check_mps_development() -> Dict[str, Any]:
        """Check MPS development readiness"""
        report = {
            'can_develop': False,
            'apple_silicon': False,
            'pytorch_mps': False,
            'xcode_tools': False,
            'missing': []
        }
        
        # Check Apple Silicon
        if HardwareDetector.detect_mps():
            report['apple_silicon'] = True
        else:
            report['missing'].append("Apple Silicon Mac required")
            return report
        
        # Check Xcode command line tools
        try:
            result = subprocess.run(
                ['xcode-select', '-p'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                report['xcode_tools'] = True
        except:
            report['missing'].append("Xcode command line tools not installed")
        
        # Check PyTorch MPS
        try:
            import torch
            if torch.backends.mps.is_available():
                report['pytorch_mps'] = True
            else:
                report['missing'].append("PyTorch MPS support not available")
        except ImportError:
            report['missing'].append("PyTorch not installed")
        
        report['can_develop'] = (
            report['apple_silicon'] and 
            report['pytorch_mps'] and 
            report['xcode_tools']
        )
        
        return report

# Click command group
@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version')
@click.option('--hardware', '--accel', type=click.Choice(['cuda', 'openvino', 'mps', 'cpu', 'auto']), 
              default='auto', help='Hardware acceleration backend')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.pass_context
def cli(ctx, version, hardware, debug):
    """Unified MBED - Semantic embedding pipeline for code"""
    
    if version:
        click.echo(f"mbed version {__version__}")
        sys.exit(0)
    
    # Store options in context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['hardware'] = HardwareType(hardware)
    
    # Hardware validation if specific backend requested
    if hardware != 'auto':
        hw_type = HardwareType(hardware)
        available = HardwareDetector.get_available()
        
        if hw_type not in available:
            click.secho(f"❌ Error: {hardware} acceleration not available", fg='red', err=True)
            click.echo(f"Available backends: {', '.join(h.value for h in available)}", err=True)
            
            if hardware == 'cuda':
                click.echo("\nTo use CUDA acceleration, you need:", err=True)
                click.echo("  • NVIDIA GPU with CUDA support", err=True)
                click.echo("  • CUDA toolkit installed", err=True)
                click.echo("  • PyTorch with CUDA support", err=True)
                click.echo("\nRun 'mbed dev-check cuda' for detailed diagnostics", err=True)
            elif hardware == 'openvino':
                click.echo("\nTo use OpenVINO acceleration, you need:", err=True)
                click.echo("  • Intel GPU (Xe, Arc, or integrated)", err=True)
                click.echo("  • OpenVINO runtime installed", err=True)
                click.echo("\nRun 'mbed dev-check openvino' for detailed diagnostics", err=True)
            elif hardware == 'mps':
                click.echo("\nTo use MPS acceleration, you need:", err=True)
                click.echo("  • Apple Silicon Mac (M1/M2/M3)", err=True)
                click.echo("  • PyTorch with MPS support", err=True)
                click.echo("\nRun 'mbed dev-check mps' for detailed diagnostics", err=True)
            
            sys.exit(1)
    
    # Show help if no command
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.command()
@click.argument('backend', type=click.Choice(['cuda', 'openvino', 'mps', 'cpu', 'all']))
def dev_check(backend):
    """Check development readiness for specific backend"""
    
    click.echo(f"🔍 Checking development readiness for {backend}...\n")
    
    if backend == 'all':
        backends = ['cuda', 'openvino', 'mps', 'cpu']
    else:
        backends = [backend]
    
    for b in backends:
        if b == 'cuda':
            report = DeveloperChecker.check_cuda_development()
            _print_dev_report("CUDA", report)
        elif b == 'openvino':
            report = DeveloperChecker.check_openvino_development()
            _print_dev_report("OpenVINO", report)
        elif b == 'mps':
            report = DeveloperChecker.check_mps_development()
            _print_dev_report("MPS", report)
        elif b == 'cpu':
            click.echo("✅ CPU Backend: Always ready for development")
            click.echo("   No special hardware required\n")

def _print_dev_report(backend: str, report: Dict[str, Any]):
    """Print development readiness report"""
    if report['can_develop']:
        click.secho(f"✅ {backend} Backend: Ready for development", fg='green')
    else:
        click.secho(f"❌ {backend} Backend: Not ready for development", fg='red')
    
    # Print details
    for key, value in report.items():
        if key in ['can_develop', 'missing']:
            continue
        
        if isinstance(value, bool):
            icon = "✓" if value else "✗"
            color = 'green' if value else 'red'
            click.echo(f"   {icon} {key.replace('_', ' ').title()}: ", nl=False)
            click.secho(str(value), fg=color)
        elif key == 'vram_gb' and value > 0:
            click.echo(f"   • VRAM: {value:.1f} GB")
    
    # Print missing components
    if report.get('missing'):
        click.echo("   Missing components:")
        for missing in report['missing']:
            click.echo(f"     - {missing}")
    
    click.echo()

@cli.command()
def generate():
    """Generate embeddings for files (NOT IMPLEMENTED)"""
    click.secho("⚠️  generate command not yet implemented", fg='yellow')
    click.echo("This will process files and generate embeddings")
    raise NotImplementedError("generate command coming in Phase 2")

@cli.command()
def search():
    """Search using semantic similarity (NOT IMPLEMENTED)"""
    click.secho("⚠️  search command not yet implemented", fg='yellow')
    click.echo("This will search your embeddings")
    raise NotImplementedError("search command coming in Phase 6")

@cli.command()
def serve():
    """Start MCP/API server (NOT IMPLEMENTED)"""
    click.secho("⚠️  serve command not yet implemented", fg='yellow')
    click.echo("This will start the MCP or REST API server")
    raise NotImplementedError("serve command coming in Phase 7")

@cli.command()
@click.pass_context
def info(ctx):
    """Show system information and available backends"""
    click.echo("MBED System Information")
    click.echo("=" * 40)
    click.echo(f"Version: {__version__}")
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo(f"Platform: {platform.platform()}")
    click.echo()
    
    click.echo("Hardware Detection:")
    click.echo("-" * 40)
    
    detected = HardwareDetector.detect_all()
    for hw, available in detected.items():
        icon = "✓" if available else "✗"
        color = 'green' if available else 'white'
        click.secho(f"{icon} {hw.value:10} : {'Available' if available else 'Not Available'}", fg=color)
    
    click.echo()
    best = HardwareDetector.select_best()
    click.echo(f"Recommended backend: {best.value}")
    
    if ctx.obj.get('debug'):
        click.echo("\nDebug Information:")
        click.echo("-" * 40)
        click.echo(f"Context: {ctx.obj}")
        
        # Show environment variables
        relevant_env = {
            'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES', 'not set'),
            'INTEL_OPENVINO_DIR': os.environ.get('INTEL_OPENVINO_DIR', 'not set'),
            'PATH': 'set' if os.environ.get('PATH') else 'not set'
        }
        click.echo("Environment:")
        for key, value in relevant_env.items():
            click.echo(f"  {key}: {value}")

@cli.command()
def migrate():
    """Migrate embeddings between databases (NOT IMPLEMENTED)"""
    click.secho("⚠️  migrate command not yet implemented", fg='yellow')
    click.echo("This will migrate embeddings between vector databases")
    raise NotImplementedError("migrate command coming in Phase 6")

@cli.command()
def resume():
    """Resume interrupted processing (NOT IMPLEMENTED)"""
    click.secho("⚠️  resume command not yet implemented", fg='yellow')
    click.echo("This will resume from last checkpoint")
    raise NotImplementedError("resume command coming in Phase 1")

if __name__ == '__main__':
    cli()