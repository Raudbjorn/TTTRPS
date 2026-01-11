# Rapyd Documentation MCP Server

[![CI](https://github.com/Raudbjorn/rapydocs/actions/workflows/test.yml/badge.svg)](https://github.com/Raudbjorn/rapydocs/actions/workflows/test.yml)
[![Platform Support](https://img.shields.io/badge/platform-macOS%20ARM%20%7C%20Intel%20%7C%20Linux-blue)](#platform-support)

A cross-platform Model Context Protocol (MCP) server that provides semantic search capabilities for Rapyd payment gateway documentation. Features both Claude Code integration and an avant-garde web interface. Optimized for Apple Silicon Macs with automatic fallback support for Intel systems and standard CPUs.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (required for FastMCP)
- Node.js 18+ (required for web interface)
- Claude Code (optional, for MCP integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/Raudbjorn/rapydocs.git
cd rapydocs

# Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create the database (REQUIRED on first setup)
# Note: Embeddings are platform-specific and must be generated locally
python create_database.py

# Test the installation
python tests/test_server.py
```

### Add to Claude Code

```bash
# Using Claude Code CLI
claude mcp add rapyd-docs \
  "$(pwd)/venv/bin/python" \
  "$(pwd)/mcp_server.py"
```

Or manually add to your Claude Code configuration:

```json
{
  "mcpServers": {
    "rapyd-docs": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/rapydocs/mcp_server.py"],
      "cwd": "/path/to/rapydocs"
    }
  }
}
```

## 🌐 Web Interface (NEW!)

### Avant-Garde Search Experience

Experience semantic search through a provocative, neo-brutalist web interface that challenges conventional design:

```bash
# 🚀 ONE-COMMAND LAUNCH - Starts everything and opens browser
./launch_web_interface.py

# Alternative shell script
./launch_web_interface.sh
```

**What you get:**
- **⚡ Instant Launch**: Single command starts API server, web interface, and opens browser
- **🎨 2025 Design**: Avant-garde neo-brutalist aesthetic with harsh typography and deliberate imperfection
- **🔍 Real-time Search**: Sub-100ms semantic search with dramatic visual feedback
- **📊 System Analytics**: Live stats page showing platform info and performance metrics
- **🖥️ Cross-platform**: Works on any system with Python 3.10+ and Node.js

**Interface Features:**
- Raw concrete aesthetic with exposed grids
- Intentionally "broken" layouts that are meticulously crafted
- Scroll-driven animations and container queries
- Bold color palettes (acid green + electric pink)
- Typography as art with glitch effects

### Web Interface URLs
- **Main Search**: http://localhost:3000
- **System Stats**: http://localhost:3000/stats  
- **About Page**: http://localhost:3000/about
- **API Docs**: http://localhost:8000/api/docs

## 📖 Features

- **🔍 Semantic Search**: Advanced vector search across 1,200+ Rapyd documentation pages
- **⚡ Pre-computed Embeddings**: Instant startup with pre-built vector database
- **🍎 Apple Silicon Optimized**: Uses Metal Performance Shaders (MPS) when available
- **🔄 Cross-Platform**: Automatic backend detection and fallback support
- **📱 Offline Capable**: Works completely offline after initial setup
- **🤖 Claude Integration**: Native MCP server for seamless Claude Code integration
- **🌐 Web Interface**: Avant-garde neo-brutalist search interface with auto-launch

## 🛠 Available Tools

Once connected to Claude Code, you can use these search tools:

- **`search_documentation`** - Search across all documentation with source filtering
- **`get_doc_summary`** - Get comprehensive topic summaries and explanations  
- **`list_documentation_sources`** - Browse available documentation sources and statistics

Example usage in Claude:
```
Search for "webhook signature verification" in Rapyd docs
Get a summary of payment methods available in Rapyd
List all available documentation sources
```

## 🏗 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude Code   │ ── │   MCP Server     │ ── │   ChromaDB      │
│                 │    │                  │    │                 │
│ - Search UI     │    │ - Query parsing  │    │ - Vector store  │
│ - Tool calling  │    │ - Result ranking │    │ - 1,200+ docs   │
│ - Context mgmt  │    │ - Source filter  │    │ - Pre-computed  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │ Universal       │
                       │ Embeddings      │
                       │                 │
                       │ • Apple Silicon │
                       │ • Intel GPU     │
                       │ • CPU Fallback  │
                       └─────────────────┘
```

## 🖥 Platform Support

### Apple Silicon (M1/M2/M3/M4) ✅
- **Recommended**: Automatic MPS acceleration if PyTorch available
- **Performance**: Sub-100ms query response times
- **Setup**: Zero additional configuration required

### Intel Systems ✅
- **GPU Acceleration**: Optional OpenVINO support
- **Installation**: `pip install openvino openvino-dev[onnx]`
- **Performance**: ~50ms query times with GPU, ~200ms with CPU

### Any CPU ✅
- **Compatibility**: Works on any system with Python 3.10+
- **Performance**: ~100-300ms query times (varies by CPU)
- **Reliability**: Guaranteed fallback for maximum compatibility

## 🧪 Testing

### Local Testing
```bash
# Run the test suite
python test_server.py

# Test MCP functionality
python tests/test_mcp_integration.py
```

### GitHub Actions
This repository includes automated testing on GitHub's ARM-based macOS runners:

- **Platform**: macOS 14 (Apple Silicon)
- **Python**: 3.10, 3.11, 3.12
- **Tests**: Installation, embedding generation, MCP server functionality

## 🚨 Troubleshooting

### Common Issues

**Slow startup (10-30 seconds)**
- ✅ Normal behavior on first run (loading models)
- ✅ Subsequent runs are much faster

**MPS warnings on Apple Silicon**
- ✅ Warnings can be safely ignored
- ✅ Falls back to CPU automatically if MPS unavailable

**Connection issues with Claude Code**
```bash
# Check MCP server status
claude mcp list

# Remove and re-add if needed
claude mcp remove rapyd-docs
claude mcp add rapyd-docs "$(pwd)/venv/bin/python" "$(pwd)/mcp_server.py"
```

## 🔒 Security & Privacy

- **Offline Operation**: Works completely offline after initial setup
- **No External Calls**: All processing happens locally
- **Data Privacy**: Your queries never leave your machine

## 📊 Data Sources

- **Rapyd Payment Documentation**: 275+ comprehensive pages
- **Total Content**: 1,200+ searchable documents

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.