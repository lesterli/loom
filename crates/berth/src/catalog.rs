use crate::types::ModelCatalog;

const CATALOG_TOML: &str = include_str!("../../../data/catalog/qwen3.5.toml");

pub fn load() -> ModelCatalog {
    toml::from_str(CATALOG_TOML).expect("failed to parse embedded qwen3.5.toml")
}
