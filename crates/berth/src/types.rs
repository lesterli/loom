use serde::{Deserialize, Serialize};

// -- Device --

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
#[allow(dead_code)] // All fields required by TOML deserialization
pub struct ChipSpec {
    pub chip_identifier: String,
    pub memory_bandwidth_gbps: f64,
    pub gpu_cores: u32,
    pub ane_tops: f64,
    pub cpu_performance_cores: u32,
    pub cpu_efficiency_cores: u32,
    pub available_memory_gb: Vec<u32>,
}

// -- Catalog --

#[derive(Debug, Deserialize)]
pub struct ModelCatalog {
    pub models: Vec<CatalogModel>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)] // All fields required by TOML deserialization
pub struct CatalogModel {
    pub model_name: String,
    pub dense_or_moe: String,
    pub num_hidden_layers: u32,
    pub num_key_value_heads: u32,
    pub head_dim: u32,
    pub total_params_billion: f64,
    pub active_params_billion: f64,
    pub artifacts: Vec<CatalogArtifact>,
    #[serde(default)]
    pub num_experts: Option<u32>,
    #[serde(default)]
    pub num_experts_per_tok: Option<u32>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)] // All fields required by TOML deserialization
pub struct CatalogArtifact {
    pub quantization: String,
    pub artifact_kind: String,
    #[serde(default)]
    pub estimated_file_size_bytes: Option<u64>,
    pub hf_repo: String,
}

// -- Estimation result --

#[derive(Debug, Serialize)]
pub struct FitResult {
    pub model_name: String,
    pub quantization: String,
    pub artifact_kind: String,
    pub fit_tier: FitTier,
    pub weights_bytes: u64,
    pub kv_cache_bytes: u64,
    pub overhead_bytes: u64,
    pub total_bytes: u64,
    pub available_bytes: u64,
    pub risk_labels: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
#[allow(dead_code)] // Unsupported used when backend doesn't support artifact
pub enum FitTier {
    Recommended,
    Works,
    Tight,
    NoFit,
    Unsupported,
}
