use serde::Serialize;
use std::collections::BTreeMap;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

#[derive(Debug, Serialize)]
pub struct ArtifactProfile {
    pub artifact_kind: String,
    pub path: String,
    pub file_size_bytes: u64,
    pub metadata: BTreeMap<String, String>,
}

// GGUF magic: 0x46475547 ("GGUF" in little-endian)
const GGUF_MAGIC: u32 = 0x46475547;

pub fn inspect(path: &str) -> Result<ArtifactProfile, String> {
    let p = Path::new(path);
    if !p.exists() {
        return Err(format!("file not found: {path}"));
    }

    let file_size_bytes = p
        .metadata()
        .map_err(|e| format!("cannot stat {path}: {e}"))?
        .len();

    if path.ends_with(".gguf") {
        inspect_gguf(path, file_size_bytes)
    } else if p.is_dir() {
        // Could be MLX directory
        Ok(ArtifactProfile {
            artifact_kind: "MLX".to_string(),
            path: path.to_string(),
            file_size_bytes,
            metadata: BTreeMap::new(),
        })
    } else {
        Err(format!("unsupported artifact: {path} (expected .gguf or MLX directory)"))
    }
}

fn inspect_gguf(path: &str, file_size_bytes: u64) -> Result<ArtifactProfile, String> {
    let mut f = File::open(path).map_err(|e| format!("cannot open {path}: {e}"))?;
    let mut metadata = BTreeMap::new();

    // Read header
    let magic = read_u32_le(&mut f)?;
    if magic != GGUF_MAGIC {
        return Err(format!("not a valid GGUF file (bad magic: 0x{magic:08x})"));
    }

    let version = read_u32_le(&mut f)?;
    metadata.insert("gguf_version".to_string(), version.to_string());

    if version < 2 || version > 3 {
        return Err(format!("unsupported GGUF version: {version}"));
    }

    let _tensor_count = read_u64_le(&mut f)?;
    let kv_count = read_u64_le(&mut f)?;

    // Read key-value metadata pairs
    let keys_of_interest = [
        "general.architecture",
        "general.name",
        "general.quantization_version",
        "general.file_type",
        // Architecture-specific keys (using wildcard matching later)
    ];

    for _ in 0..kv_count.min(512) {
        // safety cap
        let key = match read_gguf_string(&mut f) {
            Ok(k) => k,
            Err(_) => break,
        };
        let value_type = match read_u32_le(&mut f) {
            Ok(v) => v,
            Err(_) => break,
        };

        let value_str = match read_gguf_value(&mut f, value_type) {
            Ok(v) => v,
            Err(_) => break,
        };

        // Keep keys of interest or architecture-specific keys
        let dominated = keys_of_interest.iter().any(|k| key == *k);
        let arch_key = key.contains(".block_count")
            || key.contains(".head_count")
            || key.contains(".embedding_length")
            || key.contains(".context_length")
            || key.contains(".head_count_kv")
            || key.contains(".key_length")
            || key.contains(".value_length");

        if dominated || arch_key {
            metadata.insert(key, value_str);
        }
    }

    Ok(ArtifactProfile {
        artifact_kind: "GGUF".to_string(),
        path: path.to_string(),
        file_size_bytes,
        metadata,
    })
}

// GGUF value types
const GGUF_TYPE_UINT8: u32 = 0;
const GGUF_TYPE_INT8: u32 = 1;
const GGUF_TYPE_UINT16: u32 = 2;
const GGUF_TYPE_INT16: u32 = 3;
const GGUF_TYPE_UINT32: u32 = 4;
const GGUF_TYPE_INT32: u32 = 5;
const GGUF_TYPE_FLOAT32: u32 = 6;
const GGUF_TYPE_BOOL: u32 = 7;
const GGUF_TYPE_STRING: u32 = 8;
const GGUF_TYPE_ARRAY: u32 = 9;
const GGUF_TYPE_UINT64: u32 = 10;
const GGUF_TYPE_INT64: u32 = 11;
const GGUF_TYPE_FLOAT64: u32 = 12;

fn read_gguf_value(f: &mut File, value_type: u32) -> Result<String, String> {
    match value_type {
        GGUF_TYPE_UINT8 => Ok(read_u8(f)?.to_string()),
        GGUF_TYPE_INT8 => Ok((read_u8(f)? as i8).to_string()),
        GGUF_TYPE_UINT16 => {
            let mut buf = [0u8; 2];
            f.read_exact(&mut buf).map_err(|e| e.to_string())?;
            Ok(u16::from_le_bytes(buf).to_string())
        }
        GGUF_TYPE_INT16 => {
            let mut buf = [0u8; 2];
            f.read_exact(&mut buf).map_err(|e| e.to_string())?;
            Ok(i16::from_le_bytes(buf).to_string())
        }
        GGUF_TYPE_UINT32 => Ok(read_u32_le(f)?.to_string()),
        GGUF_TYPE_INT32 => {
            let mut buf = [0u8; 4];
            f.read_exact(&mut buf).map_err(|e| e.to_string())?;
            Ok(i32::from_le_bytes(buf).to_string())
        }
        GGUF_TYPE_FLOAT32 => {
            let mut buf = [0u8; 4];
            f.read_exact(&mut buf).map_err(|e| e.to_string())?;
            Ok(f32::from_le_bytes(buf).to_string())
        }
        GGUF_TYPE_BOOL => Ok(if read_u8(f)? != 0 { "true" } else { "false" }.to_string()),
        GGUF_TYPE_STRING => read_gguf_string(f),
        GGUF_TYPE_ARRAY => {
            let elem_type = read_u32_le(f)?;
            let count = read_u64_le(f)?;
            // Skip array contents (we don't need them)
            for _ in 0..count.min(1024) {
                read_gguf_value(f, elem_type)?;
            }
            Ok(format!("[array of {count}]"))
        }
        GGUF_TYPE_UINT64 => Ok(read_u64_le(f)?.to_string()),
        GGUF_TYPE_INT64 => {
            let mut buf = [0u8; 8];
            f.read_exact(&mut buf).map_err(|e| e.to_string())?;
            Ok(i64::from_le_bytes(buf).to_string())
        }
        GGUF_TYPE_FLOAT64 => {
            let mut buf = [0u8; 8];
            f.read_exact(&mut buf).map_err(|e| e.to_string())?;
            Ok(f64::from_le_bytes(buf).to_string())
        }
        _ => {
            // Unknown type, can't continue parsing
            Err(format!("unknown GGUF value type: {value_type}"))
        }
    }
}

fn read_gguf_string(f: &mut File) -> Result<String, String> {
    let len = read_u64_le(f)? as usize;
    if len > 1024 * 1024 {
        // Skip unreasonably large strings
        f.seek(SeekFrom::Current(len as i64))
            .map_err(|e| e.to_string())?;
        return Ok(format!("[string of {len} bytes]"));
    }
    let mut buf = vec![0u8; len];
    f.read_exact(&mut buf).map_err(|e| e.to_string())?;
    Ok(String::from_utf8_lossy(&buf).to_string())
}

fn read_u8(f: &mut File) -> Result<u8, String> {
    let mut buf = [0u8; 1];
    f.read_exact(&mut buf).map_err(|e| e.to_string())?;
    Ok(buf[0])
}

fn read_u32_le(f: &mut File) -> Result<u32, String> {
    let mut buf = [0u8; 4];
    f.read_exact(&mut buf).map_err(|e| e.to_string())?;
    Ok(u32::from_le_bytes(buf))
}

fn read_u64_le(f: &mut File) -> Result<u64, String> {
    let mut buf = [0u8; 8];
    f.read_exact(&mut buf).map_err(|e| e.to_string())?;
    Ok(u64::from_le_bytes(buf))
}

pub fn print_profile(profile: &ArtifactProfile) {
    println!("Kind:       {}", profile.artifact_kind);
    println!("Path:       {}", profile.path);
    println!(
        "Size:       {:.2} GB",
        profile.file_size_bytes as f64 / (1024.0 * 1024.0 * 1024.0)
    );

    if !profile.metadata.is_empty() {
        println!("Metadata:");
        for (k, v) in &profile.metadata {
            println!("  {k}: {v}");
        }
    }
}
