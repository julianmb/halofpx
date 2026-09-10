"""
halofpx.registry — Central Model Zoo & Quantization Presets Registry
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from halofpx.config import (
    MODELS_FILE,
    PRESETS_FILE,
    HF_CACHE_DIRS,
    MODELS_DIR,
    get_lemonade_user_models_path,
)

KNOWN_QUANTS = {
    "q4_k_m", "q4_k_s", "q4_k", "q4_0", "q4_1",
    "q5_k_m", "q5_k_s", "q5_0", "q5_1",
    "q6_k", "q8_0", "q8_1", "q2_k", "q3_k_m", "q3_k_s", "q3_k_l",
    "iq4_xs", "iq4_nl", "iq3_m", "iq3_s", "iq2_xxs", "iq2_xs", "iq1_s", "iq1_m",
    "fp16", "bf16", "f16", "f32", "rocmfp4", "rocmfp8", "rocmfp4_fast", "rocmfp4_strix_lean"
}

MODEL_ALIASES = {
    "ling3": "ling3-flash",
    "ling3.0": "ling3-flash",
    "ling-3.0": "ling3-flash",
    "ling-3.0-flash": "ling3-flash",
    "ling3-flash": "ling3-flash",
    "qwen3.8-flash": "qwen38-flash-next",
    "qwen3.8-flash-next": "qwen38-flash-next",
    "qwen-3.8-flash-next": "qwen38-flash-next",
    "qwen-3.8-27b": "qwen38-27b",
    "qwen3.8-27b": "qwen38-27b",
    "ornith-1.5": "ornith-1.5-35b",
    "ornith-1.5-35b": "ornith-1.5-35b",
    "nex-n2.5": "nex-n2.5-mini",
    "nex-n2.5-mini": "nex-n2.5-mini",
    "nemotron-3.5": "nemotron-3.5-30b",
    "deepseek-v4": "deepseek-v4-flash",
}


def normalize_name(name: str) -> str:
    """Normalize model string by removing non-alphanumeric chars and lowercasing."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class ModelRegistry:
    def __init__(self, models_path: Path = MODELS_FILE, presets_path: Path = PRESETS_FILE):
        self.models_path = models_path
        self.presets_path = presets_path
        self.models: Dict[str, Any] = {}
        self.presets: Dict[str, Any] = {}
        self.reload()

    def reload(self):
        self.models = {}
        self.presets = {}
        if self.models_path.exists():
            with open(self.models_path, "r", encoding="utf-8") as f:
                self.models = json.load(f)
        if self.presets_path.exists():
            with open(self.presets_path, "r", encoding="utf-8") as f:
                self.presets = json.load(f)

        # 1. Lemonade user_models.json integration
        u_path = get_lemonade_user_models_path()
        if u_path and u_path.exists():
            try:
                with open(u_path, "r", encoding="utf-8") as f:
                    u_data = json.load(f)
                for u_id, u_info in u_data.items():
                    if u_id not in self.models and f"user.{u_id}" not in self.models:
                        checkpoint = u_info.get("checkpoint", "")
                        hf_repo = checkpoint.split(":")[0] if ":" in checkpoint else checkpoint
                        fname = checkpoint.split(":")[1] if ":" in checkpoint else checkpoint
                        if not fname.endswith(".gguf") and fname != checkpoint:
                            fname = f"{fname}.gguf"

                        mmproj_info = None
                        if u_info.get("mmproj"):
                            mmproj_info = {
                                "filename": u_info.get("mmproj"),
                                "size_gib": 0.0,
                            }

                        self.models[u_id] = {
                            "display_name": u_id,
                            "category": "Lemonade User Model",
                            "hf_repo": hf_repo,
                            "source": "lemonade_user",
                            "default_variant": "default",
                            "variants": {
                                "default": {
                                    "filename": fname,
                                    "bpw": 4.0,
                                    "size_gib": float(u_info.get("size", 0.0)),
                                    "min_vram_gib": float(u_info.get("size", 0.0)) + 2.0,
                                }
                            },
                            "mmproj": mmproj_info,
                            "run_config": {
                                "ctx_size": 32768,
                                "n_gpu_layers": 99,
                                "flash_attn": True,
                            },
                        }
            except Exception:
                pass

        # 2. Discover extra local models in MODELS_DIR
        self._discover_extra_models()

    def _discover_extra_models(self):
        if not MODELS_DIR.exists():
            return
        try:
            # Build existing model index: normalized IDs, known files, and resolved directory paths
            existing_norm = {
                normalize_name(mid): mid for mid in self.models.keys()
            }
            existing_files = set()
            existing_dirs = set()
            for mid, mdata in list(self.models.items()):
                for vdata in mdata.get("variants", {}).values():
                    fn = vdata.get("filename")
                    if fn:
                        existing_files.add(Path(fn).name.lower())
                mm = mdata.get("mmproj")
                if mm and mm.get("filename"):
                    existing_files.add(Path(mm["filename"]).name.lower())
                for cache_dir in HF_CACHE_DIRS:
                    p = (cache_dir / mid).resolve()
                    if p.exists():
                        existing_dirs.add(p)

            for entry in MODELS_DIR.iterdir():
                if entry.is_dir():
                    dir_name = entry.name
                    if dir_name.startswith("."):
                        continue

                    # If this directory resolves to an existing registered model dir, skip
                    if entry.resolve() in existing_dirs:
                        continue

                    norm_dir = normalize_name(dir_name)
                    if norm_dir in existing_norm or f"extra{norm_dir}" in existing_norm:
                        continue

                    # Check for gguf files directly in entry or 1 level deeper
                    gguf_files = list(entry.glob("*.gguf"))
                    if not gguf_files:
                        gguf_files = list(entry.glob("*/*.gguf"))
                    if not gguf_files:
                        continue

                    # If all gguf files are already known variant files of an existing model, skip
                    if all(gf.name.lower() in existing_files for gf in gguf_files):
                        continue

                    mmproj_file = None
                    non_mmproj_files = []
                    for gf in gguf_files:
                        if "mmproj" in gf.name.lower():
                            mmproj_file = gf
                        else:
                            non_mmproj_files.append(gf)

                    if not non_mmproj_files:
                        continue

                    # Handle sharded models: group files matching shard patterns
                    shard_groups: Dict[str, list[Path]] = {}
                    shard_re = re.compile(r"[-._](\d+)[-._]of[-._](\d+)", re.IGNORECASE)

                    for vf in non_mmproj_files:
                        m = shard_re.search(vf.stem)
                        if m:
                            base_stem = shard_re.sub("", vf.stem)
                        else:
                            base_stem = vf.stem
                        shard_groups.setdefault(base_stem, []).append(vf)

                    variants = {}
                    for base_stem, files in shard_groups.items():
                        files.sort(key=lambda p: p.name)
                        primary_file = files[0]
                        total_size = sum(f.stat().st_size for f in files)
                        size_gib = round(total_size / (1024**3), 2)

                        vname = base_stem
                        if vname.startswith(dir_name):
                            short_vname = vname[len(dir_name):].lstrip("-_.")
                            if short_vname:
                                vname = short_vname
                        variants[vname] = {
                            "filename": primary_file.name,
                            "bpw": 4.0,
                            "size_gib": size_gib,
                            "min_vram_gib": max(16.0, size_gib + 2.0),
                        }

                    mmproj_info = None
                    if mmproj_file:
                        mmproj_info = {
                            "filename": mmproj_file.name,
                            "size_gib": round(mmproj_file.stat().st_size / (1024**3), 2),
                        }

                    # Determine recognized model name and display name
                    # Never use generic quant names like Q4_K_M for the model name
                    effective_model_id = dir_name
                    display_name = dir_name
                    if norm_dir in KNOWN_QUANTS or dir_name.lower().replace("-", "_") in KNOWN_QUANTS:
                        sample_stem = list(shard_groups.keys())[0]
                        for q in KNOWN_QUANTS:
                            pattern = re.compile(rf"[-._]{q}(?:[-._]|$)", re.IGNORECASE)
                            if pattern.search(sample_stem):
                                sample_stem = pattern.sub("", sample_stem)
                        clean_name = sample_stem.rstrip("-_.")
                        if clean_name:
                            display_name = clean_name
                            effective_model_id = clean_name.lower().replace(" ", "-")

                    self.models[effective_model_id] = {
                        "display_name": display_name,
                        "category": "Discovered Local Model",
                        "hf_repo": "",
                        "source": "extra_models_dir",
                        "default_variant": list(variants.keys())[0],
                        "variants": variants,
                        "mmproj": mmproj_info,
                        "run_config": {
                            "ctx_size": 32768,
                            "n_gpu_layers": 99,
                            "flash_attn": True,
                        },
                    }
        except Exception:
            pass

    def list_models(self) -> List[Dict[str, Any]]:
        result = []
        for model_id, data in self.models.items():
            entry = dict(data)
            entry["model_id"] = model_id
            
            # Check local file status for each variant
            variants_status = {}
            for variant_name, vdata in entry.get("variants", {}).items():
                filename = vdata.get("filename")
                local_path = self.resolve_local_file(filename, model_id=model_id)
                variants_status[variant_name] = {
                    "filename": filename,
                    "downloaded": local_path is not None,
                    "local_path": str(local_path) if local_path else None,
                    "size_gib": vdata.get("size_gib", 0.0),
                    "min_vram_gib": vdata.get("min_vram_gib", 16.0),
                    "bpw": vdata.get("bpw", 0.0),
                    "sha256": vdata.get("sha256", "")
                }
            entry["variants_status"] = variants_status
            entry["is_ready"] = any(v["downloaded"] for v in variants_status.values())

            mmproj = entry.get("mmproj")
            mmproj_path = self.resolve_local_file(mmproj.get("filename"), model_id=model_id) if mmproj else None
            entry["vision_capable"] = mmproj is not None
            entry["vision_ready"] = mmproj_path is not None
            entry["mmproj_status"] = {
                "filename": mmproj.get("filename"),
                "downloaded": mmproj_path is not None,
                "local_path": str(mmproj_path) if mmproj_path else None,
                "size_gib": mmproj.get("size_gib", 0.0),
                "sha256": mmproj.get("sha256", ""),
            } if mmproj else None
            result.append(entry)
        return result

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        if not model_id:
            return None
        # 1. Exact match
        if model_id in self.models:
            data = dict(self.models[model_id])
            data["model_id"] = model_id
            return data

        # 2. Check stripping prefixes (extra., user., builtin.)
        for prefix in ("extra.", "user.", "builtin."):
            if model_id.startswith(prefix):
                short_id = model_id[len(prefix):]
                if short_id in self.models:
                    data = dict(self.models[short_id])
                    data["model_id"] = model_id
                    return data

        # 3. Check prepending prefixes
        for prefix in ("extra.", "user.", "builtin."):
            prefixed = f"{prefix}{model_id}"
            if prefixed in self.models:
                data = dict(self.models[prefixed])
                data["model_id"] = model_id
                return data

        # 4. Normalized match (ignoring hyphens, underscores, dots, case)
        target_norm = normalize_name(model_id)
        for mid, mdata in self.models.items():
            if normalize_name(mid) == target_norm:
                data = dict(mdata)
                data["model_id"] = mid
                return data

        # 5. Display name match (case-insensitive substring or full match)
        target_lower = model_id.lower().strip()
        for mid, mdata in self.models.items():
            disp = mdata.get("display_name", "").lower().strip()
            if disp and (disp == target_lower or target_lower in disp):
                data = dict(mdata)
                data["model_id"] = mid
                return data

        # 6. Common recognized aliases
        if target_lower in MODEL_ALIASES and MODEL_ALIASES[target_lower] in self.models:
            target_id = MODEL_ALIASES[target_lower]
            data = dict(self.models[target_id])
            data["model_id"] = target_id
            return data

        return None

    def resolve_local_file(self, filename: Optional[str], model_id: Optional[str] = None) -> Optional[Path]:
        if not filename:
            return None

        # Check direct path
        direct = Path(filename)
        if direct.is_absolute() and direct.exists():
            return direct

        # Search cache directories
        for base_dir in HF_CACHE_DIRS:
            if not base_dir.exists():
                continue
            # Direct file in dir
            cand = base_dir / filename
            if cand.is_file() and ".no_exist" not in cand.parts:
                return cand
            # Direct file in model_id subdirectory
            if model_id:
                cand_sub = base_dir / model_id / filename
                if cand_sub.is_file() and ".no_exist" not in cand_sub.parts:
                    return cand_sub
                # Check directory name variants (case-insensitive / normalized)
                norm_m = normalize_name(model_id)
                try:
                    for sub in base_dir.iterdir():
                        if sub.is_dir() and normalize_name(sub.name) == norm_m:
                            cand_sub_alt = sub / filename
                            if cand_sub_alt.is_file() and ".no_exist" not in cand_sub_alt.parts:
                                return cand_sub_alt
                except Exception:
                    pass
                # Also try stripped prefix (e.g. extra.qwen -> qwen)
                for prefix in ("extra.", "user.", "builtin."):
                    if model_id.startswith(prefix):
                        short_id = model_id[len(prefix):]
                        cand_sub2 = base_dir / short_id / filename
                        if cand_sub2.is_file() and ".no_exist" not in cand_sub2.parts:
                            return cand_sub2
            # Recursive search in snapshots/models
            for match in base_dir.glob(f"**/{filename}"):
                # Skip HF negative-cache markers and incomplete downloads
                if ".no_exist" in match.parts or not match.is_file():
                    continue
                return match
        return None

    def get_model_file_path(self, model_id: str, variant: Optional[str] = None) -> Optional[Path]:
        model = self.get_model(model_id)
        if not model:
            return None

        variants = model.get("variants", {})
        if variant and variant in variants:
            filename = variants[variant].get("filename")
            path = self.resolve_local_file(filename, model_id=model_id)
            if path:
                return path

        # If no specific variant requested, check default_variant first
        def_var = model.get("default_variant")
        if def_var and def_var in variants:
            fname = variants[def_var].get("filename")
            path = self.resolve_local_file(fname, model_id=model_id)
            if path:
                return path

        # Fallback: find first downloaded variant
        for vinfo in variants.values():
            fname = vinfo.get("filename")
            path = self.resolve_local_file(fname, model_id=model_id)
            if path:
                return path

        # If variant name is direct filename or legacy quant_files
        legacy_files = model.get("quant_files", {})
        if variant and variant in legacy_files:
            return self.resolve_local_file(Path(legacy_files[variant]).name, model_id=model_id)

        return None

    def get_mmproj_file_path(self, model_id: str) -> Optional[Path]:
        model = self.get_model(model_id)
        if not model:
            return None
        mmproj_name = model.get("mmproj", {}).get("filename")
        if mmproj_name:
            return self.resolve_local_file(mmproj_name, model_id=model_id)
        return None

