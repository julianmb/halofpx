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


class ShardedRegistry(FakeRegistry):
    def get_model(self, model_id):
        if model_id == "shard-model":
            return {
                "model_id": model_id,
                "hf_repo": "owner/model",
                "default_variant": "Q4",
                "variants": {
                    "Q4": {
                        "filename": "sub/model-00001-of-00002.gguf",
                        "sha256": "",
                    }
                },
            }
        return super().get_model(model_id)


class ShardedPullTests(unittest.TestCase):
    def test_expand_shards(self):
        self.assertEqual(ModelManager._expand_shards("model.gguf"), ["model.gguf"])
        self.assertEqual(
            ModelManager._expand_shards("model-00001-of-00003.gguf"),
            [
                "model-00001-of-00003.gguf",
                "model-00002-of-00003.gguf",
                "model-00003-of-00003.gguf",
            ],
        )
        self.assertEqual(
            ModelManager._expand_shards("Q4_K_M/Ling-3.0-flash-Q4_K_M-00001-of-00002.gguf"),
            [
                "Q4_K_M/Ling-3.0-flash-Q4_K_M-00001-of-00002.gguf",
                "Q4_K_M/Ling-3.0-flash-Q4_K_M-00002-of-00002.gguf",
            ],
        )

    def test_pull_sharded_variant_downloads_all_shards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = ModelManager(ShardedRegistry())
            downloaded = []

            def download(repo_id, filename, target_dir):
                downloaded.append((repo_id, filename))
                path = target_dir / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")
                return path

            with patch("halofpx.model_manager.ROOT_DIR", root), patch.object(
                manager, "_download_file", side_effect=download
            ):
                result = manager.pull_model("shard-model")

            self.assertEqual(result["status"], "success")
            self.assertEqual(
                downloaded,
                [
                    ("owner/model", "sub/model-00001-of-00002.gguf"),
                    ("owner/model", "sub/model-00002-of-00002.gguf"),
                ],
            )
            self.assertEqual(len(result["files"]), 2)
            self.assertEqual(Path(result["local_path"]).name, "model-00001-of-00002.gguf")
            self.assertEqual(result["size_gib"], 0.0)


class ShardedRegistry(FakeRegistry):
    def get_model(self, model_id):
        if model_id == "shard-model":
            return {
                "model_id": model_id,
                "hf_repo": "owner/model",
                "default_variant": "Q4",
                "variants": {
                    "Q4": {
                        "filename": "sub/model-00001-of-00002.gguf",
                        "sha256": "",
                    }
                },
            }
        return super().get_model(model_id)


class ShardedPullTests(unittest.TestCase):
    def test_expand_shards(self):
        self.assertEqual(ModelManager._expand_shards("model.gguf"), ["model.gguf"])
        self.assertEqual(
            ModelManager._expand_shards("model-00001-of-00003.gguf"),
            [
                "model-00001-of-00003.gguf",
                "model-00002-of-00003.gguf",
                "model-00003-of-00003.gguf",
            ],
        )
        self.assertEqual(
            ModelManager._expand_shards("Q4_K_M/Ling-3.0-flash-Q4_K_M-00001-of-00002.gguf"),
            [
                "Q4_K_M/Ling-3.0-flash-Q4_K_M-00001-of-00002.gguf",
                "Q4_K_M/Ling-3.0-flash-Q4_K_M-00002-of-00002.gguf",
            ],
        )

    def test_pull_sharded_variant_downloads_all_shards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = ModelManager(ShardedRegistry())
            downloaded = []

            def download(repo_id, filename, target_dir):
                downloaded.append((repo_id, filename))
                path = target_dir / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")
                return path

            with patch("halofpx.model_manager.ROOT_DIR", root), patch.object(
                manager, "_download_file", side_effect=download
            ):
                result = manager.pull_model("shard-model")

            self.assertEqual(result["status"], "success")
            self.assertEqual(
                downloaded,
                [
                    ("owner/model", "sub/model-00001-of-00002.gguf"),
                    ("owner/model", "sub/model-00002-of-00002.gguf"),
                ],
            )
            self.assertEqual(len(result["files"]), 2)
            self.assertEqual(Path(result["local_path"]).name, "model-00001-of-00002.gguf")
            self.assertEqual(result["size_gib"], 0.0)


class ShardedRegistry(FakeRegistry):
    def get_model(self, model_id):
        if model_id == "shard-model":
            return {
                "model_id": model_id,
                "hf_repo": "owner/model",
                "default_variant": "Q4",
                "variants": {
                    "Q4": {
                        "filename": "sub/model-00001-of-00002.gguf",
                        "sha256": "",
                    }
                },
            }
        return super().get_model(model_id)


class ShardedPullTests(unittest.TestCase):
    def test_expand_shards(self):
        self.assertEqual(ModelManager._expand_shards("model.gguf"), ["model.gguf"])
        self.assertEqual(
            ModelManager._expand_shards("model-00001-of-00003.gguf"),
            [
                "model-00001-of-00003.gguf",
                "model-00002-of-00003.gguf",
                "model-00003-of-00003.gguf",
            ],
        )
        self.assertEqual(
            ModelManager._expand_shards("Q4_K_M/Ling-3.0-flash-Q4_K_M-00001-of-00002.gguf"),
            [
                "Q4_K_M/Ling-3.0-flash-Q4_K_M-00001-of-00002.gguf",
                "Q4_K_M/Ling-3.0-flash-Q4_K_M-00002-of-00002.gguf",
            ],
        )

    def test_pull_sharded_variant_downloads_all_shards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = ModelManager(ShardedRegistry())
            downloaded = []

            def download(repo_id, filename, target_dir):
                downloaded.append((repo_id, filename))
                path = target_dir / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")
                return path

            with patch("halofpx.model_manager.ROOT_DIR", root), patch.object(
                manager, "_download_file", side_effect=download
            ):
                result = manager.pull_model("shard-model")

            self.assertEqual(result["status"], "success")
            self.assertEqual(
                downloaded,
                [
                    ("owner/model", "sub/model-00001-of-00002.gguf"),
                    ("owner/model", "sub/model-00002-of-00002.gguf"),
                ],
            )
            self.assertEqual(len(result["files"]), 2)
            self.assertEqual(Path(result["local_path"]).name, "model-00001-of-00002.gguf")
            self.assertEqual(result["size_gib"], 0.0)


if __name__ == "__main__":
    unittest.main()
