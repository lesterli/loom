mod hardware;
mod types;

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
        Command::DetectHardware { json } => {
            match hardware::detect() {
                Ok(profile) => {
                    if json {
                        println!("{}", serde_json::to_string_pretty(&profile).unwrap());
                    } else {
                        print_hardware(&profile);
                    }
                }
                Err(e) => {
                    eprintln!("error: {e}");
                    std::process::exit(1);
                }
            }
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

fn print_hardware(p: &types::DeviceProfile) {
    println!("Chip:       {} ({})", p.chip_name, p.chip_family);
    println!("OS:         macOS {}", p.os_version);
    println!("Memory:     {} GB total, {:.1} GB available",
        p.memory_total_bytes / (1024 * 1024 * 1024),
        p.memory_available_bytes as f64 / (1024.0 * 1024.0 * 1024.0),
    );
    if let Some(bw) = p.memory_bandwidth_gbps {
        println!("Bandwidth:  {} GB/s", bw);
    }
    if let (Some(p_cores), Some(e_cores)) = (p.cpu_performance_cores, p.cpu_efficiency_cores) {
        println!("CPU:        {}P + {}E cores", p_cores, e_cores);
    }
    if let Some(gpu) = p.gpu_cores {
        println!("GPU:        {} cores", gpu);
    }
    if let Some(ane) = p.ane_tops {
        println!("ANE:        {} TOPS", ane);
    }
}
