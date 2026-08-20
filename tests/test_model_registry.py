import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from halofpx.registry import ModelRegistry

class ModelRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = ModelRegistry()

    def test_registered_models_loaded(self):
        models = self.registry.list_models()
        model_ids = [m["model_id"] for m in models]
        self.assertIn("qwen38-27b", model_ids)
        self.assertIn("ornith-1.5-35b", model_ids)
        self.assertIn("nemotron-3.5-30b", model_ids)

    def test_ornith_15_config(self):
        model = self.registry.get_model("ornith-1.5-35b")
        self.assertIsNotNone(model)
        self.assertEqual(model["hf_repo"], "julianmb/Ornith-1.5-35B-A3B-ROCmFP4-GGUF")
        self.assertIn("ROCmFP4", model["variants"])
        self.assertNotIn("ROCmFP4_FAST", model["variants"])
        self.assertNotIn("ROCmFP4_STRIX_LEAN", model["variants"])
        self.assertIn("Q4_K_M", model["variants"])
        self.assertEqual(model["run_config"]["draft_n"], 0)
        self.assertEqual(model["run_config"]["draft_p"], 0.0)
        self.assertFalse(model["run_config"]["mtp_enabled"])
        self.assertEqual(model["mmproj"]["filename"], "mmproj-Ornith-1.5-35B-BF16.gguf")
        self.assertEqual(
            model["mmproj"]["hf_repo"],
            "julianmb/Ornith-1.5-35B-A3B-ROCmFP4-GGUF",
        )

    def test_vision_readiness_is_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            models_path = root / "models.json"
            presets_path = root / "presets.json"
            models_path.write_text(json.dumps({
                "vision-model": {
                    "default_variant": "ROCmFP4",
                    "variants": {"ROCmFP4": {"filename": "model.gguf"}},
                    "mmproj": {"filename": "mmproj.gguf", "size_gib": 0.5},
                }
            }))
            presets_path.write_text("{}")
            (root / "model.gguf").touch()

            with patch("halofpx.registry.HF_CACHE_DIRS", [root]):
                registry = ModelRegistry(models_path, presets_path)
                status = registry.list_models()[0]
                self.assertTrue(status["is_ready"])
                self.assertTrue(status["vision_capable"])
                self.assertFalse(status["vision_ready"])

                (root / "mmproj.gguf").touch()
                status = registry.list_models()[0]
                self.assertTrue(status["vision_ready"])
                self.assertTrue(status["mmproj_status"]["downloaded"])

if __name__ == "__main__":
    unittest.main()
