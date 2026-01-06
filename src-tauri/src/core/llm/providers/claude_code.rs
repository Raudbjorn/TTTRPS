//! Claude Code Provider via CLI
//!
//! Provides LLM access through Claude Code CLI (claude -p).
//! This enables programmatic interaction with Claude Code, useful for
//! development/testing without API costs, using your existing authentication.
//!
//! ## Features
//!
//! - Full Claude Code capabilities (file access, tool use, etc.)
//! - Conversation management via session IDs
//! - JSON output parsing for structured responses
//! - Configurable timeout and model selection
//!
//! ## Limitations
//!
//! - No streaming support (full responses only)
//! - Requires Claude Code CLI to be installed
//! - Uses CLI's built-in authentication
//!
//! ## Usage
//!
//! ```rust,no_run
//! use crate::core::llm::providers::ClaudeCodeProvider;
//!
//! let provider = ClaudeCodeProvider::new();
//! // Or with custom timeout
//! let provider = ClaudeCodeProvider::with_config(300, None);
//! ```

use crate::core::llm::cost::ProviderPricing;
use crate::core::llm::router::{
    ChatChunk, ChatRequest, ChatResponse, LLMError, LLMProvider, Result,
};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::process::Stdio;
use std::time::Instant;
use tokio::io::AsyncReadExt;
use tokio::process::Command;
use tokio::sync::mpsc;
use tracing::{debug, error, info, warn};

/// Response structure from Claude Code CLI JSON output
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ClaudeCodeResponse {
    #[serde(default)]
    session_id: Option<String>,
    #[serde(default)]
    result: String,
    #[serde(default)]
    usage: Option<ClaudeCodeUsage>,
    #[serde(default)]
    cost: Option<ClaudeCodeCost>,
    #[serde(default)]
    error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ClaudeCodeUsage {
    #[serde(default)]
    input_tokens: u32,
    #[serde(default)]
    output_tokens: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ClaudeCodeCost {
    #[serde(default)]
    usd: f64,
}

/// Claude Code provider using CLI.
pub struct ClaudeCodeProvider {
    timeout_secs: u64,
    model: Option<String>,
    working_dir: Option<String>,
}

impl ClaudeCodeProvider {
    /// Create a new provider with default configuration.
    pub fn new() -> Self {
        Self::with_config(300, None, None)
    }

    /// Create a new provider with custom timeout.
    pub fn with_timeout(timeout_secs: u64) -> Self {
        Self::with_config(timeout_secs, None, None)
    }

    /// Create a new provider with custom configuration.
    pub fn with_config(timeout_secs: u64, model: Option<String>, working_dir: Option<String>) -> Self {
        Self {
            timeout_secs,
            model,
            working_dir,
        }
    }

    /// Build the message content from the request.
    ///
    /// Includes system prompt and conversation history for context.
    fn build_message(&self, request: &ChatRequest) -> String {
        let mut parts = Vec::new();

        // Add system prompt if present
        if let Some(ref system) = request.system_prompt {
            parts.push(format!("[System Instructions: {}]", system));
        }

        // Add conversation context (messages)
        for msg in request.messages.iter() {
            match msg.role {
                crate::core::llm::router::MessageRole::User => {
                    parts.push(format!("User: {}", msg.content));
                }
                crate::core::llm::router::MessageRole::Assistant => {
                    parts.push(format!("Assistant: {}", msg.content));
                }
                crate::core::llm::router::MessageRole::System => {
                    // Include system messages in context
                    parts.push(format!("[System: {}]", msg.content));
                }
            }
        }

        // Return joined message with all context preserved
        // If no messages, just return the system prompt or empty string
        if parts.is_empty() {
            String::new()
        } else {
            parts.join("\n\n")
        }
    }

    /// Execute a prompt via Claude Code CLI
    async fn execute_prompt(&self, prompt: &str) -> Result<ClaudeCodeResponse> {
        let binary = which::which("claude").map_err(|_| {
            LLMError::NotConfigured(
                "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
                    .to_string(),
            )
        })?;

        let mut cmd = Command::new(binary);
        cmd.arg("-p").arg(prompt);
        cmd.arg("--output-format").arg("json");

        // Add model if specified
        if let Some(ref model) = self.model {
            cmd.arg("--model").arg(model);
        }

        // Set working directory if specified
        if let Some(ref dir) = self.working_dir {
            cmd.current_dir(dir);
        }

        cmd.stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        debug!(command = ?cmd, "executing Claude Code CLI");

        let timeout = tokio::time::Duration::from_secs(self.timeout_secs);
        let mut child = cmd.spawn().map_err(|e| LLMError::ApiError {
            status: 0,
            message: format!("Failed to spawn Claude Code: {}", e),
        })?;

        let result = tokio::time::timeout(timeout, async {
            let mut stdout = String::new();
            let mut stderr = String::new();

            if let Some(mut stdout_handle) = child.stdout.take() {
                stdout_handle.read_to_string(&mut stdout).await?;
            }

            if let Some(mut stderr_handle) = child.stderr.take() {
                stderr_handle.read_to_string(&mut stderr).await?;
            }

            let status = child.wait().await?;
            Ok::<_, std::io::Error>((status, stdout, stderr))
        })
        .await;

        match result {
            Ok(Ok((status, stdout, stderr))) => {
                debug!(
                    status = %status,
                    stdout_len = stdout.len(),
                    stderr_len = stderr.len(),
                    "Claude Code process completed"
                );

                if !status.success() {
                    let error_msg = if !stderr.is_empty() {
                        stderr
                    } else if !stdout.is_empty() {
                        stdout
                    } else {
                        "unknown error".to_string()
                    };

                    error!(status = %status, error = %error_msg, "Claude Code failed");
                    return Err(LLMError::ApiError {
                        status: status.code().unwrap_or(1) as u16,
                        message: error_msg,
                    });
                }

                // Parse JSON response
                serde_json::from_str::<ClaudeCodeResponse>(&stdout).or_else(|_| {
                    // If not JSON, treat as plain text response
                    Ok(ClaudeCodeResponse {
                        session_id: None,
                        result: stdout.trim().to_string(),
                        usage: None,
                        cost: None,
                        error: None,
                    })
                })
            }
            Ok(Err(io_err)) => {
                error!(error = %io_err, "I/O error during Claude Code execution");
                Err(LLMError::ApiError {
                    status: 0,
                    message: format!("I/O error: {}", io_err),
                })
            }
            Err(_) => {
                warn!(
                    timeout_secs = self.timeout_secs,
                    "Claude Code request timed out"
                );
                let _ = child.kill().await;
                Err(LLMError::Timeout)
            }
        }
    }

    /// Check if Claude Code CLI is available
    pub fn is_available() -> bool {
        which::which("claude").is_ok()
    }

    /// Get Claude Code version
    pub async fn version() -> std::result::Result<String, String> {
        let binary = which::which("claude").map_err(|_| "Claude Code CLI not found".to_string())?;

        let output = Command::new(binary)
            .arg("--version")
            .output()
            .await
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            Err("Failed to get Claude Code version".to_string())
        }
    }

    /// Get full status of Claude Code CLI (installed, logged in, version)
    pub async fn get_status() -> ClaudeCodeStatus {
        // Check if skill is installed
        let skill_installed = Self::skill_path()
            .map(|p| p.exists())
            .unwrap_or(false);

        // Check if binary exists
        let binary = match which::which("claude") {
            Ok(b) => b,
            Err(_) => {
                return ClaudeCodeStatus {
                    installed: false,
                    logged_in: false,
                    skill_installed,
                    version: None,
                    user_email: None,
                    error: Some("Claude Code CLI not installed".to_string()),
                };
            }
        };

        // Get version
        let version = match Command::new(&binary)
            .arg("--version")
            .output()
            .await
        {
            Ok(output) if output.status.success() => {
                Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
            }
            _ => None,
        };

        // Check auth by attempting a minimal prompt
        // If it succeeds, we're authenticated
        let auth_result = tokio::time::timeout(
            tokio::time::Duration::from_secs(30),
            Command::new(&binary)
                .args(["-p", "hi", "--output-format", "json"])
                .stdin(Stdio::null())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output()
        )
        .await;

        match auth_result {
            Ok(Ok(output)) => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);

                if output.status.success() {
                    ClaudeCodeStatus {
                        installed: true,
                        logged_in: true,
                        skill_installed,
                        version,
                        user_email: None,
                        error: None,
                    }
                } else {
                    // Check for auth-related errors
                    let combined = format!("{} {}", stdout, stderr);
                    let is_auth_error = combined.contains("login")
                        || combined.contains("authenticate")
                        || combined.contains("unauthorized")
                        || combined.contains("session")
                        || combined.contains("token");

                    ClaudeCodeStatus {
                        installed: true,
                        logged_in: false,
                        skill_installed,
                        version,
                        user_email: None,
                        error: if is_auth_error {
                            Some("Not logged in - run 'claude' to authenticate".to_string())
                        } else {
                            Some(stderr.trim().to_string())
                        },
                    }
                }
            }
            Ok(Err(e)) => ClaudeCodeStatus {
                installed: true,
                logged_in: false,
                skill_installed,
                version,
                user_email: None,
                error: Some(format!("Failed to check auth: {}", e)),
            },
            Err(_) => ClaudeCodeStatus {
                installed: true,
                logged_in: false,
                skill_installed,
                version,
                user_email: None,
                error: Some("Auth check timed out".to_string()),
            },
        }
    }

    /// Get the path to the skill file
    fn skill_path() -> Option<std::path::PathBuf> {
        dirs::home_dir().map(|h| h.join(".claude").join("commands").join("claude-code-bridge.md"))
    }

    /// Spawn the Claude Code login flow
    /// Opens a terminal for user to run 'claude' and authenticate interactively
    pub async fn login() -> std::result::Result<(), String> {
        let binary = which::which("claude")
            .map_err(|_| "Claude Code CLI not installed")?;

        // Try to open a terminal with claude for interactive login
        // This allows the user to complete the OAuth flow
        #[cfg(target_os = "linux")]
        {
            // Try common terminal emulators
            let terminals = [
                ("kitty", vec!["-e"]),
                ("gnome-terminal", vec!["--"]),
                ("konsole", vec!["-e"]),
                ("xterm", vec!["-e"]),
                ("alacritty", vec!["-e"]),
            ];

            for (term, args) in terminals {
                if which::which(term).is_ok() {
                    let mut cmd = Command::new(term);
                    for arg in &args {
                        cmd.arg(arg);
                    }
                    cmd.arg(&binary);

                    if cmd.spawn().is_ok() {
                        return Ok(());
                    }
                }
            }
            Err("Could not open terminal. Please run 'claude' manually to login.".to_string())
        }

        #[cfg(target_os = "macos")]
        {
            // Use open with Terminal.app
            Command::new("open")
                .args(["-a", "Terminal", binary.to_str().unwrap_or("claude")])
                .spawn()
                .map_err(|e| format!("Failed to open Terminal: {}", e))?;
            Ok(())
        }

        #[cfg(target_os = "windows")]
        {
            // Open cmd with claude
            Command::new("cmd")
                .args(["/c", "start", "cmd", "/k", binary.to_str().unwrap_or("claude")])
                .spawn()
                .map_err(|e| format!("Failed to open terminal: {}", e))?;
            Ok(())
        }

        #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
        Err("Unsupported platform for automatic login. Please run 'claude' manually.".to_string())
    }

    /// Logout from Claude Code
    /// Note: Claude Code doesn't have a direct logout command
    pub async fn logout() -> std::result::Result<(), String> {
        // Claude Code stores auth in ~/.claude/credentials.json
        // Removing or renaming it effectively logs out
        if let Some(home) = dirs::home_dir() {
            let creds_path = home.join(".claude").join("credentials.json");
            if creds_path.exists() {
                tokio::fs::remove_file(&creds_path)
                    .await
                    .map_err(|e| format!("Failed to remove credentials: {}", e))?;
                info!("Removed Claude Code credentials");
                return Ok(());
            }
        }
        Ok(()) // Already logged out
    }

    /// Install the claude-code-bridge skill to ~/.claude/commands/
    pub async fn install_skill() -> std::result::Result<(), String> {
        let skill_path = Self::skill_path()
            .ok_or("Could not determine home directory")?;

        // Create the commands directory if it doesn't exist
        if let Some(parent) = skill_path.parent() {
            tokio::fs::create_dir_all(parent)
                .await
                .map_err(|e| format!("Failed to create commands directory: {}", e))?;
        }

        // Write the skill file
        tokio::fs::write(&skill_path, CLAUDE_CODE_BRIDGE_SKILL)
            .await
            .map_err(|e| format!("Failed to write skill file: {}", e))?;

        info!("Installed claude-code-bridge skill to {:?}", skill_path);
        Ok(())
    }

    /// Install Claude Code CLI via npm
    /// Opens a terminal to run: npm install -g @anthropic-ai/claude-code
    pub async fn install_cli() -> std::result::Result<(), String> {
        // Check if npm is available
        let npm = which::which("npm")
            .or_else(|_| which::which("pnpm"))
            .or_else(|_| which::which("bun"))
            .map_err(|_| "No package manager found. Please install npm, pnpm, or bun.")?;

        let pkg_manager = npm.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("npm");

        let install_cmd = format!("{} install -g @anthropic-ai/claude-code", pkg_manager);

        #[cfg(target_os = "linux")]
        {
            let terminals = [
                ("kitty", vec!["-e", "bash", "-c"]),
                ("gnome-terminal", vec!["--", "bash", "-c"]),
                ("konsole", vec!["-e", "bash", "-c"]),
                ("xterm", vec!["-e", "bash", "-c"]),
                ("alacritty", vec!["-e", "bash", "-c"]),
            ];

            for (term, args) in terminals {
                if which::which(term).is_ok() {
                    let mut cmd = Command::new(term);
                    for arg in &args {
                        cmd.arg(arg);
                    }
                    // Run install then pause so user can see result
                    cmd.arg(format!("{}; echo ''; echo 'Press Enter to close...'; read", install_cmd));

                    if cmd.spawn().is_ok() {
                        return Ok(());
                    }
                }
            }
            Err(format!("Could not open terminal. Please run manually: {}", install_cmd))
        }

        #[cfg(target_os = "macos")]
        {
            Command::new("osascript")
                .args([
                    "-e",
                    &format!(r#"tell application "Terminal" to do script "{}""#, install_cmd),
                ])
                .spawn()
                .map_err(|e| format!("Failed to open Terminal: {}", e))?;
            Ok(())
        }

        #[cfg(target_os = "windows")]
        {
            Command::new("cmd")
                .args(["/c", "start", "cmd", "/k", &install_cmd])
                .spawn()
                .map_err(|e| format!("Failed to open terminal: {}", e))?;
            Ok(())
        }

        #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
        Err(format!("Unsupported platform. Please run manually: {}", install_cmd))
    }
}

/// The claude-code-bridge skill content
const CLAUDE_CODE_BRIDGE_SKILL: &str = r#"---
name: claude-code-bridge
description: Integrate with Claude Code CLI for delegating complex coding tasks. Use when you need to spawn a separate Claude Code instance to work on files, run tests, or perform multi-step coding operations in a specific directory. Enables "Claude calling Claude" patterns for parallel work or specialized contexts.
---

# Claude Code Bridge

Delegate coding tasks to Claude Code CLI from any context.

## When to Use

- **Parallel Work**: Spawn Claude Code to work on a subtask while you continue
- **Different Context**: Need Claude Code's file access in a specific directory
- **Specialized Tasks**: Let Claude Code handle complex refactoring, testing, or debugging
- **Isolation**: Keep risky operations in a separate session

## Usage Patterns

### Via MCP Server (Recommended)

If the `claude-code-mcp` server is configured, use the MCP tools:

```
Use claude_prompt to ask Claude Code: "Refactor the authentication module to use JWT"
```

Tools available:
- `claude_prompt` - Send a prompt to Claude Code
- `claude_continue` - Continue most recent conversation
- `claude_resume` - Resume a specific session by ID
- `claude_version` - Get version info

### Via CLI (Direct)

Execute Claude Code directly:

```bash
# Single prompt
claude -p "List all TODO comments in this project" --output-format json

# Continue conversation
claude -p "Now fix the first TODO" --continue

# Resume specific session
claude -p "What files did we modify?" --resume <session-id>
```

## Best Practices

1. **Specify Working Directory**: Always set `working_dir` to give Claude Code proper context
2. **Use Descriptive Prompts**: Be specific about what you want done
3. **Capture Session IDs**: Save session IDs from responses to resume conversations
4. **Set Timeouts**: Complex tasks may need longer timeouts (default: 5 min)
5. **Check Results**: Verify Claude Code's output before proceeding

## Error Handling

- **Not Found**: Ensure Claude Code is installed (`npm install -g @anthropic-ai/claude-code`)
- **Timeout**: Increase `timeout_secs` for complex tasks
- **Permission Denied**: Claude Code may need approval for file writes
"#;

/// Status of Claude Code CLI installation and authentication
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaudeCodeStatus {
    /// Whether the CLI binary is installed
    pub installed: bool,
    /// Whether the user is logged in
    pub logged_in: bool,
    /// Whether the claude-code-bridge skill is installed
    pub skill_installed: bool,
    /// CLI version if available
    pub version: Option<String>,
    /// User email if logged in
    pub user_email: Option<String>,
    /// Error message if any
    pub error: Option<String>,
}

impl Default for ClaudeCodeProvider {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl LLMProvider for ClaudeCodeProvider {
    fn id(&self) -> &str {
        "claude-code"
    }

    fn name(&self) -> &str {
        "Claude Code (CLI)"
    }

    fn model(&self) -> &str {
        self.model.as_deref().unwrap_or("claude-code")
    }

    async fn health_check(&self) -> bool {
        Self::version().await.is_ok()
    }

    fn pricing(&self) -> Option<ProviderPricing> {
        // Uses your Claude Code account pricing (subscription or API)
        None
    }

    async fn chat(&self, request: ChatRequest) -> Result<ChatResponse> {
        let message = self.build_message(&request);
        debug!(message_len = message.len(), "sending message to Claude Code");

        let start = Instant::now();

        let response = self.execute_prompt(&message).await?;

        let latency_ms = start.elapsed().as_millis() as u64;

        if let Some(error) = response.error {
            return Err(LLMError::ApiError {
                status: 0,
                message: error,
            });
        }

        info!(
            response_len = response.result.len(),
            latency_ms,
            session_id = ?response.session_id,
            "received response from Claude Code"
        );

        Ok(ChatResponse {
            content: response.result,
            model: self.model.clone().unwrap_or_else(|| "claude-code".to_string()),
            provider: "claude-code".to_string(),
            usage: response.usage.map(|u| crate::core::llm::cost::TokenUsage {
                input_tokens: u.input_tokens,
                output_tokens: u.output_tokens,
            }),
            finish_reason: Some("stop".to_string()),
            latency_ms,
            cost_usd: response.cost.map(|c| c.usd),
            tool_calls: None,
        })
    }

    async fn stream_chat(&self, _request: ChatRequest) -> Result<mpsc::Receiver<Result<ChatChunk>>> {
        // Claude Code CLI doesn't support streaming - returns full response
        warn!("streaming not supported for Claude Code provider");
        Err(LLMError::StreamingNotSupported("claude-code".to_string()))
    }

    fn supports_streaming(&self) -> bool {
        false
    }

    fn supports_embeddings(&self) -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_provider_id() {
        let provider = ClaudeCodeProvider::new();
        assert_eq!(provider.id(), "claude-code");
        assert_eq!(provider.name(), "Claude Code (CLI)");
    }

    #[test]
    fn test_no_pricing() {
        let provider = ClaudeCodeProvider::new();
        assert!(provider.pricing().is_none());
    }

    #[test]
    fn test_no_streaming() {
        let provider = ClaudeCodeProvider::new();
        assert!(!provider.supports_streaming());
        assert!(!provider.supports_embeddings());
    }

    #[test]
    fn test_custom_config() {
        let provider = ClaudeCodeProvider::with_config(60, Some("claude-sonnet-4-20250514".to_string()), None);
        assert_eq!(provider.timeout_secs, 60);
        assert_eq!(provider.model, Some("claude-sonnet-4-20250514".to_string()));
    }

    #[test]
    fn test_default() {
        let provider = ClaudeCodeProvider::default();
        assert_eq!(provider.timeout_secs, 300);
        assert!(provider.model.is_none());
    }
}
