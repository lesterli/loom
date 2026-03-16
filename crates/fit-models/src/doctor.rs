use serde::Serialize;
use std::process::Command;

#[derive(Debug, Serialize)]
pub struct DoctorReport {
    pub checks: Vec<Check>,
}

#[derive(Debug, Serialize)]
pub struct Check {
    pub name: String,
    pub status: CheckStatus,
    pub detail: String,
}

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
#[allow(dead_code)] // Fail used when critical backend check fails
pub enum CheckStatus {
    Pass,
    Warn,
    Fail,
}

pub fn run() -> DoctorReport {
    let checks = vec![
        check_backend("llama.cpp", &["llama-cli", "llama-server"], &["--version"]),
        check_backend("ollama", &["ollama"], &["--version"]),
        check_mlx(),
    ];
    DoctorReport { checks }
}

fn check_backend(name: &str, executables: &[&str], version_args: &[&str]) -> Check {
    for exe in executables {
        if let Ok(output) = Command::new(exe).args(version_args).output() {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout)
                    .lines()
                    .next()
                    .unwrap_or("")
                    .trim()
                    .to_string();
                return Check {
                    name: name.to_string(),
                    status: CheckStatus::Pass,
                    detail: format!("{exe}: {version}"),
                };
            }
            // Some tools print version to stderr
            let stderr_version = String::from_utf8_lossy(&output.stderr)
                .lines()
                .next()
                .unwrap_or("")
                .trim()
                .to_string();
            if !stderr_version.is_empty() {
                return Check {
                    name: name.to_string(),
                    status: CheckStatus::Pass,
                    detail: format!("{exe}: {stderr_version}"),
                };
            }
        }
    }

    Check {
        name: name.to_string(),
        status: CheckStatus::Warn,
        detail: "not found".to_string(),
    }
}

fn check_mlx() -> Check {
    // MLX is a Python package; check if the mlx module is importable
    if let Ok(output) = Command::new("python3")
        .args(["-c", "import mlx; print(mlx.__version__)"])
        .output()
    {
        if output.status.success() {
            let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
            return Check {
                name: "mlx".to_string(),
                status: CheckStatus::Pass,
                detail: format!("python3 mlx: {version}"),
            };
        }
    }

    Check {
        name: "mlx".to_string(),
        status: CheckStatus::Warn,
        detail: "not found (python3 -c 'import mlx' failed)".to_string(),
    }
}

pub fn print_report(report: &DoctorReport) {
    for check in &report.checks {
        let icon = match check.status {
            CheckStatus::Pass => "\x1b[32mPASS\x1b[0m",
            CheckStatus::Warn => "\x1b[33mWARN\x1b[0m",
            CheckStatus::Fail => "\x1b[31mFAIL\x1b[0m",
        };
        println!("[{icon}] {:<12} {}", check.name, check.detail);
    }
}
