# Copyright 2023-2026 llmware

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You
# may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.


"""Global Default Configs for Embedding Models.

Stripped down to contain only embedding-related model configurations.
"""

global_model_repo_catalog_list = [

    # embedding models

    {"model_name": "all-MiniLM-L6-v2", "display_name": "mini-lm-sbert", "model_family": "HFEmbeddingModel",
     "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 384, "context_window": 512,
     "link": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
     "custom_model_files": [], "custom_model_repo": "",
     "hf_repo": "sentence-transformers/all-MiniLM-L6-v2"},

    {"model_name": 'all-mpnet-base-v2', "display_name": "mpnet-base", "model_family": "HFEmbeddingModel",
     "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 514,
     "link": "https://huggingface.co/sentence-transformers/all-mpnet-base-v2",
     "custom_model_files": [], "custom_model_repo": "",
     "hf_repo": "sentence-transformers/all-mpnet-base-v2"},

    {"model_name": 'industry-bert-insurance', "display_name": "industry-bert-insurance",
      "model_family": "HFEmbeddingModel",
      "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 512,
      "link": "https://huggingface.co/llmware/industry-bert-insurance-v0.1", "custom_model_files": [],
      "custom_model_repo": "",
      "hf_repo": "llmware/industry-bert-insurance-v0.1"},

    {"model_name": 'industry-bert-contracts', "display_name": "industry-bert-contracts",
      "model_family": "HFEmbeddingModel",
      "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 512,
      "link": "https://huggingface.co/llmware/industry-bert-contracts-v0.1", "custom_model_files": [],
      "custom_model_repo": "",
      "hf_repo": "llmware/industry-bert-contracts-v0.1"},

    {"model_name": 'industry-bert-asset-management', "display_name": "industry-bert-asset-management",
      "model_family": "HFEmbeddingModel", "model_category": "embedding", "model_location": "hf_repo",
      "embedding_dims": 768, "context_window": 512,
      "link": "https://huggingface.co/llmware/industry-bert-asset-management-v0.1", "custom_model_files": [],
      "custom_model_repo": "",
      "hf_repo": "llmware/industry-bert-asset-management-v0.1"},

    {"model_name": 'industry-bert-sec', "display_name": "industry-bert-sec", "model_family": "HFEmbeddingModel",
      "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 512,
      "link": "https://huggingface.co/llmware/industry-bert-sec-v0.1", "custom_model_files": [], "custom_model_repo": "",
      "hf_repo": "llmware/industry-bert-sec-v0.1"},

    {"model_name": 'industry-bert-loans', "display_name": "industry-bert-loans",
       "model_family": "HFEmbeddingModel", "model_category": "embedding", "model_location": "hf_repo",
       "embedding_dims": 768, "context_window": 512,
       "link": "https://huggingface.co/llmware/industry-bert-loans",
       "custom_model_files": [], "custom_model_repo": "", "hf_repo": "llmware/industry-bert-loans"},

    {"model_name": 'nomic-ai/nomic-embed-text-v1', "display_name": "nomic-text-v1",
       "model_family": "HFEmbeddingModel",
       "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 8192,
       "link": "https://huggingface.co/nomic-ai/nomic-embed-text-v1", "custom_model_files": [], "custom_model_repo": "",
       "hf_repo": "nomic-ai/nomic-embed-text-v1"},

    {"model_name": 'jinaai/jina-embeddings-v2-base-en', "display_name": "jina-base-en-v2",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 8192,
        "link": "https://huggingface.co/jinaai/jina-embeddings-v2-base-en", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "jinaai/jina-embeddings-v2-base-en"},

    {"model_name": 'jinaai/jina-embeddings-v2-small-en', "display_name": "jina-small-en-v2",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 512, "context_window": 8192,
        "link": "https://huggingface.co/jinaai/jina-embeddings-v2-small-en", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "jinaai/jina-embeddings-v2-small-en"},

    {"model_name": 'jinaai/jina-reranker-v1-turbo-en', "display_name": "jina-reranker-turbo",
      "model_family": "HFReRankerModel",
      "model_category": "reranker", "model_location": "hf_repo", "embedding_dims": 384, "context_window": 8192,
      "link": "https://huggingface.co/jinaai/jina-reranker-v1-turbo-en", "custom_model_files": [],
      "custom_model_repo": "",
      "hf_repo": "jinaai/jina-reranker-v1-turbo-en"},

    {"model_name": 'jinaai/jina-reranker-v1-tiny-en', "display_name": "jina-reranker-tiny",
        "model_family": "HFReRankerModel",
        "model_category": "reranker", "model_location": "hf_repo", "embedding_dims": 384, "context_window": 8192,
        "link": "https://huggingface.co/jinaai/jina-reranker-v1-tiny-en", "custom_model_files": [],
        "custom_model_repo": "",
        "hf_repo": "jinaai/jina-reranker-v1-tiny-en"},

    {"model_name": 'BAAI/bge-small-en-v1.5', "display_name": "bge-small-en-v1.5", "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 384, "context_window": 512,
        "link": "https://huggingface.co/BAAI/bge-small-en-v1.5", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "BAAI/bge-small-en-v1.5"},

    {"model_name": 'BAAI/bge-large-en-v1.5', "display_name": "bge-large-en-v1.5", "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 1024, "context_window": 512,
        "link": "https://huggingface.co/BAAI/bge-large-en-v1.5", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "BAAI/bge-large-en-v1.5"},

    {"model_name": 'BAAI/bge-base-en-v1.5', "display_name": "bge-base-en-v1.5", "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 512,
        "link": "https://huggingface.co/BAAI/bge-base-en-v1.5", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "BAAI/bge-base-en-v1.5"},

    {"model_name": "thenlper/gte-small", "display_name": "gte-small",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 384, "context_window": 512,
        "link": "https://huggingface.co/thenlper/gte-small", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "thenlper/gte-small"},

    {"model_name": "thenlper/gte-base", "display_name": "gte-base",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 768, "context_window": 512,
        "link": "https://huggingface.co/thenlper/gte-base", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "thenlper/gte-base"},

    {"model_name": "thenlper/gte-large", "display_name": "gte-large",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 1024, "context_window": 512,
        "link": "https://huggingface.co/thenlper/gte-large", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "thenlper/gte-large"},

    {"model_name": 'llmrails/ember-v1', "display_name": "ember-v1",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 1024, "context_window": 512,
        "link": "https://huggingface.co/llmrails/ember-v1", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "llmrails/ember-v1"},

    {"model_name": "WhereIsAI/UAE-Large-V1", "display_name": "uae-large-v1",
        "model_family": "HFEmbeddingModel",
        "model_category": "embedding", "model_location": "hf_repo", "embedding_dims": 1024, "context_window": 512,
        "link": "https://huggingface.co/WhereIsAI/UAE-Large-V1", "custom_model_files": [], "custom_model_repo": "",
        "hf_repo": "WhereIsAI/UAE-Large-V1"},

    {"model_name": 'text-embedding-ada-002', "display_name": "OpenAI-Embedding", "model_family": "OpenAIEmbeddingModel",
     "model_category": "embedding", "model_location": "api", "context_window": 8191, "embedding_dims": 1536},

    {"model_name": 'text-embedding-3-small', "display_name": "OpenAI-Embedding", "model_family": "OpenAIEmbeddingModel",
     "model_category": "embedding", "model_location": "api", "context_window": 8191, "embedding_dims": 1536},

    {"model_name": 'text-embedding-3-large', "display_name": "OpenAI-Embedding", "model_family": "OpenAIEmbeddingModel",
     "model_category": "embedding", "model_location": "api", "context_window": 8191, "embedding_dims": 3072},

    # ONNX embedding models
    {"model_name": "industry-bert-insurance-onnx", "display_name": "industry-bert-insurance-onnx",
     "model_family": "ONNXEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-insurance-onnx",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["model.onnx"]},

    {"model_name": "industry-bert-contracts-onnx", "display_name": "industry-bert-contracts-onnx",
     "model_family": "ONNXEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-contracts-onnx",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["model.onnx"]},

    {"model_name": "industry-bert-asset-management-onnx", "display_name": "industry-bert-asset-management-onnx",
     "model_family": "ONNXEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-asset-management-onnx",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["model.onnx"]},

    {"model_name": "industry-bert-sec-onnx", "display_name": "industry-bert-sec-onnx",
     "model_family": "ONNXEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-sec-onnx",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["model.onnx"]},

    {"model_name": "industry-bert-loans-onnx", "display_name": "industry-bert-loans-onnx",
     "model_family": "ONNXEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-loans-onnx",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["model.onnx"]},

    # OpenVINO embedding models
    {"model_name": "industry-bert-insurance-ov", "display_name": "industry-bert-insurance-ov",
     "model_family": "OVEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-insurance-ov",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["openvino_model.xml"]},

    {"model_name": "industry-bert-contracts-ov", "display_name": "industry-bert-contracts-ov",
     "model_family": "OVEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-contracts-ov",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["openvino_model.xml"]},

    {"model_name": "industry-bert-asset-management-ov", "display_name": "industry-bert-asset-management-ov",
     "model_family": "OVEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-asset-management-ov",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["openvino_model.xml"]},

    {"model_name": "industry-bert-sec-ov", "display_name": "industry-bert-sec-ov",
     "model_family": "OVEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-sec-ov",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["openvino_model.xml"]},

    {"model_name": "industry-bert-loans-ov", "display_name": "industry-bert-loans-ov",
     "model_family": "OVEmbeddingModel", "model_category": "embedding",
     "model_location": "llmware_repo", "embedding_dims": 768, "context_window": 512,
     "hf_repo": "llmware/industry-bert-loans-ov",
     "fetch": {"snapshot": True, "module": "llmware.models", "method": "pull_snapshot_from_hf"},
     "validation_files": ["openvino_model.xml"]},

]

# Minimal finetuning wrappers lookup - empty for embedding-only usage
global_model_finetuning_prompt_wrappers_lookup = {}

# Minimal tokenizer lookup - empty for embedding-only usage
global_tokenizer_bos_eos_lookup = {}

# No prompts needed for embedding-only usage
global_default_prompt_catalog = []

# No benchmark data needed for embedding-only usage
model_benchmark_data = []
