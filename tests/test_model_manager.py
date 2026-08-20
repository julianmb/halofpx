import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from halofpx.model_manager import ModelManager


class FakeRegistry:
    def get_model(self, model_id):
        if model_id != "vision-model":
            return None
        return {
            "model_id": model_id,
            "hf_repo": "owner/model",
            "default_variant": "ROCmFP4",
            "variants": {
                "ROCmFP4": {
                    "filename": "model.gguf",
                    "sha256": "",
                }
            },
            "mmproj": {
                "filename": "mmproj.gguf",
                "hf_repo": "owner/model",
                "sha256": "",
            },
        }


class ModelManagerTests(unittest.TestCase):
    def test_pull_multimodal_model_downloads_projector(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = ModelManager(FakeRegistry())
            downloaded = []

            def download(repo_id, filename, target_dir):
                downloaded.append((repo_id, filename))
                path = target_dir / filename
                path.write_bytes(b"test")
                return path

            with patch("halofpx.model_manager.ROOT_DIR", root), patch.object(
                manager, "_download_file", side_effect=download
            ):
                result = manager.pull_model("vision-model")

            self.assertEqual(result["status"], "success")
            self.assertTrue(result["vision_ready"])
            self.assertEqual(Path(result["mmproj_path"]).name, "mmproj.gguf")
            self.assertEqual(downloaded, [
                ("owner/model", "model.gguf"),
                ("owner/model", "mmproj.gguf"),
            ])


if __name__ == "__main__":
    unittest.main()
