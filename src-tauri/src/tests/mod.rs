//! Test modules for TTRPG Assistant
//!
//! Run all tests: `cargo test`
//! Run integration tests (requires Meilisearch): `cargo test -- --ignored`
//! Run character generation tests: `cargo test character_gen`
//! Run property tests: `cargo test property --release`
//! Run new integration tests: `cargo test integration`

mod database_tests;
pub mod integration;
mod meilisearch_integration_tests;
pub mod mocks;
mod property;
pub mod unit;
