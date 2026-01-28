# LLM and Streaming Commands Analysis

## Executive Summary

The LLM domain contains ~30 commands (~716 lines) spanning configuration, chat, streaming, model listing, embeddings, and model selection. The streaming implementation uses a fire-and-forget pattern with Tauri events.

---

## 1. Command Inventory

### 1.1 Configuration Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `configure_llm` | Configure LLM provider settings |
| `check_llm_health` | Provider health check |
| `get_llm_config` | Get current configuration |
| `run_provider_health_checks` | Force health checks |

### 1.2 Chat Commands (2 commands)

| Command | Purpose |
|---------|---------|
| `chat` | Non-streaming chat request |
| `stream_chat` | Streaming chat with Tauri events |

### 1.3 Streaming Management (2 commands)

| Command | Purpose |
|---------|---------|
| `cancel_stream` | Cancel active stream |
| `get_active_streams` | List active stream IDs |

### 1.4 Router Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `get_router_stats` | Provider performance stats |
| `get_router_costs` | Cost tracking |
| `get_healthy_providers` | List healthy providers |
| `set_routing_strategy` | Configure routing |

### 1.5 Model Listing (7 commands)

| Command | Purpose |
|---------|---------|
| `list_ollama_models` | Ollama models |
| `list_claude_models` | Claude models (with fallback) |
| `list_openai_models` | OpenAI models (with fallback chain) |
| `list_gemini_models` | Gemini models (with fallback) |
| `list_openrouter_models` | OpenRouter models |
| `list_provider_models` | Generic via LiteLLM |
| `list_chat_providers` | List available providers |

### 1.6 Cost Estimation (1 command)

| Command | Purpose |
|---------|---------|
| `estimate_request_cost` | Estimate request cost |

### 1.7 Model Selection (3 commands)

| Command | Purpose |
|---------|---------|
| `get_model_selection` | Recommend model for task |
| `get_model_selection_for_prompt` | Recommend based on prompt |
| `set_model_override` | Force/clear model override |

### 1.8 Embedding Configuration (6 commands)

| Command | Purpose |
|---------|---------|
| `configure_meilisearch_embedder` | Configure embedder for index |
| `setup_ollama_embeddings` | Setup Ollama embeddings |
| `setup_local_embeddings` | Setup HuggingFace embeddings |
| `get_embedder_status` | Query embedder config |
| `list_ollama_embedding_models` | List Ollama embedding models |
| `list_local_embedding_models` | List HuggingFace models |

---

## 2. Streaming Architecture

The `stream_chat` command implements a **fire-and-forget streaming pattern**:

```
Frontend              Backend                      Tauri Events
   │                    │                               │
   │ stream_chat()      │                               │
   ├────────────────────>│                               │
   │                    │ 1. Validate config            │
   │                    │ 2. Create stream ID            │
   │                    │ 3. tokio::spawn async task     │
   │ <- stream_id       │                               │
   │<────────────────────│                               │
   │                    │ 4. Emit "chat-chunk" events   │
   │ chat-chunk events  │<──────────────────────────────│
   │<──────────────────────────────────────────────────────│
```

**Event Type**: `ChatChunk`
```rust
pub struct ChatChunk {
    pub stream_id: String,
    pub content: String,
    pub is_final: bool,
    pub finish_reason: Option<String>,
    pub usage: Option<TokenUsage>,
    pub index: usize,
}
```

---

## 3. AppState Dependencies

```rust
pub llm_client: RwLock<Option<LLMClient>>,
pub llm_config: RwLock<Option<LLMConfig>>,
pub llm_router: AsyncRwLock<LLMRouter>,
pub llm_manager: Arc<AsyncRwLock<LLMManager>>,
pub search_client: Arc<SearchClient>,  // For embeddings
```

---

## 4. Proposed Module Structure

```
commands/llm/
├── mod.rs              # Re-exports (~20 lines)
├── types.rs            # Request/Response types (~100 lines)
├── config.rs           # Configuration + router (~100 lines)
├── chat.rs             # Non-streaming chat (~80 lines)
├── streaming.rs        # Stream management (~120 lines)
├── models.rs           # Model listing (~100 lines)
├── embeddings.rs       # Embedding config (~200 lines)
└── selection.rs        # Model selection (~50 lines)
```

**Total**: ~770 lines across 8 files

---

## 5. Key Types

### Request Types
- `ChatRequestPayload`
- `EmbedderConfigRequest`

### Response Types
- `ChatResponsePayload`
- `SetupEmbeddingsResult`
- `OllamaEmbeddingModel`
- `LocalEmbeddingModel`
- `ChatChunk`

---

## 6. Risk Assessment

### HIGH RISK: Event Emission
- `app_handle.emit("chat-chunk", &chunk)` in spawned task
- **Mitigation**: Test event propagation after extraction

### MEDIUM RISK: Config Persistence
- Config path logic with app data directory
- **Mitigation**: Test with temp directories

---

## 7. Migration Priority

1. `types.rs` - No dependencies
2. `config.rs` - Core configuration
3. `models.rs` - Model listing
4. `chat.rs` - Non-streaming
5. `streaming.rs` - Streaming (complex)
6. `embeddings.rs` - Embedding config
7. `selection.rs` - Model selection
