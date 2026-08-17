# ROCmFPX Quantization Recipes & Math for AMD Strix Halo

This document outlines the quantization formats, block alignment math, and conversion pipelines for creating high-throughput **ROCmFP4** and **ROCmFP8** GGUF weights for AMD Strix Halo.

---

## 1. Quantization Layouts Overview

| Quantization Preset | Effective BPW | Block Size | Target Subsystem | Characteristics & Use Cases |
|---|---|---|---|---|
| **`Q4_0_ROCMFP4_FAST`** | **4.26** | **32** | **Vulkan0 Wave64 / ROCm0** | **Primary speed format for maximum MTP speculative throughput (36 tok/s)** |
| **`Q8_0_ROCMFPX` (`ROCmFP8`)** | **8.25** | **32** | **Vulkan0 / ROCm0** | **Lossless 8-bit precision (<0.003 PPL delta vs FP16, ~19 tok/s)** |
| **`Q4_0_ROCMFP4_STRIX_LEAN`** | **4.34** | **32** | **Vulkan0 / ROCm0** | Preserves embedding and RMSNorm layers in FP16 |
| **`Q3_K_S`** | **3.59** | **Mixed** | **Vulkan0 / CPU** | Fast 3-bit small quant (highest unassisted decode: 16.69 t/s) |
| **`Q3_K_M`** | **3.95** | **Mixed** | **Vulkan0 / CPU** | Balanced 3-bit medium quant (12.56 GiB) |
| **`ROCmFP2_IQ2XXS`** | **2.06** | **32** | **Vulkan0 / Memory Bound** | Ultra-compact 2-bit quantization for massive MoE architectures |

---

## 2. Hardware Alignment on RDNA 3.5 (`gfx1151`)

On AMD Strix Halo (RDNA 3.5 / `gfx1151`), matrix multiplication is accelerated via Mesa RADV cooperative matrix instructions (`KHR_coopmat`):
- **Block Size (32):** Every block of 32 FP4/INT8 weights shares a single FP16 or E8M0 scaling factor, matching hardware vector register alignment (32 elements per half-wave).
- **Zero-Stall Streaming:** By avoiding complex hierarchical scales, weights stream directly from unified LPDDR5X RAM into registers without multi-stage unpacking math.
- **MTP Head Preservation:** Prediction heads (`mtp_block.dense`, `mtp_block.norm`) are automatically preserved in high-precision (FP16 or Q8_0) during the quantize pass to maintain 80%+ draft acceptance.

---

## 3. Conversion Pipeline (Step-by-Step)

### Step 1: Convert Hugging Face Safetensors to BF16 GGUF
```bash
python3 /path/to/llama.cpp/convert_hf_to_gguf.py \
  /path/to/Qwen3.8-27B-Instruct \
  --outfile Qwen3.8-27B-BF16.gguf \
  --outtype bf16
```

### Step 2: Quantize to ROCmFP4_FAST or ROCmFP8
```bash
# Quantize to ROCmFP4_FAST (4.26 bpw / 13.55 GiB)
./scripts/convert_and_quant.sh Qwen3.8-27B-BF16.gguf ./models

# Or quantize to ROCmFP8 (8.25 bpw / 26.25 GiB)
./scripts/convert_and_quant.sh --preset Q8_0_ROCMFPX Qwen3.8-27B-BF16.gguf ./models
```
