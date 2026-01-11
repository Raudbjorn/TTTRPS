# CLI Reference Guide

The MBED Unified system provides a comprehensive command-line interface (`mbed`) that serves as the main entry point for all operations.

## Installation and Setup

First, ensure you have the `mbed` executable available. From the project root:

```bash
# Make the CLI executable
chmod +x ./mbed

# Add to PATH (optional)
export PATH="$PWD:$PATH"
```

## Global Options

All commands support these global options:

- `--help`: Show help for any command
- `--version`: Show version information

## Available Commands

### `mbed info`

Display comprehensive system information including hardware detection results.

```bash
mbed info [OPTIONS]
```

**Options:**
- `--hardware, -h`: Show detailed hardware information
- `--config, -c`: Show configuration details

**Examples:**
```bash
# Basic system info
mbed info

# Detailed hardware info
mbed info --hardware

# Show configuration
mbed info --config
```

**Output includes:**
- Python version and platform information
- Available hardware backends (CUDA, MPS, OpenVINO, CPU)
- Hardware-specific details (VRAM, chip types, versions)
- Recommended backend selection
- UV package manager status

### `mbed generate`

**Primary command** - Generate embeddings for files using the unified pipeline.

```bash
mbed generate PATH [OPTIONS]
```

**Arguments:**
- `PATH`: Path to file or directory to process (required)

**Options:**
- `--hardware, --accel TEXT`: Hardware backend (cuda/mps/openvino/cpu/auto)
- `--model, -m TEXT`: Embedding model [default: nomic-embed-text]
- `--database, --db TEXT`: Vector database [default: chromadb]  
- `--output, -o PATH`: Output directory for results
- `--verbose, -v`: Enable verbose output
- `--help`: Show help

**Supported File Types:**
- Text: `.txt`, `.md`
- Code: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.rs`
- Data: `.json`
- Web: `.html`, `.htm`

**Examples:**
```bash
# Process single file with auto-detected hardware
mbed generate document.txt

# Process directory with specific hardware
mbed generate /path/to/docs --hardware cuda

# Use different model and verbose output
mbed generate codebase/ --model mxbai-embed-large --verbose

# Specify output directory
mbed generate docs/ --output ./results

# Process with specific database backend
mbed generate files/ --database faiss --hardware cuda

# Full configuration example
mbed generate /data/documents \
  --hardware cuda \
  --model nomic-embed-text \
  --database chromadb \
  --output ./embeddings \
  --verbose
```

**Processing Pipeline:**
1. **File Discovery**: Recursively finds supported files
2. **Hardware Detection**: Selects optimal backend
3. **Content Chunking**: Intelligent text segmentation
4. **Embedding Generation**: Vector creation using selected hardware
5. **Storage**: Saves to specified database backend

**Output:**
- Processing statistics (files, chunks, embeddings)
- Performance metrics (processing time)
- Error reports (if any)
- Storage location information

### `mbed setup`

Set up the development environment with UV package manager.

```bash
mbed setup [OPTIONS]
```

**Options:**
- `--hardware TEXT`: Hardware backend to set up dependencies for
- `--force, -f`: Force reinstall of dependencies

**Examples:**
```bash
# Auto-detect and setup for best hardware
mbed setup

# Setup for specific hardware
mbed setup --hardware cuda

# Force reinstall
mbed setup --hardware mps --force
```

**What it does:**
- Detects available hardware
- Installs hardware-specific dependencies
- Sets up virtual environment with UV
- Validates installation

### `mbed dev-check`

Check development environment readiness for specific backends.

```bash
mbed dev-check [BACKEND]
```

**Arguments:**
- `BACKEND`: Backend to check (cuda/openvino/mps/cpu/all) [default: all]

**Examples:**
```bash
# Check all backends
mbed dev-check

# Check specific backend
mbed dev-check cuda
mbed dev-check openvino
```

**Checks performed:**
- Hardware availability
- Required dependencies
- Development tools
- Version compatibility
- Missing components

### `mbed config`

Display and validate configuration settings.

```bash
mbed config [OPTIONS]  
```

**Options:**
- `--show`: Show current configuration (default: true)
- `--validate`: Validate configuration settings

**Examples:**
```bash
# Show current config
mbed config

# Validate configuration
mbed config --validate
```

### `mbed version`

Show version information.

```bash
mbed version
```

## Configuration

MBED uses a layered configuration system with the following precedence (highest to lowest):

1. **CLI Arguments**: Direct command-line options
2. **Environment Variables**: `MBED_*` prefixed variables
3. **Environment File**: `.env` file in current directory
4. **Project Config**: `pyproject.toml` `[tool.mbed]` section
5. **Default Values**: Built-in defaults

### Environment Variables

All configuration can be controlled via environment variables:

```bash
# Hardware and performance
export MBED_HARDWARE=cuda
export MBED_MODEL=nomic-embed-text
export MBED_BATCH_SIZE=256
export MBED_WORKERS=8

# CUDA-specific
export MBED_MIXED_PRECISION=true
export MBED_MULTI_GPU=true
export MBED_CUDA_DEVICE=0
export MBED_CUDA_VRAM_RESERVED_GB=2.0

# Database and storage
export MBED_DATABASE=chromadb
export MBED_DB_PATH=".mbed/db"

# Processing
export MBED_CHUNK_SIZE=512
export MBED_CHUNK_OVERLAP=128
export MBED_NORMALIZE_EMBEDDINGS=true

# Logging
export MBED_LOG_LEVEL=INFO
```

### Example .env File

```env
# .env file for MBED configuration
MBED_HARDWARE=cuda
MBED_MODEL=nomic-embed-text
MBED_BATCH_SIZE=256
MBED_WORKERS=8
MBED_DATABASE=chromadb
MBED_DB_PATH=.mbed/database
MBED_LOG_LEVEL=INFO
```

## Hardware Backend Selection

### Automatic Detection
By default, MBED uses automatic hardware detection with this fallback chain:
1. **CUDA** - NVIDIA GPUs (if available)
2. **MPS** - Apple Silicon (if available)  
3. **OpenVINO** - Intel hardware (if available)
4. **CPU** - Always available fallback

### Manual Selection
Override automatic detection:

```bash
# Force specific backend
mbed generate docs/ --hardware cuda
mbed generate docs/ --hardware mps
mbed generate docs/ --hardware openvino
mbed generate docs/ --hardware cpu
```

### Backend-Specific Features

#### CUDA Backend
- Dynamic batch sizing based on VRAM
- Mixed precision (FP16) support
- Multi-GPU support
- FAISS-GPU integration
- Automatic OOM recovery

```bash
# CUDA with optimizations
export MBED_MIXED_PRECISION=true
export MBED_MULTI_GPU=true
export MBED_CUDA_VRAM_RESERVED_GB=1.5
mbed generate docs/ --hardware cuda
```

#### Apple MPS Backend
- Optimized for Apple Silicon
- Metal Performance Shaders acceleration
- Memory-efficient processing

#### OpenVINO Backend
- Intel hardware optimization
- CPU and iGPU acceleration
- Model optimization support

#### CPU Backend
- Universal fallback
- Multi-threaded processing
- No hardware dependencies

## Common Workflows

### Quick Start
```bash
# 1. Check system capabilities
mbed info

# 2. Process some files
mbed generate ./documents

# 3. Check results
ls .mbed/
```

### Development Workflow
```bash
# 1. Check development environment
mbed dev-check all

# 2. Setup environment for best hardware
mbed setup

# 3. Process with verbose output
mbed generate codebase/ --verbose

# 4. Validate configuration
mbed config --validate
```

### Production Workflow
```bash
# 1. Set production config via environment
export MBED_HARDWARE=cuda
export MBED_BATCH_SIZE=512
export MBED_WORKERS=16
export MBED_DATABASE=faiss

# 2. Process large dataset
mbed generate /data/corpus --output /data/embeddings

# 3. Monitor processing
mbed generate /data/corpus --verbose
```

## Error Handling

### Common Issues

#### Hardware Not Available
```bash
$ mbed generate docs/ --hardware cuda
Error: Hardware 'cuda' is not available
Available backends: cpu, mps
Use mbed info --hardware for details
```

**Solution**: Use `mbed info` to check available hardware, or omit `--hardware` for auto-detection.

#### No Supported Files
```bash
$ mbed generate empty_dir/
No supported files found to process
Supported file types: .txt, .md, .py, .js, .ts, .jsx, .tsx, .rs, .json, .html, .htm
```

**Solution**: Ensure directory contains supported file types, or add files.

#### Memory Issues
```bash
$ mbed generate large_files/ --hardware cuda
CUDA out of memory error
```

**Solutions**: 
- Reduce batch size: `export MBED_BATCH_SIZE=64`
- Reserve more VRAM: `export MBED_CUDA_VRAM_RESERVED_GB=4.0`
- Use CPU fallback: `--hardware cpu`

### Debug Mode

Enable verbose output for debugging:

```bash
mbed generate docs/ --verbose
```

This shows:
- Detailed processing steps
- Hardware detection results
- File processing status
- Performance metrics
- Full error traces

## Integration Examples

### CI/CD Pipeline
```yaml
# .github/workflows/embeddings.yml
- name: Generate embeddings
  run: |
    export MBED_HARDWARE=cpu  # Reliable in CI
    export MBED_BATCH_SIZE=64  # Conservative for CI resources
    ./mbed generate docs/ --output ./embeddings
```

### Shell Scripts
```bash
#!/bin/bash
# process_docs.sh

set -e

echo "Checking MBED system..."
./mbed info

echo "Processing documentation..."
./mbed generate docs/ \
  --hardware auto \
  --model nomic-embed-text \
  --output ./doc_embeddings \
  --verbose

echo "Embeddings saved to ./doc_embeddings"
```

### Python Integration
```python
import subprocess
import json

# Run MBED via subprocess
result = subprocess.run([
    './mbed', 'generate', 'documents/',
    '--hardware', 'cuda',
    '--output', 'embeddings/'
], capture_output=True, text=True)

if result.returncode == 0:
    print("Embeddings generated successfully")
else:
    print(f"Error: {result.stderr}")
```

## Performance Tuning

### Batch Size Optimization
```bash
# Small files / limited memory
export MBED_BATCH_SIZE=32

# Large GPU memory
export MBED_BATCH_SIZE=512

# Production processing
export MBED_BATCH_SIZE=256
```

### Worker Configuration
```bash
# Match CPU cores
export MBED_WORKERS=$(nproc)

# Conservative setting
export MBED_WORKERS=4

# High-throughput processing
export MBED_WORKERS=16
```

### Hardware-Specific Tuning

#### CUDA Optimization
```bash
export MBED_MIXED_PRECISION=true      # Enable FP16
export MBED_MULTI_GPU=true            # Use all GPUs
export MBED_CUDA_VRAM_RESERVED_GB=2.0 # Reserve VRAM
```

#### CPU Optimization
```bash
export MBED_WORKERS=16                # High parallelism
export MBED_BATCH_SIZE=128           # Moderate batching
```