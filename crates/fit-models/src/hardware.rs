use std::process::Command;

use crate::types::{ChipSpec, ChipSpecTable, DeviceProfile};

const CHIPS_TOML: &str = include_str!("../../../data/chips.toml");

pub fn detect() -> Result<DeviceProfile, String> {
    let chip_name = detect_chip_name()?;
    let chip_family = parse_chip_family(&chip_name);
    let os_version = detect_os_version()?;
    let memory_total_bytes = detect_total_memory()?;
    let memory_available_bytes = detect_available_memory()?;
    let (cpu_p, cpu_e) = detect_cpu_cores();

    let chip_spec = lookup_chip_spec(&chip_name);

    Ok(DeviceProfile {
        chip_name,
        chip_family,
        os_version,
        memory_total_bytes,
        memory_available_bytes,
        memory_bandwidth_gbps: chip_spec.as_ref().map(|s| s.memory_bandwidth_gbps),
        cpu_performance_cores: cpu_p.or(chip_spec.as_ref().map(|s| s.cpu_performance_cores)),
        cpu_efficiency_cores: cpu_e.or(chip_spec.as_ref().map(|s| s.cpu_efficiency_cores)),
        gpu_cores: chip_spec.as_ref().map(|s| s.gpu_cores),
        ane_tops: chip_spec.as_ref().map(|s| s.ane_tops),
    })
}

fn detect_chip_name() -> Result<String, String> {
    sysctl_string("machdep.cpu.brand_string")
}

fn detect_os_version() -> Result<String, String> {
    run_command("sw_vers", &["-productVersion"])
}

fn detect_total_memory() -> Result<u64, String> {
    sysctl_string("hw.memsize")?
        .parse::<u64>()
        .map_err(|e| format!("failed to parse hw.memsize: {e}"))
}

fn detect_available_memory() -> Result<u64, String> {
    let page_size = sysctl_string("hw.pagesize")?
        .parse::<u64>()
        .map_err(|e| format!("failed to parse hw.pagesize: {e}"))?;

    let vm_stat_output = run_command("vm_stat", &[])?;
    let mut free_pages: u64 = 0;
    let mut inactive_pages: u64 = 0;
    let mut purgeable_pages: u64 = 0;

    for line in vm_stat_output.lines() {
        if let Some(count) = parse_vm_stat_line(line, "Pages free") {
            free_pages = count;
        } else if let Some(count) = parse_vm_stat_line(line, "Pages inactive") {
            inactive_pages = count;
        } else if let Some(count) = parse_vm_stat_line(line, "Pages purgeable") {
            purgeable_pages = count;
        }
    }

    Ok((free_pages + inactive_pages + purgeable_pages) * page_size)
}

fn parse_vm_stat_line(line: &str, prefix: &str) -> Option<u64> {
    if !line.starts_with(prefix) {
        return None;
    }
    line.split(':')
        .nth(1)?
        .trim()
        .trim_end_matches('.')
        .parse::<u64>()
        .ok()
}

fn detect_cpu_cores() -> (Option<u32>, Option<u32>) {
    let p_cores = sysctl_string("hw.perflevel0.physicalcpu")
        .ok()
        .and_then(|s| s.parse::<u32>().ok());
    let e_cores = sysctl_string("hw.perflevel1.physicalcpu")
        .ok()
        .and_then(|s| s.parse::<u32>().ok());
    (p_cores, e_cores)
}

fn parse_chip_family(chip_name: &str) -> String {
    // "Apple M1 Pro" -> "M1"
    // "Apple M4 Max" -> "M4"
    let name = chip_name.trim_start_matches("Apple ");
    for token in name.split_whitespace() {
        if token.starts_with('M') && token.len() >= 2 && token[1..].chars().next().is_some_and(|c| c.is_ascii_digit()) {
            return token.to_string();
        }
    }
    "Unknown".to_string()
}

fn lookup_chip_spec(chip_name: &str) -> Option<&'static ChipSpec> {
    use std::sync::LazyLock;
    static TABLE: LazyLock<ChipSpecTable> = LazyLock::new(|| {
        toml::from_str(CHIPS_TOML).expect("failed to parse embedded chips.toml")
    });
    // Exact match first, then containment. Sort candidates by identifier length
    // descending so "Apple M1 Pro" matches before "Apple M1".
    TABLE
        .chips
        .iter()
        .filter(|spec| chip_name.contains(&spec.chip_identifier) || spec.chip_identifier.contains(chip_name))
        .max_by_key(|spec| spec.chip_identifier.len())
}

fn sysctl_string(key: &str) -> Result<String, String> {
    run_command("sysctl", &["-n", key])
}

fn run_command(cmd: &str, args: &[&str]) -> Result<String, String> {
    let output = Command::new(cmd)
        .args(args)
        .output()
        .map_err(|e| format!("failed to run {cmd}: {e}"))?;

    if !output.status.success() {
        return Err(format!(
            "{cmd} failed: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}
