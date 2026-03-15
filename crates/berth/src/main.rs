mod catalog;
mod estimator;
mod hardware;
mod types;

use clap::{Parser, Subcommand};
use types::{DeviceProfile, FitResult, FitTier};

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
        Command::EstimateModels {
            backend: _,
            context,
            batch,
            artifact: _,
            json,
        } => {
            let device = match hardware::detect() {
                Ok(d) => d,
                Err(e) => {
                    eprintln!("error: {e}");
                    std::process::exit(1);
                }
            };
            let catalog = catalog::load();
            let results = estimator::estimate_catalog(&device, &catalog, context, batch);

            if json {
                println!("{}", serde_json::to_string_pretty(&results).unwrap());
            } else {
                print_hardware(&device);
                println!();
                print_estimate_table(&results);
            }
        }
        Command::InspectArtifact { .. } => {
            eprintln!("berth inspect-artifact: not yet implemented");
        }
        Command::Doctor { json: _ } => {
            eprintln!("berth doctor: not yet implemented");
        }
    }
}

fn print_hardware(p: &DeviceProfile) {
    println!("Chip:       {} ({})", p.chip_name, p.chip_family);
    println!("OS:         macOS {}", p.os_version);
    println!(
        "Memory:     {} GB total, {:.1} GB available",
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

fn print_estimate_table(results: &[FitResult]) {
    println!(
        "{:<25} {:<8} {:<6} {:>10} {:>10} {:>10}  {}",
        "Model", "Quant", "Fit", "Weights", "KV Cache", "Total", "Risks"
    );
    println!("{}", "-".repeat(90));

    for r in results {
        let fit_label = match r.fit_tier {
            FitTier::Recommended => "\x1b[32m  OK+ \x1b[0m",
            FitTier::Works => "\x1b[32m  OK  \x1b[0m",
            FitTier::Tight => "\x1b[33m TIGHT\x1b[0m",
            FitTier::NoFit => "\x1b[31m NO   \x1b[0m",
            FitTier::Unsupported => "\x1b[31m  --  \x1b[0m",
        };

        println!(
            "{:<25} {:<8} {} {:>9.1}G {:>9.1}G {:>9.1}G  {}",
            r.model_name,
            r.quantization,
            fit_label,
            r.weights_bytes as f64 / GB,
            r.kv_cache_bytes as f64 / GB,
            r.total_bytes as f64 / GB,
            r.risk_labels.join(", "),
        );
    }
}

const GB: f64 = 1024.0 * 1024.0 * 1024.0;
