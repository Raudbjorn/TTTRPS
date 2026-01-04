//! LLM Provider Unit Tests
//!
//! Comprehensive unit tests for all LLM provider implementations.
//! Uses wiremock for HTTP mocking to test:
//! - API request formatting
//! - Response parsing (success and error cases)
//! - Model switching
//! - Streaming response handling
//! - Rate limit error handling
//! - Timeout handling
//! - Invalid API key handling

mod claude_tests;
mod openai_tests;
mod gemini_tests;
mod ollama_tests;
