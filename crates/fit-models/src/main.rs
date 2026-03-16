mod artifact;
mod catalog;
mod doctor;
mod estimator;
mod hardware;
mod types;

use clap::Parser;
use types::{DeviceProfile, FitResult, FitTier};

/// What models can this machine run?
#[derive(Parser)]
#[command(name = "fit-models")]
struct Cli {
    /// Inspect a local artifact (GGUF, safetensors, MLX directory)
    #[arg(long)]
    inspect: Option<String>,
    /// Output as JSON
    #[arg(long)]
    json: bool,
}

fn main() {
    let cli = Cli::parse();

    if let Some(path) = cli.inspect {
        match artifact::inspect(&path) {
            Ok(profile) => {
                if cli.json {
                    println!("{}", serde_json::to_string_pretty(&profile).unwrap());
                } else {
                    artifact::print_profile(&profile);
                }
            }
            Err(e) => {
                eprintln!("error: {e}");
                std::process::exit(1);
            }
        }
        return;
    }

    let device = match hardware::detect() {
        Ok(d) => d,
        Err(e) => {
            eprintln!("error: {e}");
            std::process::exit(1);
        }
    };

    let backends = doctor::run();
    let catalog = catalog::load();
    let results = estimator::estimate_catalog(&device, &catalog, 4096, 1);

    if cli.json {
        let output = serde_json::json!({
            "device": device,
            "backends": backends,
            "models": results,
        });
        println!("{}", serde_json::to_string_pretty(&output).unwrap());
    } else {
        print_hardware(&device);
        println!();
        doctor::print_report(&backends);
        println!();
        print_estimate_table(&results);
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
