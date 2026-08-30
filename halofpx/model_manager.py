"""
halofpx.model_manager — Hugging Face Download & Cache Manager
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from halofpx.config import ROOT_DIR
from halofpx.registry import ModelRegistry

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
        hf_repo = var_info.get("hf_repo", model.get("hf_repo"))
        filename = var_info.get("filename")
        expected_sha = var_info.get("sha256", "")

        if not hf_repo or not filename:
            return {"status": "error", "message": f"Missing HF repo or filename for {model_id}:{var_name}"}

        target_dir = ROOT_DIR / "models" / model_id
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"📥 Pulling {model_id}:{var_name} from https://huggingface.co/{hf_repo}...")

        try:
            local_target = self._download_file(hf_repo, filename, target_dir)
        except Exception as e:
            return {"status": "error", "message": f"Download failed: {e}"}

        checksum_error = self._verify_checksum(local_target, expected_sha)
        if checksum_error:
            return {"status": "warning", "message": checksum_error, "local_path": str(local_target)}

        mmproj_path = None
        mmproj = model.get("mmproj")
        if mmproj:
            mmproj_repo = mmproj.get("hf_repo", hf_repo)
            mmproj_filename = mmproj.get("filename")
            if not mmproj_repo or not mmproj_filename:
                return {
                    "status": "error",
                    "message": f"Missing HF repo or filename for {model_id} vision projector",
                    "local_path": str(local_target),
                    "vision_ready": False,
                }
            print(f"🖼️  Pulling vision projector from https://huggingface.co/{mmproj_repo}...")
            try:
                mmproj_path = self._download_file(mmproj_repo, mmproj_filename, target_dir)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Model downloaded, but vision projector download failed: {e}",
                    "local_path": str(local_target),
                    "vision_ready": False,
                }
            checksum_error = self._verify_checksum(mmproj_path, mmproj.get("sha256", ""))
            if checksum_error:
                return {
                    "status": "warning",
                    "message": checksum_error,
                    "local_path": str(local_target),
                    "mmproj_path": str(mmproj_path),
                    "vision_ready": False,
                }

        return {
            "status": "success",
            "model_id": model_id,
            "variant": var_name,
            "local_path": str(local_target),
            "size_gib": round(local_target.stat().st_size / (1024**3), 2),
            "mmproj_path": str(mmproj_path) if mmproj_path else None,
            "vision_ready": mmproj_path is not None,
        }

    def _download_file(self, repo_id: str, filename: str, target_dir: Path) -> Path:
        local_target = target_dir / filename
        try:
            subprocess.run(
                ["hf", "download", repo_id, filename, "--local-dir", str(target_dir)],
                check=True,
            )
        except Exception:
            from huggingface_hub import hf_hub_download

            local_target = Path(
                hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(target_dir))
            )
        if not local_target.is_file():
            raise RuntimeError(f"download completed but '{filename}' was not created")
        return local_target

    def _verify_checksum(self, file_path: Path, expected_sha: str) -> Optional[str]:
        if not expected_sha:
            return None
        print(f"🔒 Verifying SHA256 checksum for {file_path.name}...")
        actual_sha = self.compute_sha256(file_path)
        if actual_sha.lower() != expected_sha.lower():
            return f"Checksum mismatch for {file_path.name}: expected {expected_sha}, got {actual_sha}"
        return None

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
