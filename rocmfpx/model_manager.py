"""
rocmfpx.model_manager — Hugging Face Download & Cache Manager
"""

import os
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from rocmfpx.config import HF_CACHE_DIRS, ROOT_DIR
from rocmfpx.registry import ModelRegistry

class ModelManager:
    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or ModelRegistry()

    def pull_model(self, model_id: str, variant: Optional[str] = None) -> Dict[str, Any]:
        model = self.registry.get_model(model_id)
        if not model:
            return {"status": "error", "message": f"Model '{model_id}' not found in registry."}

        var_name = variant or model.get("default_variant")
        variants = model.get("variants", {})
        if var_name not in variants:
            return {"status": "error", "message": f"Variant '{var_name}' not found for model '{model_id}'."}

        var_info = variants[var_name]
        hf_repo = model.get("hf_repo")
        filename = var_info.get("filename")
        expected_sha = var_info.get("sha256", "")

        if not hf_repo or not filename:
            return {"status": "error", "message": f"Missing HF repo or filename for {model_id}:{var_name}"}

        target_dir = ROOT_DIR / "models" / model_id
        target_dir.mkdir(parents=True, exist_ok=True)
        local_target = target_dir / filename

        print(f"📥 Pulling {model_id}:{var_name} from https://huggingface.co/{hf_repo}...")
        
        # Try hf CLI first
        try:
            cmd = ["hf", "download", hf_repo, filename, "--local-dir", str(target_dir)]
            subprocess.run(cmd, check=True)
        except Exception:
            # Fallback to huggingface_hub Python library
            try:
                from huggingface_hub import hf_hub_download
                downloaded = hf_hub_download(repo_id=hf_repo, filename=filename, local_dir=str(target_dir))
                local_target = Path(downloaded)
            except Exception as e:
                return {"status": "error", "message": f"Download failed: {e}"}

        # Verify Checksum if expected_sha is provided
        if expected_sha and local_target.exists():
            print(f"🔒 Verifying SHA256 checksum for {filename}...")
            actual_sha = self.compute_sha256(local_target)
            if actual_sha.lower() != expected_sha.lower():
                return {
                    "status": "warning",
                    "message": f"Checksum mismatch: expected {expected_sha}, got {actual_sha}",
                    "local_path": str(local_target)
                }

        return {
            "status": "success",
            "model_id": model_id,
            "variant": var_name,
            "local_path": str(local_target),
            "size_gib": round(local_target.stat().st_size / (1024**3), 2)
        }

    def compute_sha256(self, file_path: Path) -> str:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024 * 16):
                sha.update(chunk)
        return sha.hexdigest()

    def delete_model(self, model_id: str, variant: Optional[str] = None) -> Dict[str, Any]:
        local_file = self.registry.get_model_file_path(model_id, variant)
        if not local_file or not local_file.exists():
            return {"status": "error", "message": f"Model file for {model_id} not found locally."}
        
        try:
            local_file.unlink()
            return {"status": "success", "message": f"Deleted {local_file.name}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to delete {local_file}: {e}"}
