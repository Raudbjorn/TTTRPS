# Copyright (c) 2025 Apple Inc. Licensed under MIT License.

"""Command line interface for embedding generation."""

import logging
from pathlib import Path

import click
import numpy as np
import pandas as pd

from .utils import load_huggingface_data, load_pandas_data
from .version import __version__


def find_column_name(existing_names, candidate):
    """Find a unique column name by appending index if needed."""
    if candidate not in existing_names:
        return candidate
    else:
        index = 1
        while True:
            s = f"{candidate}_{index}"
            if s not in existing_names:
                return s
            index += 1


def determine_and_load_data(filename: str, splits: list[str] | None = None):
    """Load data from file or HuggingFace dataset."""
    suffix = Path(filename).suffix.lower()
    hf_prefix = "hf://datasets/"

    # Override Hugging Face data if given full url
    if filename.startswith(hf_prefix):
        filename = filename.split(hf_prefix)[-1]

    # Hugging Face data
    if (len(filename.split("/")) <= 2) and (suffix == ""):
        df = load_huggingface_data(filename, splits)
    else:
        df = load_pandas_data(filename)

    return df


def load_datasets(
    inputs: list[str], splits: list[str] | None = None, sample: int | None = None
) -> pd.DataFrame:
    """Load and concatenate multiple datasets."""
    existing_column_names = set()
    dataframes = []
    for fn in inputs:
        print("Loading data from " + fn)
        df = determine_and_load_data(fn, splits=splits)
        dataframes.append(df)
        for c in df.columns:
            existing_column_names.add(c)

    file_name_column = find_column_name(existing_column_names, "FILE_NAME")
    for df, fn in zip(dataframes, inputs):
        df[file_name_column] = fn

    df = pd.concat(dataframes)

    if sample:
        df = df.sample(n=sample, axis=0, random_state=np.random.RandomState(42))

    return df


@click.command()
@click.argument("inputs", nargs=-1, required=True)
@click.option("--text", default=None, help="Column containing text data.")
@click.option("--image", default=None, help="Column containing image data.")
@click.option(
    "--vector", default=None, help="Column containing pre-computed vector embeddings."
)
@click.option(
    "--split",
    default=[],
    multiple=True,
    help="Dataset split name(s) to load from Hugging Face datasets.",
)
@click.option(
    "--model",
    default=None,
    help="Model name for generating embeddings (e.g., 'all-MiniLM-L6-v2').",
)
@click.option(
    "--trust-remote-code",
    is_flag=True,
    default=False,
    help="Allow execution of remote code when loading models from Hugging Face Hub.",
)
@click.option(
    "--batch-size",
    type=int,
    default=None,
    help="Batch size for processing embeddings (default: 32 for text, 16 for images).",
)
@click.option(
    "--text-projector",
    type=click.Choice(["sentence_transformers", "litellm"]),
    default="sentence_transformers",
    help="Embedding provider: 'sentence_transformers' (local) or 'litellm' (API-based).",
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    help="API key for litellm embedding provider.",
)
@click.option(
    "--api-base",
    type=str,
    default=None,
    help="API endpoint for litellm embedding provider.",
)
@click.option(
    "--dimensions",
    type=int,
    default=None,
    help="Number of dimensions for output embeddings (litellm only).",
)
@click.option(
    "--sync",
    is_flag=True,
    default=False,
    help="Process embeddings synchronously (litellm only).",
)
@click.option(
    "--sample",
    default=None,
    type=int,
    help="Number of random samples to draw from the dataset.",
)
@click.option(
    "--umap-n-neighbors",
    type=int,
    help="Number of neighbors to consider for UMAP (default: 15).",
)
@click.option(
    "--umap-min-dist",
    type=float,
    help="The min_dist parameter for UMAP.",
)
@click.option(
    "--umap-metric",
    default="cosine",
    help="Distance metric for UMAP computation (default: 'cosine').",
)
@click.option(
    "--umap-random-state", type=int, help="Random seed for reproducible UMAP results."
)
@click.option(
    "--output",
    "-o",
    type=str,
    default=None,
    help="Output file path for the processed data (parquet format).",
)
@click.version_option(version=__version__, package_name="embedding_atlas")
def main(
    inputs,
    text: str | None,
    image: str | None,
    vector: str | None,
    split: list[str] | None,
    model: str | None,
    trust_remote_code: bool,
    batch_size: int | None,
    text_projector: str,
    api_key: str | None,
    api_base: str | None,
    dimensions: int | None,
    sync: bool,
    sample: int | None,
    umap_n_neighbors: int | None,
    umap_min_dist: int | None,
    umap_metric: str | None,
    umap_random_state: int | None,
    output: str | None,
):
    """Generate embeddings and UMAP projections from text, image, or vector data.

    INPUTS: One or more data files (parquet, csv, json) or HuggingFace dataset names.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: (%(name)s) %(message)s",
    )

    df = load_datasets(inputs, splits=split, sample=sample)
    print(f"Loaded {len(df)} rows")
    print(df)

    # Build UMAP arguments
    umap_args = {}
    if umap_min_dist is not None:
        umap_args["min_dist"] = umap_min_dist
    if umap_n_neighbors is not None:
        umap_args["n_neighbors"] = umap_n_neighbors
    if umap_random_state is not None:
        umap_args["random_state"] = umap_random_state
    if umap_metric is not None:
        umap_args["metric"] = umap_metric

    # Run embedding and projection
    if text is not None or image is not None or vector is not None:
        from .projection import (
            compute_image_projection,
            compute_text_projection,
            compute_vector_projection,
        )

        x_column = find_column_name(df.columns, "projection_x")
        y_column = find_column_name(df.columns, "projection_y")
        neighbors_column = find_column_name(df.columns, "__neighbors")

        if vector is not None:
            print(f"Computing projections from vector column: {vector}")
            compute_vector_projection(
                df,
                vector,
                x=x_column,
                y=y_column,
                neighbors=neighbors_column,
                umap_args=umap_args,
            )
        elif text is not None:
            print(f"Computing embeddings from text column: {text}")
            # Build kwargs for litellm projector
            litellm_kwargs = {}
            if api_key is not None:
                litellm_kwargs["api_key"] = api_key
            if api_base is not None:
                litellm_kwargs["api_base"] = api_base
            if dimensions is not None:
                litellm_kwargs["dimensions"] = dimensions
            if sync:
                litellm_kwargs["sync"] = sync

            compute_text_projection(
                df,
                text,
                x=x_column,
                y=y_column,
                neighbors=neighbors_column,
                model=model,
                text_projector=text_projector,
                trust_remote_code=trust_remote_code,
                batch_size=batch_size,
                umap_args=umap_args,
                **litellm_kwargs,
            )
        elif image is not None:
            print(f"Computing embeddings from image column: {image}")
            compute_image_projection(
                df,
                image,
                x=x_column,
                y=y_column,
                neighbors=neighbors_column,
                model=model,
                trust_remote_code=trust_remote_code,
                batch_size=batch_size,
                umap_args=umap_args,
            )

        print(f"Projections stored in columns: {x_column}, {y_column}")
        print(f"Neighbors stored in column: {neighbors_column}")
    else:
        print("No embedding column specified (--text, --image, or --vector)")
        print("Data loaded but no embeddings computed.")

    # Save output if specified
    if output is not None:
        output_path = Path(output)
        if output_path.suffix == ".parquet":
            df.to_parquet(output_path)
        elif output_path.suffix == ".csv":
            df.to_csv(output_path, index=False)
        elif output_path.suffix in (".json", ".jsonl"):
            df.to_json(output_path, orient="records", lines=output_path.suffix == ".jsonl")
        else:
            # Default to parquet
            df.to_parquet(output_path.with_suffix(".parquet"))
        print(f"Output saved to: {output_path}")
    else:
        print("No output file specified. Use --output/-o to save results.")


if __name__ == "__main__":
    main()
