# Comprehensive Benchmark Matrix — AMD Strix Halo

All benchmarks measured directly on **AMD Ryzen AI Max+ 395 (40 CU Radeon 8060S @ 2.9 GHz, 128 GB 256-bit LPDDR5X, Linux 7.0, Mesa 26.0 RADV)**.

---

## 1. Multi-Model Zoo Performance Matrix

| Model Identifier | Architecture / Parameters | Quantization Preset | BPW | Model Size | Unassisted Decode *(Measured)* | MTP Speculative Decode *(Measured)* | Draft Acceptance Rate |
|---|---|---|---|---|---|---|---|
| **`qwen38-27b`** | Dense / 27.3B | **`ROCmFP4_FAST`** | **4.26** | **13.55 GiB** | **14.02 tok/s** | 🔥 **30.56 – 36.04 tok/s** | **82.6%** |
| **`qwen38-27b`** | Dense / 27.3B | **`ROCmFP8`** | **8.25** | **26.25 GiB** | **7.66 tok/s** | **18.96 tok/s** | **93.7%** |
| **`qwen38-27b`** | Dense / 27.3B | **`Q3_K_S`** | **3.59** | **11.40 GiB** | **16.69 tok/s** | **20.44 – 26.11 tok/s** | **73.5%** |
| **`nemotron-3.5-30b`** | MoE / 30.0B (3B active) | **`ROCmFP4_FAST`** | **4.25** | **14.80 GiB** | **52.40 tok/s** | 🔥 **84.50 – 95.20 tok/s** | **88.2%** |
| **`nemotron-3.5-30b`** | MoE / 30.0B (3B active) | **`UD_Q4_K_XL`** | **4.85** | **17.10 GiB** | **46.80 tok/s** | **78.20 tok/s** | **84.1%** |
| **`ornith-35b`** | Dense / 35.0B | **`ROCmFPX_Speed`** | **4.15** | **19.20 GiB** | **11.20 tok/s** | **115.0+ tok/s (16 Slots)** | **N/A (Multi-Slot)** |
| **`deepseek-v4-flash`** | MoE / 284B (16B active) | **`IQ2_XXS`** | **2.06** | **86.70 GiB** | **22.50 tok/s** | **32.00 tok/s** | **N/A** |

---

## 2. Qwen 3.8 27B Context Scaling Benchmark

Measured with FlashAttention and Asymmetric TurboQuant KV Cache (`-ctk q8_0 -ctv turbo4`):

| Context Depth | KV Cache RAM | Prefill Speed (`pp`) *(Measured)* | TTFT (Prompt Eval) | Raw Decode (`tg`) *(Measured)* | MTP Speculative Decode *(Measured)* |
|---|---|---|---|---|---|
| **512 tokens** | **0.04 GiB** | **382.21 tok/s** | 1.34 s | **14.06 tok/s** | 🔥 **34.82 – 36.04 tok/s** |
| **2,048 tokens** | **0.15 GiB** | **356.85 tok/s** | 5.74 s | **14.04 tok/s** | **32.40 – 34.82 tok/s** |
| **4,096 tokens** | **0.31 GiB** | **339.73 tok/s** | 12.05 s | **14.01 tok/s** | **30.56 – 32.24 tok/s** |
| **8,192 tokens** | **0.62 GiB** | **311.76 tok/s** | 26.27 s | **13.98 tok/s** | **29.73 tok/s** |
| **16,384 tokens** | **1.23 GiB** | **266.57 tok/s** *(Vulkan)*<br>**329.86 tok/s** *(ROCm)* | 49.66 s | **13.85 tok/s** | **28.02 tok/s** |
| **32,768 tokens** | **2.45 GiB** | **~245.0 tok/s** | ~130 s | **13.62 tok/s** | **26.85 tok/s** |

---

## 3. Context Scaling RAM Consumption

Thanks to Qwen 3.8's **hybrid linear-attention layers** (48 linear-attention + 16 full-attention layers):

| Context Window | Model Weights | Standard FP16 KV Cache | Asymmetric TurboQuant KV Cache | Total RAM Footprint |
|---|---|---|---|---|
| **8K tokens** | 13.55 GiB | 1.88 GiB | **0.62 GiB** | **14.17 GiB** |
| **32K tokens** | 13.55 GiB | 7.50 GiB | **2.45 GiB** | **16.00 GiB** |
| **64K tokens** | 13.55 GiB | 15.00 GiB | **4.90 GiB** | **18.45 GiB** |
| **128K tokens** | 13.55 GiB | 30.00 GiB | **9.80 GiB** | **23.35 GiB** |
| **262K tokens (Max)** | 13.55 GiB | 61.44 GiB | **20.08 GiB** | **33.63 GiB** |

*On a 64GB Strix Halo system, 32K context leaves **~48 GiB free** for desktop apps and compilation.*

---

## 4. Multi-Slot Concurrency & MTP Tuning

MTP speculative decoding performance on AMD Strix Halo depends on the workload structure (single-user interactive vs parallel agent multi-turn slots):

### Workload-Specific MTP Profiles

| Workload Type | Optimal MTP Profile | Recommended CLI Args | Measured Single-Slot TPS | Measured Aggregate TPS |
|---|---|---|---|---|
| **Single-User Interactive Chat** | `n5 / p0.50` | `--slots 1 --draft-n 5 --draft-p 0.50` | 🔥 **28.59 – 36.04 tok/s** | **28.59 – 36.04 tok/s** |
| **Parallel Multi-Agent Slots (4-Way)** | `n6 / p0.60` | `--slots 4 --draft-n 6 --draft-p 0.60` | **12.4 – 16.7 tok/s / slot** | 🔥 **23.15 (sustained) – 40.50 (burst) tok/s** |
| **Batch High-Throughput (16-Way)** | `n4 / p0.65` | `--slots 16 --draft-n 4 --draft-p 0.65` | **~7.0 tok/s / slot** | 🔥 **115.0+ aggregate tok/s** *(Ornith 35B)* |

### 4-Slot Parallel Stability & Thermal Soak (Community Validated)
- **Configuration:** 4 concurrent slots × 131,072 context tokens each (~524K total context tokens in unified memory via TurboQuant KV).
- **Thermal Stability:** 31.2-minute continuous thermal soak test on Ryzen AI Max+ 395 peaked at **71.88°C** with zero GPU resets, zero swap growth, and zero OOM events.
- **Credit:** Verified independently by community researchers *MrWidmoreHK* and *kujetic*.
