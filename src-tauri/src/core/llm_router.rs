//! LLM Provider Router
//!
//! Intelligent routing between LLM providers with health checking,
//! automatic fallback, circuit breaker pattern, and integrated cost tracking.

use crate::core::llm::{LLMClient, LLMConfig, LLMError, ChatRequest, ChatResponse, EmbeddingResponse};
use crate::core::pricing::{get_model_pricing, get_provider_default_pricing, CostTier, get_cost_tier};
use crate::core::budget::{BudgetEnforcer, BudgetAction, SpendingRecord};
use crate::core::cost_predictor::CostPredictor;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};
use tokio::time::timeout;

// ============================================================================
// Circuit Breaker
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CircuitState {
    Closed,      // Normal operation
    Open,        // Failing, reject requests
    HalfOpen,    // Testing if recovered
}

#[derive(Debug, Clone)]
pub struct CircuitBreaker {
    state: CircuitState,
    failure_count: u32,
    success_count: u32,
    last_failure: Option<Instant>,
    failure_threshold: u32,
    success_threshold: u32,
    timeout_duration: Duration,
}

impl Default for CircuitBreaker {
    fn default() -> Self {
        Self {
            state: CircuitState::Closed,
            failure_count: 0,
            success_count: 0,
            last_failure: None,
            failure_threshold: 3,
            success_threshold: 2,
            timeout_duration: Duration::from_secs(30),
        }
    }
}

impl CircuitBreaker {
    pub fn can_execute(&mut self) -> bool {
        match self.state {
            CircuitState::Closed => true,
            CircuitState::Open => {
                // Check if timeout has passed
                if let Some(last) = self.last_failure {
                    if last.elapsed() >= self.timeout_duration {
                        self.state = CircuitState::HalfOpen;
                        self.success_count = 0;
                        return true;
                    }
                }
                false
            }
            CircuitState::HalfOpen => true,
        }
    }

    pub fn record_success(&mut self) {
        self.failure_count = 0;
        match self.state {
            CircuitState::HalfOpen => {
                self.success_count += 1;
                if self.success_count >= self.success_threshold {
                    self.state = CircuitState::Closed;
                }
            }
            _ => {
                self.state = CircuitState::Closed;
            }
        }
    }

    pub fn record_failure(&mut self) {
        self.failure_count += 1;
        self.last_failure = Some(Instant::now());
        self.success_count = 0;

        if self.failure_count >= self.failure_threshold {
            self.state = CircuitState::Open;
        }
    }

    pub fn state(&self) -> CircuitState {
        self.state
    }
}

// ============================================================================
// Provider Stats
// ============================================================================

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProviderStats {
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub total_latency_ms: u64,
    #[serde(skip)]
    pub last_used: Option<Instant>,
    /// Total tokens used (input + output)
    pub total_tokens: u64,
    /// Total cost in USD
    pub total_cost: f64,
}

impl ProviderStats {
    pub fn avg_latency_ms(&self) -> u64 {
        if self.successful_requests == 0 {
            0
        } else {
            self.total_latency_ms / self.successful_requests
        }
    }

    pub fn success_rate(&self) -> f64 {
        if self.total_requests == 0 {
            1.0
        } else {
            self.successful_requests as f64 / self.total_requests as f64
        }
    }

    pub fn avg_cost(&self) -> f64 {
        if self.successful_requests == 0 {
            0.0
        } else {
            self.total_cost / self.successful_requests as f64
        }
    }

    pub fn avg_tokens(&self) -> u64 {
        if self.successful_requests == 0 {
            0
        } else {
            self.total_tokens / self.successful_requests
        }
    }
}

// ============================================================================
// Router Configuration
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouterConfig {
    /// Request timeout in seconds
    pub request_timeout_secs: u64,
    /// Whether to enable automatic fallback
    pub enable_fallback: bool,
    /// Health check interval in seconds
    pub health_check_interval_secs: u64,
    /// Whether to enforce budget limits
    pub enforce_budget: bool,
    /// Whether to optimize for cost (may use cheaper providers when possible)
    pub cost_optimization: bool,
    /// Maximum cost tier to use
    pub max_cost_tier: Option<CostTier>,
}

impl Default for RouterConfig {
    fn default() -> Self {
        Self {
            request_timeout_secs: 120,
            enable_fallback: true,
            health_check_interval_secs: 60,
            enforce_budget: true,
            cost_optimization: false,
            max_cost_tier: None,
        }
    }
}

impl RouterConfig {
    pub fn request_timeout(&self) -> Duration {
        Duration::from_secs(self.request_timeout_secs)
    }

    pub fn health_check_interval(&self) -> Duration {
        Duration::from_secs(self.health_check_interval_secs)
    }
}

// ============================================================================
// LLM Router
// ============================================================================

pub struct LLMRouter {
    /// Available providers in priority order
    providers: Vec<(String, LLMConfig)>,
    /// Circuit breakers per provider
    circuit_breakers: Arc<RwLock<HashMap<String, CircuitBreaker>>>,
    /// Stats per provider
    stats: Arc<RwLock<HashMap<String, ProviderStats>>>,
    /// Router configuration
    config: RouterConfig,
    /// Budget enforcer for spending limits
    budget: Arc<BudgetEnforcer>,
    /// Cost predictor for usage forecasting
    cost_predictor: Arc<CostPredictor>,
}

impl LLMRouter {
    pub fn new(config: RouterConfig) -> Self {
        Self {
            providers: Vec::new(),
            circuit_breakers: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(HashMap::new())),
            config,
            budget: Arc::new(BudgetEnforcer::new()),
            cost_predictor: Arc::new(CostPredictor::new()),
        }
    }

    pub fn with_budget(mut self, budget: Arc<BudgetEnforcer>) -> Self {
        self.budget = budget;
        self
    }

    pub fn with_cost_predictor(mut self, predictor: Arc<CostPredictor>) -> Self {
        self.cost_predictor = predictor;
        self
    }

    /// Get the budget enforcer
    pub fn budget(&self) -> &BudgetEnforcer {
        &self.budget
    }

    /// Get the cost predictor
    pub fn cost_predictor(&self) -> &CostPredictor {
        &self.cost_predictor
    }

    /// Add a provider to the router
    pub fn add_provider(&mut self, name: impl Into<String>, config: LLMConfig) {
        let name = name.into();
        self.providers.push((name.clone(), config));

        // Initialize circuit breaker and stats
        if let Ok(mut breakers) = self.circuit_breakers.write() {
            breakers.insert(name.clone(), CircuitBreaker::default());
        }
        if let Ok(mut stats) = self.stats.write() {
            stats.insert(name, ProviderStats::default());
        }
    }

    /// Remove a provider
    pub fn remove_provider(&mut self, name: &str) {
        self.providers.retain(|(n, _)| n != name);
        if let Ok(mut breakers) = self.circuit_breakers.write() {
            breakers.remove(name);
        }
        if let Ok(mut stats) = self.stats.write() {
            stats.remove(name);
        }
    }

    /// Get provider names in priority order
    pub fn provider_names(&self) -> Vec<String> {
        self.providers.iter().map(|(n, _)| n.clone()).collect()
    }

    /// Get stats for a provider
    pub fn get_stats(&self, name: &str) -> Option<ProviderStats> {
        self.stats.read().ok()?.get(name).cloned()
    }

    /// Get all provider stats
    pub fn get_all_stats(&self) -> HashMap<String, ProviderStats> {
        self.stats.read().ok().map(|s| s.clone()).unwrap_or_default()
    }

    /// Get circuit breaker state for a provider
    pub fn get_circuit_state(&self, name: &str) -> Option<CircuitState> {
        self.circuit_breakers.read().ok()?.get(name).map(|cb| cb.state())
    }

    /// Check if a provider is available (circuit not open)
    fn is_provider_available(&self, name: &str) -> bool {
        if let Ok(mut breakers) = self.circuit_breakers.write() {
            if let Some(cb) = breakers.get_mut(name) {
                return cb.can_execute();
            }
        }
        false
    }

    /// Record a successful request with cost tracking
    fn record_success(&self, name: &str, model: &str, latency_ms: u64, input_tokens: u32, output_tokens: u32) {
        // Calculate cost
        let pricing = get_model_pricing(name, model)
            .unwrap_or_else(|| get_provider_default_pricing(name));
        let cost = pricing.calculate_cost(input_tokens, output_tokens);

        // Update circuit breaker
        if let Ok(mut breakers) = self.circuit_breakers.write() {
            if let Some(cb) = breakers.get_mut(name) {
                cb.record_success();
            }
        }

        // Update stats with token and cost info
        if let Ok(mut stats) = self.stats.write() {
            if let Some(s) = stats.get_mut(name) {
                s.total_requests += 1;
                s.successful_requests += 1;
                s.total_latency_ms += latency_ms;
                s.last_used = Some(Instant::now());
                s.total_tokens += (input_tokens + output_tokens) as u64;
                s.total_cost += cost;
            }
        }

        // Record in budget enforcer
        self.budget.record_spending(SpendingRecord {
            timestamp: Utc::now(),
            amount: cost,
            provider: name.to_string(),
            model: model.to_string(),
            input_tokens,
            output_tokens,
        });

        // Record in cost predictor
        self.cost_predictor.record(cost, input_tokens + output_tokens, 1);
    }

    /// Record a failed request
    fn record_failure(&self, name: &str) {
        if let Ok(mut breakers) = self.circuit_breakers.write() {
            if let Some(cb) = breakers.get_mut(name) {
                cb.record_failure();
            }
        }
        if let Ok(mut stats) = self.stats.write() {
            if let Some(s) = stats.get_mut(name) {
                s.total_requests += 1;
                s.failed_requests += 1;
                s.last_used = Some(Instant::now());
            }
        }
    }

    /// Get the next available provider
    fn get_available_provider(&self) -> Option<(String, LLMConfig)> {
        for (name, config) in &self.providers {
            if self.is_provider_available(name) {
                return Some((name.clone(), config.clone()));
            }
        }
        None
    }

    /// Get model name from config
    fn get_model_from_config(config: &LLMConfig) -> &str {
        match config {
            LLMConfig::Ollama { model, .. } => model,
            LLMConfig::Claude { model, .. } => model,
            LLMConfig::Gemini { model, .. } => model,
            LLMConfig::OpenAI { model, .. } => model,
            LLMConfig::OpenRouter { model, .. } => model,
            LLMConfig::Mistral { model, .. } => model,
            LLMConfig::Groq { model, .. } => model,
            LLMConfig::Together { model, .. } => model,
            LLMConfig::Cohere { model, .. } => model,
            LLMConfig::DeepSeek { model, .. } => model,
        }
    }

    /// Estimate cost for a request before sending
    pub fn estimate_request_cost(&self, provider: &str, model: &str, input_chars: usize, estimated_output_tokens: u32) -> f64 {
        let pricing = get_model_pricing(provider, model)
            .unwrap_or_else(|| get_provider_default_pricing(provider));
        pricing.estimate_from_chars(input_chars, estimated_output_tokens)
    }

    /// Check if a request should be allowed based on budget
    pub fn check_budget(&self, provider: &str, estimated_cost: f64) -> BudgetAction {
        if !self.config.enforce_budget {
            return BudgetAction::Allow;
        }
        self.budget.check_request(estimated_cost, provider)
    }

    /// Send a chat request with automatic fallback and cost tracking
    pub async fn chat(&self, request: ChatRequest) -> Result<ChatResponse, LLMError> {
        let mut last_error: Option<LLMError> = None;
        let mut tried_providers = Vec::new();

        // Calculate input size for cost estimation
        let input_chars: usize = request.messages.iter().map(|m| m.content.len()).sum::<usize>()
            + request.system_prompt.as_ref().map(|s| s.len()).unwrap_or(0);

        // Try providers in order
        for (name, config) in &self.providers {
            let model = Self::get_model_from_config(config);

            // Skip if circuit is open
            if !self.is_provider_available(name) {
                log::debug!("Skipping provider {} (circuit open)", name);
                continue;
            }

            // Check cost tier limit
            if let Some(max_tier) = &self.config.max_cost_tier {
                let tier = get_cost_tier(name, model);
                if tier > *max_tier {
                    log::debug!("Skipping provider {} (cost tier {:?} > max {:?})", name, tier, max_tier);
                    continue;
                }
            }

            // Check budget before making request
            if self.config.enforce_budget {
                let estimated_cost = self.estimate_request_cost(name, model, input_chars, 1000);
                match self.budget.check_request(estimated_cost, name) {
                    BudgetAction::Reject => {
                        log::warn!("Budget limit reached, skipping provider {}", name);
                        continue;
                    }
                    BudgetAction::Degrade => {
                        // Try to find a cheaper alternative, but continue if this is already cheap
                        log::info!("Budget warning: degrading from {} may be needed", name);
                    }
                    _ => {}
                }
            }

            tried_providers.push(name.clone());
            let client = LLMClient::new(config.clone());
            let start = Instant::now();

            // Execute with timeout
            let result = timeout(
                self.config.request_timeout(),
                client.chat(request.clone())
            ).await;

            match result {
                Ok(Ok(response)) => {
                    let latency = start.elapsed().as_millis() as u64;

                    // Extract token usage from response
                    let (input_tokens, output_tokens) = response.usage
                        .as_ref()
                        .map(|u| (u.input_tokens, u.output_tokens))
                        .unwrap_or_else(|| {
                            // Estimate if not provided
                            ((input_chars / 4) as u32, (response.content.len() / 4) as u32)
                        });

                    self.record_success(name, model, latency, input_tokens, output_tokens);
                    log::info!("Chat succeeded with provider {} ({}ms, {} tokens)", name, latency, input_tokens + output_tokens);
                    return Ok(response);
                }
                Ok(Err(e)) => {
                    self.record_failure(name);
                    log::warn!("Chat failed with provider {}: {}", name, e);
                    last_error = Some(e);

                    if !self.config.enable_fallback {
                        break;
                    }
                }
                Err(_) => {
                    self.record_failure(name);
                    log::warn!("Chat timed out with provider {}", name);
                    last_error = Some(LLMError::ApiError {
                        status: 504,
                        message: "Request timed out".to_string(),
                    });

                    if !self.config.enable_fallback {
                        break;
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            if tried_providers.is_empty() {
                LLMError::NotConfigured("No providers available (all circuits open or budget exceeded)".to_string())
            } else {
                LLMError::ApiError {
                    status: 503,
                    message: format!("All providers failed: {:?}", tried_providers),
                }
            }
        }))
    }

    /// Generate embeddings with automatic fallback
    pub async fn embed(&self, text: &str) -> Result<EmbeddingResponse, LLMError> {
        let mut last_error: Option<LLMError> = None;

        for (name, config) in &self.providers {
            if !self.is_provider_available(name) {
                continue;
            }

            let model = Self::get_model_from_config(config);
            let client = LLMClient::new(config.clone());
            let start = Instant::now();

            let result = timeout(
                self.config.request_timeout(),
                client.embed(text)
            ).await;

            match result {
                Ok(Ok(response)) => {
                    let latency = start.elapsed().as_millis() as u64;
                    // Embeddings are typically cheaper - estimate tokens from text length
                    let tokens = (text.len() / 4) as u32;
                    self.record_success(name, model, latency, tokens, 0);
                    return Ok(response);
                }
                Ok(Err(e)) => {
                    // Skip providers that don't support embeddings
                    if matches!(e, LLMError::EmbeddingNotSupported(_)) {
                        continue;
                    }
                    self.record_failure(name);
                    last_error = Some(e);

                    if !self.config.enable_fallback {
                        break;
                    }
                }
                Err(_) => {
                    self.record_failure(name);
                    last_error = Some(LLMError::ApiError {
                        status: 504,
                        message: "Request timed out".to_string(),
                    });

                    if !self.config.enable_fallback {
                        break;
                    }
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            LLMError::EmbeddingNotSupported("No providers support embeddings".to_string())
        }))
    }

    /// Run health checks on all providers
    pub async fn health_check_all(&self) -> HashMap<String, bool> {
        let mut results = HashMap::new();

        for (name, config) in &self.providers {
            let client = LLMClient::new(config.clone());
            let healthy = client.health_check().await.unwrap_or(false);
            results.insert(name.clone(), healthy);

            // Update circuit breaker based on health (no cost for health checks)
            if healthy {
                if let Ok(mut breakers) = self.circuit_breakers.write() {
                    if let Some(cb) = breakers.get_mut(name) {
                        cb.record_success();
                    }
                }
            }
        }

        results
    }

    /// Get provider health status
    pub fn get_provider_health(&self) -> HashMap<String, CircuitState> {
        let mut health = HashMap::new();
        if let Ok(breakers) = self.circuit_breakers.read() {
            for (name, cb) in breakers.iter() {
                health.insert(name.clone(), cb.state());
            }
        }
        health
    }

    /// Get the router configuration
    pub fn config(&self) -> &RouterConfig {
        &self.config
    }

    /// Clone the list of providers (for creating temporary routers)
    pub fn clone_providers(&self) -> Vec<(String, LLMConfig)> {
        self.providers.clone()
    }

    /// Create a router from a list of providers (for temporary use like health checks)
    pub fn from_providers(providers: Vec<(String, LLMConfig)>) -> Self {
        let mut router = Self::new(RouterConfig::default());
        for (name, config) in providers {
            router.add_provider(name, config);
        }
        router
    }
}

// ============================================================================
// Builder Pattern
// ============================================================================

impl LLMRouter {
    pub fn builder() -> LLMRouterBuilder {
        LLMRouterBuilder::new()
    }
}

pub struct LLMRouterBuilder {
    providers: Vec<(String, LLMConfig)>,
    config: RouterConfig,
    budget: Option<Arc<BudgetEnforcer>>,
    cost_predictor: Option<Arc<CostPredictor>>,
}

impl LLMRouterBuilder {
    pub fn new() -> Self {
        Self {
            providers: Vec::new(),
            config: RouterConfig::default(),
            budget: None,
            cost_predictor: None,
        }
    }

    pub fn add_provider(mut self, name: impl Into<String>, config: LLMConfig) -> Self {
        self.providers.push((name.into(), config));
        self
    }

    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.config.request_timeout_secs = timeout.as_secs();
        self
    }

    pub fn with_fallback(mut self, enabled: bool) -> Self {
        self.config.enable_fallback = enabled;
        self
    }

    pub fn with_budget_enforcement(mut self, enabled: bool) -> Self {
        self.config.enforce_budget = enabled;
        self
    }

    pub fn with_cost_optimization(mut self, enabled: bool) -> Self {
        self.config.cost_optimization = enabled;
        self
    }

    pub fn with_max_cost_tier(mut self, tier: CostTier) -> Self {
        self.config.max_cost_tier = Some(tier);
        self
    }

    pub fn with_budget(mut self, budget: Arc<BudgetEnforcer>) -> Self {
        self.budget = Some(budget);
        self
    }

    pub fn with_cost_predictor(mut self, predictor: Arc<CostPredictor>) -> Self {
        self.cost_predictor = Some(predictor);
        self
    }

    pub fn build(self) -> LLMRouter {
        let mut router = LLMRouter::new(self.config);

        // Apply shared budget/predictor if provided
        if let Some(budget) = self.budget {
            router = router.with_budget(budget);
        }
        if let Some(predictor) = self.cost_predictor {
            router = router.with_cost_predictor(predictor);
        }

        // Add providers
        for (name, config) in self.providers {
            router.add_provider(name, config);
        }

        router
    }
}

impl Default for LLMRouterBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_circuit_breaker_default_closed() {
        let mut cb = CircuitBreaker::default();
        assert_eq!(cb.state(), CircuitState::Closed);
        assert!(cb.can_execute());
    }

    #[test]
    fn test_circuit_breaker_opens_after_failures() {
        let mut cb = CircuitBreaker::default();

        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.state(), CircuitState::Closed);

        cb.record_failure(); // Third failure
        assert_eq!(cb.state(), CircuitState::Open);
        assert!(!cb.can_execute());
    }

    #[test]
    fn test_circuit_breaker_resets_on_success() {
        let mut cb = CircuitBreaker::default();

        cb.record_failure();
        cb.record_failure();
        cb.record_success();

        assert_eq!(cb.state(), CircuitState::Closed);
        assert_eq!(cb.failure_count, 0);
    }

    #[test]
    fn test_provider_stats() {
        let mut stats = ProviderStats::default();

        stats.total_requests = 10;
        stats.successful_requests = 8;
        stats.failed_requests = 2;
        stats.total_latency_ms = 1600;

        assert_eq!(stats.success_rate(), 0.8);
        assert_eq!(stats.avg_latency_ms(), 200);
    }
}
