use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct DeviceProfile {
    pub chip_name: String,
    pub chip_family: String,
    pub os_version: String,
    pub memory_total_bytes: u64,
    pub memory_available_bytes: u64,
    pub memory_bandwidth_gbps: Option<f64>,
    pub cpu_performance_cores: Option<u32>,
    pub cpu_efficiency_cores: Option<u32>,
    pub gpu_cores: Option<u32>,
    pub ane_tops: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct ChipSpecTable {
    pub chips: Vec<ChipSpec>,
}

#[derive(Debug, Deserialize)]
pub struct ChipSpec {
    pub chip_identifier: String,
    pub memory_bandwidth_gbps: f64,
    pub gpu_cores: u32,
    pub ane_tops: f64,
    pub cpu_performance_cores: u32,
    pub cpu_efficiency_cores: u32,
    pub available_memory_gb: Vec<u32>,
}
