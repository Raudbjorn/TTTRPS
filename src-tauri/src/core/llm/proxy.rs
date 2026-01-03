//! LLM Proxy Service
//!
//! Provides an OpenAI-compatible HTTP endpoint that routes requests to
//! any of the project's LLM providers. This allows Meilisearch's chat
//! feature to use providers like Claude, Gemini, etc. via the VLlm source.
//!
//! ## Endpoints
//! - `POST /v1/chat/completions` - OpenAI-compatible chat endpoint
//! - `GET /v1/models` - List available models
//! - `GET /health` - Health check
//!
//! ## Routing
//! Provider selection via model name prefix: `{provider}:{model}`
//! Examples: `claude:claude-sonnet-4-20250514`, `gemini:gemini-pro`

use super::router::{ChatChunk, ChatMessage, ChatRequest, ChatResponse, LLMError, LLMProvider, MessageRole};
use axum::{
    extract::{Json, State},
    http::StatusCode,
    response::{sse::Event, IntoResponse, Response, Sse},
    routing::{get, post},
    Router,
};
use futures_util::stream::Stream;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::sync::{oneshot, RwLock};
use tower_http::cors::{Any, CorsLayer};

// ============================================================================
// OpenAI-Compatible Types
// ============================================================================

/// OpenAI-compatible chat completion request
#[derive(Debug, Clone, Deserialize)]
pub struct OpenAIChatRequest {
    pub model: String,
    pub messages: Vec<OpenAIMessage>,
    #[serde(default)]
    pub stream: bool,
    #[serde(default)]
    pub temperature: Option<f32>,
    #[serde(default)]
    pub max_tokens: Option<u32>,
}

/// OpenAI-compatible message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenAIMessage {
    pub role: String,
    pub content: String,
}

impl From<OpenAIMessage> for ChatMessage {
    fn from(msg: OpenAIMessage) -> Self {
        let role = match msg.role.as_str() {
            "system" => MessageRole::System,
            "assistant" => MessageRole::Assistant,
            _ => MessageRole::User,
        };
        ChatMessage {
            role,
            content: msg.content,
        }
    }
}

/// OpenAI-compatible chat completion response
#[derive(Debug, Clone, Serialize)]
pub struct OpenAIChatResponse {
    pub id: String,
    pub object: String,
    pub created: u64,
    pub model: String,
    pub choices: Vec<OpenAIChoice>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usage: Option<OpenAIUsage>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OpenAIChoice {
    pub index: u32,
    pub message: OpenAIMessage,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OpenAIUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

/// OpenAI-compatible streaming chunk
#[derive(Debug, Clone, Serialize)]
pub struct OpenAIStreamChunk {
    pub id: String,
    pub object: String,
    pub created: u64,
    pub model: String,
    pub choices: Vec<OpenAIStreamChoice>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OpenAIStreamChoice {
    pub index: u32,
    pub delta: OpenAIDelta,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub finish_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OpenAIDelta {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub role: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
}

/// Model info for /v1/models endpoint
#[derive(Debug, Clone, Serialize)]
pub struct OpenAIModel {
    pub id: String,
    pub object: String,
    pub created: u64,
    pub owned_by: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct OpenAIModelList {
    pub object: String,
    pub data: Vec<OpenAIModel>,
}

// ============================================================================
// Proxy Metrics
// ============================================================================

/// Metrics for the proxy service with atomic counters for thread-safe updates
pub struct ProxyMetrics {
    pub total_requests: AtomicU64,
    pub successful_requests: AtomicU64,
    pub failed_requests: AtomicU64,
}

impl ProxyMetrics {
    /// Create a new metrics instance with zeroed counters
    pub fn new() -> Self {
        Self {
            total_requests: AtomicU64::new(0),
            successful_requests: AtomicU64::new(0),
            failed_requests: AtomicU64::new(0),
        }
    }

    /// Record a successful request
    pub fn record_success(&self) {
        self.total_requests.fetch_add(1, Ordering::Relaxed);
        self.successful_requests.fetch_add(1, Ordering::Relaxed);
    }

    /// Record a failed request
    pub fn record_failure(&self) {
        self.total_requests.fetch_add(1, Ordering::Relaxed);
        self.failed_requests.fetch_add(1, Ordering::Relaxed);
    }

    /// Get snapshot of current metrics
    pub fn snapshot(&self) -> MetricsSnapshot {
        MetricsSnapshot {
            total_requests: self.total_requests.load(Ordering::Relaxed),
            successful_requests: self.successful_requests.load(Ordering::Relaxed),
            failed_requests: self.failed_requests.load(Ordering::Relaxed),
        }
    }
}

impl Default for ProxyMetrics {
    fn default() -> Self {
        Self::new()
    }
}

/// Serializable snapshot of metrics
#[derive(Debug, Clone, Serialize)]
pub struct MetricsSnapshot {
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
}

// ============================================================================
// Proxy Service State
// ============================================================================

/// Shared state for the proxy service
pub struct ProxyState {
    /// Registered providers keyed by provider ID
    pub providers: RwLock<HashMap<String, Arc<dyn LLMProvider>>>,
    /// Default provider ID (used when no prefix in model name)
    pub default_provider: RwLock<Option<String>>,
    /// Metrics for tracking request statistics
    pub metrics: ProxyMetrics,
}

impl ProxyState {
    pub fn new() -> Self {
        Self {
            providers: RwLock::new(HashMap::new()),
            default_provider: RwLock::new(None),
            metrics: ProxyMetrics::new(),
        }
    }

    /// Parse model name to extract provider and actual model
    /// Format: "provider:model" or just "model" (uses default)
    pub async fn parse_model(&self, model: &str) -> Option<(String, String)> {
        if let Some((provider, actual_model)) = model.split_once(':') {
            Some((provider.to_string(), actual_model.to_string()))
        } else {
            // Use default provider if set
            let default = self.default_provider.read().await;
            default.as_ref().map(|p| (p.clone(), model.to_string()))
        }
    }

    /// Get a provider by ID
    pub async fn get_provider(&self, provider_id: &str) -> Option<Arc<dyn LLMProvider>> {
        let providers = self.providers.read().await;
        providers.get(provider_id).cloned()
    }
}

impl Default for ProxyState {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================================
// LLM Proxy Service
// ============================================================================

/// OpenAI-compatible LLM proxy service
pub struct LLMProxyService {
    port: u16,
    state: Arc<ProxyState>,
    shutdown_tx: Option<oneshot::Sender<()>>,
}

impl LLMProxyService {
    /// Create a new proxy service on the specified port
    pub fn new(port: u16) -> Self {
        Self {
            port,
            state: Arc::new(ProxyState::new()),
            shutdown_tx: None,
        }
    }

    /// Create with default port (8787)
    pub fn with_defaults() -> Self {
        Self::new(8787)
    }

    /// Get the proxy URL
    pub fn url(&self) -> String {
        format!("http://127.0.0.1:{}", self.port)
    }

    /// Register a provider
    pub async fn register_provider(&self, id: &str, provider: Arc<dyn LLMProvider>) {
        let mut providers = self.state.providers.write().await;
        log::info!("Registered LLM proxy provider: {} (model: {})", id, provider.model());
        providers.insert(id.to_string(), provider);
    }

    /// Unregister a provider
    pub async fn unregister_provider(&self, id: &str) {
        let mut providers = self.state.providers.write().await;
        if providers.remove(id).is_some() {
            log::info!("Unregistered LLM proxy provider: {}", id);
        }
    }

    /// Set the default provider
    pub async fn set_default_provider(&self, id: &str) {
        let mut default = self.state.default_provider.write().await;
        *default = Some(id.to_string());
        log::info!("Set default LLM proxy provider: {}", id);
    }

    /// List registered providers
    pub async fn list_providers(&self) -> Vec<String> {
        let providers = self.state.providers.read().await;
        providers.keys().cloned().collect()
    }

    /// Start the proxy service
    pub async fn start(&mut self) -> Result<(), String> {
        if self.shutdown_tx.is_some() {
            return Err("Proxy already running".to_string());
        }

        let (shutdown_tx, shutdown_rx) = oneshot::channel();
        let state = self.state.clone();
        let port = self.port;

        // Build router
        let app = Router::new()
            .route("/v1/chat/completions", post(chat_completions))
            .route("/v1/models", get(list_models))
            .route("/health", get(health_check))
            .route("/metrics", get(metrics_handler))
            .layer(CorsLayer::new().allow_origin(Any).allow_methods(Any).allow_headers(Any))
            .with_state(state);

        let addr = SocketAddr::from(([127, 0, 0, 1], port));

        // Spawn server task
        tokio::spawn(async move {
            let listener = match tokio::net::TcpListener::bind(addr).await {
                Ok(l) => l,
                Err(e) => {
                    log::error!("Failed to bind LLM proxy to {}: {}", addr, e);
                    return;
                }
            };

            log::info!("LLM proxy service started on http://{}", addr);

            axum::serve(listener, app)
                .with_graceful_shutdown(async {
                    let _ = shutdown_rx.await;
                    log::info!("LLM proxy service shutting down");
                })
                .await
                .ok();
        });

        self.shutdown_tx = Some(shutdown_tx);
        Ok(())
    }

    /// Stop the proxy service
    pub async fn stop(&mut self) {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
            log::info!("LLM proxy service stopped");
        }
    }

    /// Check if the service is running
    pub fn is_running(&self) -> bool {
        self.shutdown_tx.is_some()
    }

    /// Get metrics snapshot
    pub fn get_metrics(&self) -> MetricsSnapshot {
        self.state.metrics.snapshot()
    }
}

// ============================================================================
// HTTP Handlers
// ============================================================================

/// Health check endpoint
async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

/// Metrics endpoint returning JSON health data
async fn metrics_handler(State(state): State<Arc<ProxyState>>) -> impl IntoResponse {
    let snapshot = state.metrics.snapshot();
    let providers = state.providers.read().await;
    let provider_count = providers.len();

    Json(serde_json::json!({
        "status": "ok",
        "requests": {
            "total": snapshot.total_requests,
            "successful": snapshot.successful_requests,
            "failed": snapshot.failed_requests
        },
        "providers": {
            "count": provider_count
        }
    }))
}

/// List models endpoint
async fn list_models(State(state): State<Arc<ProxyState>>) -> impl IntoResponse {
    let providers = state.providers.read().await;
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();

    let models: Vec<OpenAIModel> = providers
        .iter()
        .map(|(id, provider)| OpenAIModel {
            id: format!("{}:{}", id, provider.model()),
            object: "model".to_string(),
            created: now,
            owned_by: provider.name().to_string(),
        })
        .collect();

    Json(OpenAIModelList {
        object: "list".to_string(),
        data: models,
    })
}

/// Chat completions endpoint
async fn chat_completions(
    State(state): State<Arc<ProxyState>>,
    Json(request): Json<OpenAIChatRequest>,
) -> Response {
    // Parse provider from model name
    let (provider_id, _actual_model) = match state.parse_model(&request.model).await {
        Some(parsed) => parsed,
        None => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({
                    "error": {
                        "message": "Invalid model format. Use 'provider:model' or set a default provider.",
                        "type": "invalid_request_error"
                    }
                })),
            )
                .into_response();
        }
    };

    // Get provider
    let provider = match state.get_provider(&provider_id).await {
        Some(p) => p,
        None => {
            return (
                StatusCode::NOT_FOUND,
                Json(serde_json::json!({
                    "error": {
                        "message": format!("Provider '{}' not found", provider_id),
                        "type": "invalid_request_error"
                    }
                })),
            )
                .into_response();
        }
    };

    // Convert messages
    let messages: Vec<ChatMessage> = request.messages.into_iter().map(|m| m.into()).collect();

    // Build internal request
    let chat_request = ChatRequest {
        messages,
        system_prompt: None,
        temperature: request.temperature,
        max_tokens: request.max_tokens,
        provider: None,
    };

    if request.stream {
        // Streaming response
        handle_streaming(provider, chat_request, request.model).await
    } else {
        // Non-streaming response
        handle_non_streaming(provider, chat_request, request.model).await
    }
}

/// Handle non-streaming chat request
async fn handle_non_streaming(
    provider: Arc<dyn LLMProvider>,
    request: ChatRequest,
    model: String,
) -> Response {
    match provider.chat(request).await {
        Ok(response) => {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs();

            let usage = response.usage.map(|u| OpenAIUsage {
                prompt_tokens: u.input_tokens,
                completion_tokens: u.output_tokens,
                total_tokens: u.input_tokens + u.output_tokens,
            });

            let openai_response = OpenAIChatResponse {
                id: format!("chatcmpl-{}", uuid::Uuid::new_v4()),
                object: "chat.completion".to_string(),
                created: now,
                model,
                choices: vec![OpenAIChoice {
                    index: 0,
                    message: OpenAIMessage {
                        role: "assistant".to_string(),
                        content: response.content,
                    },
                    finish_reason: response.finish_reason,
                }],
                usage,
            };

            Json(openai_response).into_response()
        }
        Err(e) => error_response(e),
    }
}

/// Handle streaming chat request
async fn handle_streaming(
    provider: Arc<dyn LLMProvider>,
    request: ChatRequest,
    model: String,
) -> Response {
    match provider.stream_chat(request).await {
        Ok(mut rx) => {
            let stream_id = format!("chatcmpl-{}", uuid::Uuid::new_v4());
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs();

            let stream = async_stream::stream! {
                let mut is_first = true;

                while let Some(result) = rx.recv().await {
                    match result {
                        Ok(chunk) => {
                            let delta = if is_first {
                                is_first = false;
                                OpenAIDelta {
                                    role: Some("assistant".to_string()),
                                    content: Some(chunk.content),
                                }
                            } else {
                                OpenAIDelta {
                                    role: None,
                                    content: Some(chunk.content),
                                }
                            };

                            let stream_chunk = OpenAIStreamChunk {
                                id: stream_id.clone(),
                                object: "chat.completion.chunk".to_string(),
                                created: now,
                                model: model.clone(),
                                choices: vec![OpenAIStreamChoice {
                                    index: 0,
                                    delta,
                                    finish_reason: if chunk.is_final {
                                        Some(chunk.finish_reason.unwrap_or_else(|| "stop".to_string()))
                                    } else {
                                        None
                                    },
                                }],
                            };

                            let json = serde_json::to_string(&stream_chunk).unwrap();
                            yield Ok::<_, Infallible>(Event::default().data(json));

                            if chunk.is_final {
                                yield Ok(Event::default().data("[DONE]"));
                                break;
                            }
                        }
                        Err(e) => {
                            log::error!("Stream error: {}", e);
                            break;
                        }
                    }
                }
            };

            Sse::new(stream)
                .keep_alive(axum::response::sse::KeepAlive::new())
                .into_response()
        }
        Err(e) => error_response(e),
    }
}

/// Convert LLMError to HTTP error response
fn error_response(error: LLMError) -> Response {
    let (status, error_type) = match &error {
        LLMError::AuthError(_) => (StatusCode::UNAUTHORIZED, "authentication_error"),
        LLMError::RateLimited { .. } => (StatusCode::TOO_MANY_REQUESTS, "rate_limit_error"),
        LLMError::NotConfigured(_) => (StatusCode::SERVICE_UNAVAILABLE, "service_unavailable"),
        LLMError::Timeout => (StatusCode::GATEWAY_TIMEOUT, "timeout_error"),
        _ => (StatusCode::INTERNAL_SERVER_ERROR, "internal_error"),
    };

    (
        status,
        Json(serde_json::json!({
            "error": {
                "message": error.to_string(),
                "type": error_type
            }
        })),
    )
        .into_response()
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use super::super::cost::ProviderPricing;
    use async_trait::async_trait;
    use tokio::sync::mpsc;

    // ========================================================================
    // MockProvider for testing
    // ========================================================================

    /// Mock LLM provider for testing purposes
    pub struct MockProvider {
        id: String,
        name: String,
        model: String,
        healthy: bool,
    }

    impl MockProvider {
        pub fn new(id: &str, name: &str, model: &str) -> Self {
            Self {
                id: id.to_string(),
                name: name.to_string(),
                model: model.to_string(),
                healthy: true,
            }
        }

        pub fn with_health(mut self, healthy: bool) -> Self {
            self.healthy = healthy;
            self
        }
    }

    #[async_trait]
    impl LLMProvider for MockProvider {
        fn id(&self) -> &str {
            &self.id
        }

        fn name(&self) -> &str {
            &self.name
        }

        fn model(&self) -> &str {
            &self.model
        }

        async fn health_check(&self) -> bool {
            self.healthy
        }

        fn pricing(&self) -> Option<ProviderPricing> {
            None
        }

        async fn chat(&self, _request: ChatRequest) -> super::super::router::Result<ChatResponse> {
            Ok(ChatResponse {
                content: "Mock response".to_string(),
                model: self.model.clone(),
                provider: self.id.clone(),
                usage: None,
                finish_reason: Some("stop".to_string()),
                latency_ms: 100,
                cost_usd: None,
            })
        }

        async fn stream_chat(
            &self,
            _request: ChatRequest,
        ) -> super::super::router::Result<mpsc::Receiver<super::super::router::Result<ChatChunk>>> {
            let (tx, rx) = mpsc::channel(1);
            let model = self.model.clone();
            let provider = self.id.clone();

            tokio::spawn(async move {
                let chunk = ChatChunk {
                    stream_id: "mock-stream".to_string(),
                    content: "Mock streaming response".to_string(),
                    provider,
                    model,
                    is_final: true,
                    finish_reason: Some("stop".to_string()),
                    usage: None,
                    index: 0,
                };
                let _ = tx.send(Ok(chunk)).await;
            });

            Ok(rx)
        }
    }

    // ========================================================================
    // Existing tests
    // ========================================================================

    #[test]
    fn test_openai_message_conversion() {
        let msg = OpenAIMessage {
            role: "user".to_string(),
            content: "Hello".to_string(),
        };
        let chat_msg: ChatMessage = msg.into();
        assert_eq!(chat_msg.role, MessageRole::User);
        assert_eq!(chat_msg.content, "Hello");
    }

    #[tokio::test]
    async fn test_model_parsing() {
        let state = ProxyState::new();

        // With prefix
        let result = state.parse_model("claude:claude-sonnet-4-20250514").await;
        assert_eq!(result, Some(("claude".to_string(), "claude-sonnet-4-20250514".to_string())));

        // Without prefix, no default
        let result = state.parse_model("gpt-4").await;
        assert_eq!(result, None);

        // Set default and try again
        {
            let mut default = state.default_provider.write().await;
            *default = Some("openai".to_string());
        }
        let result = state.parse_model("gpt-4").await;
        assert_eq!(result, Some(("openai".to_string(), "gpt-4".to_string())));
    }

    // ========================================================================
    // Model name parsing tests
    // ========================================================================

    #[tokio::test]
    async fn test_model_parsing_various_formats() {
        let state = ProxyState::new();

        // Standard provider:model format
        let result = state.parse_model("gemini:gemini-pro").await;
        assert_eq!(result, Some(("gemini".to_string(), "gemini-pro".to_string())));

        // Provider with complex model name
        let result = state.parse_model("openai:gpt-4-turbo-preview").await;
        assert_eq!(result, Some(("openai".to_string(), "gpt-4-turbo-preview".to_string())));

        // Model name containing colon after provider prefix
        let result = state.parse_model("custom:model:with:colons").await;
        assert_eq!(result, Some(("custom".to_string(), "model:with:colons".to_string())));

        // Empty provider part
        let result = state.parse_model(":model").await;
        assert_eq!(result, Some(("".to_string(), "model".to_string())));
    }

    // ========================================================================
    // Provider registration/lookup tests
    // ========================================================================

    #[tokio::test]
    async fn test_provider_registration() {
        let service = LLMProxyService::new(0);
        let mock = Arc::new(MockProvider::new("test-provider", "Test Provider", "test-model"));

        // Register provider
        service.register_provider("test-provider", mock.clone()).await;

        // Verify registration
        let providers = service.list_providers().await;
        assert!(providers.contains(&"test-provider".to_string()));

        // Lookup provider
        let found = service.state.get_provider("test-provider").await;
        assert!(found.is_some());
        assert_eq!(found.unwrap().id(), "test-provider");
    }

    #[tokio::test]
    async fn test_provider_unregistration() {
        let service = LLMProxyService::new(0);
        let mock = Arc::new(MockProvider::new("temp-provider", "Temp", "temp-model"));

        // Register and then unregister
        service.register_provider("temp-provider", mock).await;
        assert!(service.list_providers().await.contains(&"temp-provider".to_string()));

        service.unregister_provider("temp-provider").await;
        assert!(!service.list_providers().await.contains(&"temp-provider".to_string()));

        // Lookup should fail
        let found = service.state.get_provider("temp-provider").await;
        assert!(found.is_none());
    }

    #[tokio::test]
    async fn test_multiple_providers() {
        let service = LLMProxyService::new(0);

        let claude = Arc::new(MockProvider::new("claude", "Claude", "claude-sonnet"));
        let gemini = Arc::new(MockProvider::new("gemini", "Gemini", "gemini-pro"));
        let openai = Arc::new(MockProvider::new("openai", "OpenAI", "gpt-4"));

        service.register_provider("claude", claude).await;
        service.register_provider("gemini", gemini).await;
        service.register_provider("openai", openai).await;

        let providers = service.list_providers().await;
        assert_eq!(providers.len(), 3);
        assert!(providers.contains(&"claude".to_string()));
        assert!(providers.contains(&"gemini".to_string()));
        assert!(providers.contains(&"openai".to_string()));
    }

    // ========================================================================
    // Proxy start/stop lifecycle tests
    // ========================================================================

    #[tokio::test]
    async fn test_proxy_lifecycle() {
        let mut service = LLMProxyService::new(0); // Port 0 = OS assigns free port

        // Initially not running
        assert!(!service.is_running());

        // Start succeeds
        let result = service.start().await;
        assert!(result.is_ok());
        assert!(service.is_running());

        // Double start fails
        let result = service.start().await;
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "Proxy already running");

        // Stop
        service.stop().await;
        assert!(!service.is_running());

        // Can restart after stop
        let result = service.start().await;
        assert!(result.is_ok());
        assert!(service.is_running());

        // Cleanup
        service.stop().await;
    }

    #[tokio::test]
    async fn test_proxy_url() {
        let service = LLMProxyService::new(8787);
        assert_eq!(service.url(), "http://127.0.0.1:8787");

        let custom_service = LLMProxyService::new(9000);
        assert_eq!(custom_service.url(), "http://127.0.0.1:9000");
    }

    #[tokio::test]
    async fn test_default_provider_setting() {
        let service = LLMProxyService::new(0);

        // Set default
        service.set_default_provider("claude").await;

        // Verify via model parsing
        let result = service.state.parse_model("sonnet-4").await;
        assert_eq!(result, Some(("claude".to_string(), "sonnet-4".to_string())));
    }

    // ========================================================================
    // ProxyMetrics tests
    // ========================================================================

    #[test]
    fn test_metrics_new() {
        let metrics = ProxyMetrics::new();
        let snapshot = metrics.snapshot();

        assert_eq!(snapshot.total_requests, 0);
        assert_eq!(snapshot.successful_requests, 0);
        assert_eq!(snapshot.failed_requests, 0);
    }

    #[test]
    fn test_metrics_record_success() {
        let metrics = ProxyMetrics::new();

        metrics.record_success();
        metrics.record_success();

        let snapshot = metrics.snapshot();
        assert_eq!(snapshot.total_requests, 2);
        assert_eq!(snapshot.successful_requests, 2);
        assert_eq!(snapshot.failed_requests, 0);
    }

    #[test]
    fn test_metrics_record_failure() {
        let metrics = ProxyMetrics::new();

        metrics.record_failure();
        metrics.record_failure();
        metrics.record_failure();

        let snapshot = metrics.snapshot();
        assert_eq!(snapshot.total_requests, 3);
        assert_eq!(snapshot.successful_requests, 0);
        assert_eq!(snapshot.failed_requests, 3);
    }

    #[test]
    fn test_metrics_mixed_requests() {
        let metrics = ProxyMetrics::new();

        metrics.record_success();
        metrics.record_failure();
        metrics.record_success();
        metrics.record_success();
        metrics.record_failure();

        let snapshot = metrics.snapshot();
        assert_eq!(snapshot.total_requests, 5);
        assert_eq!(snapshot.successful_requests, 3);
        assert_eq!(snapshot.failed_requests, 2);
    }

    #[test]
    fn test_metrics_thread_safety() {
        use std::thread;

        let metrics = Arc::new(ProxyMetrics::new());
        let mut handles = vec![];

        // Spawn multiple threads recording successes
        for _ in 0..10 {
            let m = Arc::clone(&metrics);
            handles.push(thread::spawn(move || {
                for _ in 0..100 {
                    m.record_success();
                }
            }));
        }

        // Spawn multiple threads recording failures
        for _ in 0..5 {
            let m = Arc::clone(&metrics);
            handles.push(thread::spawn(move || {
                for _ in 0..100 {
                    m.record_failure();
                }
            }));
        }

        for h in handles {
            h.join().unwrap();
        }

        let snapshot = metrics.snapshot();
        assert_eq!(snapshot.total_requests, 1500); // 10*100 + 5*100
        assert_eq!(snapshot.successful_requests, 1000); // 10*100
        assert_eq!(snapshot.failed_requests, 500); // 5*100
    }

    #[test]
    fn test_proxy_state_includes_metrics() {
        let state = ProxyState::new();

        // Metrics should be accessible and zeroed
        let snapshot = state.metrics.snapshot();
        assert_eq!(snapshot.total_requests, 0);

        // Record via state
        state.metrics.record_success();
        let snapshot = state.metrics.snapshot();
        assert_eq!(snapshot.successful_requests, 1);
    }
}
