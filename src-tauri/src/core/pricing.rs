//! LLM Pricing Data
//!
//! Provides pricing information for cost estimation across providers.

use serde::{Deserialize, Serialize};

/// Pricing per million tokens (input, output) in USD
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct ModelPricing {
    pub input_per_million: f64,
    pub output_per_million: f64,
}

impl ModelPricing {
    pub const fn new(input: f64, output: f64) -> Self {
        Self {
            input_per_million: input,
            output_per_million: output,
        }
    }

    /// Calculate cost for given token counts
    pub fn calculate_cost(&self, input_tokens: u32, output_tokens: u32) -> f64 {
        let input_cost = (input_tokens as f64 / 1_000_000.0) * self.input_per_million;
        let output_cost = (output_tokens as f64 / 1_000_000.0) * self.output_per_million;
        input_cost + output_cost
    }

    /// Estimate cost for a request (rough token estimate from char count)
    pub fn estimate_from_chars(&self, input_chars: usize, estimated_output_tokens: u32) -> f64 {
        // Rough estimate: ~4 chars per token
        let estimated_input_tokens = (input_chars / 4) as u32;
        self.calculate_cost(estimated_input_tokens, estimated_output_tokens)
    }
}

/// Get pricing for a specific model
pub fn get_model_pricing(provider: &str, model: &str) -> Option<ModelPricing> {
    // Prices as of Dec 2024 - should be updated periodically
    match provider {
        "claude" | "anthropic" => match model {
            m if m.contains("opus") => Some(ModelPricing::new(15.0, 75.0)),
            m if m.contains("sonnet-4") => Some(ModelPricing::new(3.0, 15.0)),
            m if m.contains("3-5-sonnet") || m.contains("3.5-sonnet") => Some(ModelPricing::new(3.0, 15.0)),
            m if m.contains("haiku") => Some(ModelPricing::new(0.25, 1.25)),
            _ => Some(ModelPricing::new(3.0, 15.0)), // Default to sonnet pricing
        },
        "openai" => match model {
            "gpt-4o" | "gpt-4o-2024-11-20" => Some(ModelPricing::new(2.50, 10.0)),
            "gpt-4o-mini" => Some(ModelPricing::new(0.15, 0.60)),
            m if m.starts_with("gpt-4-turbo") => Some(ModelPricing::new(10.0, 30.0)),
            m if m.starts_with("gpt-4") => Some(ModelPricing::new(30.0, 60.0)),
            m if m.starts_with("gpt-3.5") => Some(ModelPricing::new(0.50, 1.50)),
            m if m.starts_with("o1-preview") => Some(ModelPricing::new(15.0, 60.0)),
            m if m.starts_with("o1-mini") => Some(ModelPricing::new(3.0, 12.0)),
            m if m.starts_with("o3") || m.starts_with("o4") => Some(ModelPricing::new(15.0, 60.0)),
            _ => Some(ModelPricing::new(2.50, 10.0)), // Default to gpt-4o
        },
        "gemini" | "google" => match model {
            m if m.contains("2.0-flash") => Some(ModelPricing::new(0.075, 0.30)),
            m if m.contains("1.5-pro") => Some(ModelPricing::new(1.25, 5.0)),
            m if m.contains("1.5-flash") => Some(ModelPricing::new(0.075, 0.30)),
            m if m.contains("1.0-pro") => Some(ModelPricing::new(0.50, 1.50)),
            _ => Some(ModelPricing::new(0.075, 0.30)), // Default to flash
        },
        "mistral" => match model {
            "mistral-large-latest" | "mistral-large" => Some(ModelPricing::new(2.0, 6.0)),
            "mistral-medium" | "mistral-medium-latest" => Some(ModelPricing::new(2.7, 8.1)),
            "mistral-small" | "mistral-small-latest" => Some(ModelPricing::new(0.2, 0.6)),
            "codestral" | "codestral-latest" => Some(ModelPricing::new(0.2, 0.6)),
            m if m.contains("nemo") => Some(ModelPricing::new(0.15, 0.15)),
            _ => Some(ModelPricing::new(0.2, 0.6)),
        },
        "groq" => {
            // Groq has very low/free pricing for most models
            Some(ModelPricing::new(0.05, 0.08))
        },
        "together" => match model {
            m if m.contains("405B") => Some(ModelPricing::new(3.5, 3.5)),
            m if m.contains("70B") => Some(ModelPricing::new(0.88, 0.88)),
            m if m.contains("8B") => Some(ModelPricing::new(0.18, 0.18)),
            m if m.contains("Mixtral") => Some(ModelPricing::new(0.6, 0.6)),
            _ => Some(ModelPricing::new(0.5, 0.5)),
        },
        "cohere" => match model {
            "command-r-plus" => Some(ModelPricing::new(2.5, 10.0)),
            "command-r" => Some(ModelPricing::new(0.15, 0.60)),
            "command-light" => Some(ModelPricing::new(0.15, 0.15)),
            _ => Some(ModelPricing::new(0.5, 2.0)),
        },
        "deepseek" => {
            // DeepSeek has very competitive pricing
            match model {
                "deepseek-reasoner" => Some(ModelPricing::new(0.55, 2.19)),
                _ => Some(ModelPricing::new(0.14, 0.28)),
            }
        },
        "openrouter" => {
            // OpenRouter adds ~5% markup, prices vary by underlying model
            // Extract provider from model ID (e.g., "openai/gpt-4o" -> "openai")
            if let Some(slash_pos) = model.find('/') {
                let underlying_provider = &model[..slash_pos];
                let underlying_model = &model[slash_pos + 1..];
                get_model_pricing(underlying_provider, underlying_model)
                    .map(|p| ModelPricing::new(p.input_per_million * 1.05, p.output_per_million * 1.05))
            } else {
                Some(ModelPricing::new(2.0, 6.0)) // Default fallback
            }
        },
        "ollama" => {
            // Ollama is local/free
            Some(ModelPricing::new(0.0, 0.0))
        },
        _ => None,
    }
}

/// Get default pricing for a provider (used when model not found)
pub fn get_provider_default_pricing(provider: &str) -> ModelPricing {
    match provider {
        "claude" | "anthropic" => ModelPricing::new(3.0, 15.0),
        "openai" => ModelPricing::new(2.50, 10.0),
        "gemini" | "google" => ModelPricing::new(0.075, 0.30),
        "mistral" => ModelPricing::new(0.2, 0.6),
        "groq" => ModelPricing::new(0.05, 0.08),
        "together" => ModelPricing::new(0.5, 0.5),
        "cohere" => ModelPricing::new(0.5, 2.0),
        "deepseek" => ModelPricing::new(0.14, 0.28),
        "openrouter" => ModelPricing::new(2.0, 6.0),
        "ollama" => ModelPricing::new(0.0, 0.0),
        _ => ModelPricing::new(1.0, 3.0), // Conservative default
    }
}

/// Provider tier for cost optimization routing
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum CostTier {
    Free,      // Ollama, some Groq models
    Budget,    // Groq, DeepSeek, small models
    Standard,  // GPT-4o-mini, Claude Haiku, Gemini Flash
    Premium,   // GPT-4o, Claude Sonnet
    Elite,     // GPT-4, Claude Opus, o1
}

/// Get cost tier for a provider/model combination
pub fn get_cost_tier(provider: &str, model: &str) -> CostTier {
    match provider {
        "ollama" => CostTier::Free,
        "groq" => CostTier::Budget,
        "deepseek" => CostTier::Budget,
        "gemini" if model.contains("flash") => CostTier::Standard,
        "gemini" => CostTier::Premium,
        "openai" if model.contains("mini") || model.contains("3.5") => CostTier::Standard,
        "openai" if model.starts_with("o1") || model.starts_with("o3") => CostTier::Elite,
        "openai" => CostTier::Premium,
        "claude" if model.contains("haiku") => CostTier::Standard,
        "claude" if model.contains("opus") => CostTier::Elite,
        "claude" => CostTier::Premium,
        "mistral" if model.contains("small") || model.contains("nemo") => CostTier::Budget,
        "mistral" => CostTier::Premium,
        "cohere" if model.contains("light") => CostTier::Budget,
        "cohere" => CostTier::Standard,
        "together" if model.contains("405B") => CostTier::Elite,
        "together" => CostTier::Standard,
        _ => CostTier::Standard,
    }
}

/// Get cheaper alternative model for a given model
pub fn get_cheaper_alternative(provider: &str, model: &str) -> Option<(&'static str, &'static str)> {
    match (provider, model) {
        // OpenAI downgrades
        ("openai", m) if m.starts_with("gpt-4o") && !m.contains("mini") => Some(("openai", "gpt-4o-mini")),
        ("openai", m) if m.starts_with("gpt-4") => Some(("openai", "gpt-4o-mini")),
        ("openai", m) if m.starts_with("o1") => Some(("openai", "gpt-4o")),

        // Claude downgrades
        ("claude", m) if m.contains("opus") => Some(("claude", "claude-3-5-sonnet-20241022")),
        ("claude", m) if m.contains("sonnet") => Some(("claude", "claude-3-5-haiku-20241022")),

        // Gemini downgrades
        ("gemini", m) if m.contains("pro") => Some(("gemini", "gemini-1.5-flash")),

        // Mistral downgrades
        ("mistral", m) if m.contains("large") => Some(("mistral", "mistral-small-latest")),

        // Cross-provider: suggest DeepSeek or Groq as budget alternatives
        (_, _) => Some(("deepseek", "deepseek-chat")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pricing_calculation() {
        let pricing = ModelPricing::new(3.0, 15.0);
        let cost = pricing.calculate_cost(1000, 500);

        // 1000 input tokens = 0.003
        // 500 output tokens = 0.0075
        // Total = 0.0105
        assert!((cost - 0.0105).abs() < 0.0001);
    }

    #[test]
    fn test_get_model_pricing() {
        let pricing = get_model_pricing("openai", "gpt-4o").unwrap();
        assert!(pricing.input_per_million > 0.0);
        assert!(pricing.output_per_million > 0.0);
    }

    #[test]
    fn test_openrouter_passthrough() {
        let pricing = get_model_pricing("openrouter", "openai/gpt-4o").unwrap();
        let openai_pricing = get_model_pricing("openai", "gpt-4o").unwrap();

        // OpenRouter should be ~5% more
        assert!(pricing.input_per_million > openai_pricing.input_per_million);
    }

    #[test]
    fn test_cost_tiers() {
        assert_eq!(get_cost_tier("ollama", "llama3.2"), CostTier::Free);
        assert_eq!(get_cost_tier("groq", "llama-70b"), CostTier::Budget);
        assert_eq!(get_cost_tier("openai", "gpt-4o-mini"), CostTier::Standard);
        assert_eq!(get_cost_tier("openai", "gpt-4o"), CostTier::Premium);
        assert_eq!(get_cost_tier("claude", "claude-3-opus"), CostTier::Elite);
    }
}
