//! Frontend Tests Module
//!
//! This module contains all frontend tests using wasm-bindgen-test.
//! Tests are organized into component tests and service tests.
//!
//! ## Running Tests
//!
//! To run all frontend tests in a browser:
//! ```bash
//! wasm-pack test --headless --firefox frontend
//! # or
//! wasm-pack test --headless --chrome frontend
//! ```
//!
//! ## Test Organization
//!
//! - `components/` - Tests for UI components
//!   - `campaign_tests` - CampaignDashboard, CampaignCard tests
//!   - `session_tests` - ActiveSession, CombatTracker, InitiativeList tests
//!   - `settings_tests` - LLM settings, Voice settings tests
//!
//! - `services/` - Tests for frontend services
//!   - `layout_service_tests` - LayoutService responsive states
//!   - `notification_tests` - NotificationService toast lifecycle
//!
//! - `header_link_test` - Regression test for HeaderLink component

pub mod components;
pub mod services;
