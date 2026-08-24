import unittest
from unittest import mock
from pathlib import Path

from halofpx.engine_manager import build_cache_args, get_cache_profile, get_amd_env, EngineManager


class CacheProfileTests(unittest.TestCase):
    def test_32gb_profile(self):
        self.assertEqual(
            get_cache_profile(32),
            {"name": "32GB", "cache_ram_mib": 8192, "ctx_checkpoints": 4},
        )

    def test_64gb_profile(self):
        self.assertEqual(
            get_cache_profile(64),
            {"name": "64GB", "cache_ram_mib": 16384, "ctx_checkpoints": 8},
        )

    def test_128gb_profile(self):
        self.assertEqual(
            get_cache_profile(128),
            {"name": "128GB", "cache_ram_mib": 32768, "ctx_checkpoints": 16},
        )

    def test_engine_environment_function_is_imported(self):
        self.assertTrue(callable(get_amd_env))

    def test_128gb_cache_command(self):
        profile = get_cache_profile(128)
        profile.update({"cache_reuse": 256, "checkpoint_every": 4096})
        args = build_cache_args(profile, Path("/tmp/slots"), mmap_enabled=False, mlock=True)
        self.assertEqual(args[args.index("-cram") + 1], "32768")
        self.assertEqual(args[args.index("-ctxcp") + 1], "16")
        self.assertIn("--no-mmap", args)
        self.assertIn("--cont-batching", args)
        self.assertIn("--kv-unified", args)
        self.assertIn("--mlock", args)

    @mock.patch("halofpx.engine_manager.urllib.request.urlopen")
    @mock.patch("halofpx.engine_manager.subprocess.Popen")
    def test_auto_optimization_enables_both_mtp_and_prompt_cache(self, mock_popen, mock_urlopen):
        mock_resp = mock.Mock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        mock_proc = mock.Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        manager = EngineManager()
        res = manager.load_model("qwen38-27b", optimization_mode="auto")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["optimization_mode"], "hybrid")

        cmd = mock_popen.call_args[0][0]
        self.assertIn("--spec-type", cmd)
        self.assertIn("draft-mtp", cmd)
        self.assertIn("-ctxcp", cmd)
        self.assertIn("--cache-prompt", cmd)

        manager.unload_model()


if __name__ == "__main__":
    unittest.main()
