use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "berth", about = "What Qwen3.5 models can this machine run?")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Detect hardware capabilities of this machine
    DetectHardware {
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Estimate which Qwen3.5 models fit on this machine
    EstimateModels {
        /// Limit to a specific backend (mlx, llama.cpp, ollama)
        #[arg(long)]
        backend: Option<String>,
        /// Override context length (default: 4096)
        #[arg(long, default_value_t = 4096)]
        context: u32,
        /// Override batch size (default: 1)
        #[arg(long, default_value_t = 1)]
        batch: u32,
        /// Estimate a specific local artifact instead of the catalog
        #[arg(long)]
        artifact: Option<String>,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Inspect a local model artifact
    InspectArtifact {
        /// Path to a local artifact (GGUF, safetensors, MLX directory)
        #[arg(long)]
        path: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Check CLI and backend readiness
    Doctor {
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Command::DetectHardware { json: _ } => {
            eprintln!("berth detect-hardware: not yet implemented");
        }
        Command::EstimateModels { .. } => {
            eprintln!("berth estimate-models: not yet implemented");
        }
        Command::InspectArtifact { .. } => {
            eprintln!("berth inspect-artifact: not yet implemented");
        }
        Command::Doctor { json: _ } => {
            eprintln!("berth doctor: not yet implemented");
        }
    }
}
