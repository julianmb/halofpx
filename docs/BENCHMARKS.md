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
| **`ornith-1.5-35b`** | MoE / 34.8B (3B active) | **`ROCmFP4`** (aug-24 MTP refresh) | **4.29** | **18.16 GiB** | **76.9 tok/s** | ✅ **105.6 t/s** (n4 / p0.6) | **87.98%** (mean 3.70/4) |
| **`ornith-1.5-35b`** | MoE / 34.8B (3B active) | **`Q4_K_M`** (baseline) | **4.85** | **21.80 GiB** | **71.5 – 71.7 tok/s** | n/a | n/a |
| **`ornith-35b`** | Dense / 35.0B | **`ROCmFPX_Speed`** | **4.15** | **19.20 GiB** | **11.20 tok/s** | **115.0+ tok/s (16 Slots)** | **N/A (Multi-Slot)** |
| **`qwen38-flash-next`** | MoE / 125B (6B active + 51B PLE) | **`UD-IQ1_S`** | **1.56** | **67.55 GiB** | **27.3 tok/s** *(bring-up)* | n/a | n/a |
| **`deepseek-v4-flash`** | MoE / 284B (16B active) | **`IQ2_XXS`** | **2.06** | **86.70 GiB** | **22.50 tok/s** | **32.00 tok/s** | **N/A** |
| **`ling3-flash`** | MoE / 124B (5.1B active) | **`Q4_K_M`** | **4.85** | **71.72 GiB** | **45.23 tok/s** | **50.5 – 51.3 tok/s** (n4 / p0.6) | **79 – 91%** |

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
| **Single-User Sustained Decode (Sweet Spot)** | `n4 / p0.0` | `--slots 1 --draft-n 4 --draft-p 0.0` | 🔥 **33.80 tok/s sustained** (2.40× over baseline) | **33.80 tok/s** |
| **Single-User Interactive Chat (Burst)** | `n5 / p0.50` | `--slots 1 --draft-n 5 --draft-p 0.50` | 🔥 **28.59 – 36.04 tok/s** | **28.59 – 36.04 tok/s** |
| **Parallel Multi-Agent Slots (4-Way)** | `n6 / p0.60` | `--slots 4 --draft-n 6 --draft-p 0.60` | **12.4 – 16.7 tok/s / slot** | 🔥 **23.15 (sustained) – 40.50 (burst) tok/s** |
| **Batch High-Throughput (16-Way)** | `n4 / p0.65` | `--slots 16 --draft-n 4 --draft-p 0.65` | **~7.0 tok/s / slot** | 🔥 **115.0+ aggregate tok/s** *(Ornith 35B)* |

> 💡 **MTP Depth (`K`) Scaling Insight:** Empirical sweeps show `K=4` is the optimal single-stream sweet spot on Strix Halo (`33.8 tok/s`). `K=6` regresses slightly due to memory bus saturation on a single stream, while `K=8` causes severe rollback degradation (`18.2 tok/s`). For 4-slot parallel concurrency, `K=6 / p0.60` maintains higher shared-slot throughput.

### Ornith-1.5-35B (Qwen3.5MoE / hybrid linear attention) — MTP is a net loss

Measured on `ROCmFP4` (Vulkan0, gfx1151), same 192-token prompt:

| Config | Decode | Draft acceptance |
|---|---|---|
| **bare (no MTP)** | **76.0 tok/s** | — |
| K2 p0.5 / p0.75 | 72.5–73.5 tok/s | ~68% |
| K4 p0.5 | 72.6 tok/s | ~68% |
| K4 p0.0 (greedy) | 35–50 tok/s | **15.9%** |
| K4 p0.0 `--spec-mtp-strict-qwen` | 31.5–46.6 tok/s | 19.9% |

- The embedded 1-layer MTP head drafts greedily but accepts only ~16% of tokens on the hybrid `qwen35moe` architecture, so the draft+verify overhead exceeds any gain. Even at relaxed `p-min` (68% acceptance) it never beats bare decode.
- `--spec-mtp-strict-qwen` (boundary-safe multi-row verification with bounded recurrent rollback for Qwen35/Qwen35MoE) improves greedy acceptance from 15.9% → 19.9% but still loses to bare.
- **Recommendation (updated 2026-08-28):** the official aug-24 MTP refresh fixed the ornith drafter — 87.98% acceptance (mean 3.70/4), **105.6 tok/s effective (+38% vs bare)** on gfx1151. `mtp_enabled: true` (n4 / p0.6) is now the default in the registry. requires the refreshed quant (sha256 0f907917…); older quants keep the weak drafter.

### 4-Slot Parallel Stability & Thermal Soak (Community Validated)
- **Configuration:** 4 concurrent slots × 131,072 context tokens each (~524K total context tokens in unified memory via TurboQuant KV).
- **Thermal Stability:** 31.2-minute continuous thermal soak test on Ryzen AI Max+ 395 peaked at **71.88°C** with zero GPU resets, zero swap growth, and zero OOM events.
- **Credit:** Verified independently by community researchers *MrWidmoreHK* and *kujetic*.

---

## 5. Quantization Fidelity & Long-Context Validation (Ornith-1.5-35B ROCmFP4)

Measured on the shipped `Ornith-1.5-35B-A3B-ROCmFP4.gguf` (gfx1151 ROCmFP4 build, commit `12f8b7e`), ROCm0 backend, cache mode (`-ctk q8_0 -ctv q8_0`, MTP disabled).

### 5.1 Perplexity vs Q4_K_M Baseline

`llama-perplexity` over `wikitext-2-raw` (validation split, 9 chunks, `n_ctx=512`, `batch=512`), ROCm0:

| Quantization | Perplexity (↓ better) |
|---|---|
| **ROCmFP4** (shipped) | **5.95 ± 0.31** |
| **Q4_K_M** (baseline) | **5.64 ± 0.29** |

→ ROCmFP4 lands within **~5.5%** of the well-tuned Q4_K_M — a small, expected trade for a speed-oriented 4-bit format (see §1: +7.5% decode over Q4_K_M on this model). Fidelity is competitive.

### 5.2 Context-Window Validation

| Context | Load | Decode (tok/s) | Prefill (tok/s) | Notes |
|---|---|---|---|---|
| **131,072** | ✅ clean | **58.6** | **96.6** | cache mode active |
| **262,144** (full train capacity) | ✅ clean, no warnings | **58.5** | **140.0** | `n_ctx_seq == n_ctx_train`; clean load |

- Both validated with the production `engine_manager` flag set (`-ctxcp 16 -cpent 4096 -cram 32768`, `--kv-unified`, `--cont-batching`).
- **Known limitation:** `cache_reuse` (KV-shift reuse) auto-disables on this hybrid SSM-state context — prompt-cache *RAM checkpoints* remain active, so resume/reuse still works; only fine-grained shifting is off.
- Multimodal path also verified: `mmproj-Ornith-1.5-35B-BF16.gguf` loads and the server answers image prompts correctly.

---

## 6. Qwen 3.8 Flash Next (`qwen4exp`) Bring-Up Benchmark

Measured directly on AMD Strix Halo (`gfx1151`, Mesa RADV Wave64) using `port-qwen4exp` (PR #98):

- **Model:** `Qwen3.8-Flash-Next-UD-IQ1_S` (67.55 GiB GGUF)
- **Engine Configuration:** `-dev Vulkan0 -ngl 99 -fa on -ub 512`
- **Measured Metrics:**
  - `pp512`: **381.73 ± 2.25 tok/s**
  - `pp4096`: **352.22 ± 3.93 tok/s**
  - `tg128`: **25.71 – 27.30 tok/s** peak decode throughput

---

## 7. Ling 3.0 Flash (`bailingmoe3`) Bring-Up Benchmark

Measured directly on AMD Strix Halo (`gfx1151`, Mesa RADV Wave64) using ROCmFPX `build-rocmfpx` (11475/08213ad5b); ROCm0 leg via q38rocm v1.7.0 prebuilt (org lineage 75e67a92b — build skew noted):

- **Model:** `Ling-3.0-flash-Q4_K_M` (71.72 GiB GGUF, 2 shards)
- **Engine Configuration:** `--jinja -dev Vulkan0 -ngl 99 -c 8192 -fa off -t 16`
- **Measured Metrics:**
  - `pp512` (Vulkan0): **372.68 ± 2.67 tok/s**
  - `tg128` (Vulkan0): **45.23 ± 0.09 tok/s**
  - `pp512` (ROCm0, v1.7.0 prebuilt): **391.80 ± 5.97 tok/s**
  - `tg128` (ROCm0, v1.7.0 prebuilt): **35.96 ± 0.09 tok/s**
  - MTP (`--spec-type draft-mtp` n4/p0.6): **50.5 – 51.3 tok/s**, 21/23 (91%) then 83/105 (79%) drafts accepted
  - `wikitext-2` perplexity: **4.6064 ± 0.0275** (597 chunks)
  - Context scaling: 32K/64K/128K all load clean (18/24/24 s); VSZ 76.7/77.2/82.1 GiB (+5.4 GiB for 4× ctx — MLA/KDA flat)
- **Requirements:** `-fa off`, bounded `-c 8192` (GGUF default 262K hangs the box); thinking via `chat_template_kwargs.enable_thinking`; card sampling (`temp 0.6 / top_p 0.95 / top_k 20`) needs generous `max_tokens` (~500 thinking tokens before content)
- **ROCmFP4 verdict: PARKED** — `Q4_0_ROCMFP4_FAST` (63.27 GiB, 4.26 bpw): PPL 7.04 vs 4.61 + incoherent generation; `Q4_0_ROCMFP4_STRIX_LEAN` (63.35 GiB): repetitive garbage. Both gated on fresh servers, load logs clean. NOT published. `Q4_K_M` remains the serving quant.
