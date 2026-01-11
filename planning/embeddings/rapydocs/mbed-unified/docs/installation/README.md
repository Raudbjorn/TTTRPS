# Installation Guide

This guide covers installation options for the MBED Unified System, from development setup to production deployment.

## Quick Start (Development)

For immediate setup using UV (recommended):

```bash
# 1. Clone or navigate to the project
cd mbed-unified

# 2. Run system check
./mbed info

# 3. Auto-setup environment
./mbed setup

# 4. Test with sample files
./mbed generate docs/ --verbose
```

## Prerequisites

### System Requirements

**Operating System:**
- Linux (Ubuntu 20.04+, RHEL 8+, CentOS 8+)
- macOS 11+ (Big Sur or later)
- Windows 10/11 with WSL2 (recommended)

**Python Requirements:**
- Python 3.11 or 3.12 (required)
- pip or uv package manager

**Hardware Requirements:**

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **RAM** | 8GB | 16GB | 32GB+ |
| **Storage** | 5GB free | 20GB SSD | 100GB+ NVMe |
| **CPU** | 4 cores | 8+ cores | 16+ cores |

**GPU Requirements (Optional):**
- **NVIDIA**: RTX 2060+ (6GB+ VRAM) / Tesla V100+ / A100+
- **Apple Silicon**: M1/M2/M3 with 16GB+ unified memory
- **Intel**: Arc series or integrated graphics with OpenVINO support

### Software Dependencies

**Required:**
- Git
- Python 3.11+
- UV package manager (auto-installed if missing)

**Optional (hardware-specific):**
- CUDA 11.8+ (for NVIDIA GPUs)
- Metal (for Apple Silicon - included in macOS)
- Intel OpenVINO Runtime 2024.0+ (for Intel hardware)

## Installation Methods

### Method 1: UV-Based Installation (Recommended)

UV provides the fastest and most reliable installation experience:

```bash
# 1. Install UV (if not present)
curl -LsSf https://astral.sh/uv/install.sh | sh
# OR: pip install uv

# 2. Clone the repository
git clone https://github.com/unified/mbed.git
cd mbed

# 3. Initialize with UV
uv sync

# 4. Setup for your hardware
./mbed setup
```

**Advantages:**
- 3-5x faster than pip
- Automatic dependency resolution
- Isolated environments
- Hardware-specific optimizations

### Method 2: Traditional pip Installation

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 2. Install core dependencies
pip install -r requirements.txt

# 3. Install hardware-specific extras
pip install -e .[cuda]      # For NVIDIA GPUs
pip install -e .[mps]       # For Apple Silicon
pip install -e .[openvino]  # For Intel hardware
pip install -e .[all]       # Everything
```

### Method 3: Docker Installation

```bash
# 1. Build Docker image
docker build -t mbed-unified .

# 2. Run with GPU support (NVIDIA)
docker run --gpus all -v $(pwd):/workspace mbed-unified

# 3. Run CPU-only
docker run -v $(pwd):/workspace mbed-unified
```

## Hardware-Specific Setup

### NVIDIA CUDA Setup

**Requirements:**
- NVIDIA GPU with Compute Capability 6.0+
- CUDA 11.8 or 12.x
- cuDNN 8.x
- NVIDIA drivers 520+

**Installation:**

```bash
# 1. Install NVIDIA CUDA Toolkit
# Ubuntu/Debian:
wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda_12.2.0_535.54.03_linux.run
sudo sh cuda_12.2.0_535.54.03_linux.run

# 2. Install CUDA dependencies
uv add torch torchvision --index-url https://download.pytorch.org/whl/cu121
uv add faiss-gpu nvidia-ml-py

# 3. Verify installation
./mbed dev-check cuda
```

**Troubleshooting:**
- Ensure CUDA is in PATH: `export PATH=/usr/local/cuda/bin:$PATH`
- Check GPU visibility: `nvidia-smi`
- Verify CUDA version: `nvcc --version`

### Apple Silicon (MPS) Setup

**Requirements:**
- macOS 11.0+ (Big Sur)
- Apple Silicon processor (M1/M2/M3)
- Xcode Command Line Tools

**Installation:**

```bash
# 1. Install Xcode Command Line Tools
xcode-select --install

# 2. Install MPS dependencies
uv add torch torchvision coremltools

# 3. Verify MPS availability
./mbed dev-check mps
```

**Performance Notes:**
- MPS performs best with 16GB+ unified memory
- Large models may require memory optimization
- Use batch size tuning for optimal performance

### Intel OpenVINO Setup

**Requirements:**
- Intel CPU (6th gen Core+) or Intel GPU
- OpenVINO Runtime 2024.0+

**Installation:**

```bash
# 1. Install OpenVINO
pip install openvino openvino-dev

# 2. Install via UV extras
uv add mbed-unified[openvino]

# 3. Verify installation
./mbed dev-check openvino
```

**Optimization:**
- OpenVINO performs well on Intel integrated graphics
- CPU optimization is automatic
- Model conversion may improve performance

### CPU-Only Setup

**Requirements:**
- Any x86_64 or ARM64 processor
- 8GB+ RAM recommended

**Installation:**

```bash
# CPU setup is included in base installation
./mbed dev-check cpu
```

## Verification and Testing

### Quick System Check

```bash
# Check all hardware backends
./mbed info --hardware

# Expected output shows available backends:
# ✅ CUDA Available    (RTX 3080, VRAM: 10.0GB)
# ✅ MPS Available     (Apple M2)
# ✅ OpenVINO Available (v2024.0)
# ✅ CPU Available     (16 cores)
```

### Development Environment Check

```bash
# Check specific backend readiness
./mbed dev-check all

# Or check individually:
./mbed dev-check cuda
./mbed dev-check mps
./mbed dev-check openvino
./mbed dev-check cpu
```

### Test Processing

```bash
# Create a test file
echo "This is a test document for MBED processing." > test.txt

# Process with different backends
./mbed generate test.txt --hardware cuda --verbose
./mbed generate test.txt --hardware mps --verbose
./mbed generate test.txt --hardware cpu --verbose

# Check results
ls -la .mbed/
```

## Configuration

### Environment Variables

Create `.env` file for persistent configuration:

```bash
# .env
MBED_HARDWARE=auto
MBED_MODEL=nomic-embed-text
MBED_BATCH_SIZE=128
MBED_WORKERS=8
MBED_DATABASE=chromadb
MBED_DB_PATH=.mbed/database
MBED_LOG_LEVEL=INFO

# CUDA-specific optimizations
MBED_MIXED_PRECISION=true
MBED_CUDA_VRAM_RESERVED_GB=2.0
```

### Project Configuration

Add to `pyproject.toml`:

```toml
[tool.mbed]
hardware = "auto"
model = "nomic-embed-text"
batch_size = 128
workers = 8
database = "chromadb"
db_path = ".mbed/database"
log_level = "INFO"
```

## Troubleshooting

### Common Installation Issues

#### UV Installation Fails
```bash
# Error: UV installation timeout
# Solution: Manual installation
pip install uv
# Or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### CUDA Not Found
```bash
# Error: CUDA runtime not found
# Solutions:
1. Check NVIDIA driver: nvidia-smi
2. Install CUDA toolkit
3. Set environment variables:
   export CUDA_HOME=/usr/local/cuda
   export PATH=$CUDA_HOME/bin:$PATH
   export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

#### Memory Issues
```bash
# Error: Out of memory during processing
# Solutions:
1. Reduce batch size: export MBED_BATCH_SIZE=32
2. Increase system memory/swap
3. Use CPU backend: --hardware cpu
4. Process smaller file sets
```

#### Permission Errors
```bash
# Error: Permission denied
# Solutions:
chmod +x ./mbed
# Or run with: python -m mbed.cli
```

### Hardware-Specific Issues

#### NVIDIA CUDA Issues
```bash
# Check GPU status
nvidia-smi

# Check CUDA installation
nvcc --version

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Check MBED CUDA detection
./mbed dev-check cuda
```

#### Apple MPS Issues
```bash
# Check MPS availability
python -c "import torch; print(torch.backends.mps.is_available())"

# Check system info
system_profiler SPHardwareDataType

# Test MPS backend
./mbed dev-check mps
```

### Performance Issues

#### Slow Processing
1. **Hardware Selection**: Ensure optimal backend is selected
   ```bash
   ./mbed info  # Check recommended backend
   ```

2. **Batch Size Tuning**: Adjust for your hardware
   ```bash
   export MBED_BATCH_SIZE=256  # Increase for more memory
   export MBED_BATCH_SIZE=64   # Decrease for less memory
   ```

3. **Worker Configuration**: Match CPU cores
   ```bash
   export MBED_WORKERS=$(nproc)  # Linux
   export MBED_WORKERS=$(sysctl -n hw.ncpu)  # macOS
   ```

#### High Memory Usage
1. **Reduce Batch Size**: Lower memory pressure
2. **Enable Mixed Precision**: For CUDA backends
   ```bash
   export MBED_MIXED_PRECISION=true
   ```
3. **Limit Workers**: Reduce parallel processing
   ```bash
   export MBED_WORKERS=4
   ```

### Getting Help

If you encounter issues not covered here:

1. **Check System Info**: `./mbed info --hardware`
2. **Run Development Check**: `./mbed dev-check all`
3. **Enable Verbose Output**: `--verbose` flag
4. **Check Logs**: Monitor system logs for errors
5. **Review Documentation**: See `/docs` for detailed guides

## Next Steps

After successful installation:

1. **Read CLI Reference**: [docs/cli-reference.md](../cli-reference.md)
2. **Try Examples**: Run `./examples` for sample workflows  
3. **Production Setup**: See [docs/deployment/production.md](../deployment/production.md)
4. **Development**: Check unit tests with `./test`

Your MBED installation is now ready for embedding generation!