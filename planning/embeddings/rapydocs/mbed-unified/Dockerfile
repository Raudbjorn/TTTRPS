# Multi-stage Dockerfile for MBED Unified System
# Supports different hardware backends with optimized layers

# =============================================================================
# Base Stage - Common dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast package management
RUN pip install uv

# Create app user and directories
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app /data /outputs && \
    chown -R app:app /app /data /outputs

WORKDIR /app

# =============================================================================
# Dependencies Stage - Install Python packages
# =============================================================================
FROM base as dependencies

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install base dependencies with UV
RUN uv sync --no-dev

# =============================================================================
# CUDA Stage - NVIDIA GPU support
# =============================================================================
FROM nvidia/cuda:12.2-devel-ubuntu20.04 as cuda-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    && ln -s /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Create app user
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app /data /outputs && \
    chown -R app:app /app /data /outputs

WORKDIR /app
USER app

# Copy source code
COPY --chown=app:app . .

# Install CUDA-specific dependencies
RUN uv sync && \
    uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    uv pip install faiss-gpu nvidia-ml-py

# =============================================================================
# Production Stage - Minimal runtime
# =============================================================================
FROM base as production

# Copy UV environment and source code
COPY --from=dependencies /app/.venv /app/.venv
COPY --chown=app:app src/ ./src/
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app mbed ./mbed

# Make CLI executable
RUN chmod +x ./mbed

USER app

# Set environment variables for production
ENV MBED_LOG_LEVEL=INFO \
    MBED_WORKERS=4 \
    MBED_BATCH_SIZE=128 \
    MBED_DB_PATH=/outputs/database

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.mbed.core.hardware import HardwareDetector; print('OK' if HardwareDetector.detect_all() else 'FAIL')"

# Default command
CMD ["python", "-m", "mbed.cli", "--help"]

# =============================================================================
# Development Stage - Include dev tools
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN uv sync --extra dev

# Install additional dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

USER app

# Set development environment variables
ENV MBED_LOG_LEVEL=DEBUG

# Default command for development
CMD ["/bin/bash"]

# =============================================================================
# CUDA Production Stage
# =============================================================================
FROM cuda-base as cuda-production

# Copy source and make executable
COPY --chown=app:app . .
RUN chmod +x ./mbed

# Set CUDA-specific environment variables
ENV MBED_HARDWARE=cuda \
    MBED_MIXED_PRECISION=true \
    MBED_CUDA_VRAM_RESERVED_GB=2.0

# Health check with CUDA support
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import torch; print('CUDA OK' if torch.cuda.is_available() else 'CUDA FAIL')"

CMD ["python", "-m", "mbed.cli", "--help"]

# =============================================================================
# CPU-Only Stage - Lightweight for CPU processing
# =============================================================================
FROM production as cpu-only

# Set CPU-specific optimizations
ENV MBED_HARDWARE=cpu \
    MBED_WORKERS=8 \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ./mbed info

CMD ["python", "-m", "mbed.cli", "--help"]