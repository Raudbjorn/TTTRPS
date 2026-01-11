# Embedding Atlas (Core)

A Python library and CLI for generating text/image embeddings with UMAP projections and K-nearest neighbor computation. Supports caching for efficient reprocessing.

## Installation

```bash
pip install embedding-atlas
```

For image embedding support:
```bash
pip install "embedding-atlas[image]"
```

For HuggingFace datasets support:
```bash
pip install "embedding-atlas[datasets]"
```

## CLI Usage

```bash
embedding-atlas [OPTIONS] INPUTS... --output output.parquet
```

### Text Embeddings

Generate embeddings from a text column:

```bash
embedding-atlas data.parquet --text content --output embedded.parquet
```

### Using Pre-computed Vectors

If you have pre-computed embeddings, generate UMAP projections:

```bash
embedding-atlas data.parquet --vector embeddings --output projected.parquet
```

### Image Embeddings

Generate embeddings from images (requires `[image]` extras):

```bash
embedding-atlas data.parquet --image image_column --output embedded.parquet
```

### Options

- `--text`: Column containing text data
- `--image`: Column containing image data
- `--vector`: Column containing pre-computed vectors
- `--model`: Model name (default: `all-MiniLM-L6-v2` for text)
- `--batch-size`: Batch size (default: 32 for text, 16 for images)
- `--text-projector`: `sentence_transformers` (local) or `litellm` (API)
- `--output/-o`: Output file path (parquet, csv, json)
- `--sample`: Random sample size
- `--umap-*`: UMAP parameters (n-neighbors, min-dist, metric, random-state)

### API-based Embeddings (LiteLLM)

Use remote embedding APIs via LiteLLM:

```bash
embedding-atlas data.parquet --text content \
  --text-projector litellm \
  --model text-embedding-3-small \
  --api-key $OPENAI_API_KEY \
  --output embedded.parquet
```

## Python API

```python
import pandas as pd
from embedding_atlas.projection import (
    compute_text_projection,
    compute_vector_projection,
    compute_image_projection,
)

df = pd.read_parquet("data.parquet")

# Text embeddings
compute_text_projection(df, "text_column", x="proj_x", y="proj_y")

# Pre-computed vectors
compute_vector_projection(df, "vector_column", x="proj_x", y="proj_y")

# Save results
df.to_parquet("output.parquet")
```

## Caching

Embeddings and projections are cached in `~/.cache/embedding_atlas/projections/`. The cache key is based on input data and model parameters.

## Output Columns

After processing, the DataFrame will have:
- `projection_x`: UMAP X coordinate
- `projection_y`: UMAP Y coordinate
- `__neighbors`: K-nearest neighbors with distances
