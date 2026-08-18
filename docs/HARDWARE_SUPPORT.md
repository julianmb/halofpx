# AMD Hardware Support Matrix & GPU VRAM Sizing

`halofpx` dynamically detects your AMD GPU architecture and allocates memory based on available VRAM or unified memory.

---

## 1. Supported Architecture Families

| GPU Architecture | Platform / Devices | Compute Target (`HIP_ARCH`) | Memory Type | Execution Notes |
|---|---|---|---|---|
| **AMD Strix Halo (RDNA 3.5)** | **Ryzen AI Max+ 395 / Radeon 8060S** | `gfx1151` / `gfx1150` | 64 GB / 128 GB Unified LPDDR5X | `HSA_OVERRIDE_GFX_VERSION=11.5.1`<br>`GGML_HIP_ENABLE_UNIFIED_MEMORY=1`<br>Optional 50 TOPS XDNA 2 NPU |
| **AMD Discrete GPUs (RDNA3 / RDNA4)** | **Radeon RX 9000 & 7000 Series** | `gfx1201`, `gfx1200`, `gfx1100` | 16 GB / 24 GB / 32 GB Dedicated VRAM | Native ROCm 7.x target (No HSA override needed) |
| **AMD Mobile / APU (RDNA3 / RDNA2)** | **Radeon 780M, 680M** | `gfx1103`, `gfx1030` | System Shared RAM | Standard Vulkan RADV / ROCm |

---

## 2. Model VRAM Fit Matrix (By Memory Tier)

### Tier 1: 16 GB VRAM Devices (e.g. 16 GB Discrete Radeon GPUs)
* ✅ **Qwen 3.8 27B `ROCmFP4_FAST` (13.55 GB):** Fits up to **16K context** (~14.8 GB total with TurboQuant).
* ✅ **Qwen 3.8 27B `Q3_K_S` (11.40 GB):** Fits up to **32K context** (~13.8 GB total).
* ✅ **Qwen 3.8 27B `ROCmFP2` (8.56 GB):** Comfortable fit across full context.
* ✅ **Nemotron 3.5 30B `ROCmFP4_FAST` (14.80 GB):** Fits up to **8K context** (~15.4 GB total).

### Tier 2: 24 GB – 32 GB VRAM Devices
* ✅ **Qwen 3.8 27B `ROCmFP4_FAST`:** Full **64K–128K context**.
* ✅ **Qwen 3.8 27B `ROCmFP8` (26.25 GB):** Fits in 32 GB VRAM cards.
* ✅ **Nemotron 3.5 30B `ROCmFP4_FAST`:** Full **262K context**.
* ✅ **Ornith 1.0 35B `ROCmFPX_Speed` (19.20 GB):** Fits up to **32K context**.

### Tier 3: 64 GB Unified RAM Devices (e.g. 64GB Strix Halo APUs)
* ✅ **Qwen 3.8 27B `ROCmFP4_FAST`:** Full **262K context** (33.6 GB total).
* ✅ **Qwen 3.8 27B `ROCmFP8` (26.25 GB):** Fits up to **64K context** (29.8 GB total).
* ✅ **Laguna S 2.1 `ROCmFP4_StrixKVSpine` (61.2 GB):** Fits up to **16K context**.
* ✅ **Ornith 1.0 35B:** Full **262K context (16 Concurrent Slots)**.

### Tier 4: 128 GB Unified RAM Devices (e.g. 128GB Strix Halo APUs)
* ✅ **All Models Supported:** Includes **DeepSeek V4 Flash 284B MoE (86.7 GB)** and full 262K multi-slot concurrent workloads.

---

## 3. Building Engine for Your AMD GPU

When you run `./scripts/build_engine.sh`, the script automatically detects your GPU architecture:

```bash
# Clone the repository
git clone https://github.com/julianmb/halofpx.git
cd halofpx

# Build engine for your detected AMD GPU
./scripts/build_engine.sh
```

- **On Strix Halo (`gfx1151`):** You can also download pre-compiled binaries via `./scripts/build_engine.sh --prebuilt`.
- **On other AMD GPUs:** Compiles directly against your detected architecture.
