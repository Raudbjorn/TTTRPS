"""Setup configuration for Rapyd Documentation Embeddings System"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rapydocs-embeddings",
    version="1.0.0",
    author="Rapyd",
    description="High-performance embeddings system with GPU acceleration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Raudbjorn/rapydocs",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "chromadb>=0.4.0",
        "psycopg2-binary>=2.9.0",
        "pgvector>=0.2.0",
        "requests>=2.28.0",
        "numpy>=1.21.0",
        "fastmcp>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
        "ollama": [
            "torch>=2.0.0",
        ],
    },
    scripts=[
        "m-bed",
    ],
    entry_points={
        "console_scripts": [
            "rapydocs-mcp=src.mcp.mcp_server:main",
        ],
    },
)