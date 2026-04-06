use crate::{run_command, AuthError, AuthInfo, AuthState};
use std::process::Output;

pub async fn check() -> Result<AuthState, AuthError> {
    let output = run_command("codex", &["login", "status"]).await?;
    parse_output(&output)
}

fn parse_output(output: &Output) -> Result<AuthState, AuthError> {
    if !output.status.success() {
        return Ok(AuthState::NotInstalled);
    }

    // Codex writes status to stderr in non-TTY environments.
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let stdout_trimmed = stdout.trim();
    let line = if stdout_trimmed.is_empty() {
        stderr.trim()
    } else {
        stdout_trimmed
    };

    if let Some(method) = line.strip_prefix("Logged in using ") {
        Ok(AuthState::Ready(AuthInfo {
            email: None,
            org_name: None,
            subscription_type: None,
            auth_method: method.to_string(),
        }))
    } else if line.contains("Not logged in") || line.is_empty() {
        Ok(AuthState::NeedsLogin)
    } else {
        Ok(AuthState::NotInstalled)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::process::ExitStatusExt;
    use std::process::ExitStatus;

    #[test]
    fn parse_logged_in_chatgpt_stdout() {
        let output = Output {
            status: ExitStatus::from_raw(0),
            stdout: b"Logged in using ChatGPT\n".to_vec(),
            stderr: vec![],
        };
        assert_eq!(
            parse_output(&output).unwrap(),
            AuthState::Ready(AuthInfo {
                email: None,
                org_name: None,
                subscription_type: None,
                auth_method: "ChatGPT".into(),
            })
        );
    }

    #[test]
    fn parse_logged_in_chatgpt_stderr() {
        let output = Output {
            status: ExitStatus::from_raw(0),
            stdout: vec![],
            stderr: b"Logged in using ChatGPT\n".to_vec(),
        };
        assert_eq!(
            parse_output(&output).unwrap(),
            AuthState::Ready(AuthInfo {
                email: None,
                org_name: None,
                subscription_type: None,
                auth_method: "ChatGPT".into(),
            })
        );
    }

    #[test]
    fn parse_logged_in_api_key() {
        let output = Output {
            status: ExitStatus::from_raw(0),
            stdout: b"Logged in using API key\n".to_vec(),
            stderr: vec![],
        };
        assert_eq!(
            parse_output(&output).unwrap(),
            AuthState::Ready(AuthInfo {
                email: None,
                org_name: None,
                subscription_type: None,
                auth_method: "API key".into(),
            })
        );
    }

    #[test]
    fn parse_not_logged_in() {
        let output = Output {
            status: ExitStatus::from_raw(0),
            stdout: b"Not logged in\n".to_vec(),
            stderr: vec![],
        };
        assert_eq!(parse_output(&output).unwrap(), AuthState::NeedsLogin);
    }

    #[test]
    fn parse_cli_failure() {
        let output = Output {
            status: ExitStatus::from_raw(1 << 8),
            stdout: vec![],
            stderr: b"error".to_vec(),
        };
        assert_eq!(parse_output(&output).unwrap(), AuthState::NotInstalled);
    }
}
