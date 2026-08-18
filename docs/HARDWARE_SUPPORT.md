# AMD Hardware Support Matrix & GPU VRAM Sizing

`rocmfpx-server` supports AMD APUs and discrete GPUs running the ROCmFPX toolchain.

---

## 1. Supported Architecture Families

| GPU Architecture | Platform / Cards | Compute Target (`HIP_ARCH`) | Memory Type | Special Settings |
|---|---|---|---|---|
| **AMD Strix Halo (RDNA 3.5)** | **Ryzen AI Max+ 395 / Radeon 8060S** | `gfx1151` | 128 GB / 64 GB Unified LPDDR5X | `HSA_OVERRIDE_GFX_VERSION=11.5.1`<br>`GGML_HIP_ENABLE_UNIFIED_MEMORY=1`<br>50 TOPS XDNA 2 NPU |
| **AMD RDNA4 Discrete GPU** | **Radeon RX 9070 / 9070 XT (Navi 48)** | `gfx1201` | 16 GB GDDR6 Dedicated VRAM | Native ROCm 7.1+ target (No HSA override needed!) |
| **AMD RDNA4 Mobile / Navi 44** | **Radeon RX 9000 Series (Navi 44)** | `gfx1200` | 8 GB / 12 GB Dedicated VRAM | Native ROCm 7.1+ target |

---

## 2. Model VRAM Fit Matrix

| Model | Variant | Size | AMD Strix Halo (64GB / 128GB) | AMD Radeon RX 9070 XT (16GB VRAM) |
|---|---|---|---|---|
| **Qwen 3.8 27B** | `ROCmFP4_FAST` (13.55 GB) | 4.26 bpw | ✅ **Full 262K context** (33.6 GB) | ✅ **Fits up to 16K context** (~14.8 GB total) |
| **Qwen 3.8 27B** | `Q3_K_S` (11.40 GB) | 3.59 bpw | ✅ **Full 262K context** | ✅ **Fits up to 32K context** (~13.8 GB total) |
| **Qwen 3.8 27B** | `ROCmFP2` (8.56 GB) | 2.69 bpw | ✅ **Full 262K context** | ✅ **Comfortable fit across long context** |
| **Qwen 3.8 27B** | `ROCmFP8` (26.25 GB) | 8.25 bpw | ✅ **Fits up to 64K context** (29.8 GB) | ⚠️ Exceeds 16GB (Requires Strix Halo / 32GB+ VRAM) |
| **Nemotron 3.5 30B** | `ROCmFP4_FAST` (14.80 GB) | 4.25 bpw | ✅ **Full 262K context** | ✅ **Fits up to 8K context** (15.4 GB total) |
| **Ornith 1.0 35B** | `ROCmFPX_Speed` (19.20 GB) | 4.15 bpw | ✅ **Full 262K context (16 Slots)** | ⚠️ Exceeds 16GB VRAM |
| **DeepSeek V4 Flash** | `IQ2_XXS` (86.70 GB) | 2.06 bpw | ✅ **Fits 128GB Strix Halo** | ⚠️ Exceeds 16GB VRAM |
| **Laguna S 2.1** | `ROCmFP4_StrixKVSpine` (61.2 GB) | 4.25 bpw | ✅ **Fits 128GB Strix Halo** | ⚠️ Exceeds 16GB VRAM |

---

## 3. Quickstart for AMD Radeon RX 9070 XT Users

### 1. Compile ROCmFPX Engine for `gfx1201`:
```bash
# Clone and build engine directly for RDNA4
git clone https://github.com/julianmb/rocmfpx-server.git
cd rocmfpx-server

./scripts/build_engine.sh
```

### 2. Launch Qwen 3.8 27B on RX 9070 XT:
```bash
# Pull model weights
rocmfpx pull qwen38-27b --variant ROCmFP4_FAST

# Load model (auto-detected on Vulkan0 with 16K context limit)
rocmfpx load qwen38-27b --ctx 16384
```
