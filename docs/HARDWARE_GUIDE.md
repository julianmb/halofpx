# AMD Strix Halo Hardware & Performance Tuning Guide

This document provides a technical hardware deep dive for **AMD Strix Halo (Ryzen AI Max+ 395 / Radeon 8060S / gfx1151)** and details the low-level Linux kernel and GPU tuning required to achieve maximum LLM inference throughput.

---

## 1. APU Architecture & Memory Subsystem

Unlike discrete GPU systems (which communicate over PCIe) or traditional mobile APUs (which use a narrow 128-bit memory bus), **AMD Strix Halo features a massive 256-bit wide unified LPDDR5X memory subsystem**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AMD STRIX HALO APU DIE                          │
│                                                                        │
│   ┌────────────────────────┐             ┌────────────────────────┐    │
│   │   16x Zen 5 CPU Cores  │             │   40 CU Radeon 8060S   │    │
│   │   32 Threads / AVX-512 │             │   RDNA 3.5 @ 2.9 GHz   │    │
│   └───────────┬────────────┘             └───────────┬────────────┘    │
│               │                                      │                 │
│               └──────────────────┬───────────────────┘                 │
│                                  │                                     │
│                     256-Bit Unified Memory Bus                         │
│                    (8x 32-Bit LPDDR5X Channels)                        │
│                                  │                                     │
│                                  ▼                                     │
│                  ┌───────────────────────────────┐                     │
│                  │  64 GB / 128 GB Unified UMA   │                     │
│                  │     LPDDR5X-8000 / 8533       │                     │
│                  └───────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Memory Bandwidth Mathematics

$$\text{Bus Width} = 256 \text{ bits} = 32 \text{ bytes per cycle}$$

* **At LPDDR5X-8533 (Rated Peak):**
  $$8533.33 \text{ MT/s} \times 32 \text{ bytes} = \mathbf{273.06 \text{ GB/s Peak Theoretical}}$$
* **At LPDDR5X-8000:**
  $$8000.00 \text{ MT/s} \times 32 \text{ bytes} = \mathbf{256.00 \text{ GB/s Peak Theoretical}}$$
* **Measured Sustained Read Bandwidth:**
  During dense 27B model streaming decode, the memory subsystem achieves **~190–200 GB/s sustained throughput** (~85% bus efficiency).

---

## 2. Dual Backend Crossover: Vulkan vs ROCm

Strix Halo supports two primary acceleration backends in `llama.cpp` / `ROCmFPX`:

| Backend | Driver / Architecture | Best For | Peak Measured Speed |
|---|---|---|---|
| **`Vulkan0`** | **Mesa RADV (STRIX_HALO Wave64 `KHR_coopmat`)** | **Token Decode & MTP Speculation** | **30.5 – 36.0 tok/s** (27B) |
| **`ROCm0`** | **ROCm / HIP 7.x (`gfx1151` vector ALU)** | **Prompt Evaluation / Prefill (TTFT)** | **390+ tok/s** (pp512) |

### Why Vulkan0 is Faster for Decode
Mesa RADV implements cooperative matrix multiplication (`VK_KHR_cooperative_matrix`) natively compiled into Wave64 dual-issue SIMD instructions. Because MTP (Multi-Token Prediction) requires validating a tree of 4–6 candidate tokens in parallel, Wave64 cooperative matrix dispatch reduces kernel launch overhead and delivers ~20% higher decode throughput than ROCm HIP.

---

## 3. Essential Linux Kernel & Hardware Tuning

### 3.1 Dynamic TTM / GTT Memory Allocation Ceiling
By default, the Linux AMDGPU kernel driver restricts GPU memory buffer allocations to **50% of visible system RAM**.

To allow the iGPU to allocate large models and long KV caches:
- **On 64GB Systems:** Default 50% provides 32 GiB (plenty for 32K context with zero tweaks). To unlock full 262K context (33.6 GiB RAM), set the ceiling to ~56 GiB:
  ```bash
  echo 14680064 | sudo tee /sys/module/ttm/parameters/pages_limit
  ```
- **On 128GB Systems:** Set the ceiling to ~120 GiB:
  ```bash
  echo 31457280 | sudo tee /sys/module/ttm/parameters/pages_limit
  ```
*(Or simply run `./scripts/apply_hardware_tweaks.sh`, which detects RAM automatically).*

### 3.2 Lock GPU Power & Clock Governor (2.9 GHz)
Prevent the GPU from dynamic down-clocking during idle prompt intervals:
```bash
echo "high" | sudo tee /sys/class/drm/card0/device/power_dpm_force_performance_level
```

### 3.3 Transparent Hugepages (THP)
Reduces TLB miss penalty during large continuous KV cache allocation:
```bash
echo "madvise" | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
```

---

## 4. AMD XDNA 2 NPU Subsystem (`/dev/accel/accel0`) — Optional

Strix Halo features a dedicated **50 TOPS XDNA 2 NPU** mapped at `/dev/accel/accel0` via the `amdxdna` kernel module. NPU acceleration is **fully optional**.

> 📘 **Full guide:** See [`docs/NPU_INTEGRATION.md`](NPU_INTEGRATION.md) for installation steps, the hybrid burst pipeline, and the empirical findings.

### Measured verdict (from the `npuhalo` research workspace)

The NPU does **not** improve sustained decode speed — any separate drafter loses to the model's own embedded MTP heads. Its proven value:

1. **1.8× faster first token on long prompts** (870 ms vs 1587 ms) via hybrid NPU-burst → iGPU handoff.
2. **~2 W always-on intent routing** (chat/code/translation classifier) with zero iGPU contention.

> ⚠️ **Scope note:** These NPU findings were **only tested on Qwen 3.8 27B** (dense, ROCmFP4_FAST), not the other zoo models.

### Requirements
- **IOMMU SVA** enabled (`iommu=pt iommu.passthrough=0` in GRUB — requires reboot).
- **XRT** runtime (`xrt-smi`) for NPU management.
- **FastFlowLM (`flm`)** via Lemonade for NPU inference.
- **Permissions:** Ensure the host user is in the `render` group:
  ```bash
  sudo usermod -a -G render $USER
  ```
