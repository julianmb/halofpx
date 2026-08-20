import unittest
from pathlib import Path
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
        self.assertEqual(model["hf_repo"], "ornith-ai/Ornith-1.5-35B-A3B-GGUF")
        self.assertIn("ROCmFP4", model["variants"])
        self.assertNotIn("ROCmFP4_FAST", model["variants"])
        self.assertNotIn("ROCmFP4_STRIX_LEAN", model["variants"])
        self.assertIn("Q4_K_M", model["variants"])
        self.assertEqual(model["run_config"]["draft_n"], 0)
        self.assertEqual(model["run_config"]["draft_p"], 0.0)
        self.assertFalse(model["run_config"]["mtp_enabled"])

if __name__ == "__main__":
    unittest.main()
