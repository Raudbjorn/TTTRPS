# Embedding Atlas (Core)

Stripped-down version of Apple's Embedding Atlas, containing only the core embedding generation pipeline.

**Retained functionality:**
- Text embedding generation (SentenceTransformers or LiteLLM API)
- Image embedding generation (ViT models)
- UMAP dimensionality reduction
- K-nearest neighbor computation
- Projection caching

See [packages/backend/README.md](packages/backend/README.md) for full documentation.

## Quick Start

```bash
cd packages/backend
pip install -e .

# Generate embeddings from text
embedding-atlas data.parquet --text content --output embedded.parquet
```

## Python API

```python
import pandas as pd
from embedding_atlas.projection import compute_text_projection

df = pd.read_parquet("data.parquet")
compute_text_projection(df, "text_column", x="proj_x", y="proj_y")
df.to_parquet("output.parquet")
```

## License

MIT License - see [LICENSE](LICENSE)

## Original Project

Based on [Apple's Embedding Atlas](https://github.com/apple/embedding-atlas).
