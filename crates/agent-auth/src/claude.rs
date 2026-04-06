use crate::{run_command, AuthError, AuthInfo, AuthState};
use serde::Deserialize;
use std::process::Output;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CliAuthStatus {
    logged_in: bool,
    auth_method: Option<String>,
    email: Option<String>,
    org_name: Option<String>,
    subscription_type: Option<String>,
}

pub async fn check() -> Result<AuthState, AuthError> {
    let output = run_command("claude", &["auth", "status", "--json"]).await?;
    parse_output(&output)
}

fn parse_output(output: &Output) -> Result<AuthState, AuthError> {
    if !output.status.success() {
        return Ok(AuthState::NotInstalled);
    }

    let status: CliAuthStatus = serde_json::from_slice(&output.stdout)?;

    if status.logged_in {
        Ok(AuthState::Ready(AuthInfo {
            email: status.email,
            org_name: status.org_name,
            subscription_type: status.subscription_type,
            auth_method: status.auth_method.unwrap_or_default(),
        }))
    } else {
        Ok(AuthState::NeedsLogin)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::process::ExitStatusExt;
    use std::process::ExitStatus;

    #[test]
    fn parse_ready() {
        let json = br#"{
            "loggedIn": true,
            "authMethod": "claude.ai",
            "apiProvider": "firstParty",
            "email": "user@example.com",
            "orgId": "abc-123",
            "orgName": "My Org",
            "subscriptionType": "max"
        }"#;

        let output = Output {
            status: ExitStatus::from_raw(0),
            stdout: json.to_vec(),
            stderr: vec![],
        };

        assert_eq!(
            parse_output(&output).unwrap(),
            AuthState::Ready(AuthInfo {
                email: Some("user@example.com".into()),
                org_name: Some("My Org".into()),
                subscription_type: Some("max".into()),
                auth_method: "claude.ai".into(),
            })
        );
    }

    #[test]
    fn parse_not_logged_in() {
        let json = br#"{"loggedIn": false}"#;
        let output = Output {
            status: ExitStatus::from_raw(0),
            stdout: json.to_vec(),
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
