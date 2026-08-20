"""
halofpx.registry — Central Model Zoo & Quantization Presets Registry
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from halofpx.config import MODELS_FILE, PRESETS_FILE, HF_CACHE_DIRS

class ModelRegistry:
    def __init__(self, models_path: Path = MODELS_FILE, presets_path: Path = PRESETS_FILE):
        self.models_path = models_path
        self.presets_path = presets_path
        self.models: Dict[str, Any] = {}
        self.presets: Dict[str, Any] = {}
        self.reload()

    def reload(self):
        if self.models_path.exists():
            with open(self.models_path, "r", encoding="utf-8") as f:
                self.models = json.load(f)
        if self.presets_path.exists():
            with open(self.presets_path, "r", encoding="utf-8") as f:
                self.presets = json.load(f)

    def list_models(self) -> List[Dict[str, Any]]:
        result = []
        for model_id, data in self.models.items():
            entry = dict(data)
            entry["model_id"] = model_id
            
            # Check local file status for each variant
            variants_status = {}
            for variant_name, vdata in entry.get("variants", {}).items():
                filename = vdata.get("filename")
                local_path = self.resolve_local_file(filename)
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
            mmproj_path = self.resolve_local_file(mmproj.get("filename")) if mmproj else None
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
        if model_id in self.models:
            data = dict(self.models[model_id])
            data["model_id"] = model_id
            return data
        return None

    def resolve_local_file(self, filename: Optional[str]) -> Optional[Path]:
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
            if cand.exists():
                return cand
            # Recursive search in snapshots/models
            for match in base_dir.glob(f"**/{filename}"):
                if match.exists() and match.is_file():
                    return match
        return None

    def get_model_file_path(self, model_id: str, variant: Optional[str] = None) -> Optional[Path]:
        model = self.get_model(model_id)
        if not model:
            return None
        
        var_name = variant or model.get("default_variant")
        variants = model.get("variants", {})
        if var_name in variants:
            filename = variants[var_name].get("filename")
            return self.resolve_local_file(filename)
        
        # If variant name is direct filename or legacy quant_files
        legacy_files = model.get("quant_files", {})
        if var_name in legacy_files:
            return self.resolve_local_file(Path(legacy_files[var_name]).name)

        return None

    def get_mmproj_file_path(self, model_id: str) -> Optional[Path]:
        model = self.get_model(model_id)
        if not model:
            return None
        mmproj_name = model.get("mmproj", {}).get("filename")
        if mmproj_name:
            return self.resolve_local_file(mmproj_name)
        return None
