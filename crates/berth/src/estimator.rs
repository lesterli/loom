use crate::types::{CatalogArtifact, CatalogModel, DeviceProfile, FitResult, FitTier, ModelCatalog};

const BACKEND_OVERHEAD_BYTES: u64 = 512 * 1024 * 1024; // 512 MB
const OS_RESERVED_BYTES: u64 = 3 * 1024 * 1024 * 1024; // ~3 GB for OS and basic apps
const KV_CACHE_BYTES_PER_ELEMENT: u64 = 2; // fp16

pub fn estimate_catalog(
    device: &DeviceProfile,
    catalog: &ModelCatalog,
    context: u32,
    batch: u32,
) -> Vec<FitResult> {
    // For catalog mode, estimate against total memory minus OS overhead,
    // not current available memory (which fluctuates with running apps).
    let usable_bytes = device.memory_total_bytes.saturating_sub(OS_RESERVED_BYTES);

    let mut results: Vec<FitResult> = catalog
        .models
        .iter()
        .flat_map(|model| {
            model
                .artifacts
                .iter()
                .filter(|a| a.estimated_file_size_bytes.is_some())
                .map(move |artifact| estimate_one(model, artifact, usable_bytes, context, batch))
        })
        .collect();

    // Sort: best fit first, then largest model first within same tier
    results.sort_by(|a, b| {
        a.fit_tier
            .cmp(&b.fit_tier)
            .then(b.weights_bytes.cmp(&a.weights_bytes))
    });

    results
}

fn estimate_one(
    model: &CatalogModel,
    artifact: &CatalogArtifact,
    usable_bytes: u64,
    context: u32,
    batch: u32,
) -> FitResult {
    let weights_bytes = artifact.estimated_file_size_bytes.unwrap_or(0);

    // KV cache: layers * seq_len * batch * num_kv_heads * head_dim * 2 * bytes_per_element
    let kv_cache_bytes = model.num_hidden_layers as u64
        * context as u64
        * batch as u64
        * model.num_key_value_heads as u64
        * model.head_dim as u64
        * 2
        * KV_CACHE_BYTES_PER_ELEMENT;

    let overhead_bytes = BACKEND_OVERHEAD_BYTES;
    let total_bytes = weights_bytes + kv_cache_bytes + overhead_bytes;

    let mut risk_labels = Vec::new();

    if kv_cache_bytes > weights_bytes / 2 {
        risk_labels.push("context_limited".to_string());
    }

    let fit_tier = if total_bytes <= usable_bytes / 2 {
        FitTier::Recommended
    } else if total_bytes <= (usable_bytes as f64 * 0.75) as u64 {
        FitTier::Works
    } else if total_bytes <= usable_bytes {
        risk_labels.push("memory_bound".to_string());
        FitTier::Tight
    } else {
        risk_labels.push("swap_risk".to_string());
        FitTier::NoFit
    };

    FitResult {
        model_name: model.model_name.clone(),
        quantization: artifact.quantization.clone(),
        artifact_kind: artifact.artifact_kind.clone(),
        fit_tier,
        weights_bytes,
        kv_cache_bytes,
        overhead_bytes,
        total_bytes,
        available_bytes: usable_bytes,
        risk_labels,
    }
}
