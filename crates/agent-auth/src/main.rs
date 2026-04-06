use agent_auth::{detect_all, Agent, AuthState};

#[tokio::main(flavor = "current_thread")]
async fn main() {
    let agent = std::env::args().nth(1);

    match agent.as_deref() {
        Some("claude") => print_result(Agent::Claude, agent_auth::check_auth(Agent::Claude).await),
        Some("codex") => print_result(Agent::Codex, agent_auth::check_auth(Agent::Codex).await),
        None | Some("all") => {
            for (agent, result) in detect_all().await {
                print_result(agent, result);
                println!();
            }
        }
        Some(other) => {
            eprintln!("Unknown agent: {other}");
            eprintln!("Usage: agent-auth [claude|codex|all]");
            std::process::exit(1);
        }
    }
}

fn print_result(agent: Agent, result: Result<AuthState, agent_auth::AuthError>) {
    print!("[{agent}] ");
    match result {
        Ok(AuthState::Ready(info)) => {
            println!("Authenticated");
            if let Some(email) = &info.email {
                println!("  Email:        {email}");
            }
            if let Some(org) = &info.org_name {
                println!("  Organization: {org}");
            }
            if let Some(sub) = &info.subscription_type {
                println!("  Subscription: {sub}");
            }
            println!("  Auth method:  {}", info.auth_method);
        }
        Ok(AuthState::NeedsLogin) => println!("Not logged in"),
        Ok(AuthState::NotInstalled) => println!("Not installed"),
        Err(e) => println!("Error: {e}"),
    }
}
