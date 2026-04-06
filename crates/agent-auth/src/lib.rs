pub mod claude;
pub mod codex;

use serde::{Deserialize, Serialize};
use std::process::Output;
use thiserror::Error;
use tokio::process::Command;

#[derive(Debug, Error)]
pub enum AuthError {
    #[error("{0} CLI not found in PATH")]
    CliNotFound(&'static str),
    #[error("failed to execute CLI: {0}")]
    ExecFailed(#[from] std::io::Error),
    #[error("failed to parse CLI output: {0}")]
    ParseFailed(#[from] serde_json::Error),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Agent {
    Claude,
    Codex,
}

impl std::fmt::Display for Agent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Claude => write!(f, "Claude Code"),
            Self::Codex => write!(f, "Codex CLI"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AuthInfo {
    pub email: Option<String>,
    pub org_name: Option<String>,
    pub subscription_type: Option<String>,
    pub auth_method: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "status")]
pub enum AuthState {
    Ready(AuthInfo),
    NeedsLogin,
    NotInstalled,
}

impl std::fmt::Display for AuthState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Ready(info) => {
                if let Some(email) = &info.email {
                    write!(f, "Ready — {} ({})", email, info.auth_method)
                } else {
                    write!(f, "Ready — {}", info.auth_method)
                }
            }
            Self::NeedsLogin => write!(f, "NeedsLogin"),
            Self::NotInstalled => write!(f, "NotInstalled"),
        }
    }
}

pub async fn check_auth(agent: Agent) -> Result<AuthState, AuthError> {
    match agent {
        Agent::Claude => claude::check().await,
        Agent::Codex => codex::check().await,
    }
}

pub async fn detect_all() -> [(Agent, Result<AuthState, AuthError>); 2] {
    let (claude_result, codex_result) = tokio::join!(claude::check(), codex::check());
    [
        (Agent::Claude, claude_result),
        (Agent::Codex, codex_result),
    ]
}

/// Spawn a CLI command, mapping NotFound to CliNotFound.
pub(crate) async fn run_command(
    program: &'static str,
    args: &[&str],
) -> Result<Output, AuthError> {
    Command::new(program)
        .args(args)
        .output()
        .await
        .map_err(|e| {
            if e.kind() == std::io::ErrorKind::NotFound {
                AuthError::CliNotFound(program)
            } else {
                AuthError::ExecFailed(e)
            }
        })
}
